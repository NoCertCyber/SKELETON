#!/usr/bin/env python3
# Master glossary window.  The pentest-chain / controls preamble lives here;
# the per-module catalogue is the shared data/glossary.txt so it can't drift.

from tkinter import *
import re
import subprocess
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import GLOSSARY
from config import WORKING_DIR
from datetime import datetime
import shlex

PREAMBLE = r'''

      ██████╗ ██╗      ██████╗ ███████╗███████╗ █████╗ ██████╗ ██╗   ██╗
     ██╔════╝ ██║     ██╔═══██╗██╔════╝██╔════╝██╔══██╗██╔══██╗╚██╗ ██╔╝
     ██║  ███╗██║     ██║   ██║███████╗███████╗███████║██████╔╝ ╚████╔╝
     ██║   ██║██║     ██║   ██║╚════██║╚════██║██╔══██║██╔══██╗  ╚██╔╝
     ╚██████╔╝███████╗╚██████╔╝███████║███████║██║  ██║██║  ██║   ██║
      ╚═════╝ ╚══════╝ ╚═════╝ ╚══════╝╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝   ╚═╝

GLOSSARY  -  master reference for the SKELETON launcher and the imports2 modules

what this window is
    The index for the whole toolkit: the launcher controls, the pentest
    chain (phases), and a one-line entry for every module.  Use it to find which
    module does the job you need, then open that module - each module's own info
    panel follows a consistent layout: what the tool is, when to use it, typical
    commands (with examples), what to pair it with, gotchas, and an
    authorisation & reporting note aimed at cyberworthiness assessments.

before you run anything
    Confirm scope and signed authorisation are in place - see the
    info_engagement_permission module. Nothing here should be run outside the
    agreed rules of engagement, targets and test window.


LAUNCHER CONTROLS  (SKELETON_WEB.py, http://127.0.0.1:80):
NEW           - clear the notes tab and reprint the SKELETON banner
TIME          - append a date / time stamp to the notes tab
Find my IP    - run ifconfig, list Ethernet interfaces, fill the IP field
Change my IP  - set eth0 to the address currently in the IP field
SAVE          - write the notes tab to /opt/SKELETON/working/<name>.txt
LOAD          - replace the notes tab with /opt/SKELETON/working/<name>.txt
Insert File   - append /opt/SKELETON/working/<file> into the notes tab
OPEN PORT     - iptables -I INPUT -p tcp --dport <port> -j ACCEPT
RUN MODULE    - open the selected module as its own page, /module/<name>
NEW Terminal  - open /terminal: a shell running on the server, in a browser tab

AUTO NOTES:
/opt/SKELETON/working/working_file.txt is polled once a second; anything
written to it is appended to the notes tab and the file is then emptied.

MODULE PICKER (three columns, left to right):
  1  pick a pentest phase                (PENTEST_CHAIN list)
  2  pick a module in that phase         (list built by /opt/SKELETON/tools/imports_ls2.sh)
  3  read the run history                (working/<tab>/runs.jsonl - re-run or copy a row)
  The description of the selected module is in the reference bar at the foot
  (looked up in /opt/SKELETON/data/glossary.txt).  RUN MODULE opens the module;
  its output pane is a real shell, so a long run is watchable and answerable.


PENTEST CHAIN  (PENTEST_CHAIN in skeleton_core.py):
info        - references, cheatsheets, encoding, environment notes
OSIN        - open-source intelligence and attack-surface recon
DNS         - DNS records, zone transfers, subdomain discovery
enum        - host / port / service / SMB / AD / SNMP enumeration
web         - HTTP / HTTPS web-application testing
mitm        - man-in-the-middle, sniffing, LLMNR / NBNS spoofing
wireless    - 802.11 and Bluetooth / BLE auditing
bruteforce  - password and hash cracking, spraying, wordlists
exploit     - exploitation, credential theft, privilege escalation
powershell  - offensive PowerShell tooling
transfer    - file transfer, tunnelling and pivoting
forensic    - DFIR, reverse engineering, malware analysis


MODULES  (every script in /opt/SKELETON/imports2/)

SESSION VARIABLES & AUTO-FILL VOCABULARY:
SKELETON exports standard environment variables for target session persistence:
  SKELETON_TARGET   - Target IP address (auto-fills "Target IP: ")
  SKELETON_URL      - Target hostname or URL (auto-fills "Target url / domain: ")
  SKELETON_LHOST    - Tester listening IP (auto-fills "LHOST yours/listening IP: ")
  SKELETON_LPORT    - Tester listening port (auto-fills "LPORT yours/listening port: ")
  SKELETON_USER     - Username (auto-fills "User name: ")
  SKELETON_PASS     - Password (auto-fills "Password: ")
  SKELETON_IFACE    - Network interface (auto-fills "Interface: ")
  SKELETON_WLAN     - Wireless monitor interface (auto-fills "Wireless interface: ")
  SKELETON_WORDLIST - Path to dictionary (auto-fills "Wordlist: ")

OFFLINE VENDORED SERVERS & CHEATSHEETS:
  info_cyberchef            - port :8137 (CyberChef web suite)
  info_hacktricks           - port :8138 (HackTricks offline mdBook)
  info_revshell_generator   - port :8139 (Reverse shell generator web app)
  PayloadsAllTheThings      - vendor/PayloadsAllTheThings offline repo

HEALTH CHECK & INTEGRITY:
  python3 tools/skeleton_check.py --describe
'''

FOOTER = r'''
UTILITY FILES (not run from the picker):
glossary                         - plain-text module lookup read by the launcher and /api/glossary
template                         - starting point for building a new imports2 module
terminal_osin                    - quick list of OSINT websites to open in a browser

'''

try:
    _cat = GLOSSARY.read_text(encoding="utf-8", errors="replace")
    _cat = _cat[_cat.index("INFO ##"):]          # drop the duplicate banner
except (OSError, ValueError):
    _cat = "(data/glossary.txt not found)\n"

info = PREAMBLE + "\n" + _cat.rstrip() + "\n\n" + FOOTER

# Catalogue entries are "name<big pad> - description"; collapse the padding.
_HEADER_RE = re.compile(r"^([A-Za-z0-9]+(?:_[A-Za-z0-9]+)+|glossary|template)"
                        r" {2,}- (.+)$")
info = "\n".join(_HEADER_RE.sub(r"\1 - \2", ln) for ln in info.split("\n"))


#GUI

#Creates $guibox window to populate all the gui
guibox = Tk()
guibox.title('info_glossary  —  master glossary of SKELETON modules and pentest structure')   #window title: tool name + purpose
guibox.geometry("950x900")   #size for the window guibox

#Define functions

def NEW_Terminal():
    subprocess.call(["gnome-terminal"])

def LOG(cmd):
    stamp = datetime.now().strftime("%d-%b-%Y (%H:%M:%S.%f)")
    text_box.insert('end', "\nTime stamp: {} - {}\n".format(stamp, cmd))
    text_box.yview('end')

def RUN_in_terminal(cmd):
    subprocess.call(['gnome-terminal -- bash -c ' + shlex.quote(cmd + ' ; exec bash')], shell=True)
    LOG(cmd)

def RUN_search_glossary():
    pat = pattern_entry.get().strip() or "kerberos"
    cmd = "grep -ni -C 2 --color=always " + shlex.quote(pat) + " " + shlex.quote(str(GLOSSARY))
    RUN_in_terminal(cmd)

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

NEW_button = Button(frame_buttons1, text=" NEW Terminal ", command=NEW_Terminal)
NEW_button.grid(row=0, column=0, padx=5, pady=5)


frame_search = Frame(frame_main)
frame_search.grid(row=3, column=0, columnspan=8, padx=5, pady=4)

pattern_label = Label(frame_search, text="Search glossary: ")
pattern_label.grid(row=0, column=0, padx=5, pady=4, sticky='e')
pattern_entry = Entry(frame_search, width=34)
pattern_entry.grid(row=0, column=1, padx=5, pady=4)
pattern_entry.insert(0, "kerberos")

SEARCH_button = Button(frame_buttons1, text=" SEARCH glossary ", command=RUN_search_glossary)
SEARCH_button.grid(row=0, column=1, padx=5, pady=5)

guibox.mainloop()   #generates guibox window
