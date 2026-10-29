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

      █████╗ ██████╗ ██████╗
     ██╔══██╗██╔══██╗██╔══██╗
     ███████║██████╔╝██████╔╝
     ██╔══██║██╔══██╗██╔═══╝
     ██║  ██║██║  ██║██║
     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝

ARP table

The ARP cache is the host's own record of which MAC answers for which IPv4
address on the local L2 segment. Reading it is passive: it reveals live hosts,
the default gateway and appliances without putting a single discovery packet on
the wire. arping / arp-spoofing turns the same protocol into a MITM primitive.
First move on a new segment during internal recon.

to generate arp table use ping IP    #any traffic to a host populates its entry

when to use it
    - immediately after landing on a segment: read the cache the OS already built
    - passive host discovery where scans are noisy or monitored
    - identify the gateway MAC / vendor OUI before deciding to poison
    - confirm you and a target share a broadcast domain (poisoning only works L2-local)
    - feeds the target list for mitm_arpspoof / mitm_bettercap / enum_nmap

typical commands
    ip neigh                                  # Linux: current ARP/NDP cache
    ip neigh show dev eth0                    # just this interface
    arp -a                                    # portable (Linux/Windows/macOS)
    arp -n                                    # numeric, no DNS
    cat /proc/net/arp                         # raw table on Linux
    for i in $(seq 1 254); do ping -c1 -W1 10.0.0.$i >/dev/null & done; wait; ip neigh   # warm the cache
    fping -a -g 10.0.0.0/24 -r0 2>/dev/null   # quieter sweep, then re-read ip neigh
    nmap -sn -PR 10.0.0.0/24                  # nmap ARP ping sweep (local only)
    arp-scan --localnet -I eth0              # dedicated ARP sweep + OUI vendor lookup
    ip -s neigh                               # with stats; spot churn / duplicate MACs

    # arping - probe / abuse a single address
    arping -c 3 -I eth0 10.0.0.1              # is this IP live at L2? show its MAC
    arping -D -I eth0 10.0.0.77               # duplicate-address detection (is .77 taken?)
    ip addr show                              # will show local addresses
    ip addr add 192.1.1.1 dev eth0           # adds a victim/secondary address to your NIC
    arping -U -s victimIP routerIP           # gratuitous ARP: tell routerIP that victimIP = your MAC
    arping -U -s victimIP routerIP/broadcast &   # arping routerIP from victimIP on eth0, backgrounded
        #arping --help   show help
        #will overwrite MAC addresses in the target ARP table (poisoning)

    usage: arping [ -0aAbdDeFpPqrRuUvzZ ] [ -w <sec> ] [ -W <sec> ] [ -S <host/ip> ]
                  [ -T <host/ip ] [ -s <MAC> ] [ -t <MAC> ] [ -c <count> ]
                  [ -C <count> ] [ -i <interface> ] [ -m <type> ] [ -g <group> ]
                  [ -V <vlan> ] [ -Q <priority> ] <host/ip/MAC | -B>

    nc -lup 8000                              # UDP listener for redirected packets
    nc -lvnp 8000                             # TCP listener (protocol dependent)

pair with
    enum_ping_sweep / enum_arp -> enum_nmap        turn discovered hosts into a port map
    mitm_arpspoof / mitm_bettercap / mitm_ettercap  act on the poisoning primitive
    mitm_responder / mitm_mitm6                    once you own the path, capture auth
    enum_netexec                                   sweep SMB across the hosts you found

gotchas / de-conflict
    - ARP is non-routable: cache and arping only ever see your own broadcast domain
    - reading the cache needs no privileges; arping / adding addresses needs root
    - a stale cache lies - warm it (ping/fping) or clear it: ip neigh flush all
    - gratuitous-ARP poisoning is disruptive and easy to detect (arpwatch, DAI on
      switches, duplicate-IP alerts); can black-hole a victim if you drop forwarding
    - VMs on a NAT/host-only network see almost nothing - need a bridged interface
    - 802.1X / port-security / Dynamic ARP Inspection may shut your port on spoofing

authorisation & reporting
    Reading the ARP cache is passive and always in scope. Sending gratuitous ARP /
    poisoning is an active MITM technique - redirects other users' traffic, can
    drop sessions - so run it only with explicit written sign-off, a defined target
    list and a time window.
    Report fix: enable Dynamic ARP Inspection + DHCP snooping on access switches,
    port-security, and 802.1X; segment flat VLANs.

netdiscover & ipv6 neighbour commands
  passive netdiscover (zero packets transmitted):
    sudo netdiscover -i eth0 -p

  active cidr discovery:
    sudo netdiscover -i eth0 -r 10.10.10.0/24 -P

  ipv6 neighbour cache:
    ip -6 neigh show
'''

#GUI

#Creates $guibox window to populate all the gui
guibox = Tk()
guibox.title('enum_arp  —  arp cache inspection for local-segment hosts')   #window title: tool name + purpose
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


def RUN_SHOW_arp_cache():
    if not iface_entry.get().strip():
        LOG("Interface is empty")
        return
    iface = shlex.quote(iface_entry.get().strip())
    outfile = shlex.quote(str(WORKING_DIR / (os.path.basename(outfile_entry.get().strip()) or "arp_out")))
    switches = switches_entry.get()                    # free-form, left unquoted
    cmd = "ip neigh show dev " + iface + " " + switches + " | tee " + outfile
    RUN_in_terminal(cmd)


def RUN_nmap_arp_sweep():
    if not target_entry.get().strip():
        LOG("Target IP is empty")
        return
    target = shlex.quote(target_entry.get().strip())
    outfile = shlex.quote(str(WORKING_DIR / (os.path.basename(outfile_entry.get().strip()) or "arp_out")))
    switches = switches_entry.get()                    # free-form, left unquoted
    cmd = "nmap -sn -PR " + target + " " + switches + " | tee " + outfile
    RUN_in_terminal(cmd)



def RUN_netdiscover_passive():
    iface = shlex.quote(iface_entry.get().strip() or "eth0")
    switches = switches_entry.get()
    outfile = shlex.quote(str(WORKING_DIR / (os.path.basename(outfile_entry.get().strip()) or "arp_out")))
    cmd = "sudo netdiscover -i " + iface + " -p " + switches + " | tee " + outfile
    RUN_in_terminal(cmd)

def RUN_netdiscover_range():
    iface = shlex.quote(iface_entry.get().strip() or "eth0")
    target = shlex.quote(target_entry.get().strip() or "10.10.10.0/24")
    switches = switches_entry.get()
    outfile = shlex.quote(str(WORKING_DIR / (os.path.basename(outfile_entry.get().strip()) or "arp_out")))
    cmd = "sudo netdiscover -i " + iface + " -r " + target + " -P " + switches + " | tee " + outfile
    RUN_in_terminal(cmd)

def RUN_arping_probe():
    iface = shlex.quote(iface_entry.get().strip() or "eth0")
    target = shlex.quote(target_entry.get().strip() or "10.10.10.10")
    switches = switches_entry.get()
    outfile = shlex.quote(str(WORKING_DIR / (os.path.basename(outfile_entry.get().strip()) or "arp_out")))
    cmd = "sudo arping -c 3 -I " + iface + " " + target + " " + switches + " | tee " + outfile
    RUN_in_terminal(cmd)

def RUN_SHOW_ipv6_neigh():
    iface = shlex.quote(iface_entry.get().strip() or "eth0")
    outfile = shlex.quote(str(WORKING_DIR / (os.path.basename(outfile_entry.get().strip()) or "arp_out")))
    cmd = "ip -6 neigh show dev " + iface + " | tee " + outfile
    RUN_in_terminal(cmd)

def RUN_fping_sweep():
    if not target_entry.get().strip():
        LOG("Target IP is empty")
        return
    target = shlex.quote(target_entry.get().strip())
    outfile = shlex.quote(str(WORKING_DIR / (os.path.basename(outfile_entry.get().strip()) or "arp_out")))
    switches = switches_entry.get()                    # free-form, left unquoted
    cmd = "fping -a -g " + target + " -r0 " + switches + " 2>/dev/null | tee " + outfile
    RUN_in_terminal(cmd)


def NEW_Terminal():
    subprocess.call(["gnome-terminal"])

def RUN_module():
    new = subprocess.call(['gnome-terminal -- bash -c "arp && bash"'], shell = True)
    current_time = datetime.now()
    current_time_value = "\n" + "Time stamp: " + current_time.strftime("%d-%b-%Y (%H:%M:%S.%f)") + " - 1_arp executed" + "\n"
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

RUN_button = Button(frame_buttons1, text=" RUN 1_arp ", command=RUN_module)
RUN_button.grid(row=0, column=0, padx=5, pady=5)


# --- input fields ------------------------------------------------------
frame_fields = Frame(frame_main)
frame_fields.grid(row=3, column=0, columnspan=8, padx=5, pady=0)

target_label = Label(frame_fields, text="Target IP: ")
target_label.grid(row=0, column=0, padx=5, pady=4, sticky='e')
target_entry = Entry(frame_fields, width=26)
target_entry.grid(row=0, column=1, padx=5, pady=4)
target_entry.insert(0, os.environ.get("SKELETON_TARGET", "10.10.10.0/24"))

iface_label = Label(frame_fields, text="Interface: ")
iface_label.grid(row=1, column=0, padx=5, pady=4, sticky='e')
iface_entry = Entry(frame_fields, width=12)
iface_entry.grid(row=1, column=1, padx=5, pady=4)
iface_entry.insert(0, os.environ.get("SKELETON_IFACE", "eth0"))

switches_label = Label(frame_fields, text="Additional switches: ")
switches_label.grid(row=2, column=0, padx=5, pady=4, sticky='e')
switches_entry = Entry(frame_fields, width=30)   #entry field for extra switches
switches_entry.grid(row=2, column=1, padx=5, pady=4)
switches_entry.insert(0, "")

outfile_label = Label(frame_fields, text="Save-file name (no spaces): ")
outfile_label.grid(row=3, column=0, padx=5, pady=4, sticky='e')
outfile_entry = Entry(frame_fields, width=46)
outfile_entry.grid(row=3, column=1, padx=5, pady=4)
outfile_entry.insert(0, "arp_out")

RUN_SHOW_arp_cache_button = Button(frame_buttons1, text=" SHOW arp cache ", command=RUN_SHOW_arp_cache)
RUN_SHOW_arp_cache_button.grid(row=0, column=0, padx=5, pady=5)

RUN_nmap_arp_sweep_button = Button(frame_buttons1, text=" RUN nmap arp sweep ", command=RUN_nmap_arp_sweep)
RUN_nmap_arp_sweep_button.grid(row=0, column=1, padx=5, pady=5)

RUN_fping_sweep_button = Button(frame_buttons1, text=" RUN fping sweep ", command=RUN_fping_sweep)
RUN_fping_sweep_button.grid(row=0, column=2, padx=5, pady=5)

NEW_button = Button(frame_buttons1, text=" NEW Terminal ", command=NEW_Terminal)
NEW_button.grid(row=0, column=1, padx=5, pady=5)


frame_buttons2 = Frame(frame_main)
frame_buttons2.grid(row=4, column=0, columnspan=8, padx=5, pady=4)

NETDISC_p_btn = Button(frame_buttons2, text=" RUN netdiscover (passive) ", command=RUN_netdiscover_passive)
NETDISC_p_btn.grid(row=0, column=0, padx=5, pady=5)

NETDISC_r_btn = Button(frame_buttons2, text=" RUN netdiscover (active) ", command=RUN_netdiscover_range)
NETDISC_r_btn.grid(row=0, column=1, padx=5, pady=5)

ARPING_btn = Button(frame_buttons2, text=" RUN arping probe ", command=RUN_arping_probe)
ARPING_btn.grid(row=0, column=2, padx=5, pady=5)

IPV6_btn = Button(frame_buttons2, text=" SHOW IPv6 neigh ", command=RUN_SHOW_ipv6_neigh)
IPV6_btn.grid(row=0, column=3, padx=5, pady=5)

guibox.mainloop()   #generates guibox window
