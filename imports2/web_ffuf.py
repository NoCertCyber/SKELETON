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

     ███████╗███████╗██╗   ██╗███████╗
     ██╔════╝██╔════╝██║   ██║██╔════╝
     █████╗  █████╗  ██║   ██║█████╗
     ██╔══╝  ██╔══╝  ██║   ██║██╔══╝
     ██║     ██║     ╚██████╔╝██║
     ╚═╝     ╚═╝      ╚═════╝ ╚═╝

web_ffuf  -  ffuf / feroxbuster  -  fast web content, vhost and parameter fuzzing

ffuf sends thousands of requests, substituting the word FUZZ in the URL, a
header, or the body from a wordlist, and filters the responses.  In a
cyberworthiness assessment it is the workhorse for content discovery (hidden
dirs/files/backups), virtual-host discovery, and finding undocumented parameters
and API endpoints on a web app.

when to use it
    - you have a web server and need to enumerate what is actually there
    - most common use: directory/file discovery with -e extensions and -ac to auto-filter noise
    - also: vhost brute (-H "Host: FUZZ..."), parameter-name/value fuzzing

install:  sudo apt-get install -y ffuf feroxbuster

FUZZ marks the injection point - path, vhost, header, param name or value.

# content discovery
$ ffuf -w /usr/share/seclists/Discovery/Web-Content/raft-medium-directories.txt \
       -u https://target.tld/FUZZ -mc 200,204,301,302,307,401,403 -e .php,.txt,.bak
# recursive, auto-calibrate junk responses
$ ffuf -w list.txt -u https://target.tld/FUZZ -recursion -recursion-depth 2 -ac
# vhost / subdomain
$ ffuf -w subs.txt -u https://target.tld/ -H "Host: FUZZ.target.tld" -fs 0
# POST parameter values
$ ffuf -w vals.txt -u https://target.tld/api -X POST -d '{"id":"FUZZ"}' \
       -H "Content-Type: application/json" -fr "not found"
# GET parameter names
$ ffuf -w /usr/share/seclists/Discovery/Web-Content/burp-parameter-names.txt \
       -u 'https://target.tld/page?FUZZ=1' -fs 4242

$ feroxbuster -u https://target.tld -x php,txt -r -d 3        #recursion by default
filters:  -mc/-fc code  -ms/-fs size  -mw/-fw words  -mr/-fr regex  -ac autocalibrate

pair with
    web_gobuster / web_dirb   alternative content brute-forcers
    web_whatweb / web_eyewitness   fingerprint before/after to prioritise targets
    web_nuclei         run templates against the paths ffuf discovers
    web_sqlmap / web_xss / web_ssti   test the parameters ffuf uncovers
    web_recon_notes    the wordlists and manual checks that pair with this

gotchas
    - pick the wordlist for the stack (SecLists raft-* for dirs, api/ for APIs); huge lists waste time
    - always -ac or a -fs/-fw filter, or soft-404 pages flood the output
    - rate-limit shared / prod targets: -p 0.1 -rate 50, and mind WAF bans
    - -recursion can explode request count - cap -recursion-depth
    - 403 != "nothing there" - try method/header/path-case tricks on interesting 403s
    - use -replay-proxy http://127.0.0.1:8080 to send only hits to Burp

authorisation & reporting
    - active brute-force: many requests, log noise, possible WAF lockout - stay in scope,
      agree timing for prod
    - report: exposed dirs/files (backups, .git, configs, admin), undocumented
      parameters/endpoints, directory listing, verbose 403/500
    - fix = remove sensitive files from web roots, disable directory listing, auth on
      admin paths, WAF + rate limiting, consistent 404s

feroxbuster recursive content discovery
  feroxbuster auto-tune crawl:
    feroxbuster -u https://example.com -w wordlist.txt -k --auto-tune --extract-links
'''

#GUI

#Creates $guibox window to populate all the gui
guibox = Tk()
guibox.title('web_ffuf  —  ffuf / feroxbuster - fast web content and parameter fuzzing')   #window title: tool name + purpose
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



def RUN_feroxbuster():
    target = target_entry.get().strip() or "https://example.com"
    base_url = target.replace('/FUZZ', '').replace('FUZZ', '') or target
    wlist = shlex.quote(wordlist_entry.get().strip() or "/usr/share/seclists/Discovery/Web-Content/raft-medium-directories.txt")
    outfile = shlex.quote(str(WORKING_DIR / (os.path.basename(outfile_entry.get().strip()) or "ffuf_out")))
    cmd = "feroxbuster -u " + shlex.quote(base_url) + " -w " + wlist + " -k --auto-tune --extract-links -o " + outfile + "_ferox.txt"
    RUN_in_terminal(cmd)

def RUN_ffuf():
    if not wordlist_entry.get().strip():
        LOG("Wordlist is empty")
        return
    if not target_entry.get().strip():
        LOG("Target url (must contain FUZZ) is empty")
        return
    wordlist = shlex.quote(wordlist_entry.get().strip())
    # ffuf refuses to run without a FUZZ keyword, and the engagement URL that
    # the launchers pre-fill this box with does not carry one - so the module
    # would be handed a target it cannot use every time the target row is set.
    # Put the keyword on the end of the path and say so.
    url = target_entry.get().strip()
    if "FUZZ" not in url:
        url = url.rstrip("/") + "/FUZZ"
        LOG("no FUZZ keyword in the target url - fuzzing the path: " + url)
    target = shlex.quote(url)
    switches = switches_entry.get()                    # free-form, left unquoted
    outfile = shlex.quote(str(WORKING_DIR / (os.path.basename(outfile_entry.get().strip()) or "ffuf_out")))
    cmd = "ffuf -w " + wordlist + " -u " + target + " " + switches + " -o " + outfile
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

target_label = Label(frame_fields, text="Target url (must contain FUZZ): ")
target_label.grid(row=0, column=0, padx=5, pady=4, sticky='e')
target_entry = Entry(frame_fields, width=52)
target_entry.grid(row=0, column=1, padx=5, pady=4)
target_entry.insert(0, "https://example.com/FUZZ")

wordlist_label = Label(frame_fields, text="Wordlist: ")
wordlist_label.grid(row=1, column=0, padx=5, pady=4, sticky='e')
wordlist_entry = Entry(frame_fields, width=60)
wordlist_entry.grid(row=1, column=1, padx=5, pady=4)
wordlist_entry.insert(0, os.environ.get("SKELETON_WORDLIST", "/usr/share/seclists/Discovery/Web-Content/raft-medium-directories.txt"))

switches_label = Label(frame_fields, text="Additional switches: ")
switches_label.grid(row=2, column=0, padx=5, pady=4, sticky='e')
switches_entry = Entry(frame_fields, width=52)
switches_entry.grid(row=2, column=1, padx=5, pady=4)
switches_entry.insert(0, "-ac -mc 200,204,301,302,307,401,403 -e .php,.txt")

outfile_label = Label(frame_fields, text="Save-file name (no spaces): ")
outfile_label.grid(row=3, column=0, padx=5, pady=4, sticky='e')
outfile_entry = Entry(frame_fields, width=46)
outfile_entry.grid(row=3, column=1, padx=5, pady=4)
outfile_entry.insert(0, "ffuf_out")

RUN_ffuf_button = Button(frame_buttons1, text=" RUN ffuf ", command=RUN_ffuf)
RUN_ffuf_button.grid(row=0, column=0, padx=5, pady=5)

NEW_button = Button(frame_buttons1, text=" NEW Terminal ", command=NEW_Terminal)
NEW_button.grid(row=0, column=1, padx=5, pady=5)


FEROX_btn = Button(frame_buttons1, text=" RUN feroxbuster ", command=RUN_feroxbuster)
FEROX_btn.grid(row=0, column=2, padx=5, pady=5)

guibox.mainloop()   #generates guibox window
