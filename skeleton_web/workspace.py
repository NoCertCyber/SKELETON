#!/usr/bin/env python3
"""The notes tabs: their channels, their work folders, and who is writing.

The launcher's notes pane is split into named tabs (e.g. "GS 192.121.10.1").
Each has its own poll channel - the built-in "main" tab keeps using
working_file.txt, every other one uses working/notes_<id>.txt - and its own
working/<name>/ folder that module and terminal file output is dropped into.
A module page or a terminal page picks which tab its output is recorded to.

All of it is one object because all of it is one piece of shared state: the
tab list, the channels, the ownership of a channel while a command runs, and
the two locks that keep several browser tabs and several shells from cutting
into each other's output.
"""
import json
import os
import re
import secrets
import threading
import time

from config import WORKING_DIR, own
import skeleton_core as core

from .settings import FILE_PATH, MAIN_TAB, TABS_PATH


# Backstops for a command whose prompt never comes back - a reverse shell, an
# ssh session, vim - so one of those cannot hold a tab's notes for the rest of
# the engagement.  No real scan reaches either: they are the fallback to the
# old stamped interleaving, not a limit on how long a scan may run.
HOLD_MAX_SECONDS = 600
HOLD_MAX_BYTES = 1 << 20

REROUTED_MAX = 256    # ids come from the client; do not grow without bound


class Workspace:
    """The notes tabs and the channel each one is written to."""

    def __init__(self):
        # working_file.txt is the channel the launcher tab polls once a second.
        # Every writer (module-run summaries, and modules' own `tee -a`) appends
        # whole blocks; the lock serialises our appends against the poll so a
        # finished run's command/output land in the notes pane in one piece even
        # when several module tabs report at the same moment.  Re-entrant
        # because `append` resolves its tab while already holding it.
        self.notes_lock = threading.RLock()
        self._tabs_lock = threading.Lock()
        self._tabs = []
        self._rerouted = set()   # tabs already reported as deleted-while-in-use

        # Which session wrote to a tab's notes last.  A long scan streams its
        # output a line at a time, so anything else writing to the same tab
        # meanwhile - a second terminal, another module - lands in the middle of
        # it.  When a tab changes hands the new writer's block is stamped, and
        # the interrupted one is stamped again when it resumes.
        self._src = {}

        # ...but a stamp only labels the split, it does not stop it, and a scan
        # cut into three stamped pieces is still a scan cut into three pieces.
        # So a command holds the tab for as long as it is running: whoever else
        # writes meanwhile is queued, in order, and let through the moment the
        # holder's prompt comes back.  The holder keeps streaming live - that is
        # the whole point of not simply buffering the scan - and what waits
        # behind it is a few lines of somebody else's terminal, which that
        # operator is already watching in the terminal itself.  Only identified
        # writers (a shell, a module run typed into one) take part; an
        # out-of-band notice passes a bare tab and goes straight through.
        #
        # tab -> {"src": who holds it, "since": when, "bytes": queued, "queue": [...]}
        self._hold = {}
        # The writers with a command in flight: between the command line and the
        # prompt that ends it.  A writer claims the tab on its first write while
        # in here, which is what lets a queue flush hand the tab straight to the
        # next command still running rather than dropping everyone back to
        # interleaving.
        self._running = set()

        self._load()

    # --- the tab list -------------------------------------------------------
    def _load(self):
        try:
            with open(TABS_PATH, encoding="utf-8") as f:
                data = json.load(f)
            tabs = [
                {"id": str(t["id"]), "name": str(t.get("name") or t["id"]),
                 "folder": str(t.get("folder") or "")}
                for t in data if isinstance(t, dict) and t.get("id")
            ]
        except (OSError, ValueError, TypeError, KeyError):
            tabs = []
        if not any(t["id"] == MAIN_TAB for t in tabs):
            tabs.insert(0, {"id": MAIN_TAB, "name": "Notes", "folder": "Notes"})
        self._tabs = tabs

    def _save(self):
        """Atomic: a crash mid-write must not leave a truncated tab list."""
        core.write_json_atomic(TABS_PATH, self._tabs)

    def tabs(self):
        with self._tabs_lock:
            return list(self._tabs)

    def ids(self):
        with self._tabs_lock:
            return [t["id"] for t in self._tabs]

    def add_tab(self, name):
        name = (name or "").strip()[:80] or "tab"
        tab = {"id": secrets.token_hex(4), "name": name,
               "folder": self._unique_folder_name(name)}
        with self._tabs_lock:
            self._tabs.append(tab)
            self._save()
            return tab, list(self._tabs)

    def rename_tab(self, tab_id, name):
        """(renamed?, tabs).  A blank name leaves the tab alone."""
        name = (name or "").strip()[:80]
        with self._tabs_lock:
            tab = next((t for t in self._tabs if t["id"] == tab_id), None)
            if tab is None:
                return None, list(self._tabs)
            if name:
                tab["name"] = name
                self._save()
            return True, list(self._tabs)

    def delete_tab(self, tab_id):
        """Drop a tab and the channel behind it.  (deleted?, tabs)."""
        with self._tabs_lock:
            tab = next((t for t in self._tabs if t["id"] == tab_id), None)
            if tab is None:
                return None, list(self._tabs)
            self._tabs.remove(tab)
            self._save()
            tabs = list(self._tabs)
        # Anything queued behind a command still running on this tab is now
        # queued against a tab that no longer resolves to itself: let it go now,
        # so it follows the reroute to the default tab instead of waiting out
        # the backstop first.
        with self.notes_lock:
            self._release(tab_id)
        try:
            os.unlink(self.buffer_path(tab_id))
        except OSError:
            pass
        return True, tabs

    def resolve(self, tab_id):
        """A known tab id, or MAIN_TAB when the caller named one that is gone."""
        if tab_id in self.ids():
            return tab_id
        # A terminal or job outlives the tab it was started against if the tab
        # is deleted mid-run.  Its output has to land somewhere, but say so
        # rather than silently reattributing it.
        #
        # The notice goes out under notes_lock like every other append: `poll`
        # holds that lock across a rotate_notes() that truncates, so writing
        # here unsynchronised could drop this line or one either side of it.
        if tab_id:
            with self.notes_lock:
                first = tab_id not in self._rerouted
                if first:
                    if len(self._rerouted) >= REROUTED_MAX:
                        self._rerouted.clear()
                    self._rerouted.add(tab_id)
                if first:
                    path = self.buffer_path(MAIN_TAB)
                    try:
                        with open(path, "a", encoding="utf-8") as f:
                            f.write(core.stamp(
                                " - notes tab '{}' was deleted while still in "
                                "use; its output is being recorded here".format(
                                    tab_id)))
                    except OSError:
                        pass
                    else:
                        own(path)
        return MAIN_TAB

    # --- where a tab's bytes go --------------------------------------------
    def buffer_path(self, tab_id):
        """The poll-channel file backing one tab."""
        if tab_id == MAIN_TAB:
            return FILE_PATH
        safe = re.sub(r"[^A-Za-z0-9_-]", "", tab_id or "")
        return str(WORKING_DIR / ("notes_{}.txt".format(safe or "x")))

    @staticmethod
    def _safe_leaf(name):
        """`name` reduced to something that can be one folder under working/."""
        safe = re.sub(r"[^A-Za-z0-9._ +-]+", "_", name or "").strip(" .")
        return "" if safe in ("", ".", "..") else safe

    def _folder_name(self, tab_id):
        """The folder leaf a tab's output belongs in, decided once and kept.

        It used to be derived from the tab's *name* on every call, so renaming a
        tab pointed it at a folder that did not exist: its runs.jsonl was
        orphaned and its run history vanished, and any shell already running
        kept writing to the old path.  The leaf is chosen when the tab is
        created and stored with it, so a rename is now just a rename.  Tabs
        written by an older version have no leaf recorded; derive one for them
        the old way and pin it, which keeps their existing folder where it is.
        """
        with self._tabs_lock:
            tab = next((t for t in self._tabs if t["id"] == tab_id), None)
            if tab is None:
                return ""
            leaf = tab.get("folder")
            if leaf:
                return leaf
            leaf = self._safe_leaf(tab.get("name")) or self._safe_leaf(tab_id)
            if not leaf:
                return ""
            tab["folder"] = leaf
            self._save()
            return leaf

    def _unique_folder_name(self, name):
        """A folder leaf for a new tab that no existing tab has claimed."""
        base = self._safe_leaf(name) or "tab"
        with self._tabs_lock:
            taken = {t.get("folder") for t in self._tabs if t.get("folder")}
        leaf, n = base, 2
        while leaf in taken or (WORKING_DIR / leaf).exists():
            leaf = "{}_{}".format(base, n)
            n += 1
        return leaf

    def folder(self, tab_id):
        """The WORKING_DIR subfolder that a tab's file output goes to (e.g.
        working/Notes, working/Recon), created on demand.  Returns an absolute
        path; falls back to WORKING_DIR if there is no safe leaf for it."""
        safe = self._folder_name(tab_id)
        if not safe:
            return str(WORKING_DIR)
        path = WORKING_DIR / safe
        try:
            path.mkdir(parents=True, exist_ok=True)
        except OSError:
            return str(WORKING_DIR)
        # Under sudo (needed for port 80) this would be a root-owned folder in
        # the tester's own work area; hand it over, setgid, so what a tool
        # writes into it from here lands in their group too.
        own(path)
        # A tree from an older run can still mix owners.  If this folder is not
        # writable by whoever we are now, fall back rather than dropping output
        # on the floor.
        if not os.access(str(path), os.W_OK):
            return str(WORKING_DIR)
        return str(path)

    # --- who holds a tab while a command runs -------------------------------
    def started(self, src):
        """A command is in flight for `src`: it may hold a tab while it runs."""
        if src is not None:
            with self.notes_lock:
                self._running.add(src)

    def finished(self, tab, src):
        """Its prompt came back: stop holding, and let the queue through."""
        if src is None:
            return
        with self.notes_lock:
            self._running.discard(src)
            self._release(self.resolve(tab), src)

    def sweep_holds(self):
        """Let go of any hold that has outstayed the backstop.

        The check on the write path only runs when somebody writes, and the
        writer queued behind a hold is exactly the one that has stopped writing
        - so a line typed into a second terminal while a `nc` session held the
        tab would sit in this queue, out of the notes and lost if the server
        went down, until something else happened to come along.  This is what
        actually collects them; the housekeeping thread calls it once a minute.
        """
        now = time.time()
        with self.notes_lock:
            for tab, hold in list(self._hold.items()):
                if (now - hold["since"] > HOLD_MAX_SECONDS
                        or hold["bytes"] >= HOLD_MAX_BYTES):
                    self._release(tab)

    def _release(self, tab, src=None):
        """Drop `tab`'s hold and replay what queued up behind it, in order.

        Called with notes_lock held.  The hold is dropped before the replay so
        the queued blocks do not simply queue again - and a writer still mid
        command re-claims the tab as its first replayed block goes by, so a scan
        that started while another one was running is not cut in its turn."""
        hold = self._hold.get(tab)
        if hold is None or (src is not None and hold["src"] != src):
            return
        del self._hold[tab]
        for qsrc, qlabel, qtext in hold["queue"]:
            self.append(qtext, tab, qsrc, qlabel)

    # --- writing ------------------------------------------------------------
    def append(self, text, tab=MAIN_TAB, src=None, label=None):
        """Append one already-complete block to a tab's notes channel, atomically.

        `src` identifies the writer and `label` names it; passing both re-stamps
        the block whenever the tab's last writer was somebody else, and queues
        it behind whatever command currently holds the tab."""
        with self.notes_lock:
            tab = self.resolve(tab)
            if src is not None:
                hold = self._hold.get(tab)
                if hold is not None and hold["src"] != src:
                    if (time.time() - hold["since"] > HOLD_MAX_SECONDS
                            or hold["bytes"] >= HOLD_MAX_BYTES):
                        self._release(tab)   # never came back; interleave again
                    else:
                        hold["queue"].append((src, label, text))
                        hold["bytes"] += len(text)
                        return
                if src in self._running and tab not in self._hold:
                    self._hold[tab] = {"src": src, "since": time.time(),
                                       "bytes": 0, "queue": []}
            path = self.buffer_path(tab)
            head = ""
            if self._src.get(tab) != src:
                if label and tab in self._src:
                    head = core.stamp(" - " + label + " (cont.)")
                self._src[tab] = src
            try:
                with open(path, "a", encoding="utf-8") as f:
                    f.write(head + text)
            except OSError:
                pass
            else:
                own(path)

    # --- reading ------------------------------------------------------------
    def poll(self, since):
        """(chunks, offsets): what each tab's channel has gained since `since`.

        Each client sends the offsets it has already consumed, so several
        launcher tabs all see the same notes instead of racing to drain them.
        A tab the caller names no offset for at all is its first look at that
        channel, and it gets the tail of it rather than all of it.
        """
        chunks, offsets = {}, {}
        ids = self.ids()
        with self.notes_lock:
            for tab_id in ids:
                path = self.buffer_path(tab_id)
                core.rotate_notes(path)
                if tab_id not in since:
                    # A client that has not polled this tab before: hand it the
                    # tail rather than the whole engagement's channel.
                    start = core.notes_tail_offset(path)
                else:
                    try:
                        # Clamp: a negative offset makes read_notes_since seek
                        # before the start of the file, which raises and hands
                        # the same bad offset back - the browser then stores it
                        # and re-sends it for ever, and that tab silently stops
                        # logging.
                        start = max(0, int(since[tab_id]))
                    except (TypeError, ValueError):
                        start = 0
                content, offsets[tab_id] = core.read_notes_since(path, start)
                if content:
                    chunks[tab_id] = content
        return chunks, offsets
