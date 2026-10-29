#!/usr/bin/env python3

from tkinter import *
from datetime import datetime
import os
import shlex
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import WORKING_DIR

#Define variables outside functions here:

info = r'''

     ██╗    ██╗██╗  ██╗ █████╗ ████████╗██╗    ██╗███████╗██████╗
     ██║    ██║██║  ██║██╔══██╗╚══██╔══╝██║    ██║██╔════╝██╔══██╗
     ██║ █╗ ██║███████║███████║   ██║   ██║ █╗ ██║█████╗  ██████╔╝
     ██║███╗██║██╔══██║██╔══██║   ██║   ██║███╗██║██╔══╝  ██╔══██╗
     ╚███╔███╔╝██║  ██║██║  ██║   ██║   ╚███╔███╔╝███████╗██████╔╝
      ╚══╝╚══╝ ╚═╝  ╚═╝╚═╝  ╚═╝   ╚═╝    ╚══╝╚══╝ ╚══════╝╚═════╝


web_whatweb  -  WhatWeb  -  website technology fingerprinting

WhatWeb identifies what a website is built on: CMS, framework, web server,
JavaScript libraries, analytics, WAF, hosting, and version numbers, plus default
pages and email addresses.  In a cyberworthiness assessment it is the quick
fingerprint that tells you which targeted tests and CVEs are relevant, and
surfaces version-disclosure findings.

when to use it
    - first contact with a web target, or bulk-fingerprinting a subnet / URL list
    - most common use:  whatweb -a 3 -v https://target        (aggressive, verbose)

whatweb 10.10.10.10  #return handy website information

http://10.10.10.10 [200 OK] Apache[2.4.41], Country[RESERVED][ZZ], Email[license@php.net], HTTPServer[Ubuntu Linux][Apache/2.4.41 (Ubuntu)], IP[10.10.10.10, Title[PHP 7.4.3 - phpinfo()]

whatweb --no-errors 10.10.10.0/24  #scan through subnet

more examples
    whatweb -a 1 https://target                     # passive (headers only), quiet first pass
    whatweb -a 3 -v https://target                   # active, show which plugins matched
    whatweb -i live-hosts.txt --log-json=ww.json     # bulk + machine-readable
    whatweb --user-agent 'Mozilla/5.0' --header 'X-Forwarded-For: 127.0.0.1' https://target
    whatweb --proxy 127.0.0.1:8080 https://target    # through Burp

pair with
    web_header_grabbing   raw header review to corroborate versions
    web_eyewitness        screenshots for the same host list
    exploit_searchsploit / web_nuclei   map the identified stack + versions to known issues
    web_recon_notes       the wider recon methodology

gotchas
    - aggression 3-4 sends extra probes (active); 1 is passive - pick per rules of engagement
    - versions come from banners/fingerprints and can be spoofed or stripped by a proxy/WAF
    - a CDN/WAF in front (Cloudflare, Akamai) masks the origin stack - note it, find the origin separately
    - plugin database ages - cross-check an odd result

authorisation & reporting
    - low-impact (a handful of requests) - safe within the in-scope host list
    - report: technology + version disclosure, outdated components, default/install
      pages left in place, exposed admin frameworks
    - fix = suppress version banners, keep components patched, remove default/sample
      content, minimise fingerprintable detail

json logging & aggression levels
  structured json export:
    whatweb --color=never --log-json=whatweb.json https://example.com
'''

#GUI

#Creates $guibox window to populate all the gui
guibox = Tk()
guibox.title('web_whatweb  —  WhatWeb - website technology fingerprinting')   #window title: tool name + purpose
guibox.geometry("950x900")   #size for the window guibox

#Define functions

def LOG(cmd):
    stamp = datetime.now().strftime("%d-%b-%Y (%H:%M:%S.%f)")
    text_box.insert('end', "\nTime stamp: {} - {}\n".format(stamp, cmd))
    text_box.yview('end')


def RUN_in_terminal(cmd):
    """Fire `cmd` in its own terminal.  Value fields are already shlex.quote()d
    by the caller; quoting the whole command once more keeps a stray quote in a
    free-form switches field from breaking out into the outer shell."""
    subprocess.call(
        ['gnome-terminal -- bash -c ' + shlex.quote(cmd + ' ; exec bash')],
        shell=True,
    )
    LOG(cmd)



def RUN_whatweb_json():
    target = shlex.quote(target_entry.get().strip() or "https://example.com")
    outfile = shlex.quote(str(WORKING_DIR / ((os.path.basename(outfile_entry.get().strip()) or "whatweb_out") + ".json")))
    cmd = "whatweb --color=never --log-json=" + outfile + " " + target
    RUN_in_terminal(cmd)

def RUN_whatweb():
    if not target_entry.get().strip():
        LOG("Target url / domain is empty")
        return
    switches = switches_entry.get()                    # free-form, left unquoted
    target = shlex.quote(target_entry.get().strip())
    outfile = shlex.quote(str(WORKING_DIR / (os.path.basename(outfile_entry.get().strip()) or "whatweb_out")))
    cmd = "whatweb " + switches + " " + target + " | tee " + outfile
    RUN_in_terminal(cmd)


def RUN_whatweb_passive():
    if not target_entry.get().strip():
        LOG("Target url / domain is empty")
        return
    target = shlex.quote(target_entry.get().strip())
    outfile = shlex.quote(str(WORKING_DIR / (os.path.basename(outfile_entry.get().strip()) or "whatweb_out")))
    cmd = "whatweb -a 1 " + target + " | tee " + outfile
    RUN_in_terminal(cmd)


def NEW_Terminal():
    subprocess.call(["gnome-terminal"])

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


# --- input fields ------------------------------------------------------
frame_fields = Frame(frame_main)
frame_fields.grid(row=3, column=0, columnspan=8, padx=5, pady=0)

target_label = Label(frame_fields, text="Target url / domain: ")
target_label.grid(row=0, column=0, padx=5, pady=4, sticky='e')
target_entry = Entry(frame_fields, width=40)
target_entry.grid(row=0, column=1, padx=5, pady=4)
target_entry.insert(0, os.environ.get("SKELETON_URL", "https://example.com"))

switches_label = Label(frame_fields, text="Additional switches: ")
switches_label.grid(row=1, column=0, padx=5, pady=4, sticky='e')
switches_entry = Entry(frame_fields, width=30)
switches_entry.grid(row=1, column=1, padx=5, pady=4)
switches_entry.insert(0, "-a 3 -v")

outfile_label = Label(frame_fields, text="Save-file name (no spaces): ")
outfile_label.grid(row=2, column=0, padx=5, pady=4, sticky='e')
outfile_entry = Entry(frame_fields, width=46)
outfile_entry.grid(row=2, column=1, padx=5, pady=4)
outfile_entry.insert(0, "whatweb_out")

RUN_whatweb_button = Button(frame_buttons1, text=" RUN whatweb ", command=RUN_whatweb)
RUN_whatweb_button.grid(row=0, column=0, padx=5, pady=5)

RUN_whatweb_passive_button = Button(frame_buttons1, text=" RUN whatweb passive ", command=RUN_whatweb_passive)
RUN_whatweb_passive_button.grid(row=0, column=1, padx=5, pady=5)

NEW_button = Button(frame_buttons1, text=" NEW Terminal ", command=NEW_Terminal)
NEW_button.grid(row=0, column=2, padx=5, pady=5)


JSON_btn = Button(frame_buttons1, text=" RUN whatweb JSON ", command=RUN_whatweb_json)
JSON_btn.grid(row=0, column=2, padx=5, pady=5)

guibox.mainloop()   #generates guibox window
