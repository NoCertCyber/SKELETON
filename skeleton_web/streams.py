#!/usr/bin/env python3
"""Getting a shell's output to the browser, and sharing one connection to do it.

A browser allows six HTTP/1.1 connections per origin, and every module page and
every /terminal page used to hold one of them open for ever for its own shell's
SSE.  So the sixth tab took the last slot and from then on the console's notes
poll never returned, a seventh page never finished loading, and nothing on
screen said why - the notes pane simply stopped.  In a launcher whose whole
design is one tab per module that is reachable in an ordinary morning's work,
and it fails in the worst way available: silently, in the part of the tool that
is keeping the record.

So the pages no longer stream for themselves.  A SharedWorker
(web/skeleton-stream.js) holds ONE MultiStream on behalf of every SKELETON page
in the browser and hands each page the frames tagged with its own sid.  The
ceiling on how many terminals can be open goes back to being the server's
business, where it belongs.
"""
import base64
import queue
import re
import threading

SID_RE = re.compile(r"[A-Za-z0-9._-]{1,64}\Z")


def safe_sid(value):
    """A client-chosen id, if it is one we can put in a frame header."""
    value = str(value or "")
    return value if SID_RE.match(value) else ""


def sse(payload):
    return "data: " + base64.b64encode(payload).decode("ascii") + "\n\n"


class Sink:
    """A subscriber to one shell's output, and a note of what it missed.

    A fast producer - `nmap -p-`, `gobuster`, `hashcat` - outruns a slow or
    backgrounded browser, and the queue behind it fills.  The transcript and
    the scrollback are written before the fan-out and so stay complete, but the
    *live view* used to discard the overflow without a word, which is the one
    thing an evidence-gathering tool must never do quietly.  Bytes that cannot
    be queued are counted here and announced in the stream as soon as the
    consumer catches up.

    Subclasses say where the bytes actually go: Sub has a queue to itself,
    Tap shares one with every other terminal on a multiplexed stream.
    """

    __slots__ = ("_dropped", "_lock")

    def __init__(self):
        self._dropped = 0
        self._lock = threading.Lock()

    @staticmethod
    def _marker(count):
        return ("\r\n[... {} bytes dropped: output outran this "
                "browser ...]\r\n".format(count)).encode("utf-8")

    def put(self, data):
        with self._lock:
            if self._dropped:
                if not self._offer(self._marker(self._dropped) + data):
                    self._dropped += len(data)
                    return
                self._dropped = 0
                return
            if not self._offer(data):
                self._dropped += len(data)

    def note_dropped(self, count):
        """Bytes this subscriber lost somewhere other than its own put()."""
        with self._lock:
            self._dropped += count

    def flush_dropped(self):
        """Announce what was dropped without waiting for the next bytes.

        The marker used to ride the *next* successful put, so a terminal that
        was starved and then went quiet - its command finished, its prompt
        back - never said what it missed: the operator saw a terminal that had
        simply skipped a command.  The stream calls this the moment its queue
        drains, which is exactly when the consumer has caught up.
        """
        with self._lock:
            if not self._dropped:
                return False
            if not self._offer(self._marker(self._dropped)):
                return False
            self._dropped = 0
            return True

    def close(self):
        """Deliver the exit sentinel even to a subscriber that is backed up.

        Never called with self._lock held - _make_room may have to account the
        frame it evicts back to another subscriber, and that takes a lock of
        its own.
        """
        if not self._offer(None):
            self._make_room()             # the stream is ending; force it in
            self._offer(None)


class Sub(Sink):
    """A subscriber with a queue to itself: one shell, one SSE connection."""

    __slots__ = ("q",)

    def __init__(self, maxsize=2000):
        Sink.__init__(self)
        self.q = queue.Queue(maxsize=maxsize)

    def _offer(self, data):
        try:
            self.q.put_nowait(data)
        except queue.Full:
            return False
        return True

    def _make_room(self):
        try:
            self.q.get_nowait()
        except queue.Empty:
            pass

    def get(self, timeout=None):
        return self.q.get(timeout=timeout)


class Tap(Sink):
    """A subscriber whose bytes go onto a stream shared with other shells.

    Every frame carries the sid it belongs to, so one connection can serve a
    whole browser's worth of terminals.  See MultiStream for why that matters.

    It also carries the token of the shell it came from.  A sid outlives the
    shell behind it - "restart shell" kills one and opens another under the
    same sid - so the sid alone cannot say which of them a frame belongs to.
    """

    __slots__ = ("stream", "sid", "token", "live")

    def __init__(self, stream, sid, token=""):
        Sink.__init__(self)
        self.stream = stream
        self.sid = sid
        self.token = token
        self.live = True

    def _offer(self, data):
        # Once this tap has been replaced, its shell's remaining output - the
        # exit sentinel above all - is somebody else's terminal now.  Swallow
        # it rather than putting it on the stream for the shell that took the
        # sid over.
        if not self.live:
            return True
        return self.stream.offer(self.sid, data, self.token)

    def _make_room(self):
        self.stream.make_room()



class MultiStream:
    """Several shells' output on one SSE connection, each frame tagged.

    The queue is shared, so one terminal flooding it would starve the rest -
    hence Sink's drop accounting is per Tap: a browser that cannot keep up
    with `nmap -p-` in one tab is told what it missed *in that tab*, and the
    others carry on.
    """

    def __init__(self, name, maxsize=8000):
        self.name = name
        self.q = queue.Queue(maxsize=maxsize)
        self.lock = threading.Lock()
        self.taps = {}               # sid -> (Tap, PtyShell)
        self.closed = False

    # -- the queue, as a Tap sees it --------------------------------------
    def offer(self, sid, data, token=""):
        try:
            self.q.put_nowait((sid, data, token))
        except queue.Full:
            return False
        return True

    def make_room(self):
        """Evict the oldest frame so one that must land can.

        Whoever's frame that was is told about it: the queue is shared, so the
        eviction is almost always somebody else's bytes, and dropping those
        unannounced is the one thing this whole file exists to avoid.
        """
        try:
            sid, data, _token = self.q.get_nowait()
        except queue.Empty:
            return
        if data is None:                  # a sentinel carries no output
            return
        with self.lock:
            entry = self.taps.get(sid)
        if entry is not None:
            entry[0].note_dropped(len(data))

    def flush_dropped(self):
        """Let every tap announce what it lost, now that the queue has room."""
        with self.lock:
            taps = [tap for tap, _sh in self.taps.values()]
        for tap in taps:
            tap.flush_dropped()

    # -- membership ---------------------------------------------------------
    def add(self, sid, sh):
        """Put a shell on this stream, its scrollback replayed down it first.

        Taking self.lock and then the shell's is the only order used here: a
        shell's pump copies its subscriber list under its own lock and calls
        put() outside it, so it never wants this one.
        """
        self.drop(sid)
        tap = Tap(self, sid, getattr(sh, "token", ""))
        with self.lock:
            if self.closed:
                return False
            self.taps[sid] = (tap, sh)
            sh.attach(tap, replay=True)
        return True

    def drop(self, sid):
        with self.lock:
            gone = self.taps.pop(sid, None)
        if gone is not None:
            tap, sh = gone
            tap.live = False        # nothing more of that shell's reaches here
            sh.detach(tap)
        return gone is not None

    def shutdown(self):
        """Detach every shell and wake the generator so it can return."""
        with self.lock:
            if self.closed:
                return
            self.closed = True
            taps = list(self.taps.values())
            self.taps.clear()
        for tap, sh in taps:
            tap.live = False
            sh.detach(tap)
        if not self.offer(None, None):    # the sentinel has to land
            self.make_room()
            self.offer(None, None)


class StreamRegistry:
    """The multiplexed streams currently open, one per browser."""

    def __init__(self):
        self._streams = {}           # stream name -> MultiStream
        self._lock = threading.Lock()

    def get(self, name):
        with self._lock:
            return self._streams.get(safe_sid(name))

    def open(self, name):
        """A fresh stream under `name`, retiring whatever held that name.

        A reconnect arrives under the same name as the connection it replaces,
        and the old generator has to be woken so it can return rather than sit
        on a dead socket holding every shell it had attached.
        """
        stream = MultiStream(name)
        with self._lock:
            old = self._streams.get(name)
            self._streams[name] = stream
        if old is not None:
            old.shutdown()
        return stream

    def close(self, name, stream):
        """The generator for `stream` has finished.  Only unregister the name
        if it still points at this one - a reconnect may already have taken
        it."""
        stream.shutdown()
        with self._lock:
            if self._streams.get(name) is stream:
                del self._streams[name]

    def shutdown(self):
        """Detach every shell and let every generator return."""
        with self._lock:
            streams = list(self._streams.values())
            self._streams.clear()
        for stream in streams:
            stream.shutdown()
