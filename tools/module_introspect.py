#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Headless bridge between the imports2/ Tk modules and SKELETON_WEB.py.
#
# Each imports2/<module>.py is a small Tk script: an `info` cheatsheet string, a
# titled window, some Label/Entry input rows and a RUN_* button that builds a
# shell command and runs it in gnome-terminal.  This script loads a module with
# Tk's mainloop stubbed out (the approach already used for headless testing),
# walks the real widget tree and reports it as JSON, or - in "run" mode -
# fills the entries with browser-supplied values, invokes a button, intercepts
# the shell command it would have handed to gnome-terminal, and runs that
# command here instead so the output can go back to the web page.
#
#   python3 tools/module_introspect.py describe <module>
#   python3 tools/module_introspect.py build <module> <payload.json>
#   python3 tools/module_introspect.py run   <module> <payload.json>
#
# "build" reports the command a button would fire without running it; "run"
# builds and then executes it.
#
# Run it under xvfb-run -a so it never needs a real display.
import builtins
import io
import json
import os
import re
import runpy
import shlex
import shutil
import socket
import subprocess
import sys
import time
import types

# Give a just-started service / server a moment to come up before the page is
# told to open it in a browser.
URL_OPEN_DELAY = float(os.environ.get("SKELETON_WEB_URL_DELAY", "1"))

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from config import WORKING_DIR  # noqa: E402

# The shared notes channel the launcher tab polls.  In the web edition every run
# is posted to it as one lock-guarded block, so a module's own launcher-style
# writes / `tee -a` into this file must be neutralised - otherwise concurrent
# runs interleave here and race the poll's read+truncate.
_NOTES_PATH = os.path.abspath(str(WORKING_DIR / "working_file.txt"))
_NOTES_FILE_RE = re.compile(
    r"""\s*(?:\|\s*tee(?:\s+-a)?|>>?)\s*"""
    r"""(?:'[^']*working_file\.txt'|"[^"]*working_file\.txt"|\S*working_file\.txt)"""
)


def _strip_notes_redirect(cmd):
    """Drop a module's `| tee -a .../working_file.txt` or `>> .../working_file.txt`."""
    return _NOTES_FILE_RE.sub("", cmd) if isinstance(cmd, str) else cmd


def _guarded_open(real_open):
    """open() wrapper that swallows writes to the shared notes file, passes all
    other paths and every read straight through."""
    def _open(file, mode="r", *args, **kwargs):
        try:
            hit = os.path.abspath(os.fspath(file)) == _NOTES_PATH
        except TypeError:
            hit = False
        if hit and any(c in mode for c in "wax+"):
            return io.BytesIO() if "b" in mode else io.StringIO()
        return real_open(file, mode, *args, **kwargs)
    return _open

RUN_TIMEOUT = int(os.environ.get("SKELETON_WEB_RUN_TIMEOUT", "180"))
# Buttons that just spawn a bare terminal - nothing to run head-less.
TERMINAL_LABELS = {"new terminal", "new_terminal"}
# Sentinel from _unwrap: the action only opens a terminal window.
TERMINAL = object()
# Terminal emulators to try, in order, for a "NEW Terminal" button.
TERMINALS = ["gnome-terminal", "x-terminal-emulator", "konsole",
             "xfce4-terminal", "mate-terminal", "xterm"]

# ANSI CSI / OSC escape sequences plus stray single-char escapes.  Many CLI tools
# emit colour codes even when stdout is not a tty; in a browser <pre> they show
# up as literal "\x1b[1;31m" noise.
_ANSI_RE = re.compile(
    r"\x1b(?:\[[0-?]*[ -/]*[@-~]|\][^\x07\x1b]*(?:\x07|\x1b\\)|[@-Z\\-_])"
)


def _strip_ansi(text):
    return _ANSI_RE.sub("", text) if text else text


def _clean(text):
    """Raw command output -> readable in a browser <pre>: drop ANSI colour codes,
    collapse carriage-return progress redraws, strip remaining control bytes."""
    if not text:
        return text
    text = _strip_ansi(text)
    lines = []
    for line in text.split("\n"):
        if "\r" in line:            # a real terminal would show only the last redraw
            line = line.split("\r")[-1]
        lines.append(line)
    text = "\n".join(lines)
    return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)


def _spawn_terminal():
    """Actually open a terminal window on the server's desktop, like the Tk
    module's NEW_Terminal() does.

    Under xvfb-run our own DISPLAY points at the throwaway X server, so prefer
    SKELETON_WEB_DISPLAY (the web server's real display, passed through by
    SKELETON_WEB.py) when it is set."""
    display = os.environ.get("SKELETON_WEB_DISPLAY") or os.environ.get("DISPLAY")
    if not display:
        return {"command": "gnome-terminal",
                "output": "no X display on the server - cannot open a terminal window"}
    env = dict(os.environ, DISPLAY=display)
    # Our own XAUTHORITY is xvfb-run's throwaway cookie - drop it, or use the
    # real desktop's cookie that SKELETON_WEB.py passed through.
    xauth = os.environ.get("SKELETON_WEB_XAUTHORITY")
    if xauth:
        env["XAUTHORITY"] = xauth
    else:
        env.pop("XAUTHORITY", None)
    for term in TERMINALS:
        if not shutil.which(term):
            continue
        try:
            proc = subprocess.Popen(
                [term], cwd=REPO, start_new_session=True, env=env,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
        except OSError as exc:
            return {"command": term, "output": "failed to launch {}: {}".format(term, exc)}
        return {"command": term,
                "output": "opened {} on the server desktop ({}, pid {})".format(
                    term, display, proc.pid)}
    return {"command": "gnome-terminal",
            "output": "no terminal emulator found on the server (tried: {})".format(
                ", ".join(TERMINALS))}


def _stub_tk():
    """Import tkinter with mainloop() neutered so a module builds without blocking."""
    import tkinter

    tkinter.Tk.mainloop = lambda self, *a, **k: None
    tkinter.Misc.mainloop = lambda self, *a, **k: None
    tkinter.mainloop = lambda *a, **k: None
    return tkinter


def _load(module):
    """runpy the module as __main__; return its namespace dict."""
    path = os.path.join(REPO, "imports2", module + ".py")
    if not os.path.isfile(path):
        raise SystemExit("no such module: {}".format(module))
    return runpy.run_path(path, run_name="__main__")


def _flatten(root):
    """(winfo_class, widget) for every descendant of root, in creation order."""
    out = []

    def walk(w):
        for child in w.winfo_children():
            out.append((child.winfo_class(), child))
            walk(child)

    walk(root)
    return out


def _var_value(w, varname):
    try:
        return str(w.getvar(str(varname)))
    except Exception:
        return ""


def _group_of(w):
    """The Tk path of the widget's parent frame - fields sharing one are one row,
    mirroring how the module's own GUI groups them into frames."""
    try:
        return str(w.winfo_parent())
    except Exception:
        return ""


def _inputs(flat):
    """Ordered [(kind, widget, label, default, extra)] for every Entry,
    Checkbutton and OptionMenu.

    Each is labelled by the most recent preceding Label; a Checkbutton uses its
    own text.  OptionMenu (a Menubutton backed by a Tk variable) also reports its
    choices; Checkbutton reports its on/off values and current state.  Every
    input carries extra["group"] = its parent frame, so the web page can lay the
    fields out in the same rows as the module's Tk window."""
    out = []
    last_label = ""
    for cls, w in flat:
        if cls in ("Label", "TLabel"):
            try:
                last_label = str(w.cget("text")).strip()
            except Exception:
                last_label = ""
            continue
        if cls in ("Entry", "TEntry"):
            try:
                default = w.get()
            except Exception:
                default = ""
            # The module sized this box for what it holds - a 15-character user
            # name, a 52-character wordlist path.  Carry that across so the web
            # page can give each field the same share of a row.
            try:
                width = int(w.cget("width"))
            except Exception:
                width = 0
            out.append(("entry", w, last_label or "value", default,
                        {"group": _group_of(w), "width": width}))
            last_label = ""
        elif cls in ("Checkbutton", "TCheckbutton"):
            try:
                text = str(w.cget("text")).strip()
                var = w.cget("variable")
                on = str(w.cget("onvalue"))
                off = str(w.cget("offvalue"))
            except Exception:
                continue
            if not var:
                continue
            current = _var_value(w, var)
            out.append(("check", w, text or last_label or "option", current,
                        {"on": on, "off": off, "checked": current == on,
                         "group": _group_of(w)}))
            last_label = ""
        elif cls in ("Menubutton", "TMenubutton"):
            try:
                default = str(w.cget("text"))
            except Exception:
                default = ""
            options = []
            try:
                menu = w.nametowidget(w.cget("menu"))
                end = menu.index("end")
                if end is not None:
                    options = [str(menu.entrycget(i, "label"))
                               for i in range(end + 1)]
            except Exception:
                options = []
            out.append(("option", w, last_label or "option", default,
                        {"options": options, "group": _group_of(w)}))
            last_label = ""
    return out


def _describe(module):
    _stub_tk()
    ns = _load(module)
    root = ns.get("guibox")
    flat = _flatten(root) if root is not None else []

    fields = []
    for kind, _w, label, default, extra in _inputs(flat):
        f = {"label": label, "default": default, "kind": kind,
             "group": extra.get("group", "")}
        if kind == "entry":
            f["width"] = extra.get("width", 0)
        if kind == "check":
            f["checked"] = bool(extra.get("checked"))
            f["on"] = extra.get("on", "")
            f["off"] = extra.get("off", "")
        elif kind == "option":
            f["options"] = extra.get("options", [])
        fields.append(f)

    buttons = []
    for idx, (cls, w) in enumerate(b for b in flat if b[0] == "Button"):
        try:
            text = str(w.cget("text")).strip()
        except Exception:
            text = "button {}".format(idx)
        # A button carries its parent frame the way the inputs do: where the
        # module put a button in the same frame as an entry, the web page can
        # put it on that same row rather than in a bar of its own.
        buttons.append({"index": idx, "text": text or "button {}".format(idx),
                        "group": _group_of(w)})

    info = ns.get("info")
    if not isinstance(info, str):
        info = ""
        for cls, w in flat:
            if cls == "Text":
                try:
                    info = w.get("1.0", "end-1c")
                except Exception:
                    pass
                break
    info = _strip_ansi(info)

    title = ""
    try:
        title = root.title()
    except Exception:
        pass

    return {
        "module": module,
        "title": title or module,
        "info": info,
        "fields": fields,
        "buttons": buttons,
    }


def _strip_terminal_argv(argv):
    """['gnome-terminal', '--working-directory', DIR, '--', 'python3', '-m', ...]
    -> (['python3', '-m', ...], DIR).  Also unwraps a trailing `bash -c "<cmd>"`.
    Returns (command list-or-str-or-None, cwd-or-None)."""
    cwd = None
    rest = []
    i, n = 1, len(argv)
    while i < n:
        a = argv[i]
        if a == "--":
            rest = list(argv[i + 1:])
            break
        if a in ("--working-directory", "--default-working-directory") and i + 1 < n:
            cwd = argv[i + 1]
            i += 2
            continue
        if a.startswith("--working-directory="):
            cwd = a.split("=", 1)[1]
            i += 1
            continue
        if a == "-e" and i + 1 < n:  # gnome-terminal -e "<cmd string>"
            return argv[i + 1], cwd
        i += 1
    if not rest:  # no `--` seen; take the trailing non-option words
        rest = [x for x in argv[1:] if not x.startswith("-")]
    if len(rest) >= 3 and os.path.basename(rest[0]) in ("bash", "sh") and rest[1] == "-c":
        inner = re.sub(r"\s*(;\s*exec\s+bash|&&\s*bash|;\s*bash)\s*$", "",
                       rest[2]).strip()
        return (inner or None), cwd
    return (rest or None), cwd


def _wait_port(port, host="127.0.0.1", timeout=120):
    """Block until something accepts TCP on host:port, or `timeout` seconds pass.

    Used for servers that do real work before they bind (mdbook rebuilds the
    whole book first), so a fixed sleep is either too short or wastes time.
    """
    deadline = time.time() + timeout
    while time.time() < deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            try:
                s.connect((host, port))
                return True
            except OSError:
                time.sleep(1)
    return False


def _served_page(root):
    """Best landing path for a static server rooted at `root` ('' means /)."""
    try:
        if os.path.isfile(os.path.join(root, "index.html")):
            return ""
        htmls = sorted(f for f in os.listdir(root) if f.lower().endswith(".html"))
    except OSError:
        return ""
    if not htmls:
        return ""
    named = [f for f in htmls if os.path.splitext(f)[0] == os.path.basename(root)]
    if named:
        return named[0]
    return htmls[0] if len(htmls) == 1 else ""


def _unwrap(call):
    """Recover the real command from an intercepted subprocess call.

    Handles the module idioms:
        subprocess.call(['gnome-terminal -- bash -c "<cmd> ; exec bash"'], shell=True)
        subprocess.call(['gnome-terminal --wait -- bash -c "<cmd> && bash"'], shell=True)
        subprocess.Popen(['gnome-terminal', '--working-directory', DIR, '--', 'python3', ...])
        subprocess.call(["gnome-terminal"])            -> TERMINAL (just a terminal)
        subprocess.call(["some", "argv"])              -> the argv list
    Returns (fn_name, command, cwd): command is a str (run via the shell), a list
    (run as argv), TERMINAL, or None; cwd is a str or None.
    """
    fn_name, args, kwargs = call
    argv = args[0] if args else kwargs.get("args")
    cwd = kwargs.get("cwd")
    if kwargs.get("shell") and isinstance(argv, list) and argv and isinstance(argv[0], str):
        argv = argv[0]

    if isinstance(argv, list):
        base = os.path.basename(argv[0]) if argv else ""
        if base in TERMINALS:
            if len(argv) == 1:
                return fn_name, TERMINAL, cwd
            inner, tcwd = _strip_terminal_argv(argv)
            return fn_name, inner, (tcwd or cwd)
        return fn_name, argv, cwd

    if not isinstance(argv, str):
        return fn_name, None, cwd

    # Parse it as the shell would.  Slicing the outer quote characters off
    # instead would leave the shell's own escaping in place, so a field value
    # containing a quote came back as ...'"'"'... and could not be re-run.
    try:
        words = shlex.split(argv)
    except ValueError:                       # unbalanced quotes - fall back below
        words = []
    if words and os.path.basename(words[0]) in TERMINALS:
        inner, tcwd = _strip_terminal_argv(words)
        if inner is TERMINAL or inner:
            return fn_name, inner, (tcwd or cwd)

    m = re.search(r"bash\s+-c\s+(.*)$", argv, re.S)
    if m:
        inner = m.group(1).strip()
        if len(inner) >= 2 and inner[0] in "\"'" and inner[-1] == inner[0]:
            inner = inner[1:-1]
        inner = re.sub(r"\s*(;\s*exec\s+bash|&&\s*bash|;\s*bash)\s*$", "", inner).strip()
        return fn_name, (inner or None), cwd
    if argv.strip() in TERMINALS:
        return fn_name, TERMINAL, cwd
    if "gnome-terminal" in argv:
        wd = re.search(r"--working-directory[= ]\s*'?([^\s'\"]+)", argv)
        m2 = re.search(r"gnome-terminal\b.*?\s--\s+(.*)$", argv, re.S)
        cmd = m2.group(1).strip() if m2 else None
        return fn_name, (cmd or None), (wd.group(1) if wd else cwd)
    return fn_name, argv, cwd


# The real subprocess entry points, kept aside so a captured command can still
# be launched for real after the module's own calls have been stubbed out.
_REAL = {
    "call": subprocess.call,
    "Popen": subprocess.Popen,
    "run": subprocess.run,
}


def _build(module, payload):
    """Drive a module's widgets, press one of its buttons and capture the
    command that button *would* run - without running it.

    Returns a dict whose ``kind`` says what the command is:
        "terminal" - the button just opens a terminal
        "none"     - the button maps to nothing head-less
        "browser"  - it opens a URL (plus optional setup steps)
        "popen"    - a long-lived server / listener
        "plain"    - an ordinary command to execute and collect output from
    Keys prefixed with ``_`` are in-process only and are stripped by the CLI.
    """
    _stub_tk()

    calls = []

    def _cap(name):
        def inner(*a, **k):
            calls.append((name, a, k))
            return types.SimpleNamespace(returncode=0, stdout="", stderr="", pid=-1)
        return inner

    real_open = builtins.open

    def _stub():
        subprocess.call = _cap("call")
        subprocess.Popen = _cap("Popen")
        subprocess.run = _cap("run")
        builtins.open = _guarded_open(real_open)

    def _restore():
        subprocess.call = _REAL["call"]
        subprocess.Popen = _REAL["Popen"]
        subprocess.run = _REAL["run"]
        builtins.open = real_open

    _stub()
    try:
        ns = _load(module)
    finally:
        _restore()

    root = ns.get("guibox")
    flat = _flatten(root) if root is not None else []
    inputs = _inputs(flat)
    buttons = [w for cls, w in flat if cls == "Button"]

    for (kind, w, _label, _default, _extra), value in zip(inputs, payload.get("fields", [])):
        try:
            if kind == "entry":
                w.delete(0, "end")
                w.insert(0, value)
            elif kind == "option":  # drive the OptionMenu's backing Tk variable
                varname = w.cget("textvariable") or w.cget("variable")
                if varname:
                    w.setvar(str(varname), value)
            elif kind == "check":   # set the Checkbutton var to its on/off value
                varname = w.cget("variable")
                if varname:
                    w.setvar(str(varname), value)
        except Exception:
            pass

    idx = int(payload.get("button", 0))
    if not buttons:
        return {"kind": "none", "command": "", "output": "(module exposes no buttons)"}
    if not (0 <= idx < len(buttons)):
        idx = 0

    label = ""
    try:
        label = str(buttons[idx].cget("text")).strip().lower()
    except Exception:
        pass
    if label in TERMINAL_LABELS:
        return {"kind": "terminal", "command": "", "output": ""}

    calls.clear()
    # Re-stub only for the duration of the callback so we grab its command.
    _stub()
    try:
        buttons[idx].invoke()
    finally:
        _restore()

    if not calls:
        return {"kind": "none", "command": "",
                "output": "(button did not launch a command)"}

    fn_name, cmd, cwd = _unwrap(calls[-1])
    run_cwd = cwd if cwd and os.path.isdir(cwd) else REPO
    if cmd is TERMINAL:
        return {"kind": "terminal", "command": "", "output": ""}
    if cmd is None:
        return {"kind": "none", "command": "",
                "output": "(this action does not map to a head-less command)"}

    shell = isinstance(cmd, str)
    if shell:
        cmd = _strip_notes_redirect(cmd)

    # Route this run's file output into the per-notes-tab folder the web layer
    # asked for: swap the WORKING_DIR/... prefix (leaving the notes channel
    # alone) and start the command in that folder for any relative paths.
    out_dir = payload.get("out_dir")
    if out_dir:
        try:
            os.makedirs(out_dir, exist_ok=True)
        except OSError:
            out_dir = None
    if out_dir and os.path.abspath(out_dir) != os.path.abspath(str(WORKING_DIR)):
        _wd = str(WORKING_DIR)
        _keep = os.path.join(_wd, "working_file.txt")

        def _redir(s):
            if not isinstance(s, str) or _wd not in s:
                return s
            s = s.replace(_keep, "\x00N\x00")
            s = s.replace(_wd + os.sep, out_dir + os.sep)
            return s.replace("\x00N\x00", _keep)

        cmd = _redir(cmd) if shell else [_redir(x) for x in cmd]
        if run_cwd in (REPO, _wd):
            run_cwd = out_dir

    printable = cmd if shell else " ".join(cmd)
    # What a caller types at a shell to run this: an argv command has to be
    # quoted back into one line, or an argument with a space in it would split.
    command_sh = printable if shell else shlex.join(cmd)

    _BROWSERS = ("xdg-open", "sensible-browser", "x-www-browser", "firefox",
                 "google-chrome", "chromium", "chromium-browser", "open")
    _argv0 = os.path.basename((cmd.split() or [""])[0]) if shell and cmd else (
        os.path.basename(cmd[0]) if isinstance(cmd, list) and cmd else "")

    if _argv0 in _BROWSERS:
        kind = "browser"
    elif fn_name == "Popen":
        kind = "popen"
    else:
        kind = "plain"

    return {"kind": kind, "command": printable, "command_sh": command_sh,
            "cwd": run_cwd, "shell": shell,
            "_cmd": cmd, "_calls": calls, "_run_cwd": run_cwd}


def _execute(built):
    """Run what _build() captured and return {command, output[, url]}."""
    kind = built.get("kind")
    if kind == "terminal":
        return _spawn_terminal()
    if kind == "none":
        return {"command": built.get("command", ""), "output": built.get("output", "")}

    cmd = built["_cmd"]
    calls = built["_calls"]
    shell = built["shell"]
    run_cwd = built["_run_cwd"]
    printable = built["command"]

    _BROWSERS = ("xdg-open", "sensible-browser", "x-www-browser", "firefox",
                 "google-chrome", "chromium", "chromium-browser", "open")

    # A browser-launcher (xdg-open / firefox / ...) can't run head-less; hand the
    # URL back so the web page opens it in a new window instead.
    if kind == "browser":
        m = re.search(r"https?://[^\s'\"]+", printable)
        url = m.group(0) if m else ""
        # run any setup steps the module did before opening the browser
        # (e.g. `sudo systemctl start nessusd`) - never block on a password.
        notes = []
        for c in calls[:-1]:
            _fn2, c_cmd, c_cwd = _unwrap(c)
            if not c_cmd or c_cmd is TERMINAL:
                continue
            c_disp = c_cmd if isinstance(c_cmd, str) else " ".join(c_cmd)
            if os.path.basename((c_disp.split() or [""])[0]) in _BROWSERS:
                continue
            run_c = re.sub(r"\bsudo\b", "sudo -n", c_disp)
            try:
                p = _REAL["run"](run_c, shell=True, cwd=(c_cwd or run_cwd),
                                 capture_output=True, text=True, timeout=60)
                got = _clean((p.stdout or "") + (p.stderr or "")).strip()
                notes.append("$ {}\n{}".format(
                    run_c, got or "(exit {})".format(p.returncode)))
            except (OSError, subprocess.TimeoutExpired) as exc:
                notes.append("$ {}\n(failed: {})".format(run_c, exc))
        if url:
            time.sleep(URL_OPEN_DELAY)          # let the service settle first
            notes.append("open {} in your browser".format(url))
        return {"command": printable,
                "output": "\n".join(notes) or "(browser launch with no URL)",
                "url": url}

    # A module that used Popen (not call/run) wants a long-lived process - a local
    # web server, listener, sniffer.  Blocking on it here just times out, so
    # launch it detached on the server and report where to reach it.
    if kind == "popen":
        try:
            proc = _REAL["Popen"](
                cmd, shell=shell, cwd=run_cwd,
                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL, start_new_session=True,
            )
        except OSError as exc:
            return {"command": printable, "output": "failed to start: {}".format(exc)}
        parts = cmd if isinstance(cmd, list) else re.split(r"\s+", cmd)
        result = {"command": printable,
                  "output": "started in the background on the server "
                            "(pid {}, cwd {})".format(proc.pid, run_cwd)}
        if any("http.server" in p for p in parts) or "-S" in parts:
            port = next((p for p in reversed(parts) if p.isdigit()), "8000")
            result["url"] = "http://127.0.0.1:{}/{}".format(port, _served_page(run_cwd))
            time.sleep(URL_OPEN_DELAY)          # let the server bind first
            result["output"] += "\nopen {} in your browser".format(result["url"])
        elif any(os.path.basename(p) in ("mdbook", "mdbook-serve") for p in parts) \
                and "serve" in parts:
            # mdbook's own dev server (HackTricks "run hacktricks"): it rebuilds
            # the whole book before binding, so poll the port, don't fixed-sleep.
            m = re.search(r"(?:-p|--port)[=\s]+(\d+)", printable)
            port = m.group(1) if m else "3000"
            result["url"] = "http://127.0.0.1:{}/".format(port)
            _wait_port(int(port), timeout=150)
            result["output"] += "\nopen {} in your browser".format(result["url"])
        return result

    try:
        proc = _REAL["run"](
            cmd, shell=shell, cwd=run_cwd, capture_output=True, text=True,
            timeout=RUN_TIMEOUT, errors="replace",
        )
        output = (proc.stdout or "") + (proc.stderr or "")
        returncode = proc.returncode
        timed_out = False
    except subprocess.TimeoutExpired as exc:
        # Keep whatever the command managed to print before the deadline -
        # a partial nmap / gobuster result is still worth having.
        def _txt(v):
            if not v:
                return ""
            return v if isinstance(v, str) else v.decode("utf-8", "replace")
        output = _txt(exc.stdout) + _txt(exc.stderr)
        output += "\n(timed out after {}s)".format(RUN_TIMEOUT)
        returncode = None
        timed_out = True
    except OSError as exc:
        return {"command": printable, "output": "failed to run: {}".format(exc)}

    # Many modules redirect into a working-dir file; surface it if they did.
    if shell:
        redir = re.search(r">\s*'?([^'\s;|&]+)'?", cmd)
        if redir:
            target = redir.group(1)
            if not os.path.isabs(target):
                target = os.path.join(run_cwd, target)
            try:
                if os.path.commonpath([os.path.abspath(target), str(WORKING_DIR)]) == str(WORKING_DIR):
                    with open(target, "r", encoding="utf-8", errors="replace") as fh:
                        body = fh.read()
                    output += "\n----- {} -----\n{}".format(os.path.basename(target), body)
            except (OSError, ValueError):
                pass

    output = _clean(output)
    if not output.strip():
        output = ("(command produced no output; timed out)" if timed_out
                  else "(command produced no output; exit {})".format(returncode))
    return {"command": printable, "output": output}


def _run(module, payload):
    return _execute(_build(module, payload))


def main(argv):
    if len(argv) >= 3 and argv[1] == "describe":
        print(json.dumps(_describe(argv[2])))
        return
    if len(argv) >= 4 and argv[1] == "run":
        with open(argv[3], "r", encoding="utf-8") as fh:
            payload = json.load(fh)
        print(json.dumps(_run(argv[2], payload)))
        return
    if len(argv) >= 4 and argv[1] == "build":
        # Same as `run`, but stop before executing: report the command the
        # chosen button would fire so the caller can stream it itself.
        with open(argv[3], "r", encoding="utf-8") as fh:
            payload = json.load(fh)
        built = _build(argv[2], payload)
        print(json.dumps({k: v for k, v in built.items()
                          if not k.startswith("_")}))
        return
    raise SystemExit(__doc__)


if __name__ == "__main__":
    main(sys.argv)
