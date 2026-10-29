#!/usr/bin/env python3
"""A login shell on a pty, and the registry of the ones that are running.

One PtyShell backs every terminal in the web edition: the /terminal page and
the terminal pane on each module page alike.  A module run is not a separate
process - the command is typed into this shell - so its output stays on screen,
its prompts can be answered, and the operator can carry on working in the same
session once it has finished.  That is also why so much of this file is about
the *transcript*: the only record of what ran is what the shell echoed back.
"""
import fcntl
import itertools
import os
import pty
import signal
import struct
import termios
import threading
import time

import skeleton_core as core

from . import screen, streams
from .settings import TERM_IDLE_TIMEOUT, TERM_SCROLLBACK

# One per shell ever started here.  A sid outlives the shell behind it -
# "restart shell" kills one and opens another under the same sid - so a frame
# tagged only with the sid cannot say which shell it came from, and the dead
# one's exit sentinel used to arrive after the page had already attached to its
# replacement: the page then believed the new shell had exited too, stopped
# reading, and showed a live terminal as a dead one.
_TOKENS = itertools.count(1)


class PtyShell:
    """A login shell on a pty; fan-out of its output to SSE subscribers.

    One of these backs every terminal in the web edition: the /terminal page
    and the terminal pane on each module page alike.  A module run is not a
    separate process - the command is typed into this shell - so its output
    stays on screen, its prompts can be answered, and the operator can carry on
    working in the same session once it has finished.
    """

    def __init__(self, workspace, sid, tab, record=True):
        self.workspace = workspace
        self.sid = sid
        self.tab = tab
        self.record = record
        # Which shell this is, as against which terminal tab it belongs to.
        self.token = "t{}".format(next(_TOKENS))
        self.alive = True
        self.lock = threading.Lock()
        self.subs = set()                 # of queue.Queue
        self.scrollback = bytearray()
        self.last_attach = time.time()
        self._notes_buf = bytearray()     # pending pty output, split on \n
        self._in_line = bytearray()       # keys typed since the last Enter
        self._in_esc = 0                  # 0 none, 1 saw ESC, 2 inside CSI/SS3
        self._in_paste = False            # between ESC[200~ and ESC[201~
        self._pending_cmd = ""            # typed line waiting for the shell to echo it
        self._pending_lock = threading.Lock()
        self._await_echo = False          # Enter is in, its echo is not out yet
        self._repainting = False          # a command line was just drawn on screen
        self._echo_once = ""              # one bare echo of it left to swallow

        cwd = self.workspace.folder(self.workspace.resolve(tab))
        self.cwd = cwd
        env = core.session_env(base=os.environ)
        env["TERM"] = "xterm-256color"
        env.setdefault("LANG", "C.UTF-8")
        env["SKELETON_WEB"] = "1"
        shell = env.get("SHELL") or "/bin/bash"
        self.argv = [shell, "-i"]

        pid, fd = pty.fork()
        if pid == 0:                       # child
            try:
                os.chdir(cwd)
            except OSError:
                pass
            # The tools this shell runs need our privileges; the files they
            # drop in the work folder do not.  A group-writable umask means
            # output lands usable by the folder's owner from the moment it is
            # created - the sweep that hands it over follows a few seconds
            # behind, and a half-written capture should not be locked away in
            # the meantime.
            os.umask(0o002)
            try:
                os.execvpe(self.argv[0], self.argv, env)
            except OSError:
                os.execvpe("/bin/sh", ["/bin/sh", "-i"], env)
            os._exit(127)

        self.pid = pid
        self.fd = fd
        # Every line this shell puts in the notes is tagged with these: the id
        # says which session wrote it, the label heads the block when the tab
        # changes hands.  A module run re-labels the shell it is typed into.
        self.note_src = "sh:{}:{}".format(id(self), pid)
        # The pid is in the label because two terminals on one notes tab are
        # otherwise two identical headers, and the point of the header is to
        # say which of them wrote the lines under it.
        self.base_label = "terminal session ({}, pid {})".format(shell, pid)
        self.note_label = self.base_label
        self.note_run = False             # next accepted line is a module's command
        if self.record:
            self.workspace.append(core.stamp(" - " + self.note_label), tab, self.note_src)
        threading.Thread(target=self._pump, daemon=True).start()

    # -- server -> browser --------------------------------------------------
    def _pump(self):
        try:
            self._read_loop()
        finally:
            # The only place this fd is closed: nothing else is reading it, so
            # the number cannot be recycled under a blocked reader.
            try:
                os.close(self.fd)
            except OSError:
                pass

    def _read_loop(self):
        while True:
            try:
                data = os.read(self.fd, 65536)
            except OSError:
                break
            if not data:
                break
            with self.lock:
                self.scrollback += data
                self._trim_scrollback()
                subs = list(self.subs)
            for sub in subs:
                sub.put(data)
            self._to_notes(data)
        self.alive = False
        try:                              # reap the child so it leaves no zombie
            os.waitpid(self.pid, 0)
        except OSError:                   # ChildProcessError is an OSError
            pass
        with self.lock:
            subs = list(self.subs)
        for sub in subs:
            sub.close()                   # sentinel: process exited
        self._flush_notes()

    def _to_notes(self, data):
        """Copy a readable transcript of the pty *output* to the notes tab:
        ANSI stripped, \\r redraw frames collapsed, prompt lines and the shell's
        own echo of the just-typed command dropped, consecutive dupes removed."""
        if not self.record:
            return
        self._notes_buf += data
        while True:
            nl = self._notes_buf.find(b"\n")
            if nl < 0:
                break
            line, self._notes_buf = self._notes_buf[:nl], self._notes_buf[nl + 1:]
            self._emit_notes_line(line)
        if len(self._notes_buf) > 4096:              # runaway line with no \n
            self._emit_notes_line(bytes(self._notes_buf))
            self._notes_buf = bytearray()

    def _emit_notes_line(self, raw):
        """One pty line -> the notes: what the terminal ended up showing.

        Splitting on \r and keeping the last frame does not recover that.  A
        shell redraws the line it is reading - zsh moves the cursor back over
        it on every keystroke, wraps it a screen-width at a time once it is too
        long, and paints it once more in its syntax-highlighting colours when
        Enter is pressed - so the frames arrive interleaved with the text they
        overwrite.  Flattened, they ran together ("echo helloecho"); a repaint
        that ended in \r flattened to nothing at all, which is how a command
        recalled with the up-arrow left no trace in the transcript.

        So a redraw is replayed onto a cursor - with the renderer the
        downloaded log already uses - and only two things are taken from it:
        the command line the shell accepted, and nothing else.  Everything that
        is not a redraw is command output, and goes through as it arrives."""
        text = raw.decode("utf-8", "replace")
        echoing = bool(self._pending_cmd or self._await_echo)
        repaint = bool(screen.REPAINT_RE.search(text)) or bool(
            screen.REDRAW_RE.search(text)
            and (self._in_line or self._repainting or echoing))
        if repaint or echoing:
            for row in screen.render_screen(text).split("\n"):
                row = row.rstrip()
                # Only once Enter is in: the same line is drawn a dozen times
                # while it is being typed, and none of those drafts ran.
                if row and echoing:
                    hit = screen.PROMPT_CMD_RE.match(row)
                    if hit:
                        self._log_cmd(hit.group("cmd").strip())
                        return                # the rest of this is that repaint
                if not repaint:
                    self._emit_notes_text(row)
            return
        self._emit_notes_text(screen.flatten(text))

    def _emit_notes_text(self, text):
        if not text:
            return
        if text == self._echo_once:           # a raw pty echoing back the typing
            self._echo_once = ""
            return
        self._echo_once = ""
        if screen.PROMPT_RE.match(text):            # a prompt on its own
            # ...which is the shell saying the last command finished, so
            # whatever queued up behind it can go through now.
            self.workspace.finished(self.tab, self.note_src)
            return
        typed = self._take_pending()
        if typed:
            # Nothing echoed this line back behind a prompt, so the keystrokes
            # are all there is: a raw `nc` session, a program reading its own
            # input.  Log them before the output they produced.
            self._log_cmd(typed)
            if text == typed:
                self._echo_once = ""
                return
        self._await_echo = False
        self._repainting = False
        self.workspace.append(text + "\n", self.tab, self.note_src, self.note_label)

    def _log_cmd(self, cmd):
        """Write one `$ <command>` line.

        Repeats are kept - running the same command three times is three
        entries - so nothing here drops a line for being identical to the one
        before it.  That is what used to swallow the second and third run of a
        command whose output was a single line."""
        twice = screen.DOUBLED_RE.match(cmd)
        if twice:
            cmd = twice.group(1)
        typed = self._take_pending()
        if typed and typed.startswith(cmd) and len(typed) > len(cmd):
            # The echo was cut short: a long command wraps at the terminal's
            # width and only its first row reached us as a line.  What was
            # typed is the whole of it.
            cmd = typed
        elif typed and cmd.startswith(typed):
            rest = cmd[len(typed):].strip()
            if rest and rest in typed:        # the tail drawn over itself again
                cmd = typed
        if not cmd:
            return
        self._echo_once = cmd
        self._await_echo = False
        self._repainting = True
        # From here to the prompt that ends it, this command holds the tab:
        # its output goes down in one piece and anything else writing to the
        # same notes waits its turn.
        self.workspace.started(self.note_src)
        self.workspace.append("$ " + cmd + "\n", self.tab, self.note_src, self.note_label)

    def _take_pending(self):
        """The last typed line, if it is still waiting for the shell to echo it."""
        with self._pending_lock:
            cmd, self._pending_cmd = self._pending_cmd, ""
        return cmd

    def _flush_notes(self):
        if self._notes_buf:
            self._emit_notes_line(bytes(self._notes_buf))
            self._notes_buf = bytearray()
        typed = self._take_pending()
        if typed:
            self._log_cmd(typed)
        # The shell is gone: a command of its still holding the tab would hold
        # it until the backstop expired, with nobody left to give it back.
        self.workspace.finished(self.tab, self.note_src)

    def _record_input(self, data):
        """Follow the keystrokes, and hold each finished line for the echo.

        What the operator typed is not always what ran - zle fills in history,
        autosuggestions and completions that never pass through here - so the
        line is handed to _emit_notes_line to be confirmed against the shell's
        own echo of it.  It is logged from here only when nothing echoes it
        back: what you type into `nc` / `ssh` / a reverse shell."""
        if not self.record:
            return
        i, n = 0, len(data)
        while i < n:
            b = data[i]; i += 1
            if self._in_esc == 1:                     # byte after ESC
                self._in_esc = 2 if b in (0x5b, 0x4f) else 0   # '[' CSI / 'O' SS3
                continue
            if self._in_esc == 2:                     # inside CSI/SS3 -> wait for final byte
                if 0x40 <= b <= 0x7e:
                    self._in_esc = 0
                    tail = bytes(data[max(0, i - 5):i])
                    if tail == b"[200~":
                        self._in_paste = True
                    elif tail == b"[201~":
                        self._in_paste = False
                continue
            if b == 0x1b:
                self._in_esc = 1
            elif b in (0x0d, 0x0a):                   # Enter -> a full line
                if self._in_paste:                    # newline inside a paste is literal
                    self._in_line.append(0x20)
                    continue
                line = bytes(self._in_line).decode("utf-8", "replace").strip()
                self._in_line.clear()
                # Held, not logged: the shell is about to echo the line it
                # actually accepted, which - unlike these keystrokes - includes
                # whatever zle filled in (history, autosuggestion, completion).
                # _emit_notes_line hands it back if no echo ever arrives.
                stale = self._take_pending()
                if stale:
                    self._log_cmd(stale)
                self._await_echo = True
                if self.note_run:         # the command a module page just sent
                    self.note_run = False
                elif line:                # the operator's own command: plain session again
                    self.note_label = self.base_label
                if line:
                    with self._pending_lock:
                        self._pending_cmd = line
            elif b in (0x7f, 0x08):                   # backspace / DEL
                if self._in_line:
                    self._in_line.pop()
            elif b in (0x03, 0x15, 0x0c) and not self._in_paste:  # Ctrl-C / Ctrl-U / Ctrl-L
                self._in_line.clear()
            elif b >= 0x20:
                self._in_line.append(b)
        if len(self._in_line) > 8192:                 # unsubmitted runaway line
            del self._in_line[:-8192]

    # -- browser -> server ------------------------------------------------
    def write(self, data):
        raw = data.encode("utf-8", "replace") if isinstance(data, str) else data
        try:
            self._record_input(raw)
        except Exception:
            pass
        try:
            os.write(self.fd, raw)
        except OSError:
            pass

    def cwd_now(self):
        """The directory this shell is in now - it follows the operator's `cd`."""
        try:
            return os.path.realpath("/proc/{}/cwd".format(self.pid))
        except OSError:
            return ""

    def resize(self, rows, cols):
        try:
            fcntl.ioctl(self.fd, termios.TIOCSWINSZ,
                        struct.pack("HHHH", max(rows, 1), max(cols, 1), 0, 0))
        except OSError:
            pass

    def emit(self, text):
        """Put text on this shell's screen that did not come out of its pty.

        The one-shot run path (a module action a shell line cannot represent -
        opening a browser, starting a server) has no pty of its own, so its
        output would otherwise live only in the page that asked for it and be
        missing from the terminal's log.  Written here it is on the screen and
        in the scrollback, like everything else the terminal shows.
        """
        raw = text.replace("\n", "\r\n").encode("utf-8", "replace")
        with self.lock:
            self.scrollback += raw
            self._trim_scrollback()
            subs = list(self.subs)
        for sub in subs:
            sub.put(raw)

    def _trim_scrollback(self):
        """Drop the oldest bytes once over budget - but only whole lines.

        Trimming to an exact byte count splits UTF-8 code points and escape
        sequences, so the snapshot replayed to a reattaching client could start
        mid-sequence: colour bleeding down the screen, or a first line that
        never arrives.  The Download of that session carried the same hole.
        Caller holds self.lock.
        """
        if len(self.scrollback) <= TERM_SCROLLBACK:
            return
        cut = len(self.scrollback) - TERM_SCROLLBACK
        nl = self.scrollback.find(b"\n", cut)
        if nl != -1 and nl - cut < 8192:      # a line boundary within reach
            cut = nl + 1
        del self.scrollback[:cut]

    def attach(self, sub=None, replay=False):
        """Register a subscriber and hand back the scrollback to replay.

        With replay=True the snapshot is pushed through the subscriber itself,
        while the lock is still held, so that on a multiplexed stream - where
        the frames of every terminal share one queue - live output cannot
        overtake the replay and land in front of it.
        """
        sub = sub if sub is not None else streams.Sub()
        with self.lock:
            self.subs.add(sub)
            self.last_attach = time.time()
            snap = bytes(self.scrollback)
            if replay:
                if snap:
                    sub.put(snap)
                snap = b""
        return sub, snap

    def detach(self, q):
        with self.lock:
            self.subs.discard(q)
            self.last_attach = time.time()

    def kill(self):
        """Signal the shell dead.  The pty fd is *not* closed here.

        _pump sits blocked in os.read() on that fd.  Closing it from another
        thread is undefined, and if the number is then handed to a fresh
        pty.fork() the dead shell's pump reads the new shell's output - one
        terminal's bytes turning up in another's screen and notes tab.  Killing
        the process group instead makes the read return EOF, and _pump closes
        the fd on its way out.
        """
        self.alive = False
        for sg in (signal.SIGHUP, signal.SIGKILL):
            try:
                os.killpg(self.pid, sg)
            except OSError:
                try:
                    os.kill(self.pid, sg)
                except OSError:
                    pass


class TerminalRegistry:
    """Every live shell, keyed by the sid its browser tab generated.

    The sid lives in sessionStorage, so reloading a page reattaches to the same
    shell rather than starting another one - which is what makes a reload
    during an hour-long scan cost nothing.
    """

    def __init__(self, workspace):
        self.workspace = workspace
        self._shells = {}                 # sid -> PtyShell
        self._lock = threading.Lock()

    def get(self, sid, tab, create=True, record=True):
        with self._lock:
            sh = self._shells.get(sid)
            if sh and not sh.alive:
                self._shells.pop(sid, None)
                sh = None
            if sh is None and create:
                sh = self._shells[sid] = PtyShell(self.workspace, sid, tab, record)
            return sh

    def peek(self, sid):
        """The shell for `sid` without starting one."""
        with self._lock:
            return self._shells.get(sid)

    def pop(self, sid):
        """Unregister `sid`'s shell and hand it back, so the caller can kill it."""
        with self._lock:
            return self._shells.pop(sid, None)

    def start_reaper(self):
        threading.Thread(target=self._reap_loop, name="skeleton-term-reaper",
                         daemon=True).start()

    def _reap_loop(self):
        """Retire shells that have died or that nobody has watched for an hour.

        Everything here runs under the lock, and a shell is only unregistered if
        the sid still points at *that* object: get() replaces a dead shell with
        a live one under the same sid, and an unlocked pop used to delete the
        replacement instead - leaving a root shell, its pty and its reader
        thread running with nothing able to reach or reap them.
        """
        while True:
            time.sleep(60)
            # Not a shell, but the same once-a-minute housekeeping: a command
            # that never gives its prompt back must not hold a tab's notes for
            # ever.
            self.workspace.sweep_holds()
            now = time.time()
            doomed = []
            with self._lock:
                for sid, sh in list(self._shells.items()):
                    with sh.lock:
                        watched = bool(sh.subs)
                        last = sh.last_attach
                    if not sh.alive or (not watched
                                        and now - last > TERM_IDLE_TIMEOUT):
                        if self._shells.get(sid) is sh:
                            del self._shells[sid]
                            doomed.append(sh)
            for sh in doomed:        # signalling is slow; do it outside the lock
                sh.kill()

    def shutdown(self):
        with self._lock:
            shells = list(self._shells.values())
            self._shells.clear()
        for sh in shells:
            sh.kill()
