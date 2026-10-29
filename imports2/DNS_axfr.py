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

      █████╗ ██╗  ██╗███████╗██████╗
     ██╔══██╗╚██╗██╔╝██╔════╝██╔══██╗
     ███████║ ╚███╔╝ █████╗  ██████╔╝
     ██╔══██║ ██╔██╗ ██╔══╝  ██╔══██╗
     ██║  ██║██╔╝ ██╗██║     ██║  ██║
     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝     ╚═╝  ╚═╝


DNS_axfr  -  dig / host  -  DNS zone-transfer (AXFR) test

A DNS zone transfer (AXFR) asks a name server to hand over every record in a
zone in a single reply.  It exists for secondary-NS syncing and is meant to be
locked to trusted IPs; when it is left open you get the whole internal
namespace - hostnames, internal IPs, dev / staging boxes, mail infra - for free.
Sits right at the front of external recon, before you brute-force subdomains the
hard way.

when to use it
    - recon / footprinting phase, first move once you have the domain and its NS set
    - yields: full subdomain list, internal IP ranges, naming scheme, mail/infra hosts
    - a success can end subdomain enumeration outright - you already have everything;
      a refusal is the normal case, then fall back to brute force + CT logs
    - drives the target list for the rest of the engagement

typical commands
    host domain.com                            resolve A record (quick sanity check)
    dig domain.com +short                      minimal answer - just the IP
    dig any domain.com                         dump every record type for the name
    dig domain.com A                           A records only
    dig +nocmd domain.com MX +noall +answer    trimmed output - answer section only
    dig domain.com +short                      DNS lookup, return IP only
    dig domain.com PTR                         reverse DNS / pointer record lookup
    dig domain.com MX                          mail exchangers for the domain
    dig domain.com NS                          authoritative name servers (get these first)
    dig +short NS domain.com                   just the NS hostnames, one per line
    whois domain.com                           registrar + name servers; then `host` each NS for its IP

    zone transfer proper
    dig axfr @domain.com domain.com            issue an AXFR zone-transfer request
    dig @IP_of_name_server -t AXFR domain.com  by IP; -t XFR / -t AXFR both work
    dig @10.50.96.5 foocampus.com -t AXFR +nocookie      real example, EDNS cookie disabled
    host -t axfr foocampus.com 10.50.96.5      same test with host(1)
    host -l domain.com ns1.domain.com          host list-zone shorthand
    for ns in $(dig +short NS domain.com); do dig axfr @$ns domain.com; done   try every NS

    windows (interactive nslookup)
    > nslookup                                 start the interactive resolver
    > server IP_address                        point at the target DNS / name server
    > set type=any
    > ls -d domain.com                         request the zone transfer

pair with
    DNS_dnsrecon / DNS_dnsenum   both attempt AXFR automatically, plus subdomain brute force
    DNS_fierce / DNS_dnsmap      brute-force subdomains when AXFR is refused
    DNS_crtsh / OSIN_amass       certificate-transparency + passive names to fill the gaps
    DNS_whois / DNS_nslookup     registrar and manual record lookups around this
    enum_nmap                    feed discovered hosts straight into port scanning

gotchas / de-conflict
    - most name servers refuse AXFR - "Transfer failed." / "communications error" is normal, not a bug
    - try EVERY NS in the set; secondaries are often left more permissive than the primary
    - AXFR is always TCP 53 - a firewall on TCP 53 looks identical to a refusal
    - +nocookie / +notcp / +tcp toggles help when dig throws EDNS or connection errors
    - -t IXFR is the incremental variant - rarely open, occasionally worth a try
    - zone transfers are DNS server misconfigurations: should be limited to trusted
      downstream name servers, or the whole zone is enumerable by anyone

authorisation & reporting
    - an AXFR query is low-noise and close to passive, but it IS a direct request to
      target infrastructure - keep it inside the authorised scope and window
    - a success is itself a finding: "DNS server <ns> permits unauthenticated zone
      transfer of zone <domain> from any host"
    - remediation one-liner: restrict transfers to explicit secondary-NS IPs
      (allow-transfer { ...; }; in BIND) or disable them entirely
    - /opt/SKELETON/working holds saved output for this module

bind fingerprinting & dns posture checks
  bind version chaos txt:
    dig @ns1.target.com version.bind CHAOS TXT +short

  email & domain authentication records:
    dig TXT target.com +short           # SPF record
    dig TXT _dmarc.target.com +short    # DMARC policy (p=none/quarantine/reject)
    dig CAA target.com +short           # Authorized Certificate Authorities
'''

#GUI

#Creates $guibox window to populate all the gui
guibox = Tk()
guibox.title('DNS_axfr  —  dig AXFR zone-transfer test')   #window title: tool name + purpose
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


def RUN_dig_AXFR():
    if not target_entry.get().strip():
        LOG("Target url / domain is empty")
        return
    target = shlex.quote(target_entry.get().strip())
    server = server_entry.get().strip()
    server = "@" + shlex.quote(server) if server else ""
    outfile = shlex.quote(str(WORKING_DIR / (os.path.basename(outfile_entry.get().strip()) or "axfr_out")))
    switches = switches_entry.get()                    # free-form, left unquoted
    cmd = "dig axfr " + target + " " + server + " " + switches + " | tee " + outfile
    RUN_in_terminal(cmd)


def RUN_dig_ANY():
    if not target_entry.get().strip():
        LOG("Target url / domain is empty")
        return
    target = shlex.quote(target_entry.get().strip())
    outfile = shlex.quote(str(WORKING_DIR / (os.path.basename(outfile_entry.get().strip()) or "axfr_out")))
    switches = switches_entry.get()                    # free-form, left unquoted
    cmd = "dig any " + target + " " + switches + " | tee " + outfile
    RUN_in_terminal(cmd)



def RUN_dig_AXFR_all():
    target = shlex.quote(target_entry.get().strip() or "example.com")
    outfile = shlex.quote(str(WORKING_DIR / (os.path.basename(outfile_entry.get().strip()) or "axfr_out")))
    switches = switches_entry.get()
    cmd = 'for ns in $(dig +short NS ' + target + '); do echo "=== AXFR @$ns ==="; dig axfr ' + target + ' @"$ns" +nocookie ' + switches + '; done | tee ' + outfile
    RUN_in_terminal(cmd)

def RUN_dig_posture():
    target = shlex.quote(target_entry.get().strip() or "example.com")
    outfile = shlex.quote(str(WORKING_DIR / (os.path.basename(outfile_entry.get().strip()) or "axfr_out")))
    cmd = '(echo "=== NS ==="; dig NS ' + target + ' +short; echo "=== MX ==="; dig MX ' + target + ' +short; echo "=== TXT/SPF ==="; dig TXT ' + target + ' +short; echo "=== DMARC ==="; dig TXT _dmarc.' + target + ' +short; echo "=== CAA ==="; dig CAA ' + target + ' +short) | tee ' + outfile
    RUN_in_terminal(cmd)

def RUN_dig_NS_MX():
    if not target_entry.get().strip():
        LOG("Target url / domain is empty")
        return
    target = shlex.quote(target_entry.get().strip())
    outfile = shlex.quote(str(WORKING_DIR / (os.path.basename(outfile_entry.get().strip()) or "axfr_out")))
    switches = switches_entry.get()                    # free-form, left unquoted
    cmd = "dig " + target + " NS +short " + switches + " ; dig " + target + " MX +short " + switches + " | tee " + outfile
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
target_entry = Entry(frame_fields, width=34)
target_entry.grid(row=0, column=1, padx=5, pady=4)
target_entry.insert(0, os.environ.get("SKELETON_URL", "example.com"))

server_label = Label(frame_fields, text="DNS server (optional): ")
server_label.grid(row=1, column=0, padx=5, pady=4, sticky='e')
server_entry = Entry(frame_fields, width=24)
server_entry.grid(row=1, column=1, padx=5, pady=4)
server_entry.insert(0, "")

switches_label = Label(frame_fields, text="Additional switches: ")
switches_label.grid(row=2, column=0, padx=5, pady=4, sticky='e')
switches_entry = Entry(frame_fields, width=30)   #entry field for extra switches
switches_entry.grid(row=2, column=1, padx=5, pady=4)
switches_entry.insert(0, "")

outfile_label = Label(frame_fields, text="Save-file name (no spaces): ")
outfile_label.grid(row=3, column=0, padx=5, pady=4, sticky='e')
outfile_entry = Entry(frame_fields, width=46)
outfile_entry.grid(row=3, column=1, padx=5, pady=4)
outfile_entry.insert(0, "axfr_out")

RUN_dig_AXFR_button = Button(frame_buttons1, text=" RUN dig AXFR ", command=RUN_dig_AXFR)
RUN_dig_AXFR_button.grid(row=0, column=0, padx=5, pady=5)

RUN_dig_ANY_button = Button(frame_buttons1, text=" RUN dig ANY ", command=RUN_dig_ANY)
RUN_dig_ANY_button.grid(row=0, column=1, padx=5, pady=5)

RUN_dig_NS_MX_button = Button(frame_buttons1, text=" RUN dig NS/MX ", command=RUN_dig_NS_MX)
RUN_dig_NS_MX_button.grid(row=0, column=2, padx=5, pady=5)

NEW_button = Button(frame_buttons1, text=" NEW Terminal ", command=NEW_Terminal)
NEW_button.grid(row=0, column=3, padx=5, pady=5)


RUN_dig_AXFR_all_btn = Button(frame_buttons1, text=" TRY AXFR ALL NS ", command=RUN_dig_AXFR_all)
RUN_dig_AXFR_all_btn.grid(row=1, column=0, padx=5, pady=5)

RUN_dig_posture_btn = Button(frame_buttons1, text=" RUN TXT / SPF / DMARC / CAA ", command=RUN_dig_posture)
RUN_dig_posture_btn.grid(row=1, column=1, padx=5, pady=5)

guibox.mainloop()   #generates guibox window
