#!/usr/bin/env python3
"""Where the web edition's dials live.

Paths that describe the tree are config.py's business; these are the ones that
describe the *server* - what it binds, what it polls, how much of a terminal it
keeps.  All of them are read once, at import, so a value is the same everywhere
it is used.
"""
import os

from config import SKELETON_ROOT, TOOLS_DIR, WORKING_DIR

# The headless bridge to the imports2/ modules.
INTROSPECT = str(TOOLS_DIR / "module_introspect.py")

HOST = os.environ.get("SKELETON_WEB_HOST", "127.0.0.1")
PORT = int(os.environ.get("SKELETON_WEB_PORT", "80"))

# Vendored xterm.js and the page's own css/js, served at /web.
WEB_DIR = str(SKELETON_ROOT / "web")

# The built-in notes tab and the channel file behind it.
MAIN_TAB = "main"
FILE_PATH = str(WORKING_DIR / "working_file.txt")
TABS_PATH = str(WORKING_DIR / "notes_tabs.json")
POLL_INTERVAL_MS = 1000

TERM_SCROLLBACK = 256 * 1024      # bytes replayed to a (re)attaching stream
TERM_IDLE_TIMEOUT = 3600          # reap a shell with no client attached this long

# On start-up the server opens its own console down the left of the screen.
# SKELETON_WEB_OPEN=0 keeps the browser shut (headless boxes, systemd units).
OPEN_BROWSER = os.environ.get("SKELETON_WEB_OPEN", "1").lower() not in ("0", "no", "off")
