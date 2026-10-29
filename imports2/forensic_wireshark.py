#!/usr/bin/env python3

from tkinter import *
from datetime import datetime
import subprocess

#Define variables outside functions here:

info = r'''

     ██╗    ██╗██╗██████╗ ███████╗███████╗██╗  ██╗ █████╗ ██████╗ ██╗  ██╗
     ██║    ██║██║██╔══██╗██╔════╝██╔════╝██║  ██║██╔══██╗██╔══██╗██║ ██╔╝
     ██║ █╗ ██║██║██████╔╝█████╗  ███████╗███████║███████║██████╔╝█████╔╝
     ██║███╗██║██║██╔══██╗██╔══╝  ╚════██║██╔══██║██╔══██║██╔══██╗██╔═██╗
     ╚███╔███╔╝██║██║  ██║███████╗███████║██║  ██║██║  ██║██║  ██║██║  ██╗
      ╚══╝╚══╝ ╚═╝╚═╝  ╚═╝╚══════╝╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝

Wireshark - the GUI packet analyser.  Load a capture (.pcap / .pcapng / many
other formats) and dissect it protocol by protocol: follow streams, carve
transferred files, decrypt TLS/WPA, chase retransmits, and pull credentials and
IOCs out of traffic.  In an investigation it answers "what actually crossed the
wire" - C2 beacons, exfil, lateral movement, rogue APs.  For headless / scripted
work use forensic_tshark; for automatic artefact carving use forensic_networkminer.

when to use it
    - DFIR: examine a capture from a span port / full-packet sensor around an
      alert - who talked to the C2, what was uploaded, which host moved laterally
    - malware triage: watch a detonated sample's network in the sandbox - DNS,
      HTTP(S) beacons, user-agent, JA3, downloaded stages
    - wireless assessment: dissect an 802.11 capture - beacons, handshakes,
      WEP IVs, WPS state (filters below)
    - pen-test evidence: prove cleartext creds / sensitive data in transit; keep
      the pcap + stream export as the artefact

FILTERS:
https://www.wireshark.org/docs/man-pages/
https://packetlife.net/media/library/13/Wireshark_Display_Filters.pdf

capinfos file.pcap  #give basic info about pcap

ne, != Not equal
gt, > Greater than
lt, < Less than
ge, >= Greater than or equal to
le, <= Less than or equal to
contains, Contains specified data
Use Boolean operators (and, or, not)

ip.src == IP
display only source IP

!wlan.fc.type_subtype == 8
This filter will list all the frames that do not have an 802.11 frame control subtype value of 8. This filter will exclude all the beacon frames from a wireless packet capture.

!wlan.fc.protected == 1
This filter will list all the frames that do not have the WEP bit (or privacy bit) set. This is useful for identifying unencrypted wireless traffic.

wlan.bssid == 00:e0:63:82:19:c6
This filter will display only packets that have the specified BSSID. By changing the BSSID value, this filter will be useful for excluding any traffic received from other nearby access points on the same channel.

frame contains ORA-
This filter will search the entire packet for any instances of the string "ORA-". Note that this string is case sensitive and will not match instances of "ora-" or "Ora-". This filter is useful for identifying unencrypted Oracle traffic on a network.

!!!http or ip contains!!!
search decrypted traffic data
frame contains
search encrypted frame payload
EX: http contains user

tcp or udp or arp or isakmp
This filter does not use the typical expression logic for traffic filtering. Instead, it will discard all fields that are not of the type TCP, UDP, ARP, or ISAKMP. This filter is useful for extracting these specific upper-layer protocols and can be modified to add or subtract specific protocol fields.

!(wlan.bssid == 00:10:e7:f5:c3:1f or wlan.bssid == 00:60:1d:f0:47:39)
This filter shows all traffic that is not from either of the identified BSSIDs. This type of filter is useful for excluding traffic from "known secure" networks, looking to identify any traffic from other wireless networks.

wlan.wep.iv and frame.pkt_len == 68 and wlan.da == ff:ff:ff:ff:ff:ff
ARP packets

wlan.wep.iv
Filter Initialization Vector in WEP

eap or eapol
Looking for authentication packets WPA2 4-way handshake
AP >>> ANonce, start new PTK negotiation >>> client
AP <<< SNonce, MIC of Frame 2 >>> client
AP >>> MIC of Frame 3 >>> client
AP <<< MIC of Frame 4, ready to TX/RX <<< client

ICMPTX
ICMP ping request display payload information
Linux use a sequential pattern of 0x0a 0x0b 0x0c 0x0d, etc
Windows systems use alphanumeric characters in the pattern "abcdef ...789"

wps.wifi_protected_setup_state eq 0x02
Beacon frame indicating WPS supported by the device

#########################################################

TO SET DECRYPTION KEY

Edit | Preferences | expand Protocols tree | IEEE 802.11
Ignore the Protection bit => no
Enable decryption
To add key select Edit

#########################################################

# tshark -n -i mon0 -a filesize:250 -b files:3 -w wifi-fuzz -Y "wlan.addr eq 00:13:ce:55:98:ef"

tshark is disabling name resolution (-n) and capturing on the mon0 interface (-i mon0). Starts a new packet capture file after the previous one reaches 250K in size (-a filesize:250). Only three files will be retained during the capture (-b files:3), all with the filename prefix "wifi-fuzz" (-w wifi-fuzz). Limit the frames being captured to packets sent to or sent from the specified MAC address with a Wireshark display filter (-Y "wlan.addr eq 00:13:ce:55:98:ef")

#########################################################

NetworkMiner.exe #located at /opt/SKELETON/vendor/Tools_Win_binary/NetworkMiner_2-8-1/

windows tool to extract files from pcap, provides extended range of available protocols

#########################################################

# NOTES
# tshark -n -i mon0 -a filesize:250 -b files:3 -w wifi-fuzz -Y "wlan.addr eq 00:13:ce:55:98:ef"

#########################################################

command recipes / workflow
    capinfos capture.pcapng                              # size, packet count, time span, hashes
    File > Open  capture.pcapng                          # or drag-drop
    Statistics > Protocol Hierarchy                      # what protocols are present, by volume
    Statistics > Conversations  (TCP tab, sort Bytes)    # top talkers -> pick the suspicious flow
    Statistics > Endpoints > IP  (+ GeoIP)               # external destinations
    right-click packet > Follow > TCP Stream / HTTP Stream / TLS Stream
    File > Export Objects > HTTP  (also SMB / TFTP / IMF / DICOM)   # carve transferred files
    File > Export Specified Packets                      # save just the filtered flow as evidence
    Statistics > IO Graph                                # beacon spotting - regular interval spikes
    Analyze > Expert Information                         # resets, retransmits, malformed
    Edit > Preferences > Protocols > TLS > (Pre)-Master-Secret log filename = sslkeys.log   # decrypt TLS
    Edit > Preferences > Protocols > IEEE 802.11 > Decryption keys (wpa-pwd / wpa-psk)      # decrypt WPA
    View > Coloring Rules ; Configuration Profiles       # per-investigation setup

useful display filters (paste into the filter bar)
    ip.addr == 10.0.0.5 && tcp.port == 445              # one host, SMB
    tcp.flags.syn == 1 && tcp.flags.ack == 0            # connection attempts / scan
    http.request                                        # every outbound HTTP request
    dns && !dns.flags.response                          # DNS queries only (DGA / tunnelling)
    dns.qry.name contains "."                           # eyeball long / odd DNS labels
    tls.handshake.type == 1                             # TLS Client Hello (SNI, JA3)
    frame contains "password" ; http contains "Authorization"
    smb2.cmd == 5 || smb.cmd == 0xa2                     # SMB create - lateral movement / file access
    tcp.analysis.retransmission || tcp.analysis.zero_window

pair with
    forensic_tshark          same engine, CLI - scripted extraction and stats
    forensic_networkminer    automatic file / image / credential / host carving from the pcap
    forensic_volatility      match windows.netscan connections to flows in the capture
    forensic_malware_analysis   capture the sandbox run, dissect the C2 here
    forensic_capa / forensic_strings   analyse the files you Export-Objects out

gotchas / de-conflict
    - opening Wireshark on a live interface is a capture, not analysis - for
      evidence work from a saved file and note who captured it, where and when
    - multi-GB captures make the GUI crawl; pre-filter with tshark/editcap or use
      a display filter early, and split with editcap -c / -i
    - "frame contains" scans raw bytes (post-decrypt for TLS); "http contains"
      needs the layer dissected - not the same thing
    - TLS decryption needs the key log from the client at capture time; you
      cannot decrypt after the fact without it
    - dissectors have had RCE bugs - analyse hostile captures on the isolated VM,
      keep Wireshark updated
    - run as an unprivileged user; only dumpcap needs capture privileges

authorisation & reporting
    - hash the pcap (sha256) on receipt; open read-only, never re-save over the
      original - export a filtered copy for the report instead
    - record: capture source and method, timezone, Wireshark version, the exact
      display filters used, and the stream / object exports kept as artefacts
    - deliverable IOCs: external IPs / domains / URLs, JA3/JA3S, user-agents,
      transferred file hashes, timestamps of first/last contact

wireshark display filter cheatsheet
  filter unencrypted credentials:
    http.request.method == "POST" || ftp || pop || imap

  filter kerberos pre-auth & error codes:
    kerberos.CNameString || kerberos.error_code

  filter smb lateral movement:
    smb2.filename contains ".exe" || smb2.filename contains "ADMIN$"
'''

#GUI

#Creates $guibox window to populate all the gui
guibox = Tk()
guibox.title('forensic_wireshark  —  Wireshark - GUI packet analysis')   #window title: tool name + purpose
guibox.geometry("950x900")   #size for the window guibox

#Define functions

def NEW_Terminal():
    subprocess.call(["gnome-terminal"])

def RUN_module():
    new = subprocess.call(['gnome-terminal -- bash -c "wireshark"'], shell = True)
    current_time = datetime.now()
    current_time_value = "\n" + "Time stamp: " + current_time.strftime("%d-%b-%Y (%H:%M:%S.%f)") + " - 4_wireshark executed" + "\n"
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

RUN_button = Button(frame_buttons1, text=" RUN 4_wireshark ", command=RUN_module)
RUN_button.grid(row=0, column=0, padx=5, pady=5)

NEW_button = Button(frame_buttons1, text=" NEW Terminal ", command=NEW_Terminal)
NEW_button.grid(row=0, column=1, padx=5, pady=5)

guibox.mainloop()   #generates guibox window
