# SKELETON (Demo Edition)

[![Edition](https://img.shields.io/badge/Edition-Demo%20(20%20Core%20Tools)-blue.svg)](#demo-vs-full-edition)
[![Full Version](https://img.shields.io/badge/Full%20Arsenal-233%2B%20Tools%20($30%20AUD)-success.svg)](https://payhip.com/b/dR8ng)
[![Platform](https://img.shields.io/badge/Platform-Kali%20Linux%20%7C%20Parrot%20OS-black.svg)](#requirements)
[![Python](https://img.shields.io/badge/Python-3.8%2B-brightgreen.svg)](#requirements)
[![YouTube](https://img.shields.io/badge/YouTube-@nocertcyber-red.svg)](https://www.youtube.com/@nocertcyber)
[![Patreon](https://img.shields.io/badge/Patreon-NoCertCyber-FF424D.svg)](https://www.patreon.com/nocertcyber)

> **The Offline Penetration Testing & OSCP Workbench.**  
> Stop memorizing hundreds of command switches or losing track of notes during 24-hour exams, lab challenges, and fieldwork. SKELETON pairs curated, battle-tested cheat sheets with auto-filling inputs, live streaming `xterm.js` terminals, and automatic engagement logging — completely offline in your browser.

---

### ⚡ Quick Links
* **[🚀 Try the Demo](#quick-start)**
* **[💎 Get Full Version — $30 AUD (~$20 USD) (Instant Access on Payhip)](https://payhip.com/b/dR8ng)**
* **[📺 Video Guides & Walkthroughs (YouTube @nocertcyber)](https://www.youtube.com/@nocertcyber)**
* **[💬 Support & Community (Patreon)](https://www.patreon.com/nocertcyber)**

---

## Demo vs. Full Edition

This repository is the official **SKELETON Demo Edition**, designed to let security professionals, OSCP/PNPT students, and CTF players experience the workflow hands-on with 20 flagship tools. 

To unlock the full 233-tool arsenal across all 12 engagement stages, grab the **Full Version** on Payhip.

| Capability / Feature | Demo Edition (This Repo) | Full Edition ($30 AUD) |
|---|:---:|:---:|
| **Included Interactive Modules** | 20 Flagship Tools | **233+ Complete Tools** |
| **Complete Reference Glossary** | ✅ Included (All 233 tools) | **✅ Included (All 233 tools)** |
| **Auto Session Autofill (Target/LHOST/Creds)** | ✅ Included | **✅ Included** |
| **Embedded `xterm.js` Streaming Terminal** | ✅ Included | **✅ Included** |
| **Live Command & Output Logging to Notes** | ✅ Included | **✅ Included** |
| **Multiple Named Notes Tabs & Save/Load** | ✅ Included | **✅ Included** |
| **Network & IP Configuration Helpers** | ✅ Included | **✅ Included** |
| **Active Directory Arsenal** *(NetExec, BloodHound, Mimikatz, Certipy, Coercer, BloodyAD)* | Reference only | **⚡ Full Interactive Execution** |
| **Web Exploitation Suite** *(ffuf, sqlmap, nuclei, GraphQL, JWT, SSTI, SSRF, Uploads)* | Core web tools only | **⚡ Full 29-tool Suite** |
| **Pivoting & Tunnels** *(chisel, ligolo-ng, sshuttle, frp, reGeorg, DNS/ICMP)* | Netcat only | **⚡ Full 15-tool Pivoting Arsenal** |
| **Wireless & BLE Suite** *(airodump, wifite, airgeddon, bettercap, evil twin)* | airodump only | **⚡ Full 29-tool Suite** |
| **Binary & Memory Forensics** *(Volatility, Ghidra, capa, Cutter, deepbluecli)* | Wireshark only | **⚡ Full 24-tool Suite** |
| **Lifetime Access & Future Updates** | Manual pull | **⚡ Instant Download + Future Tool Updates** |
| **Instant Access** | Free Download | **[👉 Buy Full Version on Payhip ($30 AUD)](https://payhip.com/b/dR8ng)** |

---

## Why SKELETON?

### 1. No More Copy-Paste Syntax Errors
Every tool module features standard, validated field vocabulary (`Target IP:`, `Target url / domain:`, `LHOST`, `LPORT`, `User name:`, `Password:`). Set your engagement target once in the header: every module opened afterwards automatically pre-fills with green indicators.

### 2. Real Interactive Terminals, Not Dumb Transcripts
Each module opens a genuine `xterm.js` terminal session streamed over a shared single SSE connection (`SharedWorker`). Long-running tools (`nmap -p-`, `gobuster`, `hashcat`) render output in real time. Need to enter a password prompt or press `Ctrl-C`? You can interact directly with the process.

### 3. Automatic Evidence & Run Logging
Every command fired through a button or typed in the terminal is automatically time-stamped and appended to your active **Notes pane** and saved to `working/<tab>/runs.jsonl`. When it's time to write your exam or client report, your complete audit trail is already formatted and ready.

### 4. 100% Offline & Engagement-Safe
SKELETON binds strictly to `127.0.0.1` and requires zero external cloud connections. The privilege stops at the tools: although root privileges are used to execute tools requiring raw sockets or packet capture, SKELETON automatically reclaims ownership of all generated output files so your standard user owns every piece of evidence.

---

## Quick Start

### 1. Requirements
- Linux (tested on **Kali Linux**, **Parrot OS**, and **Debian/Ubuntu**)
- Python 3 with `flask` and `xvfb` (`sudo apt install python3-flask xvfb net-tools`)

### 2. Launch SKELETON
```bash
# Clone the repository
git clone https://github.com/NoCertCyber/SKELETON.git /opt/SKELETON
cd /opt/SKELETON

# Start the local web workbench
sudo python3 SKELETON_WEB.py
```

Open your browser and navigate to:
```
http://127.0.0.1:80
```

---

## The 12 Attack Chain Stages

SKELETON categorizes penetration testing tools along the natural progression of an engagement:

| Stage | Modules | What It Covers |
|---|:---:|---|
| `info` | 16 | Cheat sheets: payload generation, encoding, ATT&CK, Linux/Windows methodology, glossary |
| `OSIN` | 14 | Passive recon: Amass, Shodan, theHarvester, SpiderFoot, Google dorking, breach data |
| `DNS` | 11 | Zone transfers (AXFR), certificate transparency, subdomain enumeration, whois |
| `enum` | 27 | Active service discovery: Nmap, NetExec, BloodHound, LDAP, SMB, SNMP, NFS, Trivy |
| `web` | 29 | Web application testing: ffuf, nuclei, sqlmap, XSS/SSTI/SSRF, JWT, GraphQL |
| `mitm` | 13 | On-path attacks: Responder, mitm6, ettercap, arpspoof, tcpdump, PCredz |
| `wireless` | 29 | 802.11 and BLE: airodump, hashcat, reaver, wifite, evil twin, Kismet |
| `bruteforce` | 12 | Password auditing: Hydra, Hashcat, John the Ripper, Kerbrute, custom wordlists |
| `exploit` | 36 | Exploitation & privesc: Metasploit, Impacket, Mimikatz, C2 frameworks, LinPEAS/WinPEAS |
| `powershell` | 7 | Offensive PowerShell: AMSI bypass, Nishang, reverse shells, active directory scripts |
| `transfer` | 15 | Pivoting & exfiltration: Chisel, Ligolo-ng, sshuttle, SOCKS proxies, encrypted tunnels |
| `forensic` | 24 | DFIR & reverse engineering: Volatility, Wireshark, Ghidra, capa, event log analysis |

---

## Featured in Demo Edition

The 21 flagship tools unlocked for full interactive execution in this Demo Edition:

1. `info_glossary` — Built-in 233-tool glossary and quick reference search
2. `info_revshell_generator` — Instant reverse shell generator (Bash, Python, Perl, PowerShell, Socat)
3. `info_linux` — Essential Linux privilege escalation and enumeration commands
4. `OSIN_theharvester` — Reconnaissance and email/subdomain discovery
5. `OSIN_shodan` — Internet-connected device intelligence queries
6. `DNS_axfr` — DNS zone transfer audit and nameserver checks
7. `DNS_nslookup` — Manual record verification and mail routing checks
8. `enum_nmap` — Fast port scanning, service versioning, and NSE scripts
9. `enum_netexec` — Active Directory & SMB network sweep framework
10. `enum_arp` — Local subnet address resolution protocol sweeps
11. `web_gobuster` — High-speed URI directory and DNS brute forcing
12. `web_whatweb` — Web technology, CMS, and framework fingerprinter
13. `web_ffuf` — Advanced web fuzzing, parameters, and virtual hosts
14. `mitm_responder` — LLMNR, NBT-NS and mDNS poisoner and credential harvester
15. `wireless_airodump` — 802.11 packet capture and BSSID survey
16. `bruteforce_hydra` — Network login brute-forcer for SSH, FTP, RDP, HTTP
17. `exploit_basic_shell` — TTY upgrades, listener generators, and payload spawners
18. `exploit_searchsploit` — Offline Exploit-DB search and mirror utility
19. `powershell_info` — PowerShell offensive methodology and execution cheat sheet
20. `transfer_netcat` — Reliable file transfer, relays, and listener setup
21. `forensic_wireshark` — Packet capture inspection and protocol forensics

---

## Video Tutorials

Watch hands-on demos, tool deep dives, and engagement walkthroughs on YouTube:
* 📺 **Channel:** [@nocertcyber on YouTube](https://www.youtube.com/@nocertcyber)
* 📹 [NCC Cyber Security SKELETON Tool Overview](https://www.youtube.com/@nocertcyber)
* 📹 [Crazy Fast Nmap Scans with NCC SKELETON](https://www.youtube.com/@nocertcyber)

---

## Upgrade to Full Version

Unlock the entire 233-tool suite for a one-time payment of **$30 AUD** (~$20 USD / £15 GBP):
- Instant ZIP download with all 233 modules in `imports2/`
- Full command execution and automated argument assembly for every tool
- Complete Active Directory, Pivoting, Exploit, and Wireless suites
- Free lifetime updates as new tools and cheat sheets are added

👉 **[Get SKELETON Full Version on Payhip ($30 AUD)](https://payhip.com/b/dR8ng)**  
👉 **[Support Ongoing Development on Patreon](https://www.patreon.com/nocertcyber)**

---

## ❤️ Backers & Supporters

A huge thank you to the community members backing the ongoing development of SKELETON on [Patreon](https://www.patreon.com/nocertcyber):

* **Champions**: *Be the first Champion supporter!*
* **Backers**: Peter

Want your name or handle listed here? [Back SKELETON on Patreon](https://www.patreon.com/nocertcyber)

---

## Author & Security Notice

Created by **NoCertCyber** ([@nocertcyber](https://www.youtube.com/@nocertcyber)).

> **Authorisation Notice:** SKELETON is designed solely for authorised penetration testing, defensive auditing, and training in isolated lab environments (e.g. HackTheBox, TryHackMe, Proving Grounds). Users are responsible for adhering to applicable laws and obtaining explicit written authorisation prior to testing.
