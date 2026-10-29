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

     ███████╗██╗  ██╗ ██████╗ ██████╗  █████╗ ███╗   ██╗
     ██╔════╝██║  ██║██╔═══██╗██╔══██╗██╔══██╗████╗  ██║
     ███████╗███████║██║   ██║██║  ██║███████║██╔██╗ ██║
     ╚════██║██╔══██║██║   ██║██║  ██║██╔══██║██║╚██╗██║
     ███████║██║  ██║╚██████╔╝██████╔╝██║  ██║██║ ╚████║
     ╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═══╝

OSIN_shodan  -  Shodan  -  internet-exposed host / service search engine

Shodan continuously scans the whole IPv4 space, grabs service banners, TLS
certs, screenshots and default-cred / CVE indicators, and lets you query the
result set.  Because the scanning is Shodan's, you get port-scan-quality data
about a target's internet-facing estate WITHOUT sending a single packet to the
target - the ideal passive first look on a cyberworthiness assessment.  Useful
for: mapping exposed services by org/ASN/netblock, finding forgotten hosts,
pulling extra hostnames/subdomains out of TLS certs, spotting expired certs,
end-of-life software, exposed databases, RDP/VNC and ICS/SCADA panels.

    https://www.shodan.io                                        web search + account
    https://exploits.shodan.io/welcome                           exploit search front-end
    https://www.shodan.io/explore/category/industrial-control-systems   ICS explore
    https://ics-radar.shodan.io                                  live ICS exposure map

what it gives you
    - service + port list per host, banners, and product/version strings
    - TLS certificate details (CN / SAN often reveal extra subdomains)
    - expired / self-signed certs - config-hygiene and social-engineering leads
    - IP geolocation, owning org / ISP / ASN
    - "vuln:" CVE tags, default-credential and screenshot data

when to use it
    - very first recon step, before any active scanning
    - yields: the client's exposed attack surface as an outsider sees it
    - drives scope validation (which IPs are really theirs) and quick-win findings

install & auth
    pip install shodan        (ships on Kali)
    shodan init <API_KEY>     one-time; key is on your account page

typical commands  (CLI)
    shodan host 1.2.3.4                         banners, ports, hostnames, CVEs for one IP
    shodan search 'org:"Acme Corp"' --fields ip_str,port,hostnames,org
    shodan search 'net:192.0.2.0/24' --fields ip_str,port,product
    shodan search 'ssl.cert.subject.cn:target.com'      hosts by cert CN (subdomain pivot)
    shodan search 'hostname:target.com http.title:"Login"'
    shodan search 'vuln:CVE-2021-44228 org:"Acme"'      Log4Shell-tagged hosts in the org
    shodan count 'apache country:GB'           just the result count, no query credits burned
    shodan stats --facets port,org,vuln 'net:192.0.2.0/24'   facet breakdown for scoping
    shodan domain target.com                   subdomains + DNS + recent scan data
    shodan download acme 'org:"Acme Corp"'     bulk export to acme.json.gz
    shodan parse --fields ip_str,port,transport acme.json.gz
    shodan alert create "Acme" 192.0.2.0/24   monitor a netblock; shodan alert list / stats
    shodan myip                                what egress IP you look like

    useful filters:  org:  net:  hostname:  ssl.cert.subject.cn:  ssl.cert.expired:true
                     http.title:  http.status:  product:  version:  port:  vuln:  (CVE)
                     has_screenshot:true  country:  city:  os:  asn:

most common use
    shodan search 'org:"<client>"' --fields ip_str,port,product,hostnames  and
    shodan stats --facets port,vuln,product 'net:<client CIDR>'  - gives the exposed-
    service table and CVE tags for the report before you touch the network.  Then
    shodan host <ip> on anything interesting.  Use "count" not "search" while iterating
    on a query to avoid spending query credits.

pair with
    OSIN_projectdiscovery   verify the live hosts / ports Shodan lists with httpx / naabu
    OSIN_theharvester       cross-check subdomains; feed cert CNs back into DNS enum
    enum_nmap               targeted active scan of the ports Shodan flags
    web_nuclei              template-scan the exposed web hosts

gotchas
    - Shodan data is a snapshot - can be days/weeks stale (port since closed) or miss a
      host it hasn't rescanned; confirm before reporting as live
    - free/community keys are heavily rate/credit limited; "count" and "stats" are cheaper
    - "vuln:" filter needs a paid membership; results are version-inference, not proof
    - hosts behind CDN/WAF show the edge, not the origin
    - your search terms and API key sit with Shodan - fine for OSINT, note it in the RoE

authorisation & reporting
    - fully passive: Shodan scanned the target, not you - normally no client sign-off,
      but list it as a data source in the report
    - report: every exposed service (IP/port/product/version), expired/weak certs,
      EOL software, exposed admin/DB/RDP/ICS, and CVE-tagged hosts
    - fix = close/firewall the port, put admin behind VPN/allowlist, renew certs,
      upgrade EOL software, request removal via Shodan if a host is decommissioned

###################################################

shodan internetdb (free, unauthenticated, zero api key)
  query open ports, cpes & cvss:
    curl -s https://internetdb.shodan.io/1.2.3.4 | jq .
'''

#GUI

#Creates $guibox window to populate all the gui
guibox = Tk()
guibox.title('OSIN_shodan  —  Shodan - internet-exposed host search engine')   #window title: tool name + purpose
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


def RUN_shodan_host():
    if not target_entry.get().strip():
        LOG("Target IP is empty")
        return
    target = shlex.quote(target_entry.get().strip())
    outfile = shlex.quote(str(WORKING_DIR / (os.path.basename(outfile_entry.get().strip()) or "shodan_out")))
    switches = switches_entry.get()                    # free-form, left unquoted
    cmd = "shodan host " + target + " " + switches + " | tee " + outfile
    RUN_in_terminal(cmd)



def RUN_shodan_internetdb():
    target = shlex.quote(target_entry.get().strip() or "1.2.3.4")
    outfile = shlex.quote(str(WORKING_DIR / (os.path.basename(outfile_entry.get().strip()) or "shodan_out")))
    cmd = "curl -s https://internetdb.shodan.io/" + target + " | jq . | tee " + outfile
    RUN_in_terminal(cmd)

def RUN_shodan_count():
    query = shlex.quote(query_entry.get().strip() or 'org:"Acme Corp"')
    switches = switches_entry.get()
    outfile = shlex.quote(str(WORKING_DIR / (os.path.basename(outfile_entry.get().strip()) or "shodan_out")))
    cmd = "shodan count " + query + " " + switches + " | tee " + outfile
    RUN_in_terminal(cmd)

def RUN_shodan_stats():
    query = shlex.quote(query_entry.get().strip() or 'org:"Acme Corp"')
    switches = switches_entry.get()
    outfile = shlex.quote(str(WORKING_DIR / (os.path.basename(outfile_entry.get().strip()) or "shodan_out")))
    cmd = "shodan stats --facets port,vuln,product,org " + query + " " + switches + " | tee " + outfile
    RUN_in_terminal(cmd)

def RUN_shodan_search():
    if not query_entry.get().strip():
        LOG("Search terms is empty")
        return
    query = shlex.quote(query_entry.get().strip())
    outfile = shlex.quote(str(WORKING_DIR / (os.path.basename(outfile_entry.get().strip()) or "shodan_out")))
    switches = switches_entry.get()                    # free-form, left unquoted
    cmd = "shodan search " + query + " --fields ip_str,port,hostnames,org " + switches + " | tee " + outfile
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

query_label = Label(frame_fields, text="Search terms: ")
query_label.grid(row=0, column=0, padx=5, pady=4, sticky='e')
query_entry = Entry(frame_fields, width=40)
query_entry.grid(row=0, column=1, padx=5, pady=4)
query_entry.insert(0, "org:\"Acme Corp\"")

target_label = Label(frame_fields, text="Target IP: ")
target_label.grid(row=1, column=0, padx=5, pady=4, sticky='e')
target_entry = Entry(frame_fields, width=22)
target_entry.grid(row=1, column=1, padx=5, pady=4)
target_entry.insert(0, os.environ.get("SKELETON_TARGET", "1.2.3.4"))

switches_label = Label(frame_fields, text="Additional switches: ")
switches_label.grid(row=2, column=0, padx=5, pady=4, sticky='e')
switches_entry = Entry(frame_fields, width=40)   #entry field for extra switches
switches_entry.grid(row=2, column=1, padx=5, pady=4)
switches_entry.insert(0, "")

outfile_label = Label(frame_fields, text="Save-file name (no spaces): ")
outfile_label.grid(row=3, column=0, padx=5, pady=4, sticky='e')
outfile_entry = Entry(frame_fields, width=46)
outfile_entry.grid(row=3, column=1, padx=5, pady=4)
outfile_entry.insert(0, "shodan_out")

RUN_shodan_host_button = Button(frame_buttons1, text=" RUN shodan host ", command=RUN_shodan_host)
RUN_shodan_host_button.grid(row=0, column=0, padx=5, pady=5)

RUN_shodan_search_button = Button(frame_buttons1, text=" RUN shodan search ", command=RUN_shodan_search)
RUN_shodan_search_button.grid(row=0, column=1, padx=5, pady=5)

NEW_button = Button(frame_buttons1, text=" NEW Terminal ", command=NEW_Terminal)
NEW_button.grid(row=0, column=2, padx=5, pady=5)


RUN_internetdb_btn = Button(frame_buttons1, text=" RUN InternetDB (no API key) ", command=RUN_shodan_internetdb)
RUN_internetdb_btn.grid(row=1, column=0, padx=5, pady=5)

RUN_shodan_count_btn = Button(frame_buttons1, text=" RUN shodan count (0 credits) ", command=RUN_shodan_count)
RUN_shodan_count_btn.grid(row=1, column=1, padx=5, pady=5)

RUN_shodan_stats_btn = Button(frame_buttons1, text=" RUN shodan stats (facets) ", command=RUN_shodan_stats)
RUN_shodan_stats_btn.grid(row=1, column=2, padx=5, pady=5)

guibox.mainloop()   #generates guibox window
