#!/usr/bin/env python3
"""What ran, per notes tab.

A module run is a command typed into that page's shell, so there is no separate
process to follow: the shell's own transcript machinery copies the command and
everything it prints to the notes tab, and this adds the one line that makes it
findable afterwards - the launcher's Runs panel, and the block appended to a
saved job file.  The outcome itself stays where the operator is already
looking, in the terminal it ran in.

One runs.jsonl per tab folder, so a restart does not lose the history.
"""
import itertools
import json
import os
import time
from datetime import datetime

from config import own
import skeleton_core as core


class RunLog:
    """The runs recorded against each notes tab."""

    def __init__(self, workspace):
        self.workspace = workspace
        # runs.jsonl outlives the server, so a counter that starts at 1 again on
        # every boot writes a second "run1" into the same file.  The start time
        # in front of it makes an id say which run of which session it was.
        self._epoch = int(time.time())
        self._seq = itertools.count(1)   # ids for the run-history records

    def path(self, tab):
        return os.path.join(self.workspace.folder(self.workspace.resolve(tab)),
                            "runs.jsonl")

    def record(self, module, command, cwd, tab):
        """Append one run to the tab's runs.jsonl - the shape /api/jobs returns."""
        rec = {
            "id": "run{}-{}".format(self._epoch, next(self._seq)),
            "module": module,
            "command": command,
            "cwd": cwd,
            "tab": tab,
            "started": time.time(),
            "where": "shell",  # its output and exit code are in that terminal
        }
        try:
            with self.workspace.notes_lock:
                path = self.path(tab)
                with open(path, "a", encoding="utf-8") as fh:
                    fh.write(json.dumps(rec) + "\n")
                own(path)
        except OSError as exc:  # never fail silently - the operator needs to know
            self.workspace.append(
                core.stamp(" - could not record the run: {}".format(exc)), tab)
        return rec

    def recent(self, tab, limit=100):
        """Runs read back from the tab's runs.jsonl."""
        out = []
        try:
            with open(self.path(tab), encoding="utf-8") as fh:
                for line in fh:
                    try:
                        out.append(json.loads(line))
                    except ValueError:
                        continue
        except OSError:
            return []
        return out[-limit:]

    def clear(self, tab):
        """Throw this tab's run history away.  Returns an error string, or ''.

        A command still running in a module terminal is left alone - it is on
        the wire, and its output is in the terminal it was typed into."""
        try:
            with self.workspace.notes_lock:
                path = self.path(tab)
                open(path, "w").close()
                own(path)
        except OSError as exc:
            return str(exc)
        return ""

    def history_text(self, tab):
        """The run history as a trailing block for saved job files ('' when
        empty).  Read from the tab's runs.jsonl, so it survives a restart."""
        runs = self.recent(tab)
        if not runs:
            return ""
        lines = []
        for r in runs:
            when = datetime.fromtimestamp(
                r.get("started") or 0).strftime("%d-%b-%Y %H:%M:%S")
            exit_code = r.get("exit")
            lines.append("{}  {}{}\n    $ {}".format(
                when, r.get("module", "?"),
                "" if exit_code is None else "  (exit {})".format(exit_code),
                r.get("command", "")))
        return "### RUN HISTORY ###\n" + "\n".join(lines) + "\n"
