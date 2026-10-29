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

     ███╗   ██╗███████╗██╗      ██████╗  ██████╗ ██╗  ██╗██╗   ██╗██████╗
     ████╗  ██║██╔════╝██║     ██╔═══██╗██╔═══██╗██║ ██╔╝██║   ██║██╔══██╗
     ██╔██╗ ██║███████╗██║     ██║   ██║██║   ██║█████╔╝ ██║   ██║██████╔╝
     ██║╚██╗██║╚════██║██║     ██║   ██║██║   ██║██╔═██╗ ██║   ██║██╔═══╝
     ██║ ╚████║███████║███████╗╚██████╔╝╚██████╔╝██║  ██╗╚██████╔╝██║
     ╚═╝  ╚═══╝╚══════╝╚══════╝ ╚═════╝  ╚═════╝ ╚═╝  ╚═╝ ╚═════╝ ╚═╝

DNS_nslookup  -  nslookup  -  interactive and one-shot DNS queries

The DNS query client that ships on every Windows and Linux box.  No install, no
dependencies - the tool you reach for first to resolve a name, list the NS/MX
set, do a reverse lookup, or try a zone transfer from a shell you just landed
on.  Recon-phase footprinting, and a quick on-host check during post-exploitation.

when to use it
    - recon: resolve the target, pull NS / MX / TXT, spot the DNS provider
    - reachability check: proves UDP/TCP 53 to a given server is open before you
      point heavier DNS tooling at it
    - post-exploitation: enumerate internal DNS from a foothold with a tool that
      is always present and never flagged
    - one of the "does AXFR work?" checks (ls -d) before escalating to dig

typical commands
    one-shot
    nslookup example.com                          resolve name -> IP (A/AAAA)
    nslookup example.com 8.8.8.8                  resolve using a specific server
    nslookup -type=PTR 10.0.0.5                   reverse lookup (PTR record)
    nslookup -type=MX example.com                 mail exchangers for the domain
    nslookup -type=NS example.com                 authoritative name servers
    nslookup -type=TXT example.com                SPF / DKIM / verification strings
    nslookup -type=SRV _ldap._tcp.dc._msdcs.DOMAIN.LOCAL     locate AD domain controllers
    nslookup -type=any example.com                every record type the server will return
    nslookup -type=SOA example.com               primary NS + zone serial / timers
    nslookup -debug example.com                   full response detail (TTL, flags, authority)

    interactive session
    nslookup                                      start interactive shell / show current server
    > server 10.50.96.5                           point at a specific DNS server (needs port 53 open)
    > set q=NS                                    set the record type (NS shown; also mx, cname, any, ptr)
    > example.com                                 run the query
    > set q=mx
    > example.com
    > set q=cname                                 return canonical name
    > ls -d example.com                           request a full zone transfer (AXFR)
    > exit

    worked example (from a real engagement)
    > server 10.50.96.5
    > set q=NS
    > foocampus.com        -> foocampus.com nameserver = ns.foocampus.com.
                              foocampus.com nameserver = ns1.foocampus.com.
    > ns.foocampus.com     -> returns the NS host's IP address
    > ns1.foocampus.com    -> returns the NS host's IP address
    > set q=MX
    > foocampus.com        -> mail exchanger = 10 pop3.foocampus.com.  (+ its IP)

pair with
    DNS_axfr / DNS_dnsrecon   escalate a working `ls -d` into a proper dig AXFR dump
    DNS_whois                 registrar / registrant data around the NS set
    DNS_dnsenum / DNS_fierce / DNS_sublist3r   when you need brute force, not manual lookups
    enum_nmap                port-scan the hosts you resolve here

gotchas / de-conflict
    - forward/record lookups are passive; `ls -d` (zone transfer) is a direct request to the NS - keep in scope
    - `ls -d` only exists in the Windows nslookup; on Linux use `dig axfr` / `host -l` instead
    - nslookup does NOT read /etc/hosts or nsswitch - it talks straight to DNS, so results can differ from `ping`
    - needs the chosen server reachable on port 53 (UDP, TCP for AXFR / large answers)
    - deprecated in favour of dig/host for scripting - output format is awkward to parse
    - `-type=any` is widely refused / minimised by modern resolvers (RFC 8482)

authorisation & reporting
    - standard resolution is passive and needs no sign-off; zone-transfer attempts
      stay within the authorised DNS scope
    - reporting: note any server answering `ls -d` / AXFR, and internal names or
      SRV records exposed to external resolvers
    - remediation one-liner: restrict zone transfers to secondary NS and split
      internal DNS from the public zone

nslookup advanced options
  tcp mode:     nslookup -vc domain.com          # forces TCP 53 query
  server port:  nslookup -port=8600 consul.local # non-standard DNS port
'''

#GUI

#Creates $guibox window to populate all the gui
guibox = Tk()
guibox.title('DNS_nslookup  —  nslookup interactive DNS queries')   #window title: tool name + purpose
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


def RUN_nslookup():
    if not rtype_entry.get().strip():
        LOG("Record type is empty")
        return
    if not target_entry.get().strip():
        LOG("Target url / domain is empty")
        return
    rtype = shlex.quote(rtype_entry.get().strip())
    target = shlex.quote(target_entry.get().strip())
    server = server_entry.get().strip()
    server = "" + shlex.quote(server) if server else ""
    outfile = shlex.quote(str(WORKING_DIR / (os.path.basename(outfile_entry.get().strip()) or "nslookup_out")))
    switches = switches_entry.get()                    # free-form, left unquoted
    cmd = "nslookup -type=" + rtype + " " + switches + " " + target + " " + server + " | tee " + outfile
    RUN_in_terminal(cmd)



def RUN_nslookup_sweep():
    target = shlex.quote(target_entry.get().strip() or "example.com")
    server = server_entry.get().strip()
    server_arg = (" " + shlex.quote(server)) if server else ""
    outfile = shlex.quote(str(WORKING_DIR / (os.path.basename(outfile_entry.get().strip()) or "nslookup_out")))
    cmd = "(nslookup -type=NS " + target + server_arg + " ; nslookup -type=MX " + target + server_arg + " ; nslookup -type=TXT " + target + server_arg + " ; nslookup -type=SOA " + target + server_arg + ") | tee " + outfile
    RUN_in_terminal(cmd)

def RUN_nslookup_ad_dc():
    target = shlex.quote(target_entry.get().strip() or "example.com")
    server = server_entry.get().strip()
    server_arg = (" " + shlex.quote(server)) if server else ""
    outfile = shlex.quote(str(WORKING_DIR / (os.path.basename(outfile_entry.get().strip()) or "nslookup_out")))
    cmd = "nslookup -type=SRV _ldap._tcp.dc._msdcs." + target + server_arg + " | tee " + outfile
    RUN_in_terminal(cmd)

def RUN_nslookup_PTR():
    if not target_entry.get().strip():
        LOG("Target url / domain is empty")
        return
    target = shlex.quote(target_entry.get().strip())
    server = server_entry.get().strip()
    server = "" + shlex.quote(server) if server else ""
    outfile = shlex.quote(str(WORKING_DIR / (os.path.basename(outfile_entry.get().strip()) or "nslookup_out")))
    switches = switches_entry.get()                    # free-form, left unquoted
    cmd = "nslookup -type=PTR " + switches + " " + target + " " + server + " | tee " + outfile
    RUN_in_terminal(cmd)


def NEW_Terminal():
    subprocess.call(["gnome-terminal"])

def RUN_module():
    new = subprocess.call(["gnome-terminal -- nslookup"], shell = True)
    current_time = datetime.now()
    current_time_value = "\n" + "Time stamp: " + current_time.strftime("%d-%b-%Y (%H:%M:%S.%f)") + " - 53_nslookup executed" + "\n"
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

RUN_button = Button(frame_buttons1, text=" RUN 53_nslookup ", command=RUN_module)
RUN_button.grid(row=0, column=0, padx=5, pady=5)


# --- input fields ------------------------------------------------------
frame_fields = Frame(frame_main)
frame_fields.grid(row=3, column=0, columnspan=8, padx=5, pady=0)

target_label = Label(frame_fields, text="Target url / domain: ")
target_label.grid(row=0, column=0, padx=5, pady=4, sticky='e')
target_entry = Entry(frame_fields, width=34)
target_entry.grid(row=0, column=1, padx=5, pady=4)
target_entry.insert(0, os.environ.get("SKELETON_URL", "example.com"))

rtype_label = Label(frame_fields, text="Record type: ")
rtype_label.grid(row=1, column=0, padx=5, pady=4, sticky='e')
rtype_entry = Entry(frame_fields, width=12)
rtype_entry.grid(row=1, column=1, padx=5, pady=4)
rtype_entry.insert(0, "A")

server_label = Label(frame_fields, text="DNS server (optional): ")
server_label.grid(row=2, column=0, padx=5, pady=4, sticky='e')
server_entry = Entry(frame_fields, width=24)
server_entry.grid(row=2, column=1, padx=5, pady=4)
server_entry.insert(0, "")

switches_label = Label(frame_fields, text="Additional switches: ")
switches_label.grid(row=3, column=0, padx=5, pady=4, sticky='e')
switches_entry = Entry(frame_fields, width=30)   #entry field for extra switches
switches_entry.grid(row=3, column=1, padx=5, pady=4)
switches_entry.insert(0, "")

outfile_label = Label(frame_fields, text="Save-file name (no spaces): ")
outfile_label.grid(row=4, column=0, padx=5, pady=4, sticky='e')
outfile_entry = Entry(frame_fields, width=46)
outfile_entry.grid(row=4, column=1, padx=5, pady=4)
outfile_entry.insert(0, "nslookup_out")

RUN_nslookup_button = Button(frame_buttons1, text=" RUN nslookup ", command=RUN_nslookup)
RUN_nslookup_button.grid(row=0, column=0, padx=5, pady=5)

RUN_nslookup_PTR_button = Button(frame_buttons1, text=" RUN nslookup PTR ", command=RUN_nslookup_PTR)
RUN_nslookup_PTR_button.grid(row=0, column=1, padx=5, pady=5)

NEW_button = Button(frame_buttons1, text=" NEW Terminal ", command=NEW_Terminal)
NEW_button.grid(row=0, column=1, padx=5, pady=5)


RUN_sweep_btn = Button(frame_buttons1, text=" RUN NS/MX/TXT/SOA sweep ", command=RUN_nslookup_sweep)
RUN_sweep_btn.grid(row=1, column=0, padx=5, pady=5)

RUN_ad_dc_btn = Button(frame_buttons1, text=" LOCATE AD DCs (SRV) ", command=RUN_nslookup_ad_dc)
RUN_ad_dc_btn.grid(row=1, column=1, padx=5, pady=5)

guibox.mainloop()   #generates guibox window
