#!/usr/bin/env python3
"""Central paths / settings for SKELETON.

Every hard-coded ``/opt/SKELETON/...`` literal in the launcher and in the
``imports2/`` modules should come from here so the tree can be relocated.

Override at runtime with environment variables::

    SKELETON_ROOT=/srv/skeleton python3 SKELETON_WEB.py
    SKELETON_WORKING=/tmp/out    python3 SKELETON_WEB.py
    SKELETON_USER=ncc            python3 SKELETON_WEB.py   # owns working/

The ``imports2/`` modules are launched as ``python3 /opt/SKELETON/imports2/NAME.py``
so ``imports2/`` is on ``sys.path``; they reach this module with::

    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from config import WORKING_DIR, WORDLIST   # etc.
"""
import os
import pwd
import stat
import threading
import time
from pathlib import Path

SKELETON_ROOT = Path(os.environ.get("SKELETON_ROOT", Path(__file__).resolve().parent))

WORKING_DIR = Path(os.environ.get("SKELETON_WORKING", SKELETON_ROOT / "working"))
DATA_DIR = SKELETON_ROOT / "data"
IMPORTS_DIR = SKELETON_ROOT / "imports2"
TOOLS_DIR = SKELETON_ROOT / "tools"
# Third-party tool clones live under here (git-ignored).
# Kept out of the repo root so the tree stays legible.
VENDOR_DIR = SKELETON_ROOT / "vendor"

WORDLIST = DATA_DIR / "rockyou.txt"
NAMES = DATA_DIR / "names.txt"
GLOSSARY = DATA_DIR / "glossary.txt"

# Names in imports2/ that are support files, not launchable pentest modules.
NON_MODULE_STEMS = {"template", "glossary", "terminal_osin", "config"}

WINDOW_GEOMETRY = os.environ.get("SKELETON_GEOMETRY", "950x900")


# --- who the work folder belongs to -----------------------------------------
#
# SKELETON is run as root: half the tools it drives want raw sockets, a
# monitor-mode NIC or a packet capture, and the web edition binds port 80.
# Nothing it *writes* needs root, though.  A working/ full of root-owned files
# is a folder the tester cannot then open, edit, delete or grep from their own
# desktop session - the scan reports and captures of their own engagement come
# back "Permission denied" - so everything that lands under WORKING_DIR is put
# in the name of the unprivileged account that started the run instead.
#
# Name that account with SKELETON_USER=someone; set SKELETON_RECLAIM=0 to leave
# ownership alone entirely.

def _resolve_work_user():
    """(uid, gid, name) of the account working/ belongs to.

    The first candidate naming a real, non-root account wins: an explicit
    SKELETON_USER, then the account that ran `sudo`, then whoever owns the
    source tree - a plain `su -` root session leaves no SUDO_* behind, but the
    checkout is still the tester's.  With no unprivileged candidate at all we
    fall back to whoever we are now, which makes every call below a no-op.
    """
    def account(value):
        if value in (None, "", "root", "0", 0):
            return None
        try:
            text = str(value)
            return pwd.getpwuid(int(text)) if text.isdigit() else pwd.getpwnam(text)
        except (KeyError, ValueError, OverflowError):
            return None

    candidates = [os.environ.get("SKELETON_USER"),
                  os.environ.get("SUDO_USER"),
                  os.environ.get("SUDO_UID"),
                  os.environ.get("PKEXEC_UID")]
    try:                                   # the checkout's own owner
        candidates.append(SKELETON_ROOT.stat().st_uid)
    except OSError:
        pass
    for candidate in candidates:
        pw = account(candidate)
        if pw and pw.pw_uid:
            return pw.pw_uid, pw.pw_gid, pw.pw_name
    me = os.getuid()
    try:
        return me, os.getgid(), pwd.getpwuid(me).pw_name
    except KeyError:
        return me, os.getgid(), str(me)


WORK_UID, WORK_GID, WORK_USER = _resolve_work_user()

# Bits put back on a path taken off root.  Files get group read/write and
# directories the setgid bit as well, so anything a tool creates before the
# sweep below reaches it is still the tester's to open.  Only ever added: an
# executable stays executable, and a capture pulled off a target keeps whatever
# mode it arrived with rather than being quietly rewritten.
WORK_FILE_BITS = 0o660
WORK_DIR_BITS = 0o2770

# ...with one exception, taken off every path whatever else is done to it.
# working/ holds an engagement's evidence, and nothing here has any business
# leaving it writable by every account on the box - but `own` only ever ORed
# bits in, so a mode it never chose stood.  A tree created under a umask of 0
# (root, an installer, an older run) therefore stayed 0777 for good: `own`
# returned early the moment the path was already the tester's, so the one path
# that most wanted correcting was the one path never looked at.
WORK_OTHER_BITS = stat.S_IWOTH

RECLAIM_ENABLED = os.environ.get("SKELETON_RECLAIM", "1") != "0"


def handing_back():
    """True when there is actually work to do: we are root, and working/ is
    somebody else's."""
    return RECLAIM_ENABLED and WORK_UID != 0 and os.geteuid() == 0


def _fix_mode(path, mode, restore):
    """Correct one path's permissions.  Never raises; a path we may not chmod
    (not ours, and we are not root) is left as it is.

    `restore` is for a path just taken back off root, which needs the tester's
    group put back on it.  Everything else only has world write taken off.
    """
    want = stat.S_IMODE(mode)
    if restore:
        want |= WORK_DIR_BITS if stat.S_ISDIR(mode) else WORK_FILE_BITS
    want &= ~WORK_OTHER_BITS
    if want == stat.S_IMODE(mode):
        return
    try:
        os.chmod(path, want)
    except OSError:
        pass


def own(path):
    """Put one path under working/ in WORK_USER's name, at a mode that suits an
    engagement's evidence.  Returns True if it ends up theirs.

    Safe to call after every write: off the root path it is one lstat and an
    integer comparison, and it never follows a symlink - a link planted in
    working/ must not become a lever for chowning or chmodding something
    outside it.
    """
    if not path:
        return False
    path = str(path)
    try:
        st = os.lstat(path)
    except OSError:
        return False
    if stat.S_ISLNK(st.st_mode):
        return False
    if st.st_uid != WORK_UID or st.st_gid != WORK_GID:
        if handing_back():
            try:
                os.chown(path, WORK_UID, WORK_GID)
            except OSError:
                return False
            _fix_mode(path, st.st_mode, restore=True)
            return True
    # Already theirs, or not ours to hand over.  Either way the ownership is
    # settled and the mode may not be: a tool picks the mode of its own output,
    # and an older run's tree carries whatever it was left at.
    if RECLAIM_ENABLED:
        _fix_mode(path, st.st_mode, restore=False)
    return st.st_uid == WORK_UID


# A walk has to stop somewhere: a packet capture split into its own tree can
# run to a lot of files, and this is a housekeeping pass, not the job.
RECLAIM_MAX_PATHS = 20000

# One walk at a time.  A front-end reclaims on its own tick as well as from a
# watcher thread, and two sweeps racing over the same tree would be all cost
# and no benefit - the second finds nothing the first has not already handed
# back.  A caller who arrives mid-sweep skips rather than waits.
_walk_lock = threading.Lock()


def reclaim(root=None, limit=RECLAIM_MAX_PATHS):
    """Put everything under `root` (default working/) right for the tester -
    the owner, and the mode.  Returns how many paths `own` changed.

    `own` covers what SKELETON writes itself.  This covers what it *runs*: the
    tools inherit our privileges, so an nmap report, a tcpdump capture or a
    hashcat potfile lands owned by root no matter who asked for it - and picks
    its own permissions while it is at it, which is why the walk visits a path
    that is already the tester's rather than only one that is still root's.
    """
    if not handing_back():
        return 0
    if not _walk_lock.acquire(blocking=False):
        return 0
    try:
        root = str(root or WORKING_DIR)
        changed = 1 if _needs_hand_back(root) and own(root) else 0
        seen = 0
        for dirpath, dirnames, filenames in os.walk(root):   # never follows links
            for name in dirnames + filenames:
                seen += 1
                if seen > limit:
                    return changed
                path = os.path.join(dirpath, name)
                if _needs_hand_back(path) and own(path):
                    changed += 1
        return changed
    finally:
        _walk_lock.release()


def _needs_hand_back(path):
    """Is there anything for `own` to do here - the owner, or the mode?

    The mode half is what carries the tightening across a tree that already
    belongs to the tester: the walk used to skip those paths entirely, so a
    world-writable folder from an older run was never visited again.
    """
    try:
        st = os.lstat(path)
    except OSError:
        return False
    return st.st_uid != WORK_UID or bool(stat.S_IMODE(st.st_mode) & WORK_OTHER_BITS)


_reclaim_lock = threading.Lock()
_reclaim_due = [0.0]


def reclaim_soon(interval=5.0):
    """`reclaim()`, but at most once every `interval` seconds.

    For the front-ends to call from somewhere that already ticks - a notes
    poll, a finished run - so tool output is handed back promptly without a
    walk of working/ on every request.
    """
    if not handing_back():
        return 0
    with _reclaim_lock:
        now = time.monotonic()
        if now < _reclaim_due[0]:
            return 0
        _reclaim_due[0] = now + interval
    return reclaim()


def watch_work_folder(interval=15.0):
    """Keep handing working/ back for as long as this process lives.

    A daemon thread, started once, only where it has something to do.  The
    front-ends reclaim on their own tick; this is what covers a module run
    standalone (`python3 imports2/enum_nmap.py`), where the tool writes its
    output into working/ from a terminal of its own and nothing else is
    watching.
    """
    if not handing_back():
        return None

    def loop():
        while True:
            time.sleep(interval)
            try:
                reclaim()
            except OSError:
                pass

    thread = threading.Thread(target=loop, name="skeleton-reclaim", daemon=True)
    thread.start()
    return thread


# Ensure the scratch dir exists for modules that write into it - in the
# tester's name, so what they run next inherits the group and lands writable.
WORKING_DIR.mkdir(parents=True, exist_ok=True)
own(WORKING_DIR)

# Started here rather than from the front-ends because a module is also a
# program in its own right: `python3 imports2/enum_nmap.py` run straight from a
# terminal writes into working/ with nobody else watching.  Costs nothing off
# the root path - `handing_back()` is false and no thread is started at all.
watch_work_folder()
