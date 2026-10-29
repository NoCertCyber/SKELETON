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

      ██████╗  ██████╗ ██████╗ ██╗   ██╗███████╗████████╗███████╗██████╗
     ██╔════╝ ██╔═══██╗██╔══██╗██║   ██║██╔════╝╚══██╔══╝██╔════╝██╔══██╗
     ██║  ███╗██║   ██║██████╔╝██║   ██║███████╗   ██║   █████╗  ██████╔╝
     ██║   ██║██║   ██║██╔══██╗██║   ██║╚════██║   ██║   ██╔══╝  ██╔══██╗
     ╚██████╔╝╚██████╔╝██████╔╝╚██████╔╝███████║   ██║   ███████╗██║  ██║
      ╚═════╝  ╚═════╝ ╚═════╝  ╚═════╝ ╚══════╝   ╚═╝   ╚══════╝╚═╝  ╚═╝


web_gobuster  -  gobuster  -  directory/file, DNS-subdomain and vhost brute-forcing

gobuster is a fast Go brute-forcer with modes for web content (dir), subdomain
discovery (dns), virtual hosts (vhost) and more.  In a cyberworthiness assessment
it is a quick first pass to find hidden paths on a web server and to enumerate
subdomains of an in-scope domain.

when to use it
    - content discovery on a web server, or subdomain enumeration on a domain
    - most common use:  gobuster dir -u http://TARGET/ -w common.txt -x php,txt -b 404,403

gobuster dir -u http://10.10.10.10/ -w /usr/share/dirb/wordlists/common.txt
#looking for website paths

gobuster dns -d website.com -w /usr/share/SecLists/Discovery/DNS/namelist.txt
#looking for subdomains

--help

dir	Uses directory/file enumeration mode
dns	Uses DNS subdomain enumeration mode
fuzz	Uses fuzzing mode. Replaces the keyword FUZZ in the URL, Headers and the request body

-w, --wordlist string       Path to the wordlist
-v, --verbose               Verbose output (errors)
-q, --quiet                 Don't print the banner and other noise

# NOTES
# looking for website paths
# looking for subdomains

more examples
    gobuster dir -u https://target -w raft-medium-directories.txt -x php,txt,bak -t 50 -k -b 404,403 -o dir.txt
    gobuster dns -d target.com -w /usr/share/SecLists/Discovery/DNS/subdomains-top1million-110000.txt -t 50 -i
    gobuster vhost -u https://target -w subs.txt --append-domain --exclude-length 0

pair with
    web_ffuf / web_dirb / feroxbuster   more flexible fuzzing (headers, params, recursion)
    DNS_dnsenum / DNS_sublist3r / OSIN_bbot   passive subdomain sources to combine with dns mode
    web_whatweb / web_eyewitness   fingerprint the hosts/paths found
    web_nuclei / web_sqlmap   follow-up testing on discovered endpoints

gotchas
    - -k to ignore TLS cert errors; -b / --exclude-length to drop soft-404 noise
    - dir mode only finds what is in the wordlist and returns a "real" status - pick the list for the stack
    - dns mode is DNS-only (no web request) - fast and quiet; -i shows resolved IPs
    - vhost mode: use --exclude-length or --append-domain correctly or every response "matches"
    - aggressive -t on prod can trip rate limits / WAF - throttle

authorisation & reporting
    - dir/vhost modes send many HTTP requests (active); dns mode queries resolvers - stay in scope
    - report: hidden dirs/files, admin paths, backups, subdomains (esp. dev/staging,
      dangling records = takeover risk)
    - fix = remove sensitive content from web roots, auth on admin paths, disable
      directory listing, prune stale DNS records, WAF + rate limiting

gobuster v3 vhost & s3 bucket enumeration
  vhost append-domain mode:
    gobuster vhost -u https://example.com -w subs.txt --append-domain

  s3 bucket search:
    gobuster s3 -w buckets.txt
'''

#GUI

#Creates $guibox window to populate all the gui
guibox = Tk()
guibox.title('web_gobuster  —  gobuster - directory, vhost and DNS brute force')   #window title: tool name + purpose
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



def RUN_gobuster_vhost_append():
    target = shlex.quote(target_entry.get().strip() or "https://example.com")
    wlist = shlex.quote(wordlist_entry.get().strip() or "/usr/share/seclists/Discovery/Web-Content/common.txt")
    outfile = shlex.quote(str(WORKING_DIR / (os.path.basename(outfile_entry.get().strip()) or "gobuster_out")))
    cmd = "gobuster vhost -u " + target + " -w " + wlist + " --append-domain -k -t 50 -o " + outfile + "_vhost.txt"
    RUN_in_terminal(cmd)

def RUN_gobuster_dir():
    if not target_entry.get().strip():
        LOG("Target url / domain is empty")
        return
    if not wordlist_entry.get().strip():
        LOG("Wordlist is empty")
        return
    target = shlex.quote(target_entry.get().strip())
    wordlist = shlex.quote(wordlist_entry.get().strip())
    switches = switches_entry.get()                    # free-form, left unquoted
    outfile = shlex.quote(str(WORKING_DIR / (os.path.basename(outfile_entry.get().strip()) or "gobuster_out")))
    cmd = "gobuster dir -u " + target + " -w " + wordlist + " " + switches + " -o " + outfile
    RUN_in_terminal(cmd)


def RUN_gobuster_dns():
    if not target_entry.get().strip():
        LOG("Target url / domain is empty")
        return
    if not wordlist_entry.get().strip():
        LOG("Wordlist is empty")
        return
    target = shlex.quote(target_entry.get().strip())
    wordlist = shlex.quote(wordlist_entry.get().strip())
    switches = switches_entry.get()                    # free-form, left unquoted
    outfile = shlex.quote(str(WORKING_DIR / (os.path.basename(outfile_entry.get().strip()) or "gobuster_out")))
    cmd = "gobuster dns -d " + target + " -w " + wordlist + " " + switches + " -o " + outfile
    RUN_in_terminal(cmd)


def RUN_gobuster_vhost():
    if not target_entry.get().strip():
        LOG("Target url / domain is empty")
        return
    if not wordlist_entry.get().strip():
        LOG("Wordlist is empty")
        return
    target = shlex.quote(target_entry.get().strip())
    wordlist = shlex.quote(wordlist_entry.get().strip())
    switches = switches_entry.get()                    # free-form, left unquoted
    outfile = shlex.quote(str(WORKING_DIR / (os.path.basename(outfile_entry.get().strip()) or "gobuster_out")))
    cmd = "gobuster vhost -u " + target + " -w " + wordlist + " " + switches + " -o " + outfile
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
target_entry = Entry(frame_fields, width=46)
target_entry.grid(row=0, column=1, padx=5, pady=4)
target_entry.insert(0, os.environ.get("SKELETON_URL", "https://example.com"))

wordlist_label = Label(frame_fields, text="Wordlist: ")
wordlist_label.grid(row=1, column=0, padx=5, pady=4, sticky='e')
wordlist_entry = Entry(frame_fields, width=60)
wordlist_entry.grid(row=1, column=1, padx=5, pady=4)
wordlist_entry.insert(0, os.environ.get("SKELETON_WORDLIST", "/usr/share/seclists/Discovery/Web-Content/DirBuster-2007_directory-list-2.3-medium.txt"))

switches_label = Label(frame_fields, text="Additional switches: ")
switches_label.grid(row=2, column=0, padx=5, pady=4, sticky='e')
switches_entry = Entry(frame_fields, width=46)
switches_entry.grid(row=2, column=1, padx=5, pady=4)
switches_entry.insert(0, "-t 50 -x php,txt,html")

outfile_label = Label(frame_fields, text="Save-file name (no spaces): ")
outfile_label.grid(row=3, column=0, padx=5, pady=4, sticky='e')
outfile_entry = Entry(frame_fields, width=46)
outfile_entry.grid(row=3, column=1, padx=5, pady=4)
outfile_entry.insert(0, "gobuster_out")

RUN_gobuster_dir_button = Button(frame_buttons1, text=" RUN gobuster dir ", command=RUN_gobuster_dir)
RUN_gobuster_dir_button.grid(row=0, column=0, padx=5, pady=5)

RUN_gobuster_dns_button = Button(frame_buttons1, text=" RUN gobuster dns ", command=RUN_gobuster_dns)
RUN_gobuster_dns_button.grid(row=0, column=1, padx=5, pady=5)

RUN_gobuster_vhost_button = Button(frame_buttons1, text=" RUN gobuster vhost ", command=RUN_gobuster_vhost)
RUN_gobuster_vhost_button.grid(row=0, column=2, padx=5, pady=5)

NEW_button = Button(frame_buttons1, text=" NEW Terminal ", command=NEW_Terminal)
NEW_button.grid(row=0, column=3, padx=5, pady=5)


VHOST_app_btn = Button(frame_buttons1, text=" RUN vhost (--append-domain) ", command=RUN_gobuster_vhost_append)
VHOST_app_btn.grid(row=0, column=4, padx=5, pady=5)

guibox.mainloop()   #generates guibox window
