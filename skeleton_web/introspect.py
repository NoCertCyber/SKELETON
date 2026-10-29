#!/usr/bin/env python3
"""The bridge to tools/module_introspect.py.

An imports2/ module is a standalone Tk script, and the web edition renders it
as a page.  That is only possible because the helper can load one head-lessly,
walk its real widget tree, and either report what it found (`describe`) or work
out the command a button would fire (`build`) - or run it outright (`run`) for
the actions a shell line cannot represent.

Every call goes out through `xvfb-run`, so the module's own window never
appears; an action that is *meant* to open a window gets the real desktop
passed through in a side channel instead.
"""
import json
import os
import re
import subprocess
import tempfile

from config import IMPORTS_DIR, TOOLS_DIR
import skeleton_core as core

from .settings import INTROSPECT

# Every Tk module carries its own "NEW Terminal" button; on the web there is one
# terminal button, in the launcher header, so the per-module copies are dropped.
NEW_TERMINAL_RE = re.compile(r"new\s*_?\s*terminal", re.I)


class ModuleIntrospector:
    """Runs the helper, and remembers what `describe` said."""

    def __init__(self, desktop):
        self.desktop = desktop
        # describe output keyed by module -> (source mtime, payload); rebuilt
        # on change.
        self._cache = {}

    def _call(self, args, timeout):
        """Run the helper under a headless X server, return (parsed JSON, error).

        xvfb hides the module's Tk window while it is introspected, but an
        action that opens a window should still land on the real desktop - pass
        our own DISPLAY through in a side channel so the helper can target it."""
        cmd = ["xvfb-run", "-a", "python3", INTROSPECT] + args
        env = os.environ.copy()
        if self.desktop.display:
            env["SKELETON_WEB_DISPLAY"] = self.desktop.display
        if self.desktop.xauthority:
            env["SKELETON_WEB_XAUTHORITY"] = self.desktop.xauthority
        try:
            proc = subprocess.run(cmd, cwd=str(TOOLS_DIR.parent), capture_output=True,
                                  text=True, timeout=timeout, env=env)
        except subprocess.TimeoutExpired:
            return None, "module_introspect timed out"
        except OSError as exc:
            return None, "could not start module_introspect: {}".format(exc)
        if proc.returncode != 0:
            return None, (proc.stderr or proc.stdout or "module_introspect failed").strip()
        try:
            return json.loads(proc.stdout), None
        except ValueError:
            return None, "module_introspect returned non-JSON: {}".format(proc.stdout[:300])

    def _call_with_payload(self, verb, module, payload, timeout):
        """`build` and `run` both take the filled-in fields as a JSON file."""
        tmp = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False,
                                          encoding="utf-8")
        try:
            json.dump(payload, tmp)
            tmp.close()
            return self._call([verb, module, tmp.name], timeout=timeout)
        finally:
            os.unlink(tmp.name)

    def describe(self, module):
        """Cached describe payload for a module, keyed on the source file's mtime."""
        try:
            mtime = (IMPORTS_DIR / (module + ".py")).stat().st_mtime
        except OSError:
            mtime = 0
        cached = self._cache.get(module)
        if cached and cached[0] == mtime:
            return cached[1], None
        data, err = self._call(["describe", module], timeout=60)
        if err:
            return None, err
        # Buttons keep their original index, which is what a run posts back.
        data["buttons"] = [b for b in data.get("buttons", [])
                           if not NEW_TERMINAL_RE.search(b.get("text", ""))]
        # Tag each field with the engagement value that belongs in it, so the
        # page can pre-fill from the session instead of the module's example
        # default.
        for f in data.get("fields", []):
            if f.get("kind") == "entry":
                f["session_key"] = core.session_key_for(f.get("label", "")) or ""
        self._cache[module] = (mtime, data)
        return data, None

    def build(self, module, payload, timeout=120):
        """The command the chosen button would fire, without running it."""
        return self._call_with_payload("build", module, payload, timeout)

    def run(self, module, payload, timeout=240):
        """Fill the fields, invoke the button, run what it builds; buffered."""
        return self._call_with_payload("run", module, payload, timeout)
