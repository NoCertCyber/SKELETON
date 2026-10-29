"""The web terminal: one pty-backed login shell per browser tab.

Each terminal tab owns a persistent shell on the server, keyed by a
client-generated `sid` kept in sessionStorage so a reload reattaches to the
same shell rather than starting another.  Output streams to the browser over
SSE (base64 framed, so raw control bytes and partial UTF-8 survive);
keystrokes, resizes and Ctrl-C come back as small POSTs.  That is what lets
`nc -lvnp`, `ssh`, `msfconsole` and reverse shells work where the old one-shot
subprocess.run could not.

A cleaned, line-buffered transcript is copied to the chosen notes tab (the
"record" checkbox in the page header).
"""
import base64
import queue
import re
from datetime import datetime

from flask import Blueprint, Response, abort, jsonify, render_template, request

from .. import screen, streams
from ..settings import MAIN_TAB

SSE_HEADERS = {
    "Cache-Control": "no-cache, no-transform",
    "X-Accel-Buffering": "no",
    "Connection": "keep-alive",
}


def blueprint(svc):
    bp = Blueprint("terminal", __name__)

    @bp.get("/terminal")
    def terminal_page():
        """A real browser-tab terminal (xterm.js + a pty-backed shell on the
        server), the web stand-in for the launcher's gnome-terminal."""
        return render_template("terminal.html")

    @bp.get("/api/terminal/stream")
    def api_terminal_stream():
        """SSE: replay this sid's scrollback, then stream live pty output.

        The fallback for a browser with no SharedWorker; /api/terminal/multi is
        what the pages normally use.
        """
        sid = request.args.get("sid", "")
        tab = request.args.get("tab") or MAIN_TAB
        record = request.args.get("record", "1") != "0"
        if not sid:
            abort(400)
        sh = svc.terminals.get(sid, tab, record=record)
        # The page sends its current notes-tab and record settings on every
        # attach, but they used to be honoured only when the shell was first
        # created.  A reload onto a live shell therefore left the page showing
        # one destination while the server recorded to another - the operator's
        # output filed under the wrong tab, with the UI insisting otherwise.
        sh.tab = svc.workspace.resolve(tab)
        sh.record = record

        def gen():
            # attach() inside the generator, not before it: a response that is
            # never iterated (client gone between request and stream) otherwise
            # leaves its queue in sh.subs, and a shell with a phantom subscriber
            # never looks idle, so the reaper never retires it.
            q, snap = sh.attach()
            try:
                yield "retry: 1500\n\n"
                if snap:
                    yield streams.sse(snap)
                while True:
                    try:
                        chunk = q.get(timeout=15)
                    except queue.Empty:
                        q.flush_dropped()   # caught up: say what was missed
                        yield ": keep-alive\n\n"
                        continue
                    if chunk is None:
                        yield "event: exit\ndata: \n\n"
                        break
                    yield streams.sse(chunk)
                    if q.q.empty():
                        q.flush_dropped()
            finally:
                sh.detach(q)

        return Response(gen(), mimetype="text/event-stream", headers=SSE_HEADERS)

    @bp.get("/api/terminal/multi")
    def api_terminal_multi():
        """Every terminal this browser has open, on one SSE connection.

        Output frames are `<sid> <base64>`; an `exit` event carries `<sid>
        <token>` - which terminal, and which of the shells that have held it,
        since "restart shell" gives one sid a second shell and the dead one's
        sentinel can arrive after the page has attached to its replacement.
        A `ready` event goes out first and again after
        every reconnect, which is the browser's cue to (re-)subscribe the
        terminals it is showing: an EventSource that drops and comes back finds
        nothing subscribed on this side, and the scrollback replay that
        subscribing performs is what makes the gap invisible.
        """
        name = streams.safe_sid(request.args.get("stream", ""))
        if not name:
            abort(400)

        def gen():
            # open() inside the generator, not before it: a response that is
            # never iterated (the client gone between request and stream)
            # otherwise leaves a MultiStream registered under this name with
            # nothing left to close it.  /api/terminal/stream attaches inside
            # its generator for the same reason.
            stream = svc.streams.open(name)   # retires whatever held this name
            try:
                yield "retry: 1500\n\n"
                yield "event: ready\ndata: \n\n"
                while True:
                    try:
                        sid, chunk, token = stream.q.get(timeout=15)
                    except queue.Empty:
                        stream.flush_dropped()   # caught up: say what was missed
                        yield ": keep-alive\n\n"
                        continue
                    if sid is None:                   # this stream is retired
                        break
                    if chunk is None:
                        yield "event: exit\ndata: " + sid + " " + token + "\n\n"
                    else:
                        yield ("data: " + sid + " "
                               + base64.b64encode(chunk).decode("ascii") + "\n\n")
                        if stream.q.empty():
                            stream.flush_dropped()
            finally:
                svc.streams.close(name, stream)

        return Response(gen(), mimetype="text/event-stream", headers=SSE_HEADERS)

    @bp.post("/api/terminal/multi/sub")
    def api_terminal_multi_sub():
        """Put one sid's shell on an open multiplexed stream, starting the shell
        if it is not running yet, and replay its scrollback down that stream."""
        body = request.json or {}
        sid = streams.safe_sid(body.get("sid"))
        stream = svc.streams.get(body.get("stream"))
        if not sid or stream is None:
            # The browser reconnects and re-subscribes on its own; say which of
            # the two it was rather than aborting into HTML.
            return jsonify(ok=False, error="no such stream"), 409
        tab = body.get("tab") or MAIN_TAB
        record = bool(body.get("record", True))
        sh = svc.terminals.get(sid, tab, record=record)
        sh.tab = svc.workspace.resolve(tab)   # every attach, as /stream does
        sh.record = record
        if not stream.add(sid, sh):
            return jsonify(ok=False, error="stream closed"), 409
        # Which shell the caller is now attached to.  An exit for any other one
        # is a shell it has already replaced, and acting on it would leave the
        # page deaf to the shell it actually has.
        return jsonify(ok=True, token=sh.token)

    @bp.post("/api/terminal/multi/unsub")
    def api_terminal_multi_unsub():
        """Take one sid off the stream - that page has gone.  The shell itself
        stays: reattaching to it after a reload is what the sid is for."""
        body = request.json or {}
        stream = svc.streams.get(body.get("stream"))
        if stream is not None:
            stream.drop(streams.safe_sid(body.get("sid")))
        return jsonify(ok=True)

    @bp.post("/api/terminal/input")
    def api_terminal_input():
        body = request.json or {}
        sh = svc.terminals.get(body.get("sid", ""), body.get("tab") or MAIN_TAB,
                               create=False)
        if not sh or not sh.alive:
            return jsonify(ok=False, error="no session"), 404
        sh.write(body.get("data", ""))
        return jsonify(ok=True)

    @bp.post("/api/terminal/resize")
    def api_terminal_resize():
        body = request.json or {}
        sh = svc.terminals.get(body.get("sid", ""), body.get("tab") or MAIN_TAB,
                               create=False)
        if not sh:
            return jsonify(ok=False), 404
        try:
            sh.resize(int(body.get("rows", 24)), int(body.get("cols", 80)))
        except (TypeError, ValueError):
            return jsonify(ok=False), 400
        return jsonify(ok=True)

    @bp.post("/api/terminal/config")
    def api_terminal_config():
        """Update the notes tab this shell records to, and whether it records."""
        body = request.json or {}
        sh = svc.terminals.get(body.get("sid", ""), body.get("tab") or MAIN_TAB,
                               create=False)
        if not sh:
            return jsonify(ok=False), 404
        if "tab" in body and body["tab"]:
            sh.tab = svc.workspace.resolve(body["tab"])
        if "record" in body:
            sh.record = bool(body["record"])
        return jsonify(ok=True, record=sh.record, tab=sh.tab)

    @bp.post("/api/terminal/kill")
    def api_terminal_kill():
        """Kill this sid's shell (the next /stream starts a fresh one)."""
        sh = svc.terminals.pop((request.json or {}).get("sid", ""))
        if sh:
            sh.kill()
        return jsonify(ok=True)

    @bp.get("/api/terminal/log")
    def api_terminal_log():
        """Everything this shell has printed so far, as a downloadable file."""
        sh = svc.terminals.peek(request.args.get("sid", ""))
        if sh is None:
            abort(404)
        with sh.lock:
            body = screen.clean_output(bytes(sh.scrollback))
        # A module page names its own log, so a folder of them says which module
        # each one came from rather than four files called terminal-*.txt.
        name = re.sub(r"[^A-Za-z0-9_-]", "",
                      request.args.get("name", "")) or "terminal"
        return Response(body, mimetype="text/plain; charset=utf-8", headers={
            "Content-Disposition": 'attachment; filename="{}-{}.txt"'.format(
                name[:64], datetime.now().strftime("%Y%m%d-%H%M%S")),
        })

    return bp
