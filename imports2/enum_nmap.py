#!/usr/bin/env python3

from tkinter import *
from datetime import datetime
import subprocess
import shlex
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import WORKING_DIR, own

#Define variables outside functions here:

info = r'''

     ███╗   ██╗███╗   ███╗ █████╗ ██████╗
     ████╗  ██║████╗ ████║██╔══██╗██╔══██╗
     ██╔██╗ ██║██╔████╔██║███████║██████╔╝
     ██║╚██╗██║██║╚██╔╝██║██╔══██║██╔═══╝
     ██║ ╚████║██║ ╚═╝ ██║██║  ██║██║
     ╚═╝  ╚═══╝╚═╝     ╚═╝╚═╝  ╚═╝╚═╝

enum_nmap  -  nmap  -  network host discovery, port / service / OS / vuln scanning

nmap is the baseline discovery and enumeration tool for any cyberworthiness
assessment.  It finds live hosts, maps open TCP/UDP ports, fingerprints the
service and version behind each, guesses the OS, and - through the NSE scripting
engine - probes for named vulnerabilities and misconfigurations.  Everything
downstream (SMB, web, AD, database, brute-force modules) is aimed using its
output, so run it first and keep the -oA files as evidence.

when to use it
    - the first active step against an in-scope host or range, and again whenever
      scope or credentials change
    - yields: alive hosts, open ports, service+version, OS guess, and NSE findings
      (SMB shares/users, TLS issues, default creds, CVE hints)
    - most common: a fast full-TCP sweep to find every open port, then a deep
      -sC -sV -O scan of just those ports

most common use
    sudo nmap -p- --min-rate 2000 -T4 -Pn -oA scans/full <host>          # 1: every TCP port, fast
    ports=$(grep -oP '^\d+(?=/tcp\s+open)' scans/full.nmap | paste -sd,)  # pull the open list
    sudo nmap -sC -sV -O -p"$ports" -oA scans/deep <host>                # 2: scripts + versions + OS
    Read scans/deep.nmap top-down: version strings drive CVE lookups, NSE lines
    flag quick wins, the OS guess sets the toolset.  -oG / .xml feed other tools.

pair with
    enum_ping_sweep     fping / hping3 discovery when ICMP/ARP is filtered or nmap -sn misses hosts
    enum_smbclient / enum_smb_shares / enum_netexec   follow up 139/445 findings
    enum_snmpwalk       follow up 161/udp
    bruteforce_medusa / bruteforce_ncrack / bruteforce_patator   attack the auth services nmap maps
    exploit_* modules   version + NSE output points to the right exploit path
    web enum modules    follow up 80/443/8080/8443

gotchas
    - -sS, -O, decoys and idle scan need root (sudo); without it nmap falls back to -sT
    - --min-rate / -T4/-T5 can overrun fragile kit (SCADA, printers, old firewalls) - drop to -T2 and --scan-delay there
    - -Pn skips host discovery: use it when ICMP is filtered, but it makes every host "up" and slows large ranges
    - UDP (-sU) is slow and lossy; scope it to --top-ports and expect open|filtered
    - version/NSE probes are logged and can crash brittle services; --script vuln includes intrusive checks
    - a firewall/IPS may tar-pit or blackhole you mid-scan - watch for every port suddenly "filtered"

authorisation & reporting
    - host discovery and a plain SYN/connect scan are low impact; -sV, -O, -A and
      NSE (especially vuln/brute/dos categories) are intrusive and need explicit
      client sign-off and an agreed window
    - keep -oA output per target as the evidence trail; note scan start/stop times
    - report: exposed / unexpected services, obsolete versions with known CVEs,
      SMB1 / weak TLS / anonymous access from NSE ; fix = close or firewall the
      port, patch/upgrade the service, disable legacy protocols, restrict by source

###SCANNING OPTIONS###

nmap -sn 200.200.0.0/16
nmap -sn 200.200.123.1-12
nmap -sn 172.16.12.*
nmap -sn 200.200.12-13.*

-T 0-5 scan speed
0 - 5 min between packets
1 - 15 sec between packets
2 - 0.4 sec between packets
3 - normal default
4 - aggressive safe to use
5 - very fast
--scan-delay 0.1   #slow down
--max-parallelism 1   #scan 1 port at a time per host
--max-retries 0   #no recuirement to retry scanning ports if failed

key v increase verbosity V decrease verbosity
key d increase debugging D decrease debugging

-sn #host discovery, disables port scanning
-Pn #assume host is up, disables ICMP Echo Requests
--send-ip 127.0.0.1 #no arp
-sT #TCP
-sU #UDP
-sV #protocol version scan
-sC #default nmap scripts

sudo nmap --script-updatedb  #update scripts

sudo nmap -sV <target> --script <script-name>,<script-name>,...  #use -sV to find version before running script
	--script=[script,all,category,dir..]
		less /usr/share/nmap/scripts/script.db #all scripts
			smb2-security-mode
			smb-protocols
			smb-os-discovery
			ssh-auth-methods
	--script-help #script info
	--script-trace  #show commands used by nmap and responses
	--script-args arguments #pass args
	--script-args=smbuser=ADMIN,smbpass=ADMIN,config=config_file

Fuzzer: Send unexpected data
Intrusive: May leave logs, guess passwords
Malware: Detect malware or backdoor
Safe: Not designed to crash target
Version: Detect service version
Vuln: Look for a given vuln
Default: Scripts run when Nmap is run with -A or -sC
Auth: Test authentication
Broadcast: Look for target hosts via broadcasting
Brute: Brute force auth attempts
Discovery: Info gathering
Dos: May cause denial-of-service
Exploit: Exploit a vulnerability
External: Send information to third party for lookup


nmap --script smb-check-vulns.nse --script-args=unsafe=1 <IP> #check for SMB vulnerability
nmap --script vuln #check for vulnerabilitys

nmap --script-help "smb*" and discovery #will list all available scripts
nmap --script-help "*" #all scripts
nmap --script-help "http*" #all http scripts
nmap --script-help "http*" | grep "^http-"  #aonly http scripts names
nmap --script ipidseq IP -p PORT #can ID good zombie if ipidsec: incremental

script.db script info file
grep "safe or intrusive or any from above" /usr/local/share/nmap/scripts/script.db

###DNS###
nmap -sL <target>
Zero Network Traffic to Target: It does not send pings, stealth probes, or port scan packets to the destination hosts
DNS Resolution Check: It performs a reverse DNS (rDNS) resolution on the IP addresses to find their associated hostnames
Target Verification: It is used primarily to double-check a list of target IP addresses or subnets before launching an actual, intrusive scan.

nmap -sL --dns-servers <ip> <target>   #if not using DHCP
nmap -sL -n <target>   #Performs a list scan but disables DNS resolution (-n), making it completely silent and instant

DNS bruteforce attack
sudo nmap --script dns-brute --script-args dns-brute.domain=domain.com,dns-brute.threads=6,dns-brute.hostlist=./namelist.txt -sS -p 53  #namelist.txt is dictionary of common host names to bruteforce

###OUTPUT OPTIONS###

-oN fileoutput #normal output
-oG fileoutput #grep one liner output
-oX fileoutput #XML output
-oA fileoutput #stores in 3 files ^^^

xsltproc nmap_file.xml -o nmap_file.html   #Generates HTML output for web browser

ndiff scan1.xml scan2.xml  #compare 2 nmap scans

nmap -A will give os and more detailed scan
	-A # -O -sV -sC --traceroute

nmap -sn -iL hostlist.txt #scan all ip ranges from txt list

nmap -sn IP --disable-arp-ping #forces to use ICMP packets with TCP

nmap -O #will give OS
	#TTL 64 is UNIX/Linux, TTL 128 is Windows, TTL 254 is AIX/Solaris

nmap -Pn -O #will tell nmap that target is active and possibly drops ping scan

###HOST DISCOVERY###

  -sL: List Scan - simply list targets to scan
  -sn: Ping Scan - disable port scan
  -Pn: Treat all hosts as online -- skip host discovery/ disable ICMP echo request
  -PS/PA/PU/PY[portlist]: TCP SYN/ACK, UDP or SCTP discovery to given ports
  -PE/PP/PM: ICMP echo, timestamp, and netmask request discovery probes
  -PO[protocol list]: IP Protocol Ping
  -n/-R: Never do DNS resolution/Always resolve [default: sometimes]
  --dns-servers <serv1[,serv2],...>: Specify custom DNS servers
  --system-dns: Use OS's DNS resolver
  --traceroute: Trace hop path to each host
  --packet-trace	Shows all packets sent and received.
  --reason	Displays the reason for a specific result.
  --disable-arp-ping	Disables ARP Ping Requests.
  --open #only show open ports
  -F #scan top 100 ports
  --top-ports N #scan for the N most popular ports

###SCAN TECHNIQUES###

  -sS/sT/sA/sW/sM: TCP SYN/Connect()/ACK/Window/Maimon scans
  -sU: UDP Scan
  -sN/sF/sX: TCP Null, FIN, and Xmas scans #target ports protected by firewall

  -sN #Null scan TCP flag header is 0  *\\
  -sF #FIN scan only set TCP FIN bit   **> Forces to return RST packet back if closed
  -sX #Xmas scan FIN, PSH, URG flags   */

  --scanflags <flags>: Customize TCP scan flags
  -sI <zombie host[:probeport]>: Idle scan
  -sY/sZ: SCTP INIT/COOKIE-ECHO scans
  -sO: IP protocol scan
  -b <FTP relay host>: FTP bounce scan #targets file share server

  -sT #TCP connect scan
  -sS #SYN scan, more stelth without completing connection, still can be detected
  -sA #performs an TCP ACK-Scan
  -sV #version detect

###PORTS###

	open		#connection to the scanned port has been established, can be TCP connections, UDP datagrams as well as SCTP associations
	closed		#TCP protocol indicates that the packet we received back contains an RST flag, can also be used to determine if our target is alive or not
	filtered	#no response is returned or we get an error code from the target
	unfiltered	#only occurs during the TCP-ACK scan and means that the port is accessible, but it cannot be determined whether it is open or closed
	open|filtered	#no response, indicates that a firewall or packet filter may protect the port
	closed|filtered	#only occurs in the IP ID idle scans and indicates that it was impossible to determine if the scanned port is closed or filtered by a firewall

nmap -p 21,22,139,445,443,80 target
nmap -p 100-1000 target
# -p- scan all 65535 ports
# -F scan top 100 # top 1000 is default

less /usr/share/nmap/nmap-service-probes #matching rules/protocols applyed by nmap
	/string #use to search for string

less /usr/share/nmap/scripts/script.db #all scripts available safe/discover/intrusive/...
	cd /usr/share/nmap/scripts/ #script .nse location

less /usr/share/nmap/nmap-services #show ratings for top ports

65535 ports
Source port typically ephemeral
Linux  		32768–61000
BSD<4.6  	1024–5000
Windows XP  	1025–5000
Server 2008  	49152–65535
2008 + Exchange	1025–60000

Destination port must be known
Typically < 1024, but not a requirement

            20 FTP data
            21 FTP control
            22 SSH
            23 telnet
            80,443 HTTP/HTTPS web server
            445 Windows shares SMB
            25 SMTP simple mail transfer protocol
            135 NetBIOS over TCP
            137-139 Windows NetDIOS services
            1433-1434 MSSQL Database
            3306 MySQL Database
            3389 RDP
            8080,8443 HTTP(s) web server, HTTP Proxy
            53 DNS
            5985/5986 WinRM

###EXTRA###

#arrow up will display status
-D RND:5	Sets the number of random Decoys that will be used to scan the target.
-e	Specifies the network interface that is used for the scan.
-S 10.10.10.200	Specifies the source IP address for the scan.
-g	Specifies the source port for the scan.
--dns-server <ns>	DNS resolution is performed by using a specified name server.

Performance Options
--max-retries <num>	Sets the number of retries for scans of specific ports.
--stats-every=5s	Displays scan's status every 5 seconds.
-v/-vv	Displays verbose output during the scan.
--initial-rtt-timeout 50ms	Sets the specified time value as initial RTT timeout.
--max-rtt-timeout 100ms	Sets the specified time value as maximum RTT timeout.
--min-rate 300	Sets the number of packets that will be sent simultaneously.

nmap --reason #explain why port identifyed us open or closed

!!! can tcpdump in background

1) sudo nmap 10.10.10.0/24 -sn -oA tnet | grep for | cut -d" " -f5   #prints host IP only
	#-oA tnet		Stores the results in all formats starting with the name 'tnet'
2) sudo nmap -sn -oA tnet -iL hosts.lst   #Performs defined scans against targets in provided 'hosts.lst'
3) sudo nmap 10.10.10.10 -sn -oA host -PE --packet-trace   #--packet-trace option ensure that ICMP echo requests are sent, we also define the option (-PE)
	#-PE			Performs the ping scan by using 'ICMP Echo requests' against the target
	#--packet-trace		Shows all packets sent and received
	#--reason		Displays the reason for specific result
	#--disable-arp-ping	Disable ARP pings, use ICMP echo requests
4) sudo nmap 10.10.10.10 -p 443 --packet-trace --disable-arp-ping -Pn -n --reason -sT #SYN-ACK connection request
5) sudo nmap 10.10.10.10 -n -Pn -p 445 -O -S 10.10.100.1 --source-port 53 -e tun0   #Scan with different IP through specified interface
6) sudo nmap -oA /opt/SKELETON/working/Test -T 2 -Pn -sT -sV -O --reason -v -D RND:10 --source-port 53 --disable-arp-ping --packet-trace -n --max-retries 5 10.10.10.10

###BEST-PRACTICE ADDITIONS###

recommended workflow (fold into the numbered examples above)
    sudo nmap -sn -T4 -oA disc 10.0.0.0/24                  host discovery only
    sudo nmap -p- --min-rate 2000 -T4 -Pn -oA full <host>   every TCP port, fast
    sudo nmap -sC -sV -O -p<open ports> -oA deep <host>     scripts + versions + OS on what is open
    sudo nmap -sU --top-ports 100 -oA udp <host>            common UDP
    sudo nmap -sV --script vuln -p<open ports> -oA vuln <host>   named-vuln pass (intrusive - get sign-off)

useful one-liners
    nmap --top-ports 1000 -T4 <host>                        quick triage without -p-
    nmap -p- --min-rate 5000 -Pn -n -oG - <host> | ...      grep-friendly output to a pipe
    nmap -sC -sV -p445,139 --script "smb-* and not brute" <host>   safe SMB scripts only
    nmap -sV -p443 --script ssl-enum-ciphers <host>         TLS cipher / protocol audit
    nmap -6 -sC -sV <ipv6-host>                             IPv6 target
    nmap --resume full.gnmap                                continue an interrupted scan
    nmap -iL hosts.lst -sV -oA sweep                        scan a target file
    ncat / nmap-services / nmap-service-probes ship with the package

timing / stability notes
    - default is -T3; -T4 is the usual engagement choice on modern LANs
    - fragile targets: -T2 --scan-delay 100ms --max-retries 1 --host-timeout 15m
    - --min-rate sets a floor, --max-rate a ceiling (packets/sec); prefer these to -T on WAN links
    - --stats-every 30s and pressing v / d during a scan show progress

nmap xml reporting & gnmap port extraction
  convert xml scan to html:
    xsltproc scan.xml -o scan.html

  extract open tcp ports from gnmap:
    grep -oP '\d+/open' scan.gnmap | cut -d/ -f1 | sort -un | paste -sd, -
'''

#GUI

#Creates $guibox window to populate all the gui
guibox = Tk()
guibox.title('enum_nmap  —  nmap - detailed port / version / OS / vuln scanning')   #window title: tool name + purpose

# Get screen width and height
screen_width = guibox.winfo_screenwidth()
screen_height = guibox.winfo_screenheight()

# Set the window size to half the screen width and full screen height
guibox.geometry(f"{screen_width // 2}x{screen_height}")  # Half of the screen width, full height

# Position the window on the right half of the screen
guibox.geometry(f"+{screen_width // 2}+0")  # This positions the window at the right side, starting from (screen_width // 2)


checkbox_ports_var = IntVar(guibox)
checkbox_ports_var_default = IntVar(guibox)
T_options = [
    '0 - 5 min between packets',
    '1 - 15 sec between packets',
    '2 - 0.4 sec between packets',
    '3 - normal default',
    '4 - aggressive safe to use',
    '5 - very fast'
]
T_selected = StringVar(guibox)
T_selected.set(T_options[4])
sn_box_var = StringVar(guibox)
Pn_box_var = StringVar(guibox)
sT_box_var = StringVar(guibox)
sU_box_var = StringVar(guibox)
sV_box_var = StringVar(guibox)
sS_box_var = StringVar(guibox)
O_box_var = StringVar(guibox)
A_box_var = StringVar(guibox)
sC_box_var = StringVar(guibox)
sL_box_var = StringVar(guibox)
sN_box_var = StringVar(guibox)
sF_box_var = StringVar(guibox)
sX_box_var = StringVar(guibox)

#Define functions

def NEW_Terminal():
  subprocess.call(["gnome-terminal"])


def RUN_in_terminal(cmd):
    subprocess.call(['gnome-terminal -- bash -c ' + shlex.quote(cmd + ' ; exec bash')], shell=True)

def RUN_fast_all_tcp():
    target = shlex.quote(IP_name_entry.get().strip() or "10.10.10.10")
    outfile = shlex.quote(str(WORKING_DIR / (os.path.basename(Output_label_entry.get().strip()) or "nmap_out")))
    cmd = "sudo nmap -Pn -p- --min-rate 2000 -T4 --open -oA " + outfile + "_alltcp " + target
    RUN_in_terminal(cmd)

def RUN_top_udp():
    target = shlex.quote(IP_name_entry.get().strip() or "10.10.10.10")
    outfile = shlex.quote(str(WORKING_DIR / (os.path.basename(Output_label_entry.get().strip()) or "nmap_out")))
    cmd = "sudo nmap -Pn -sU --top-ports 100 --open -oA " + outfile + "_udp " + target
    RUN_in_terminal(cmd)

def RUN_html_report():
    outfile = shlex.quote(str(WORKING_DIR / (os.path.basename(Output_label_entry.get().strip()) or "nmap_out")))
    cmd = "xsltproc " + outfile + ".xml -o " + outfile + ".html"
    RUN_in_terminal(cmd)

def VULN_scan():
  nmap_string = " -sV --script vulners --script-args mincvss=4 " + Extra_label_entry.get() + " " + shlex.quote(IP_name_entry.get())
  current_time = datetime.now()
  current_time_value = "\n" + "Time stamp: " + current_time.strftime("%d-%b-%Y (%H:%M:%S.%f)") + " - nmap" + nmap_string + "\n"
  text_box.insert('end', current_time_value)
  text_box.yview('end')
  with open(WORKING_DIR / "working_file.txt", "w") as f:  # Open the file for writing
      f.write(current_time_value + "\n")  # Write the text to the file
      time.sleep(0.01)
  own(WORKING_DIR / "working_file.txt")  # nmap needs root; the notes do not
  start_nmap = subprocess.call(['gnome-terminal -- bash -c ' + shlex.quote('nmap' + nmap_string + ' | tee -a ' + str(WORKING_DIR / "working_file.txt") + ' ; exec bash')], shell = True) #opens set nmap in terminal


def START_nmap():
  T_value = T_selected.get()
  # basename + a fallback, like every other module's save-file box: a name
  # with a slash in it made WORKING_DIR / name land somewhere else entirely
  # (an absolute one discards the working dir), so the -oA files - the whole
  # evidence trail this module exists to leave - went where the notes tab and
  # the Runs panel do not look.
  out = shlex.quote(str(WORKING_DIR / (os.path.basename(
      Output_label_entry.get().strip()) or "nmap_out")))
  if sn_box_var.get() == " -sn":
    nmap_string = " -oA " + out + " -T " + T_value[0] + sn_box_var.get() + " " + Extra_label_entry.get() + " " + shlex.quote(IP_name_entry.get())
  elif checkbox_ports_var.get() == 1:
    n_ports = " -p-"
    nmap_string = n_ports + " -oA " + out + " -T " + T_value[0] + Pn_box_var.get() + sT_box_var.get() + sU_box_var.get() + sV_box_var.get() + sS_box_var.get() + O_box_var.get() + A_box_var.get() + sC_box_var.get() + sL_box_var.get() + sN_box_var.get() + sF_box_var.get() + sX_box_var.get() + " " + Extra_label_entry.get() + " " + shlex.quote(IP_name_entry.get())
  elif checkbox_ports_var_default.get() == 1:
    nmap_string = " -oA " + out + " -T " + T_value[0] + Pn_box_var.get() + sT_box_var.get() + sU_box_var.get() + sV_box_var.get() + sS_box_var.get() + O_box_var.get() + A_box_var.get() + sC_box_var.get() + sL_box_var.get() + sN_box_var.get() + sF_box_var.get() + sX_box_var.get() + " " + Extra_label_entry.get() + " " + shlex.quote(IP_name_entry.get())
  else:
    n_ports = " -p " + Port_label_entry.get()
    nmap_string = n_ports + " -oA " + out + " -T " + T_value[0] + Pn_box_var.get() + sT_box_var.get() + sU_box_var.get() + sV_box_var.get() + sS_box_var.get() + O_box_var.get() + A_box_var.get() + sC_box_var.get() + sL_box_var.get() + sN_box_var.get() + sF_box_var.get() + sX_box_var.get() + " " + Extra_label_entry.get() + " " + shlex.quote(IP_name_entry.get())
  current_time = datetime.now()
  current_time_value = "\n" + "Time stamp: " + current_time.strftime("%d-%b-%Y (%H:%M:%S.%f)") + " - nmap" + nmap_string + "\n"
  text_box.insert('end', current_time_value)
  text_box.yview('end')
  with open(WORKING_DIR / "working_file.txt", "w") as f:  # Open the file for writing
        f.write(current_time_value + "\n")  # Write the text to the file
  own(WORKING_DIR / "working_file.txt")  # nmap needs root; the notes do not

  start_nmap = subprocess.call(['gnome-terminal -- bash -c ' + shlex.quote('nmap' + nmap_string + ' | tee -a ' + str(WORKING_DIR / "working_file.txt") + ' ; exec bash')], shell = True) #opens set nmap in terminal


#Grid Frames
frame_message = Frame(guibox)
frame_message.pack(padx=5, pady=5, fill=BOTH, expand=True)

frame_main = Frame(guibox)
frame_main.pack(padx=5, pady=0)

frame_buttons1 = Frame(frame_main)
frame_buttons1.grid(row=0, column=0, padx=5, pady=0)

frame_ip = Frame(frame_main)
frame_ip.grid(row=1, column=0, padx=5, pady=0)

frame_ports = Frame(frame_main)
frame_ports.grid(row=2, column=0, padx=5, pady=5)

frame_output = Frame(frame_main)
frame_output.grid(row=3, column=0, padx=5, pady=0)

frame_box1 = Frame(frame_main)
frame_box1.grid(row=4, column=0, padx=5, pady=0)

frame_box2 = Frame(frame_main)
frame_box2.grid(row=5, column=0, padx=5, pady=0)

frame_box3 = Frame(frame_main)
frame_box3.grid(row=6, column=0, padx=5, pady=0)

frame_buttons2 = Frame(frame_main)
frame_buttons2.grid(row=7, column=0, padx=5, pady=0)

#interface
text_box = Text(   #creates text box inside frame_message with the info text
    frame_message,
    wrap=WORD,
    height=15,
    width=80
)

text_box.insert('end', info)   #adds info to the end of text_box
text_box.pack(side=LEFT, fill=BOTH, expand=True)   #config for slider variant
text_box.yview('1.0')

sb = Scrollbar(frame_message)   #assign scrollbar
sb.pack(side=RIGHT, fill=BOTH)   #scrollbar configuration

text_box.config(yscrollcommand=sb.set)   #set scrollbar on y axis
sb.config(command=text_box.yview)

IP_name_label = Label(frame_ip,text="IP range EX 10.10.0.0/16, 10.10.0.1-12, 172.16.12.*, 10.10.12-13.*")
IP_name_label.grid(row=1, column = 0, padx=5, pady=5)

IP_name_entry = Entry(frame_ip, width=42)   #entry field for IP range
IP_name_entry.grid(row=1, column = 1, padx=5, pady=5)
IP_name_entry.insert(0, os.environ.get("SKELETON_TARGET", "Enter_IP_range"))

Port_label = Label(frame_ports,text="Port range EX 443,80,100-1000")
Port_label.grid(row=1, column = 0, padx=5, pady=5)

Port_label_entry = Entry(frame_ports, width=35)   #entry field for port range
Port_label_entry.grid(row=1, column = 1, padx=5, pady=5)
Port_label_entry.insert(0, "Enter_port_range_to_scan_or_select")

checkbox_ports = Checkbutton(frame_ports, text="All 65535 ports", variable=checkbox_ports_var, onvalue=1, offvalue=0)
checkbox_ports.grid(row=1, column = 2, padx=5, pady=5)

checkbox_ports_default = Checkbutton(frame_ports, text="Default Top 1000", variable=checkbox_ports_var_default, onvalue=1, offvalue=0)
checkbox_ports_default.grid(row=1, column = 3, padx=5, pady=5)

Output_label = Label(frame_output,text="Output file name ")
Output_label.grid(row=1, column = 0, padx=5, pady=5)

Output_label_entry = Entry(frame_output, width=35)   #entry field for output file name
Output_label_entry.grid(row=1, column = 1, padx=5, pady=5)
Output_label_entry.insert(0, "Enter_output_file_name")

T_label = Label(frame_output,text="-T 0-5 scan speed ")
T_label.grid(row=1, column = 2, padx=5, pady=5)

T_options_box = OptionMenu(frame_output, T_selected, *T_options)
T_options_box.grid(row=1, column = 3, padx=5, pady=5)

sn_box = Checkbutton(frame_box1, text="-sn #host discovery, run by it self", variable=sn_box_var, onvalue=" -sn", offvalue="")
sn_box.grid(row=1, column = 0, padx=0, pady=5)

Pn_box = Checkbutton(frame_box1, text="-Pn #assume host is up", variable=Pn_box_var, onvalue=" -Pn", offvalue="")
Pn_box.grid(row=1, column = 1, padx=0, pady=5)

sT_box = Checkbutton(frame_box1, text="-sT #TCP", variable=sT_box_var, onvalue=" -sT", offvalue="")
sT_box.grid(row=1, column = 2, padx=0, pady=5)

sU_box = Checkbutton(frame_box1, text="-sU #UDP", variable=sU_box_var, onvalue=" -sU", offvalue="")
sU_box.grid(row=1, column = 3, padx=0, pady=5)

sV_box = Checkbutton(frame_box1, text="-sV #version scan", variable=sV_box_var, onvalue=" -sV", offvalue="")
sV_box.grid(row=1, column = 4, padx=0, pady=5)

sS_box = Checkbutton(frame_box2, text="-sS #SYN scan", variable=sS_box_var, onvalue=" -sS", offvalue="")
sS_box.grid(row=1, column = 0, padx=0, pady=5)

O_box = Checkbutton(frame_box2, text="-O #will give OS", variable=O_box_var, onvalue=" -O", offvalue="")
O_box.grid(row=1, column = 1, padx=0, pady=5)

A_box = Checkbutton(frame_box2, text="-A # -O -sV -sC --traceroute", variable=A_box_var, onvalue=" -A", offvalue="")
A_box.grid(row=1, column = 2, padx=0, pady=5)

sC_box = Checkbutton(frame_box2, text="-sC #default nmap scripts", variable=sC_box_var, onvalue=" -sC", offvalue="")
sC_box.grid(row=1, column = 3, padx=0, pady=5)

sL_box = Checkbutton(frame_box2, text="-sL #reverse DNS", variable=sL_box_var, onvalue=" -sL", offvalue="")
sL_box.grid(row=1, column = 4, padx=0, pady=5)

sN_box = Checkbutton(frame_box3, text="-sN #Null scan TCP flag header is 0", variable=sN_box_var, onvalue=" -sN", offvalue="")
sN_box.grid(row=1, column = 0, padx=0, pady=5)

sF_box = Checkbutton(frame_box3, text="-sF #FIN scan only set TCP FIN bit", variable=sF_box_var, onvalue=" -sF", offvalue="")
sF_box.grid(row=1, column = 1, padx=0, pady=5)

sX_box = Checkbutton(frame_box3, text="-sX #Xmas scan FIN, PSH, URG flags", variable=sX_box_var, onvalue=" -sX", offvalue="")
sX_box.grid(row=1, column = 2, padx=0, pady=5)

Extra_label = Label(frame_buttons2,text="Additional switches")
Extra_label.grid(row=2, column = 0, padx=5, pady=5)

Extra_label_entry = Entry(frame_buttons2, width=30)   #entry field for extrta switches
Extra_label_entry.grid(row=2, column = 1, padx=5, pady=5)
Extra_label_entry.insert(0, "--reason -v --open")

SCAN_button = Button(frame_buttons2, text=" Start Nmap ", command=START_nmap)
SCAN_button.grid(row=2, column=2, padx=5, pady=5)

VULN_button = Button(frame_buttons2, text=" VULN Scan ", command=VULN_scan)
VULN_button.grid(row=2, column=3, padx=5, pady=5)

NEW_button = Button(frame_buttons2, text=" NEW Terminal ", command=NEW_Terminal)
NEW_button.grid(row=2, column=4, padx=5, pady=5)



frame_buttons3 = Frame(frame_main)
frame_buttons3.grid(row=5, column=0, columnspan=8, padx=5, pady=4)

FAST_tcp_btn = Button(frame_buttons3, text=" FAST All-TCP (-p- --min-rate 2000) ", command=RUN_fast_all_tcp)
FAST_tcp_btn.grid(row=0, column=0, padx=5, pady=5)

TOP_udp_btn = Button(frame_buttons3, text=" TOP 100 UDP (-sU) ", command=RUN_top_udp)
TOP_udp_btn.grid(row=0, column=1, padx=5, pady=5)

HTML_report_btn = Button(frame_buttons3, text=" XML -> HTML (xsltproc) ", command=RUN_html_report)
HTML_report_btn.grid(row=0, column=2, padx=5, pady=5)

guibox.mainloop()   #generates guibox window#
