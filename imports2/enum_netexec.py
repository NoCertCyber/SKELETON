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

     ███╗   ██╗███████╗████████╗███████╗██╗  ██╗███████╗ ██████╗
     ████╗  ██║██╔════╝╚══██╔══╝██╔════╝╚██╗██╔╝██╔════╝██╔════╝
     ██╔██╗ ██║█████╗     ██║   █████╗   ╚███╔╝ █████╗  ██║
     ██║╚██╗██║██╔══╝     ██║   ██╔══╝   ██╔██╗ ██╔══╝  ██║
     ██║ ╚████║███████╗   ██║   ███████╗██╔╝ ██╗███████╗╚██████╗
     ╚═╝  ╚═══╝╚══════╝   ╚═╝   ╚══════╝╚═╝  ╚═╝╚══════╝ ╚═════╝

NetExec (nxc) - the maintained fork of CrackMapExec.  One tool to sweep and
attack SMB / WinRM / LDAP / MSSQL / SSH / RDP / FTP / WMI / VNC across a subnet:
auth checks, share/user/policy enum, password spraying, credential dumping, and
module-driven attacks.  The workhorse of internal AD tests.

install:  sudo apt-get install -y netexec     (binary: nxc  or  netexec)

when to use it
    - right after finding 445/5985/389/1433 open: `nxc smb <range>` for a free
      map of hosts, signing status, SMBv1, OS, domain
    - to validate a credential everywhere at once (and spot where it's local admin)
    - to spray a password across a user list (mind the lockout policy!)
    - to dump SAM/LSA/NTDS once you have local admin somewhere
    - `Pwn3d!` in the output = you have admin on that box

typical commands
    recon / auth
    $ nxc smb 10.10.10.0/24                                   # host list, signing, SMBv1, domain
    $ nxc smb 10.10.10.10 -u user -p 'Pass' --shares --sessions --loggedon-users --users --groups --pass-pol
    $ nxc smb 10.10.10.0/24 -u user -p 'Pass' -d corp.local --spider C\$ --pattern passw --content
    $ nxc smb 10.10.10.10 -u user -H <LMHASH:NTHASH> -x "whoami"      # pass-the-hash + exec
    $ nxc smb 10.10.10.10 -u user -p 'Pass' -k                        # Kerberos (ccache)
    $ nxc smb 10.10.10.10 -u user -p 'Pass' --local-auth             # local (non-domain) account

    spray (Pwn3d! = local admin on that host)
    $ nxc smb dc01 -u users.txt -p 'Spring2026!' --continue-on-success
    $ nxc smb 10.10.10.0/24 -u users.txt -p passwords.txt --no-bruteforce   # 1:1 user:pass pairing

    credential dumping (need admin)
    $ nxc smb 10.10.10.10 -u user -p 'Pass' --sam --lsa
    $ nxc smb dc01 -u user -p 'Pass' --ntds                          # DCSync-style NTDS dump
    $ nxc smb 10.10.10.10 -u user -p 'Pass' -M lsassy               # or nanodump / procdump / handlekatz

    other protocols
    $ nxc ldap dc01 -u user -p 'Pass' --bloodhound -c all -ns 10.10.10.10
    $ nxc ldap dc01 -u user -p 'Pass' --kerberoasting kr.txt --asreproast ar.txt
    $ nxc winrm 10.10.10.10 -u user -p 'Pass' -x "ipconfig"
    $ nxc mssql 10.10.10.10 -u sa -p 'Pass' --local-auth -q "SELECT @@version"
    $ nxc ssh 10.10.10.0/24 -u root -p passwords.txt

    modules
    $ nxc smb 10.10.10.10 -u user -p 'Pass' -L                       # list modules
    $ nxc smb 10.10.10.10 -u user -p 'Pass' -M gpp_password         # spider_plus, wdigest, coerce_plus, ...

    creds DB:  ~/.nxc/  (SQLite workspaces)  ->  nxc smb --dpapi / --use-kcache

pair with
    enum_bloodhound     ingest the --bloodhound zip; graph the path
    exploit_impacket    secretsdump / wmiexec / ntlmrelayx on the hosts it flags
    bruteforce_hashcat  crack the roasted / dumped hashes
    mitm_responder      capture creds to feed back into nxc spraying
    enum_ldap           deeper LDAP once nxc confirms the bind works

gotchas
    - spraying counts toward lockout - check --pass-pol first, throttle, and
      leave a buffer below the threshold
    - `--sam/--lsa/--ntds` are noisy and drop artefacts (services, files) - EDR
      will alert; prefer -M lsassy for stealthier LSASS access
    - SMB signing "True/Required" on a host means you can't relay to it
    - some modules need extra deps (lsassy, dploot) - `pipx inject netexec ...`

authorisation & reporting
    - auth checks and enum are low impact; spraying, exec and cred dumping are
      active and destructive-adjacent - explicit sign-off + target list + window
    - report: reused local admin creds, SMB signing not required, over-broad
      share ACLs, weak/again-no lockout policy, LAPS gaps

netexec multi-protocol & module reference
  unauthenticated smb signing sweep:
    nxc smb 10.10.10.0/24

  mssql execution:
    nxc mssql 10.10.10.10 -u sa -p pass -q "SELECT @@version"

  spider shares for passwords:
    nxc smb 10.10.10.10 -u user -p pass -M spider_plus
'''

#GUI

#Creates $guibox window to populate all the gui
guibox = Tk()
guibox.title('enum_netexec  —  NetExec (nxc) - swiss-army knife for AD / SMB / WinRM / MSSQL / LDAP')   #window title: tool name + purpose
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


def RUN_nxc_smb():
    if not target_entry.get().strip():
        LOG("Target IP is empty")
        return
    if not user_entry.get().strip():
        LOG("User name is empty")
        return
    if not password_entry.get().strip():
        LOG("Password is empty")
        return
    target = shlex.quote(target_entry.get().strip())
    user = shlex.quote(user_entry.get().strip())
    password = shlex.quote(password_entry.get().strip())
    switches = switches_entry.get()                    # free-form, left unquoted
    outfile = shlex.quote(str(WORKING_DIR / (os.path.basename(outfile_entry.get().strip()) or "netexec_out")))
    cmd = "nxc smb " + target + " -u " + user + " -p " + password + " " + switches + " | tee " + outfile
    RUN_in_terminal(cmd)


def RUN_nxc_ldap():
    if not target_entry.get().strip():
        LOG("Target IP is empty")
        return
    if not user_entry.get().strip():
        LOG("User name is empty")
        return
    if not password_entry.get().strip():
        LOG("Password is empty")
        return
    target = shlex.quote(target_entry.get().strip())
    user = shlex.quote(user_entry.get().strip())
    password = shlex.quote(password_entry.get().strip())
    switches = switches_entry.get()                    # free-form, left unquoted
    outfile = shlex.quote(str(WORKING_DIR / (os.path.basename(outfile_entry.get().strip()) or "netexec_out")))
    cmd = "nxc ldap " + target + " -u " + user + " -p " + password + " " + switches + " | tee " + outfile
    RUN_in_terminal(cmd)



def RUN_nxc_smb_SigningSweep():
    target = shlex.quote(target_entry.get().strip() or "10.10.10.0/24")
    outfile = shlex.quote(str(WORKING_DIR / (os.path.basename(outfile_entry.get().strip()) or "netexec_out")))
    cmd = "nxc smb " + target + " | tee " + outfile
    RUN_in_terminal(cmd)

def RUN_nxc_null_guest():
    target = shlex.quote(target_entry.get().strip() or "10.10.10.10")
    outfile = shlex.quote(str(WORKING_DIR / (os.path.basename(outfile_entry.get().strip()) or "netexec_out")))
    cmd = "nxc smb " + target + " -u '' -p '' --shares --users ; nxc smb " + target + " -u 'guest' -p '' --shares | tee " + outfile
    RUN_in_terminal(cmd)

def RUN_nxc_mssql():
    target = shlex.quote(target_entry.get().strip() or "10.10.10.10")
    user = user_entry.get().strip()
    password = password_entry.get().strip()
    auth = (" -u " + shlex.quote(user) + " -p " + shlex.quote(password)) if user else ""
    switches = switches_entry.get()
    outfile = shlex.quote(str(WORKING_DIR / (os.path.basename(outfile_entry.get().strip()) or "netexec_out")))
    cmd = "nxc mssql " + target + auth + " " + switches + " | tee " + outfile
    RUN_in_terminal(cmd)

def RUN_nxc_rdp():
    target = shlex.quote(target_entry.get().strip() or "10.10.10.10")
    user = user_entry.get().strip()
    password = password_entry.get().strip()
    auth = (" -u " + shlex.quote(user) + " -p " + shlex.quote(password)) if user else ""
    switches = switches_entry.get()
    outfile = shlex.quote(str(WORKING_DIR / (os.path.basename(outfile_entry.get().strip()) or "netexec_out")))
    cmd = "nxc rdp " + target + auth + " " + switches + " | tee " + outfile
    RUN_in_terminal(cmd)

def RUN_nxc_ssh():
    target = shlex.quote(target_entry.get().strip() or "10.10.10.10")
    user = user_entry.get().strip()
    password = password_entry.get().strip()
    auth = (" -u " + shlex.quote(user) + " -p " + shlex.quote(password)) if user else ""
    switches = switches_entry.get()
    outfile = shlex.quote(str(WORKING_DIR / (os.path.basename(outfile_entry.get().strip()) or "netexec_out")))
    cmd = "nxc ssh " + target + auth + " " + switches + " | tee " + outfile
    RUN_in_terminal(cmd)

def RUN_nxc_winrm():
    if not target_entry.get().strip():
        LOG("Target IP is empty")
        return
    if not user_entry.get().strip():
        LOG("User name is empty")
        return
    if not password_entry.get().strip():
        LOG("Password is empty")
        return
    target = shlex.quote(target_entry.get().strip())
    user = shlex.quote(user_entry.get().strip())
    password = shlex.quote(password_entry.get().strip())
    switches = switches_entry.get()                    # free-form, left unquoted
    outfile = shlex.quote(str(WORKING_DIR / (os.path.basename(outfile_entry.get().strip()) or "netexec_out")))
    cmd = "nxc winrm " + target + " -u " + user + " -p " + password + " " + switches + " | tee " + outfile
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

target_label = Label(frame_fields, text="Target IP: ")
target_label.grid(row=0, column=0, padx=5, pady=4, sticky='e')
target_entry = Entry(frame_fields, width=46)
target_entry.grid(row=0, column=1, padx=5, pady=4)
target_entry.insert(0, os.environ.get("SKELETON_TARGET", "10.10.10.10"))

user_label = Label(frame_fields, text="User name: ")
user_label.grid(row=1, column=0, padx=5, pady=4, sticky='e')
user_entry = Entry(frame_fields, width=24)
user_entry.grid(row=1, column=1, padx=5, pady=4)
user_entry.insert(0, os.environ.get("SKELETON_USER", ""))

password_label = Label(frame_fields, text="Password: ")
password_label.grid(row=2, column=0, padx=5, pady=4, sticky='e')
password_entry = Entry(frame_fields, width=24)
password_entry.grid(row=2, column=1, padx=5, pady=4)
password_entry.insert(0, os.environ.get("SKELETON_PASS", ""))

switches_label = Label(frame_fields, text="Additional switches: ")
switches_label.grid(row=3, column=0, padx=5, pady=4, sticky='e')
switches_entry = Entry(frame_fields, width=52)
switches_entry.grid(row=3, column=1, padx=5, pady=4)
switches_entry.insert(0, "--shares --users --pass-pol")

outfile_label = Label(frame_fields, text="Save-file name (no spaces): ")
outfile_label.grid(row=4, column=0, padx=5, pady=4, sticky='e')
outfile_entry = Entry(frame_fields, width=46)
outfile_entry.grid(row=4, column=1, padx=5, pady=4)
outfile_entry.insert(0, "netexec_out")

RUN_nxc_smb_button = Button(frame_buttons1, text=" RUN nxc smb ", command=RUN_nxc_smb)
RUN_nxc_smb_button.grid(row=0, column=0, padx=5, pady=5)

RUN_nxc_ldap_button = Button(frame_buttons1, text=" RUN nxc ldap ", command=RUN_nxc_ldap)
RUN_nxc_ldap_button.grid(row=0, column=1, padx=5, pady=5)

RUN_nxc_winrm_button = Button(frame_buttons1, text=" RUN nxc winrm ", command=RUN_nxc_winrm)
RUN_nxc_winrm_button.grid(row=0, column=2, padx=5, pady=5)

NEW_button = Button(frame_buttons1, text=" NEW Terminal ", command=NEW_Terminal)
NEW_button.grid(row=0, column=3, padx=5, pady=5)


frame_buttons2 = Frame(frame_main)
frame_buttons2.grid(row=4, column=0, columnspan=8, padx=5, pady=4)

SMB_sweep_btn = Button(frame_buttons2, text=" RUN nxc smb sweep (no-auth) ", command=RUN_nxc_smb_SigningSweep)
SMB_sweep_btn.grid(row=0, column=0, padx=5, pady=5)

NULL_guest_btn = Button(frame_buttons2, text=" RUN nxc null + guest ", command=RUN_nxc_null_guest)
NULL_guest_btn.grid(row=0, column=1, padx=5, pady=5)

MSSQL_btn = Button(frame_buttons2, text=" RUN nxc mssql ", command=RUN_nxc_mssql)
MSSQL_btn.grid(row=0, column=2, padx=5, pady=5)

RDP_btn = Button(frame_buttons2, text=" RUN nxc rdp ", command=RUN_nxc_rdp)
RDP_btn.grid(row=0, column=3, padx=5, pady=5)

SSH_btn = Button(frame_buttons2, text=" RUN nxc ssh ", command=RUN_nxc_ssh)
SSH_btn.grid(row=0, column=4, padx=5, pady=5)

guibox.mainloop()   #generates guibox window
