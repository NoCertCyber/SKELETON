#!/usr/bin/env python3

from tkinter import *
from datetime import datetime
import subprocess
import shlex
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import WORKING_DIR

#Define variables outside functions here:

info = r'''

     ████████╗██╗  ██╗███████╗██╗  ██╗ █████╗ ██████╗ ██╗   ██╗███████╗███████╗████████╗███████╗██████╗
     ╚══██╔══╝██║  ██║██╔════╝██║  ██║██╔══██╗██╔══██╗██║   ██║██╔════╝██╔════╝╚══██╔══╝██╔════╝██╔══██╗
        ██║   ███████║█████╗  ███████║███████║██████╔╝██║   ██║█████╗  ███████╗   ██║   █████╗  ██████╔╝
        ██║   ██╔══██║██╔══╝  ██╔══██║██╔══██║██╔══██╗╚██╗ ██╔╝██╔══╝  ╚════██║   ██║   ██╔══╝  ██╔══██╗
        ██║   ██║  ██║███████╗██║  ██║██║  ██║██║  ██║ ╚████╔╝ ███████╗███████║   ██║   ███████╗██║  ██║
        ╚═╝   ╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝  ╚═══╝  ╚══════╝╚══════╝   ╚═╝   ╚══════╝╚═╝  ╚═╝

OSIN_theharvester  -  theHarvester  -  emails, subdomains, hosts and names from public sources

theHarvester is a fast passive-recon tool: give it a domain (or company name)
and it queries dozens of search engines, certificate-transparency logs, passive-
DNS and threat-intel feeds, then returns emails, subdomains, resolved hosts,
virtual hosts, IPs and sometimes staff names.  On a cyberworthiness assessment
it is the standard first pass to seed a target list - the email format it
reveals feeds password-spray / phishing scope, and the subdomains feed active
enumeration.  Ships on Kali (pipx install / git clone https://github.com/laramies/theHarvester).

    https://github.com/laramies/theHarvester
    theHarvester -d website.com -l 100 -b google        minimal example

core flags
    -d      domain, or the company / keyword to search
    -l      limit the number of results returned
    -b      data source(s) - comma-separated, or "all"
    -f      write results to file (HTML + JSON, base name)
    -n      DNS reverse-lookup the discovered / netblock range
    -c      DNS brute-force common subdomain names
    -s      take the hosts found and look each up in Shodan
    -r      DNS resolve the discovered hostnames
    -t      check discovered subdomains for takeover
    --screenshot <dir>   screenshot the resolved web hosts
    (older tip: "automatic option is default - y = automatic, n = manual")

-b data sources
                    baidu, bing, bingapi, bufferoverun, certspotter,
                    crtsh, dnsdumpster, duckduckgo, exalead, github-code,
                    google, hackertarget, hunter, intelx, linkedin,
                    linkedin_links, netcraft, otx, pentesttools,
                    projectdiscovery, qwant, rapiddns, securityTrails,
                    spyse, sublist3r, threatcrowd, threatminer, trello,
                    twitter, urlscan, virustotal, yahoo
    (some sources - bingapi, github-code, hunter, intelx, securityTrails,
     shodan - need an API key set in api-keys.yaml; "all" just skips the rest)

when to use it
    - the first OSINT step, before DNS enum and active scanning
    - yields: email addresses + format, subdomains, hosts/IPs, virtual hosts, names
    - drives phishing/spray scope and hands a subdomain list to active enum

typical commands
    theHarvester -d target.com -b all -l 500                    all sources, cap results
    theHarvester -d target.com -b bing,crtsh,duckduckgo,otx,rapiddns,urlscan -l 500
    theHarvester -d target.com -b crtsh,rapiddns -f target      save target.html / .json
    theHarvester -d target.com -b all -l 1000 -n -c             + reverse-DNS + subdomain brute
    theHarvester -d target.com -b all -s                        + Shodan lookup of found hosts
    theHarvester -d target.com -b anubis,crtsh --screenshot shots/
    (the module's RUN button runs:  theHarvester -d <target> -l 1000
     -b google,bing,linkedin,dnsdumpster,duckduckgo,yahoo -f <working-dir>/<name>.txt)

most common use
    theHarvester -d target.com -b all -l 500 -f target   - read target.json: the emails
    give you the username format (first.last@, flast@ ...) for spray/phish scope, and
    the hosts/subdomains list is your seed for OSIN_projectdiscovery / DNS enum.

pair with
    OSIN_projectdiscovery / DNS_sublist3r    resolve + probe the subdomains found here
    OSIN_spiderfoot / OSIN_reconftw          broader automated OSINT if this pass is thin
    OSIN_shodan                              detail on the hosts (-s does a basic lookup)
    breach-data / credential modules         validate the harvested emails

gotchas
    - search engines rate-limit and CAPTCHA operator-heavy queries - google/bing runs
      often return little; lean on crtsh, rapiddns, otx, urlscan for subdomains
    - LinkedIn / social sources are frequently broken and return few or no names
    - results include stale and third-party hosts - resolve and verify before testing
    - passive to the TARGET, but the data sources see your queries + IP - use research egress

authorisation & reporting
    - fully passive third-party lookups (unless you add -n/-c/-r/-t/--screenshot, which
      resolve and touch hosts) - the passive form normally needs no client sign-off
    - report: exposed email addresses / naming convention, external subdomain inventory,
      any credentials or keys surfaced via github-code / intelx
    - fix = review what staff emails are public, retire stale DNS, rotate leaked secrets,
      brief staff on phishing given the exposed address format

theharvester api keys and reliable sources
  api key location:
    ~/.theHarvester/api-keys.yaml or /etc/theHarvester/api-keys.yaml

  extract json hosts:
    jq -r '.hosts[]?' theHarvester_out.json | cut -d: -f1 | sort -u
'''

#GUI

#Creates $guibox window to populate all the gui
guibox = Tk()
guibox.title('OSIN_theharvester  —  theHarvester - emails, hosts and names from public sources')   #window title: tool name + purpose
guibox.geometry("950x900")   #size for the window guibox


#Define functions

def NEW_Terminal():
    subprocess.call(["gnome-terminal"])


def RUN_in_terminal(cmd):
    subprocess.call(['gnome-terminal -- bash -c ' + shlex.quote(cmd + ' ; exec bash')], shell=True)
    LOG(cmd)

def LOG(cmd):
    current_time = datetime.now()
    current_time_value = "\n" + "Time stamp: " + current_time.strftime("%d-%b-%Y (%H:%M:%S.%f)") + " - " + cmd + "\n"
    text_box.insert('end', current_time_value)
    text_box.yview('end')


def RUN_theHarvester_reliable():
    target = shlex.quote(target_entry.get().strip() or "example.com")
    switches = switches_entry.get()
    outfile = shlex.quote(str(WORKING_DIR / (os.path.basename(name_entry.get().strip()) or "theHarvester_out")))
    cmd = "theHarvester -d " + target + " -l 1000 -b anubis,certspotter,crtsh,dnsdumpster,hackertarget,otx,rapiddns,urlscan -f " + outfile + " " + switches
    RUN_in_terminal(cmd)

def RUN_theHarvester_all():
    target = shlex.quote(target_entry.get().strip() or "example.com")
    switches = switches_entry.get()
    outfile = shlex.quote(str(WORKING_DIR / (os.path.basename(name_entry.get().strip()) or "theHarvester_out")))
    cmd = "theHarvester -d " + target + " -l 500 -b all -f " + outfile + " " + switches
    RUN_in_terminal(cmd)

def RUN_theHarvester():
    # basename + a fallback, like every other module's save-file box:
    # a name with a slash in it made WORKING_DIR / name land somewhere
    # else entirely (an absolute one discards the working dir), so the
    # report went where the notes tab and the Runs panel do not look.
    name = os.path.basename(name_entry.get().strip()) or "theHarvester_out"
    outfile = shlex.quote(str(WORKING_DIR / (name + ".txt")))
    switches = switches_entry.get()                    # free-form, left unquoted
    cmd = 'theHarvester -d ' + shlex.quote(target_entry.get()) + ' -l 1000 -b google,bing,linkedin,dnsdumpster,duckduckgo,yahoo -f ' + outfile + " " + switches
    subprocess.call(['gnome-terminal -- bash -c ' + shlex.quote(cmd + ' ; exec bash')], shell = True)
    LOG(cmd)


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

frame_buttons2 = Frame(frame_main)
frame_buttons2.grid(row=3, column=0, columnspan=8, padx=5, pady=0)

frame_buttons3 = Frame(frame_main)
frame_buttons3.grid(row=4, column=0, columnspan=8, padx=5, pady=0)

#interface
text_box = Text(
    frame_message,
    height=45,
    width=115
)
text_box.grid(row=1)

text_box.insert('end', info)
text_box.pack(side=LEFT, fill=BOTH, expand=True)
text_box.yview('1.0')

sb = Scrollbar(frame_message)
sb.pack(side=RIGHT, fill=BOTH)

text_box.config(yscrollcommand=sb.set)
sb.config(command=text_box.yview)

target_label = Label(frame_buttons1, text="Target url / domain: ")
target_label.grid(row=0, column=0, padx=5, pady=5)
target_entry = Entry(frame_buttons1, width=30)
target_entry.grid(row=0, column=1, padx=5, pady=5)
target_entry.insert(0, os.environ.get("SKELETON_URL", 'example.com'))

switches_label = Label(frame_buttons1, text="Additional switches: ")
switches_label.grid(row=1, column=0, padx=5, pady=5)
switches_entry = Entry(frame_buttons1, width=30)   #entry field for extra switches
switches_entry.grid(row=1, column=1, padx=5, pady=5)
switches_entry.insert(0, "")

name_label = Label(frame_buttons1, text="Save-file name (no spaces): ")
name_label.grid(row=2, column=0, padx=5, pady=5)
name_entry = Entry(frame_buttons1, width=25)
name_entry.grid(row=2, column=1, padx=5, pady=5)
name_entry.insert(0, 'theHarvester_out')

RUN_theHarvester_button = Button(frame_buttons3, text=" RUN theHarvester ", command=RUN_theHarvester)
RUN_theHarvester_button.grid(row=0, column=0, padx=5, pady=5)

NEW_button = Button(frame_buttons3, text=" NEW Terminal ", command=NEW_Terminal)
NEW_button.grid(row=0, column=1, padx=5, pady=5)


RUN_th_reliable_btn = Button(frame_buttons1, text=" RUN passive reliable (no CAPTCHA) ", command=RUN_theHarvester_reliable)
RUN_th_reliable_btn.grid(row=1, column=0, padx=5, pady=5)

RUN_th_all_btn = Button(frame_buttons1, text=" RUN all sources (-b all) ", command=RUN_theHarvester_all)
RUN_th_all_btn.grid(row=1, column=1, padx=5, pady=5)

guibox.mainloop()   #generates guibox window
