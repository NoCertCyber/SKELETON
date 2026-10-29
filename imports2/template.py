#!/usr/bin/env python3
# Scaffold for a new SKELETON module.  Copy to imports2/<stage>_<tool>.py and
# fill in the banner / notes and (for an interactive tool) the input fields and
# the RUN_* function.  The launcher starts each module as its own process.

from tkinter import *
from datetime import datetime
import os
import shlex
import subprocess

# If the module needs the shared working dir or the wordlists, uncomment this
# and import what you need (never hard-code /opt/SKELETON/... in a command):
# import sys
# sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# from config import WORKING_DIR, WORDLIST, NAMES, own
#
# SKELETON runs as root, so anything this module writes itself lands owned by
# root - a file the tester then cannot edit or delete from their own session.
# Call own(path) after writing one.  A file the *tool* writes needs nothing:
# config's watcher hands the work folder back every few seconds.

info = r'''

     ████████╗███████╗███╗   ███╗██████╗ ██╗      █████╗ ████████╗███████╗
     ╚══██╔══╝██╔════╝████╗ ████║██╔══██╗██║     ██╔══██╗╚══██╔══╝██╔════╝
        ██║   █████╗  ██╔████╔██║██████╔╝██║     ███████║   ██║   █████╗
        ██║   ██╔══╝  ██║╚██╔╝██║██╔═══╝ ██║     ██╔══██║   ██║   ██╔══╝
        ██║   ███████╗██║ ╚═╝ ██║██║     ███████╗██║  ██║   ██║   ███████╗
        ╚═╝   ╚══════╝╚═╝     ╚═╝╚═╝     ╚══════╝╚═╝  ╚═╝   ╚═╝   ╚══════╝


   MODULE INFORMATION - cheatsheet text goes here

when to use it
    - template / scaffold for authoring new SKELETON stage modules
    - copy to imports2/<stage>_<tool>.py and customize fields and RUN_* functions

typical commands
    - python3 /opt/SKELETON/imports2/<stage>_<tool>.py

most common use
    - boilerplate starting point providing standard Tkinter layout, LOG, and RUN_in_terminal

pair with
    - tools/skeleton_check.py    verify compliance before committing

gotchas
    - always use shlex.quote() for dynamic values in commands
    - always use os.path.basename() on save-file entry fields
    - never use "file name" or "save-file" in input file labels
    - do not use info += ... with /opt/SKELETON literals (violates check_relocate)

authorisation & reporting
    - scaffold only; ensure target authorization is in place before running active tools
'''

# --- GUI --------------------------------------------------------------------

guibox = Tk()
guibox.title('template  —  <tool> - <purpose>')
guibox.geometry("950x900")


def NEW_Terminal():
    subprocess.call(["gnome-terminal"])


def LOG(cmd):
    stamp = datetime.now().strftime("%d-%b-%Y (%H:%M:%S.%f)")
    text_box.insert('end', "\nTime stamp: {} - {}\n".format(stamp, cmd))
    text_box.yview('end')


# --- running a command ------------------------------------------------------
#
# THE ONE SAFE PATTERN.  Copy it exactly; tools/skeleton_check.py enforces it.
#
#   * every VALUE field (target, user, password, filename, port) goes through
#     shlex.quote() - it must reach the tool as one literal argument;
#   * a free-form "Additional switches" field stays UNQUOTED on purpose, so it
#     can expand to several arguments;
#   * the whole assembled command is then quoted ONCE for the outer shell with
#     shlex.quote(cmd + ' ; exec bash').  Never interpolate into a "..." string
#     inside the gnome-terminal argument - a stray quote in any field breaks
#     out of the outer shell there.
#
# def RUN_tool():
#     cmd = "tool " + shlex.quote(target_entry.get()) + " " + switch_entry.get()
#     RUN_in_terminal(cmd)


def RUN_in_terminal(cmd):
    """Fire `cmd` in its own terminal window and log it.  `cmd` must already
    have had shlex.quote() applied to each of its value fields."""
    subprocess.call(
        ['gnome-terminal -- bash -c ' + shlex.quote(cmd + ' ; exec bash')],
        shell=True,
    )
    LOG(cmd)


# --- field defaults ---------------------------------------------------------
#
# The launcher exports the current engagement target as environment variables,
# so a module pre-fills from whatever the operator set once in the target bar
# and falls back to its own example value when launched standalone:
#
#     target_entry.insert(0, os.environ.get("SKELETON_TARGET", "10.10.10.10"))
#
# SKELETON_TARGET / _URL / _LHOST / _LPORT / _USER / _PASS / _IFACE / _WORDLIST
#
# --- field labels -----------------------------------------------------------
#
# Label your fields from this vocabulary and the web UI auto-fills them from
# the session with no extra wiring (skeleton_core.FIELD_MAP matches on it):
#
#     "Target IP: "                     -> SKELETON_TARGET
#     "Target url / domain: "           -> SKELETON_URL
#     "LHOST yours/listening IP: "      -> SKELETON_LHOST
#     "LPORT yours/listening port: "    -> SKELETON_LPORT
#     "User name: "  /  "Password: "    -> SKELETON_USER / SKELETON_PASS
#     "Interface: "                     -> SKELETON_IFACE
#     "Wordlist: "                      -> SKELETON_WORDLIST
#     "Wireless interface: "          -> SKELETON_WLAN
#
# Safe save-file construction pattern:
#     outfile = shlex.quote(str(WORKING_DIR / (os.path.basename(outfile_entry.get().strip()) or "default_out")))
#     "Additional switches: "           free-form, left unquoted
#     "Save-file name (no spaces): "    written under WORKING_DIR


# Grid frames
frame_main = Frame(guibox)
frame_main.grid(row=0, column=0, columnspan=1, padx=5, pady=0, sticky="nsew")
guibox.rowconfigure(0, weight=1)
guibox.columnconfigure(0, weight=1)
frame_main.rowconfigure(1, weight=1)
frame_main.columnconfigure(0, weight=1)

frame_message = Frame(frame_main)
frame_message.grid(row=1, column=0, columnspan=1, padx=5, pady=5, sticky="nsew")

frame_buttons1 = Frame(frame_main)
frame_buttons1.grid(row=2, column=0, columnspan=8, padx=5, pady=0)

# Interface
text_box = Text(frame_message, height=45, width=115)
text_box.insert('end', info)
text_box.pack(side=LEFT, fill=BOTH, expand=True)
text_box.yview('1.0')

sb = Scrollbar(frame_message)
sb.pack(side=RIGHT, fill=BOTH)
text_box.config(yscrollcommand=sb.set)
sb.config(command=text_box.yview)

NEW_button = Button(frame_buttons1, text=" NEW Terminal ", command=NEW_Terminal)
NEW_button.grid(row=0, column=0, padx=5, pady=5)

guibox.mainloop()
