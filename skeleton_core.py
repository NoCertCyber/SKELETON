#!/usr/bin/env python3
"""The launcher logic that is not a Flask route.

`SKELETON_WEB.py` serves the toolkit; everything behind those routes lives
here: the stage/module catalogue, the glossary reader, the notes channel, the
engagement session, and the handful of system actions the button bar runs.
Kept separate so the launcher stays readable and this half stays testable
without a request context.

This is launcher-level only.  The `imports2/` modules stay standalone
copy-paste scripts by design - they never import this module.
"""
import json
import os
import re
import subprocess
import tempfile
from datetime import datetime

from config import (
    GLOSSARY,
    IMPORTS_DIR,
    NON_MODULE_STEMS,
    WORKING_DIR,
    own,
)

# --- catalogue --------------------------------------------------------------

# Penetration-testing stages, in rough engagement order.  Each is the filename
# prefix of the modules in that stage (enum_*, web_*, ...).  "ALL" is a
# synthetic entry that lists every module regardless of stage.
ALL_STAGES = "ALL"
PENTEST_CHAIN = [
    ALL_STAGES,
    "info",
    "OSIN",
    "DNS",
    "enum",
    "web",
    "mitm",
    "wireless",
    "bruteforce",
    "exploit",
    "powershell",
    "transfer",
    "forensic",
]

# The module list and the glossary are static for a session - read them once.
MODULE_NAMES = sorted(
    p.stem for p in IMPORTS_DIR.glob("*.py") if p.stem not in NON_MODULE_STEMS
)
MODULE_SET = set(MODULE_NAMES)

# --- Demo edition configuration ---------------------------------------------
IS_DEMO = True
PAYHIP_URL = "https://payhip.com/b/dR8ng"
PRICE_STR = "$30 AUD"
DEMO_MODULES = {
    "info_glossary",
    "info_revshell_generator",
    "info_linux",
    "OSIN_theharvester",
    "OSIN_shodan",
    "DNS_axfr",
    "DNS_nslookup",
    "enum_nmap",
    "enum_netexec",
    "enum_arp",
    "web_gobuster",
    "web_whatweb",
    "web_ffuf",
    "mitm_responder",
    "wireless_airodump",
    "bruteforce_hydra",
    "exploit_basic_shell",
    "exploit_searchsploit",
    "powershell_info",
    "transfer_netcat",
    "forensic_wireshark",
}

try:
    GLOSSARY_LINES = GLOSSARY.read_text(encoding="utf-8", errors="replace").split("\n")
except OSError:
    GLOSSARY_LINES = []

BANNER = '''
     ░██████╗██╗░░██╗███████╗██╗░░░░░███████╗████████╗░█████╗░███╗░░██╗
     ██╔════╝██║░██╔╝██╔════╝██║░░░░░██╔════╝╚══██╔══╝██╔══██╗████╗░██║
     ╚█████╗░█████═╝░█████╗░░██║░░░░░█████╗░░░░░██║░░░██║░░██║██╔██╗██║
     ░╚═══██╗██╔═██╗░██╔══╝░░██║░░░░░██╔══╝░░░░░██║░░░██║░░██║██║╚████║
     ██████╔╝██║░╚██╗███████╗███████╗███████╗░░░██║░░░╚█████╔╝██║░╚███║
     ╚═════╝░╚═╝░░╚═╝╚══════╝╚══════╝╚══════╝░░░╚═╝░░░░╚════╝░╚═╝░░╚══╝

         "We are here to make security better by Alexander Holden"

###Notes:###
'''


def modules_for_stage(stage):
    if stage == ALL_STAGES:
        return list(MODULE_NAMES)
    return [m for m in MODULE_NAMES if m.startswith(stage)]


def describe_module(module):
    """First glossary description line for a module stem, or '' if none."""
    for line in GLOSSARY_LINES:
        if line.startswith(module) and " - " in line:
            return line.split(" - ", 1)[1].strip()
    return ""


def glossary_block(module):
    """The module's full glossary entry: its header line plus the indented
    dotpoints that follow it."""
    out = []
    for i, raw in enumerate(GLOSSARY_LINES):
        if module not in raw:
            continue
        item = raw
        if " - " in item:  # collapse the name-column padding
            name, rest = item.split(" - ", 1)
            item = "{} - {}".format(name.strip(), rest)
        out.append(item)
        if not raw.startswith((" ", "\t")):
            for extra in GLOSSARY_LINES[i + 1:]:
                if not extra.startswith((" ", "\t")):
                    break
                out.append(extra)
    return "\n".join(out)


def search_modules(query, stage=ALL_STAGES):
    """Substring search over module name and glossary description.  An empty
    query falls back to the given stage."""
    query = (query or "").strip().lower()
    if not query:
        return modules_for_stage(stage)
    return [m for m in MODULE_NAMES
            if query in m.lower() or query in describe_module(m).lower()]


# --- notes ------------------------------------------------------------------

def stamp(suffix=""):
    """A '\\nTime stamp: DD-Mon-YYYY (HH:MM:SS.ffffff)<suffix>\\n' line."""
    now = datetime.now().strftime("%d-%b-%Y (%H:%M:%S.%f)")
    return "\nTime stamp: {}{}\n".format(now, suffix)


# A notes channel is append-only and each reader tracks its own byte offset.
# Draining it instead (read + truncate) meant the first reader to poll took the
# content away from every other one, so two launcher tabs split a run's output
# between them.  Files are rotated rather than grown without limit; a reader
# whose offset is past the end simply resyncs from 0.
NOTES_MAX = 4 * 1024 * 1024


def read_notes_since(path, offset=0):
    """(new_text, next_offset) for a notes channel file.

    `offset` is where this reader got to last time.  A file shorter than the
    offset has been rotated, so the reader starts again from the beginning.
    """
    try:
        size = os.path.getsize(path)
    except OSError:
        return "", 0
    if size < offset:            # rotated out from under us
        offset = 0
    if size == offset:
        return "", offset
    try:
        with open(path, "rb") as f:
            f.seek(offset)
            data = f.read()
    except OSError:
        return "", offset
    return data.decode("utf-8", "replace"), offset + len(data)


# What a client that has never polled before is given.  The channel is
# append-only and kept for the whole engagement, so a page opened late used to
# be handed every byte of it at once - up to NOTES_MAX - and re-render the lot
# in one pass before it could show anything.  The tail is what an operator
# actually wants back on screen; the rest is in the file, and in the job the
# SAVE button writes.
NOTES_FIRST_READ = 256 * 1024


def notes_tail_offset(path, limit=NOTES_FIRST_READ):
    """Where a first-time reader should start: the whole file when it is small,
    otherwise the start of the first whole line within `limit` of the end."""
    try:
        size = os.path.getsize(path)
    except OSError:
        return 0
    if size <= limit:
        return 0
    start = size - limit
    try:
        with open(path, "rb") as f:
            f.seek(start)
            chunk = f.read(4096)
    except OSError:
        return start
    nl = chunk.find(b"\n")
    return start + nl + 1 if nl != -1 else start


def rotate_notes(path):
    """Empty a notes channel that has grown past NOTES_MAX.  Readers notice
    because the file is now shorter than their offset."""
    try:
        if os.path.getsize(path) <= NOTES_MAX:
            return False
        with open(path, "w"):
            pass
    except OSError:
        return False
    return True


def safe_working_path(name, suffix=""):
    """`name` resolved to a single leaf inside WORKING_DIR, or None.

    Guards SAVE / LOAD / Insert File against a path like ../../etc/passwd.
    """
    leaf = os.path.basename((name or "").strip())
    if not leaf or leaf in (".", ".."):
        return None
    return WORKING_DIR / (leaf + suffix)


def write_json_atomic(path, data):
    """Replace `path` with `data` as JSON, via a temp file in the same dir, so
    an interrupted write cannot leave a truncated file behind."""
    path = str(path)
    d = os.path.dirname(path) or "."
    fd, tmp = tempfile.mkstemp(dir=d, prefix=".tmp", suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        # mkstemp opens 0600, and under sudo that is 0600 *root* - the session
        # and credential files the tester is meant to read back.  Hand the file
        # over before it takes the real name, so the swap is still atomic.
        own(tmp)
        os.replace(tmp, path)
    except OSError:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        return False
    return True


# --- engagement session -----------------------------------------------------
#
# One target, shared by every module and both front-ends.  The Tk launcher runs
# modules as separate processes, so the session travels to them as environment
# variables; a converted module reads its Entry default from
# os.environ.get("SKELETON_TARGET", "<its own example>").

SESSION_PATH = WORKING_DIR / "session.json"

SESSION_KEYS = ("target", "url", "lhost", "lport", "user", "pass",
                "iface", "wlan", "wordlist")

SESSION_DEFAULTS = {
    "target": "",
    "url": "",
    "lhost": "",
    "lport": "4444",
    "user": "",
    "pass": "",
    "iface": "eth0",
    # A wireless engagement uses a different NIC from the wired one, and half
    # the wireless tools want its monitor-mode name - so it is its own value
    # rather than sharing "iface".
    "wlan": "wlan0",
    "wordlist": "",
}

# Which session value belongs in a field, matched against its label.  Order
# matters: the first pattern that matches wins, so put the specific ones first.
FIELD_MAP = [
    (re.compile(r"\b(lhost|listening ip|your ip|callback ip)\b", re.I), "lhost"),
    (re.compile(r"\b(lport|listening port|your port|callback port)\b", re.I), "lport"),
    (re.compile(r"\b(target url|url to download|domain)\b", re.I), "url"),
    (re.compile(r"\b(target ip|ip range|ips ex|target host|rhost)\b", re.I), "target"),
    (re.compile(r"\b(wireless interface|monitor interface|wlan)\b", re.I), "wlan"),
    (re.compile(r"\b(interface|iface)\b", re.I), "iface"),
    (re.compile(r"\b(wordlist|password list|pass list)\b", re.I), "wordlist"),
    # Not "^user", which also caught "User list:" - a path to a names file,
    # into which the web launcher then wrote the engagement's single user name
    # and left kerbrute reading a file called "admin".
    (re.compile(r"\b(user ?name|username)\b|^\s*user\s*:?\s*$", re.I), "user"),
    (re.compile(r"\bpass(word)?\b", re.I), "pass"),
    (re.compile(r"^\s*target\s*:?\s*$", re.I), "target"),
]


def session_key_for(label):
    """The session key a field label maps to, or None."""
    for pattern, key in FIELD_MAP:
        if pattern.search(label or ""):
            return key
    return None


def load_session():
    data = dict(SESSION_DEFAULTS)
    try:
        with open(SESSION_PATH, encoding="utf-8") as f:
            stored = json.load(f)
        if isinstance(stored, dict):
            for k in SESSION_KEYS:
                if isinstance(stored.get(k), str):
                    data[k] = stored[k]
    except (OSError, ValueError):
        pass
    return data


def save_session(values):
    data = load_session()
    for k in SESSION_KEYS:
        if isinstance(values.get(k), str):
            data[k] = values[k].strip()
    write_json_atomic(SESSION_PATH, data)
    return data


def session_env(session=None, base=None):
    """`base` environment plus SKELETON_* for each non-empty session value -
    what a module process inherits so its fields pre-fill."""
    env = dict(os.environ if base is None else base)
    for k, v in (session or load_session()).items():
        if v:
            env["SKELETON_" + k.upper()] = v
    return env


# --- saved targets ----------------------------------------------------------
#
# The session carries the one *active* target - the value every module pre-fills
# from.  An engagement is rarely one host, though, so the launcher also keeps
# the list of targets seen so far and switches the active one between them.

TARGETS_PATH = WORKING_DIR / "targets.json"


def load_targets():
    """The saved target list, oldest first.  A missing or malformed file reads
    as an empty list."""
    try:
        with open(TARGETS_PATH, encoding="utf-8") as f:
            stored = json.load(f)
    except (OSError, ValueError):
        return []
    out = []
    if isinstance(stored, list):
        for item in stored:
            if isinstance(item, str) and item.strip():
                out.append(item.strip())
    return out


def save_targets(targets):
    """Write the list back, dropping blanks and duplicates; returns it."""
    clean, seen = [], set()
    for item in targets or []:
        target = str(item or "").strip()
        if not target or target in seen:
            continue
        seen.add(target)
        clean.append(target)
    write_json_atomic(TARGETS_PATH, clean)
    return clean


def add_target(target):
    """Remember one target, keeping the place it already had in the list."""
    target = str(target or "").strip()
    if not target:
        return load_targets()
    return save_targets(load_targets() + [target])


def remove_target(target):
    """Forget one target.  The active target is the session's business and is
    left alone - a target can be dropped from the list while still in use."""
    target = str(target or "").strip()
    return save_targets([t for t in load_targets() if t != target])


# --- saved credentials ----------------------------------------------------
#
# The engagement session carries one working user / password.  The launcher's
# credential manager keeps the wider list of pairs gathered on the box (found,
# sprayed, cracked) so any of them can be recalled into the session fields.

CREDS_PATH = WORKING_DIR / "creds.json"


def load_creds():
    """The saved [{'user': ..., 'pass': ...}] list, oldest first.  A missing or
    malformed file reads as an empty list."""
    try:
        with open(CREDS_PATH, encoding="utf-8") as f:
            stored = json.load(f)
    except (OSError, ValueError):
        return []
    out = []
    if isinstance(stored, list):
        for item in stored:
            if not isinstance(item, dict):
                continue
            user, pw = str(item.get("user", "")), str(item.get("pass", ""))
            if user or pw:
                out.append({"user": user, "pass": pw})
    return out


def save_creds(creds):
    """Write the list back, dropping blank and duplicate pairs; returns it."""
    clean, seen = [], set()
    for item in creds or []:
        user = str((item or {}).get("user", "")).strip()
        pw = str((item or {}).get("pass", "")).strip()
        if not (user or pw) or (user, pw) in seen:
            continue
        seen.add((user, pw))
        clean.append({"user": user, "pass": pw})
    write_json_atomic(CREDS_PATH, clean)
    return clean


def add_cred(user, pw):
    """Append one pair (moving an existing match to the end)."""
    user, pw = str(user).strip(), str(pw).strip()
    kept = [c for c in load_creds() if (c["user"], c["pass"]) != (user, pw)]
    kept.append({"user": user, "pass": pw})
    return save_creds(kept)


def remove_cred(user, pw):
    """Drop the pair matching `user` / `pw` exactly."""
    user, pw = str(user).strip(), str(pw).strip()
    return save_creds([c for c in load_creds()
                       if (c["user"], c["pass"]) != (user, pw)])


# --- system actions ---------------------------------------------------------

NETWORK_DETAILS_PATH = str(WORKING_DIR / "network_details.txt")


def find_ip():
    """(ip, ifconfig_output, error).  Mirrors the launcher's 'Find my IP'."""
    try:
        with open(NETWORK_DETAILS_PATH, "w") as out:
            subprocess.call(["ifconfig"], stdout=out)
        own(NETWORK_DETAILS_PATH)
        with open(NETWORK_DETAILS_PATH, encoding="utf-8", errors="replace") as f:
            content = f.read()
    except OSError as exc:
        return "", "", "Find my IP failed (is net-tools installed?): {}".format(exc)
    try:
        return content.split()[5], content, ""
    except IndexError:
        return "127.0.0.1", content, "Could not parse an IP address out of ifconfig output"


def valid_ip(ip):
    """True for a dotted quad (optionally /prefix) this box could be given.

    Both launchers hand the value straight to `ifconfig <iface> <ip>`.  That is
    argv, not a shell string, so nothing can be injected through it - but an
    empty or flag-shaped value made ifconfig do something other than what was
    asked and report it as success, which is the sort of surprise a tester does
    not need halfway through an engagement.
    """
    ip = (ip or "").strip()
    if "/" in ip:
        ip, _, prefix = ip.partition("/")
        if not prefix.isdigit() or not 0 <= int(prefix) <= 32:
            return False
    parts = ip.split(".")
    if len(parts) != 4:
        return False
    return all(p.isdigit() and len(p) <= 3 and 0 <= int(p) <= 255 for p in parts)


def change_ip_argv(ip, iface="eth0"):
    return ["ifconfig", iface, ip]


def valid_port(port):
    port = (port or "").strip()
    return port.isdigit() and 0 < int(port) < 65536


def open_port_argv(port):
    return ["iptables", "-I", "INPUT", "-p", "tcp", "--dport", port, "-j", "ACCEPT"]
