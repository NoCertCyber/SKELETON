#!/usr/bin/env python3

from tkinter import *
from datetime import datetime
import subprocess
import webbrowser
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import VENDOR_DIR
from config import WORKING_DIR
import shlex

#Define variables outside functions here:

# The Reverse Shell Generator site (revshells.com source) is cloned into the
# vendor tree.  It is a plain static site - every asset it needs is vendored in
# the repo - so serve it with python3 -m http.server and browse it offline.
# Port is overridable.
PORT = int(os.environ.get("SKELETON_REVSHELL_PORT", "8139"))

RSG_DIR = VENDOR_DIR / "reverse-shell-generator"


info = r'''

      ____  _______     ______  _   _ _____ _     _     ____
     |  _ \| ____\ \   / / ___|| | | | ____| |   | |   / ___|
     | |_) |  _|  \ \ / /\___ \| |_| |  _| | |   | |   \___ \
     |  _ <| |___  \ V /  ___) |  _  | |___| |___| |___ ___) |
     |_| \_\_____|  \_/  |____/|_| |_|_____|_____|_____|____/

info_revshell_generator  -  Reverse Shell Generator (revshells.com)  -  build a
                            matching listener + reverse-shell one-liner, offline

Fill in your IP and port once and the page produces a copy-paste listener command
AND the reverse-shell payload for dozens of languages/contexts (Bash, sh, nc,
ncat, PHP, Python, Perl, Ruby, PowerShell variants, Go, Java, Lua, NodeJS,
awk, ...), plus TTY-upgrade snippets and an msfvenom builder.  In a cyberworthiness
assessment it is the fastest way to get a working callback once you have code
execution, without misremembering quoting.

when to use it
    - you have command execution (RCE, web shell, SSTI, injection) and need a shell back
    - you need the exact TTY-upgrade steps or an msfvenom line
    - most common use: set LHOST/LPORT, copy the "nc" listener, copy a payload row

run it
    run revshells  - serves the vendored copy (vendor/reverse-shell-generator) on
                     127.0.0.1:{port} via python3 -m http.server; opens the browser.
                     Close that terminal to stop it.
    Online version:  https://www.revshells.com/   (don't put a client's real IPs into the hosted one)

how to use
    set IP + Port (top of the page)
    pick a listener: nc, ncat, rlwrap nc, pwncat, msfconsole  ->  copy it, run it first
    pick a payload row (Bash, PHP, Python, PowerShell #3, ...) and the shell type
    "raw" / "URL encode" toggles the encoding; the pencil icon edits the template

pair with
    exploit_shell_handler / transfer_netcat   run the listener the page gives you
    exploit_tty_upgrade    the same PTY-upgrade steps, with more detail
    exploit_msfvenom       when you need a compiled payload, not a one-liner
    web_php_shell / web_shell_upload / web_command_injection   the delivery modules

gotchas
    - the payload must match the target's available interpreter AND egress (try 443/53 if 4444 is filtered)
    - PowerShell rows: use #3 (base64) when quoting/AV mangles the plain one
    - a bare  nc -e  is not available on many modern nc builds - use the mkfifo variant
    - firewalls/NAT: you need the target able to reach your LHOST:LPORT inbound

authorisation & reporting
    - the generator is local/benign; the payloads are live - only against authorised
      targets, and log every callback
    - report: that code execution led to an interactive shell, the privilege level,
      and which egress port/protocol the callback used (egress-filtering finding)
'''.format(port=PORT)

#GUI

#Creates $guibox window to populate all the gui
guibox = Tk()
guibox.title('info_revshell_generator  —  Reverse Shell Generator - build one-liners for any target')   #window title: tool name + purpose
guibox.geometry("950x900")   #size for the window guibox

#Define functions

_server_started = False


def NEW_Terminal():
    subprocess.call(["gnome-terminal"])

def LOG(cmd):
    stamp = datetime.now().strftime("%d-%b-%Y (%H:%M:%S.%f)")
    text_box.insert('end', "\nTime stamp: {} - {}\n".format(stamp, cmd))
    text_box.yview('end')

def RUN_in_terminal(cmd):
    subprocess.call(['gnome-terminal -- bash -c ' + shlex.quote(cmd + ' ; exec bash')], shell=True)
    LOG(cmd)

def RUN_nc_listener():
    lport = shlex.quote(lport_entry.get().strip() or "4444")
    cmd = "rlwrap -cAr nc -lvnp " + lport
    RUN_in_terminal(cmd)


def RUN_module():
    """Start (once) a local web instance of the vendored Reverse Shell Generator."""
    global _server_started
    index = RSG_DIR / "index.html"
    if not index.is_file():
        text_box.insert('end', "\nReverse Shell Generator not found under {}\n".format(RSG_DIR))
        text_box.insert('end', "clone it there:  git clone "
                               "https://github.com/0dayCTF/reverse-shell-generator "
                               "{}\n".format(RSG_DIR))
        text_box.yview('end')
        return

    url = "http://127.0.0.1:{}/".format(PORT)
    if not _server_started:
        subprocess.Popen([
            "gnome-terminal", "--working-directory", str(RSG_DIR),
            "--", "python3", "-m", "http.server", str(PORT),
        ])
        _server_started = True
        guibox.after(1500, lambda: webbrowser.open(url))   #give the server a moment
    else:
        webbrowser.open(url)

    current_time = datetime.now()
    current_time_value = "\n" + "Time stamp: " + current_time.strftime("%d-%b-%Y (%H:%M:%S.%f)") + " - revshell generator web instance on " + url + "\n"
    text_box.insert('end', current_time_value)
    text_box.yview('end')

#Grid Frames
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

#interface
text_box = Text(   #creates text box inside frame_message with info text
    frame_message,
    height=45,
    width=115
)
text_box.grid(row=1)

text_box.insert('end', info)   #adds info to the end of text_box
text_box.pack(side=LEFT, fill=BOTH, expand=True)   #config for slider variant
text_box.yview('1.0')

sb = Scrollbar(frame_message)   #assign scrollbar
sb.pack(side=RIGHT, fill=BOTH)   #scrollbar configuration

text_box.config(yscrollcommand=sb.set)   #set scrollbar on y axis
sb.config(command=text_box.yview)

RUN_button = Button(frame_buttons1, text=" run revshells ", command=RUN_module)
RUN_button.grid(row=0, column=0, padx=5, pady=5)

NEW_button = Button(frame_buttons1, text=" NEW Terminal ", command=NEW_Terminal)
NEW_button.grid(row=0, column=1, padx=5, pady=5)


frame_fields = Frame(frame_main)
frame_fields.grid(row=3, column=0, columnspan=8, padx=5, pady=4)

lport_label = Label(frame_fields, text="LPORT yours/listening port: ")
lport_label.grid(row=0, column=0, padx=5, pady=4, sticky='e')
lport_entry = Entry(frame_fields, width=20)
lport_entry.grid(row=0, column=1, padx=5, pady=4)
lport_entry.insert(0, os.environ.get("SKELETON_LPORT", "4444"))

LISTEN_button = Button(frame_buttons1, text=" START rlwrap nc listener ", command=RUN_nc_listener)
LISTEN_button.grid(row=0, column=2, padx=5, pady=5)

guibox.mainloop()   #generates guibox window
