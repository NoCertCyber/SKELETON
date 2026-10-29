#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# The SKELETON launcher.  A single-page site: the notes pane (fed by
# working/working_file.txt), the NEW / TIME / SAVE / LOAD / Insert File
# actions, Find my IP / Change my IP / OPEN PORT, and the three-column
# stage -> module -> glossary browser with a search box, RUN MODULE,
# NEW Terminal and a run history.
#
# "RUN MODULE" opens the module in a new browser tab as its own web page
# (/module/<name>) rather than spawning its Tk window: tools/module_introspect.py
# loads imports2/<name>.py head-less, and this server serves its cheatsheet,
# input fields and buttons.  Its output pane is a real shell - the same
# pty-backed terminal the "NEW Terminal" button opens - so pressing a button
# fills the fields, invokes the module's RUN_* callback, intercepts the shell
# command it would have handed to gnome-terminal and types it into that shell.
# The output therefore lands somewhere you can keep working: answer a password
# prompt, Ctrl-C it, then run your own follow-up commands against what it found.
#
# "NEW Terminal" opens /terminal in a new tab: the same shell on a page of its
# own, running each command on the server (in place of gnome-terminal) and
# copying the command and its output to the notes pane with a timestamp.
#
# This file is the entry point and nothing else - the server itself is the
# skeleton_web package, one module per job, and its create_app() wires them
# together.  Start here and follow the imports.
#
# Bind to localhost only unless you know what you are exposing - the API runs
# system commands (ifconfig, iptables, and whatever a module builds) by design.
#
#   sudo python3 SKELETON_WEB.py                 # port 80, localhost
#   SKELETON_WEB_HOST=0.0.0.0 SKELETON_WEB_PORT=8080 python3 SKELETON_WEB.py
#   SKELETON_WEB_OPEN=0 python3 SKELETON_WEB.py   # no browser on start-up
#
# Once it is listening it opens the console on the left of the screen, sized to
# match the browser window already open, leaving room for the terminal it was
# started from.
import os
import threading

from config import WORK_USER, WORKING_DIR, handing_back, reclaim
from skeleton_web import create_app
from skeleton_web.settings import HOST, OPEN_BROWSER, PORT

# Module scope, not inside main(): tools/skeleton_check.py imports this file and
# renders the pages through app.test_client() to check the JavaScript they
# serve.
app = create_app()


def main():
    desktop = app.extensions["skeleton"].desktop
    print("SKELETON_WEB on http://{}:{}  (working dir: {})".format(
        HOST, PORT, WORKING_DIR))
    if handing_back():
        # Root drives the tools, but the output is the tester's.  Take one
        # pass over whatever an earlier run left behind; from here the poll
        # tick and config's watcher keep it that way.
        handed = reclaim()
        print("work folder -> {} ({} path{} handed back)".format(
            WORK_USER, handed, "" if handed == 1 else "s"))
    if PORT < 1024 and os.geteuid() != 0:
        print("note: binding port {} needs root - try  "
              "sudo python3 SKELETON_WEB.py".format(PORT))
    if desktop.display:
        print("module windows -> DISPLAY={}{}".format(
            desktop.display,
            "  XAUTHORITY=" + desktop.xauthority if desktop.xauthority
            else "  (no XAUTHORITY found)"))
    else:
        print("no DISPLAY available - module actions that open a window will "
              "report that they cannot")
    if OPEN_BROWSER and desktop.display:
        # The console cannot load until app.run() is listening, so the opener
        # waits on the socket from a thread of its own.
        threading.Thread(target=desktop.open_when_up, args=(HOST, PORT),
                         daemon=True).start()
    app.run(host=HOST, port=PORT, threaded=True)


if __name__ == "__main__":
    main()
