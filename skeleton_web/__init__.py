#!/usr/bin/env python3
"""The SKELETON web edition, as a package.

`SKELETON_WEB.py` at the repo root is the entry point; everything behind it
lives here.  Each module owns one thing, and each cluster of shared state is
owned by one object rather than by module-level globals:

    screen      pty output -> the text the terminal actually showed
    workspace   the notes tabs, their channels and their work folders
    shell       a login shell on a pty, and the registry of them
    streams     the SSE fan-out, and the one-connection-per-browser multiplexer
    introspect  the bridge to tools/module_introspect.py
    runs        the per-tab run history
    desktop     the tester's X session: where a browser window goes
    views/      the Flask blueprints, one per group of routes

Services holds one of each and is handed to every blueprint, so a route reaches
its collaborators through an object it was given rather than through a global.
Views depend on services; services never depend on views.

This is launcher-level only.  The `imports2/` modules stay standalone
copy-paste scripts by design - they never import any of it.
"""
import atexit
import signal

from flask import Flask

from .desktop import Desktop
from .introspect import ModuleIntrospector
from .runs import RunLog
from .settings import WEB_DIR
from .shell import TerminalRegistry
from .streams import StreamRegistry
from .workspace import Workspace


class Services:
    """One of everything the routes need, wired together once."""

    def __init__(self):
        # The notes tabs, their channels and their work folders - and the locks
        # that keep several browser tabs and several shells out of each other's
        # output.
        self.workspace = Workspace()
        # The tester's X session: where a module's window or our console goes.
        self.desktop = Desktop()
        # The headless bridge that turns an imports2/ Tk script into a page.
        self.introspect = ModuleIntrospector(self.desktop)
        self.terminals = TerminalRegistry(self.workspace)
        self.streams = StreamRegistry()
        self.runs = RunLog(self.workspace)

    def shutdown(self):
        """Leave no root shell or pty behind."""
        self.streams.shutdown()      # let the SSE generators return first
        self.terminals.shutdown()


def create_app(start_background=True):
    """The Flask app, with every blueprint registered against one Services.

    `start_background=False` builds the app without the reaper thread or the
    shutdown hooks - for rendering a page in a test client, where neither has
    anything to do.
    """
    app = Flask(__name__, static_folder=WEB_DIR, static_url_path="/web")
    svc = Services()
    app.extensions["skeleton"] = svc

    from . import views                       # after svc: views import services
    for module in views.ALL:
        app.register_blueprint(module.blueprint(svc))

    if start_background:
        svc.terminals.start_reaper()
        atexit.register(svc.shutdown)

        def on_signal(signum, _frame):
            """atexit alone leaves root shells behind on SIGTERM (systemctl
            stop, a kill from a script) - only SIGINT from the terminal ever
            reached it."""
            svc.shutdown()
            raise SystemExit(128 + signum)

        try:                          # only the main thread may install these
            signal.signal(signal.SIGTERM, on_signal)
        except (ValueError, OSError):
            pass
    return app
