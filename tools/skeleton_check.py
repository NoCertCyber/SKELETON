#!/usr/bin/env python3
"""SKELETON self-check - the gate every change runs through.

Stdlib only, like the rest of the tree.  Run from anywhere:

    python3 tools/skeleton_check.py            # everything except the slow pass
    python3 tools/skeleton_check.py --describe # also head-lessly build all modules
    python3 tools/skeleton_check.py --only quoting

Checks
  compile   every module byte-compiles - and so do the launchers, the shared
            core, config.py and tools/, which are not modules but break just
            as loudly
  names     nothing here uses a name it never imports - a NameError that only
            fires when the code runs, which byte-compiling cannot see
  quoting   no module interpolates a value into a shell=True string without
            shlex.quote() - the defect class that template.py used to teach
  shadowed  no module defines the same function twice (a converted button
            reusing a name the module already had)
  paths     no field is pre-filled with an absolute path that is not there
  relocate  nothing outside a cheat-sheet hard-codes /opt/SKELETON, so
            SKELETON_ROOT still moves the tree
  glossary  data/glossary.txt and imports2/ agree 1:1, both directions
  stages    every module's filename prefix is a stage the launchers list
  describe  tools/module_introspect.py can drive every module (needs xvfb-run)
  build     every button builds the command it would run (needs xvfb-run) -
            describe only proves the window opens, not that pressing anything
            in it works - and its output still lands under working/ when the
            save-file box holds a path.  Skips BUILD_SKIP: a module that does
            its work in Python rather than through a command really would do it
  scripts   the JavaScript the web edition serves parses, and every
            /web file its pages ask for is there (needs flask + node;
            skipped when either is missing)

Exit status is 0 only when every selected check passes.
"""
import argparse
import ast
import builtins
import concurrent.futures
import importlib.util
import json
import os
import py_compile
import re
import shutil
import subprocess
import symtable
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import GLOSSARY, IMPORTS_DIR, NON_MODULE_STEMS, TOOLS_DIR  # noqa: E402

# Kept in step with pentest_chain / PENTEST_CHAIN in the two launchers.
STAGES = ("info", "OSIN", "DNS", "enum", "web", "mitm", "wireless",
          "bruteforce", "exploit", "powershell", "transfer", "forensic")


def modules():
    return sorted(p for p in IMPORTS_DIR.glob("*.py")
                  if p.stem not in NON_MODULE_STEMS)


# --- compile ---------------------------------------------------------------

def support_sources():
    """The Python outside imports2/ that a run depends on.

    The gate used to compile only the modules, so a typo in SKELETON_WEB.py -
    the whole launcher - was found by whoever started the server,
    mid-engagement.  These are cheap; there is no reason to leave them out.
    """
    root = IMPORTS_DIR.parent
    found = [root / name for name in
             ("SKELETON_WEB.py", "skeleton_core.py", "config.py")]
    found += sorted((root / "skeleton_web").rglob("*.py"))
    found += sorted(TOOLS_DIR.rglob("*.py"))
    return [p for p in found if p.is_file()]


def check_compile(paths):
    bad = []
    paths = list(paths) + support_sources()
    with tempfile.TemporaryDirectory() as tmp:
        for i, p in enumerate(paths):
            try:
                py_compile.compile(str(p), cfile=os.path.join(tmp, "%d.pyc" % i),
                                   doraise=True)
            except py_compile.PyCompileError as exc:
                bad.append("{}: {}".format(p.name, str(exc).strip().splitlines()[-1]))
    return bad


# --- relocate ---------------------------------------------------------------
#
# config.py exists so the tree can be moved (SKELETON_ROOT=/srv/skeleton).  A
# module that hard-codes /opt/SKELETON in a command or a field default ignores
# it and breaks silently the moment the tree is anywhere else - and `paths`
# cannot catch that, because it only asks whether the file exists, and on the
# box where the tree still lives at /opt/SKELETON it does.
#
# Cheat-sheet text is exempt: `info` and its friends are documentation, and a
# worked example is meant to show a real path.

_CHEATSHEET_GLOBALS = {"info", "main_message", "message", "text", "INFO",
                       "PREAMBLE", "banner", "BANNER"}
_ROOT_LITERAL = "/opt/SKELETON"


def _cheatsheet_constants(tree):
    """id()s of the string constants that make up a module's cheat-sheet."""
    out = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        if not any(isinstance(t, ast.Name) and t.id in _CHEATSHEET_GLOBALS
                   for t in node.targets):
            continue
        for sub_node in ast.walk(node.value):
            if isinstance(sub_node, ast.Constant):
                out.add(id(sub_node))
    return out


def check_relocate(paths):
    bad = []
    for p in paths:
        src = p.read_text(encoding="utf-8", errors="replace")
        if _ROOT_LITERAL not in src:
            continue
        try:
            tree = ast.parse(src, str(p))
        except SyntaxError:
            continue
        exempt = _cheatsheet_constants(tree)
        for node in ast.walk(tree):
            if (isinstance(node, ast.Constant) and isinstance(node.value, str)
                    and _ROOT_LITERAL in node.value and id(node) not in exempt):
                first = node.value.strip().splitlines()[:1]
                bad.append("{}:{}: hard-coded {} (use config.py): {}".format(
                    p.name, node.lineno, _ROOT_LITERAL,
                    (first[0] if first else "")[:70]))
    return bad


# --- names ------------------------------------------------------------------
#
# A module that uses a name it never imports byte-compiles perfectly and then
# raises NameError the moment a button is pressed.  `datetime` was missing from
# 97 of the 233: each of them ran its command and then threw on the way to
# writing the timestamp into its own window, so the run happened and the
# module's own record of it did not.  Neither `compile` nor `build` can see
# that - the exception lands in a Tk callback, which prints it and carries on.
#
# symtable does the work: a name a scope reads as a global, that the module
# never binds and that is neither a builtin nor something `from tkinter import
# *` brought in, is a NameError with a button in front of it.

_RUNTIME_GLOBALS = {"__file__", "__name__", "__doc__", "__package__",
                    "__spec__", "__loader__", "__builtins__"}


def _star_names():
    """What `from tkinter import *` puts in a module's namespace."""
    try:
        import tkinter
    except ImportError:               # a box with no Tk cannot run the modules
        return None                   # anyway; skip rather than cry wolf
    return {n for n in dir(tkinter) if not n.startswith("_")}


def _scopes(table, out):
    out.append(table)
    for child in table.get_children():
        _scopes(child, out)
    return out


def check_names(paths):
    star = _star_names()
    if star is None:
        return []
    known_base = set(dir(builtins)) | _RUNTIME_GLOBALS
    bad = []
    for p in list(paths) + support_sources():   # the launchers break the same way

        src = p.read_text(encoding="utf-8", errors="replace")
        try:
            top = symtable.symtable(src, str(p), "exec")
        except SyntaxError:
            continue                  # `compile` reports it, and better
        known = {s.get_name() for s in top.get_symbols()
                 if s.is_assigned() or s.is_imported()} | known_base
        if "from tkinter import *" in src:
            known |= star
        missing = {}
        for scope in _scopes(top, []):
            for sym in scope.get_symbols():
                name = sym.get_name()
                if name in known or not sym.is_referenced():
                    continue
                if scope is top:
                    if not (sym.is_assigned() or sym.is_imported()):
                        missing.setdefault(name, scope.get_name())
                elif sym.is_global():
                    missing.setdefault(name, scope.get_name())
        for name, where in sorted(missing.items()):
            bad.append("{}: '{}' is used in {}() but never imported or "
                       "defined".format(p.name, name, where))
    return bad


# --- quoting ---------------------------------------------------------------
#
# A module builds a shell string and hands it to subprocess with shell=True.
# Values typed by the operator must reach the tool as literal arguments, so
# every dynamic piece has to pass through shlex.quote() somewhere between the
# widget and the shell.  We walk the AST rather than grepping, because every
# module embeds pages of command text inside its `info` cheatsheet string.

def _is_quote_call(node):
    return (isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "quote")


def _dynamic_parts(node):
    """Yield the sub-expressions of a string-building expression that are not
    literals and not already wrapped in shlex.quote()."""
    if isinstance(node, ast.Constant):
        return
    if _is_quote_call(node):
        return
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        yield from _dynamic_parts(node.left)
        yield from _dynamic_parts(node.right)
        return
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mod):
        yield node
        return
    if isinstance(node, ast.JoinedStr):          # f-string
        for v in node.values:
            if isinstance(v, ast.FormattedValue):
                yield from _dynamic_parts(v.value)
        return
    if isinstance(node, ast.Call):
        # "...".format(a, b) - the template is safe, the arguments are not
        if isinstance(node.func, ast.Attribute) and node.func.attr == "format":
            for a in list(node.args) + [k.value for k in node.keywords]:
                yield from _dynamic_parts(a)
            return
        if isinstance(node.func, ast.Attribute) and node.func.attr == "join":
            for a in node.args:
                yield from _dynamic_parts(a)
            return
    yield node


class _QuotingVisitor(ast.NodeVisitor):
    """Find subprocess.*(..., shell=True) whose command is built from unquoted
    dynamic parts, following one level of local variable assignment."""

    def __init__(self, path):
        self.path = path
        self.problems = []
        self.assigned = {}

    def visit_Assign(self, node):
        for t in node.targets:
            if isinstance(t, ast.Name):
                self.assigned[t.id] = node.value
        self.generic_visit(node)

    def _resolve(self, node, depth=0):
        """A Name bound earlier in the file stands in for its value."""
        if isinstance(node, ast.Name) and depth < 4 and node.id in self.assigned:
            return self._resolve(self.assigned[node.id], depth + 1)
        return node

    def visit_Call(self, node):
        self.generic_visit(node)
        is_shell = any(k.arg == "shell" and isinstance(k.value, ast.Constant)
                       and k.value.value is True for k in node.keywords)
        if not is_shell or not node.args:
            return
        if not (isinstance(node.func, ast.Attribute)
                and node.func.attr in ("call", "run", "Popen", "check_output")):
            return

        arg = node.args[0]
        # subprocess.call(['<one long shell string>'], shell=True)
        if isinstance(arg, (ast.List, ast.Tuple)) and len(arg.elts) == 1:
            arg = arg.elts[0]

        for part in _dynamic_parts(self._resolve(arg)):
            part = self._resolve(part)
            if _is_quote_call(part):
                continue
            for sub in _dynamic_parts(part):
                if _is_quote_call(sub):
                    continue
                self.problems.append(
                    "{}:{}: unquoted value in a shell=True command "
                    "(wrap it in shlex.quote)".format(self.path.name, node.lineno))
                return


def check_quoting(paths):
    bad = []
    for p in paths:
        try:
            tree = ast.parse(p.read_text(encoding="utf-8", errors="replace"), str(p))
        except SyntaxError as exc:
            bad.append("{}: {}".format(p.name, exc))
            continue
        v = _QuotingVisitor(p)
        v.visit(tree)
        bad.extend(v.problems)
    return bad


# --- shadowed ---------------------------------------------------------------
#
# A module defining the same function twice silently loses the first one, which
# is exactly what happens when a converted button reuses a name the module
# already had (its button then runs the wrong command, or nothing).

def check_shadowed(paths):
    bad = []
    for p in paths:
        try:
            tree = ast.parse(p.read_text(encoding="utf-8", errors="replace"), str(p))
        except SyntaxError:
            continue
        seen = {}
        for node in tree.body:
            if isinstance(node, ast.FunctionDef):
                if node.name in seen:
                    bad.append("{}:{}: def {}() shadows the one on line {}".format(
                        p.name, node.lineno, node.name, seen[node.name]))
                seen[node.name] = node.lineno
    return bad


# --- paths ------------------------------------------------------------------
#
# A field pre-filled with an absolute path that does not exist is a
# launch-breaking default: the button builds a command that cannot work and the
# operator only finds out from the tool's error.  Only absolute paths are
# checked - a relative default like "hashes.txt" names the operator's own file.

_PATH_RE = re.compile(r"^(/opt/SKELETON/|/usr/share/|/usr/local/)")


def _default_consts(tree):
    """Every literal used as an Entry default, including the fallback of an
    os.environ.get("SKELETON_X", "<default>")."""
    out = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "insert"
                and len(node.args) == 2):
            continue
        val = node.args[1]
        if isinstance(val, ast.Call) and isinstance(val.func, ast.Attribute) \
                and val.func.attr == "get" and len(val.args) == 2:
            val = val.args[1]
        if isinstance(val, ast.Constant) and isinstance(val.value, str):
            out.append((node.lineno, val.value))
    return out


def check_paths(paths):
    bad = []
    for p in paths:
        try:
            tree = ast.parse(p.read_text(encoding="utf-8", errors="replace"), str(p))
        except SyntaxError:
            continue
        for lineno, value in _default_consts(tree):
            if _PATH_RE.match(value) and not os.path.exists(value):
                bad.append("{}:{}: field default does not exist: {}".format(
                    p.name, lineno, value))
    return bad


# --- glossary --------------------------------------------------------------

_ENTRY_RE = re.compile(r"^(\w+)\s+-\s")


def check_glossary(paths):
    stems = {p.stem for p in paths}
    try:
        lines = GLOSSARY.read_text(encoding="utf-8", errors="replace").split("\n")
    except OSError as exc:
        return ["cannot read {}: {}".format(GLOSSARY, exc)]
    entries = set()
    dupes = []
    for line in lines:
        m = _ENTRY_RE.match(line)
        if m:
            if m.group(1) in entries:
                dupes.append("duplicate glossary entry: " + m.group(1))
            entries.add(m.group(1))
    bad = list(dupes)
    bad += ["no glossary entry: " + s for s in sorted(stems - entries)]
    try:
        import skeleton_core as core
        is_demo = getattr(core, "IS_DEMO", False)
    except Exception:
        is_demo = False
    if not is_demo:
        bad += ["glossary entry with no module: " + s for s in sorted(entries - stems)]
    return bad


# --- stages ----------------------------------------------------------------

def check_stages(paths):
    return ["{}: prefix is not one of {}".format(p.name, ", ".join(STAGES))
            for p in paths if not p.stem.split("_")[0] in STAGES]


# --- describe --------------------------------------------------------------

def _describe_one(stem):
    try:
        proc = subprocess.run(
            ["xvfb-run", "-a", "python3", str(TOOLS_DIR / "module_introspect.py"),
             "describe", stem],
            capture_output=True, text=True, timeout=120)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return "{}: describe failed to run: {}".format(stem, exc)
    if proc.returncode != 0:
        return "{}: describe exited {}: {}".format(
            stem, proc.returncode, proc.stderr.strip().splitlines()[-1:] or "")
    try:
        data = json.loads(proc.stdout)
    except ValueError:
        return "{}: describe did not return JSON".format(stem)
    if not data.get("buttons"):
        return "{}: describe found no buttons".format(stem)
    return None


def check_describe(paths):
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        results = pool.map(_describe_one, [p.stem for p in paths])
    return [r for r in results if r]


# --- build ------------------------------------------------------------------
#
# `describe` proves a module's window can be built and walked.  It says nothing
# about what happens when a button is pressed - and that is the path every run
# now takes, through module_introspect's `build`.  This presses all of them,
# with each field left at its default, and asks only that a command comes back.

# `build` is meant to be side-effect free - it reports the command a button
# would fire without firing it - and it is, for every module that goes through
# subprocess, because module_introspect stubs that out.  A module whose button
# does the work in Python itself is a different matter: pressing it really does
# the work, which is exactly how it is meant to behave in the web UI, and not
# something a checker should be doing.  web_download_page fetches a URL with
# urllib, so building it downloads a page - a live request, on a box that is
# meant to have no internet.  Press everything except these.
BUILD_SKIP = {"web_download_page"}

# A module's save-file box names a leaf under working/, and the house pattern
# is os.path.basename(entry.get().strip()) or "<default>".  Miss the basename
# and `WORKING_DIR / name` does what pathlib is documented to do: an absolute
# name discards the working dir completely, a "../" one climbs out of it.  The
# report then lands somewhere the notes tab and the Runs panel do not look -
# and the run itself succeeds, so nothing says so.  Fourteen modules had it.
# Type an absolute path into every save-file box and see where the output goes.
_OUTPUT_FIELD = re.compile(r"save-?file|output file|output name|file name", re.I)
_ESCAPE = "/etc/skeleton_check_escape"


def _field_values(data, override):
    """The module's own defaults, with `override` in every save-file box."""
    values = []
    for field in data.get("fields", []):
        kind = field.get("kind")
        if kind == "check":
            values.append(field.get("off", "0"))
        elif _OUTPUT_FIELD.search(field.get("label") or ""):
            values.append(override)
        else:
            values.append(field.get("default") or "")
    return values


def _build_one(stem):
    out = []
    if stem in BUILD_SKIP:
        return out
    try:
        proc = subprocess.run(
            ["xvfb-run", "-a", "python3", str(TOOLS_DIR / "module_introspect.py"),
             "describe", stem],
            capture_output=True, text=True, timeout=120)
        data = json.loads(proc.stdout)
    except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
        return ["{}: describe failed before build: {}".format(stem, exc)]
    for button in data.get("buttons", []):
        payload = json.dumps({"button": button.get("index", 0), "fields": []})
        fd, path = tempfile.mkstemp(suffix=".json")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(payload)
            proc = subprocess.run(
                ["xvfb-run", "-a", "python3",
                 str(TOOLS_DIR / "module_introspect.py"), "build", stem, path],
                capture_output=True, text=True, timeout=120)
        except (OSError, subprocess.TimeoutExpired) as exc:
            out.append("{}: build '{}' failed to run: {}".format(
                stem, button.get("text", "?"), exc))
            continue
        finally:
            try:
                os.unlink(path)
            except OSError:
                pass
        label = button.get("text", "?")
        if proc.returncode != 0:
            tail = (proc.stderr.strip().splitlines() or ["?"])[-1]
            out.append("{}: build '{}' exited {}: {}".format(
                stem, label, proc.returncode, tail[:120]))
            continue
        try:
            json.loads(proc.stdout)
        except ValueError:
            out.append("{}: build '{}' did not return JSON".format(stem, label))
    out.extend(_escape_one(stem, data))
    return out


def _escape_one(stem, data):
    """Where does a button's output go when the save-file box holds a path?"""
    values = _field_values(data, _ESCAPE)
    if _ESCAPE not in values:
        return []                                  # no save-file box to abuse
    out = []
    for button in data.get("buttons", []):
        payload = json.dumps({"button": button.get("index", 0), "fields": values})
        fd, path = tempfile.mkstemp(suffix=".json")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(payload)
            proc = subprocess.run(
                ["xvfb-run", "-a", "python3",
                 str(TOOLS_DIR / "module_introspect.py"), "build", stem, path],
                capture_output=True, text=True, timeout=120)
            built = json.loads(proc.stdout).get("command") or ""
        except (OSError, ValueError, subprocess.TimeoutExpired):
            continue                               # the pass above reports it
        finally:
            try:
                os.unlink(path)
            except OSError:
                pass
        if _ESCAPE in built:
            out.append("{}: '{}' writes its output outside working/ when the "
                       "save-file box holds a path (basename it): {}".format(
                           stem, button.get("text", "?"), built[:90]))
    return out


def check_build(paths):
    bad = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        for result in pool.map(_build_one, [p.stem for p in paths]):
            bad.extend(result)
    return bad


# --- scripts ----------------------------------------------------------------
#
# The web edition keeps its pages - HTML, CSS and a few hundred lines of
# JavaScript each - inside SKELETON_WEB.py as Python strings.  Byte-compiling
# that file proves the *Python* is well formed and nothing more: a syntax error
# in the JavaScript compiles perfectly and then breaks the console in the
# browser, silently, because a page whose script fails to parse simply does
# nothing.  Render the real pages and let node parse what they serve.

_SCRIPT_RE = re.compile(r"<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>", re.S)
# The /web assets a rendered page pulls in: <script src> and <link href>.
_ASSET_RE = re.compile(r"""(?:src|href)=["'](/web/[^"'?#]+)""")

# Third-party bundles served as they were downloaded.  Ours are every other
# .js under web/.
_VENDORED_JS = {"xterm.js", "xterm-addon-fit.js"}


def check_scripts(_paths):
    """The JavaScript the web edition serves parses, and every file a page
    asks for is actually there.

    Both matter and neither is loud.  A script that fails to parse leaves the
    page doing nothing at all - no error the operator sees - and a <script src>
    pointing at a file that is not there is quieter still: the browser 404s it
    and carries on rendering a console whose buttons do nothing.  The pages
    used to carry their JavaScript inline, so rendering them and parsing what
    came back covered the first of those; now that it lives in web/*.js, both
    have to be checked directly.
    """
    # Both are optional: the gate itself stays stdlib-only, and a box with no
    # node or no flask simply does not run this one.
    if not shutil.which("node"):
        return []
    if importlib.util.find_spec("flask") is None:
        return []
    root = IMPORTS_DIR.parent
    web = root / "web"
    bad = []

    # 1. everything under web/ that is ours parses.  Includes the SharedWorker
    #    that multiplexes the terminal streams, which is the one script no page
    #    would report broken: a worker that fails to parse just never starts.
    ours = sorted(p for p in web.glob("*.js") if p.name not in _VENDORED_JS)
    if not ours:
        return ["web/ has no JavaScript in it - the pages serve none"]
    for path in ours:
        why = _node_check(path.read_text(encoding="utf-8"))
        if why is not None:
            bad.append("web/{} does not parse: {}".format(path.name, why))

    sys.path.insert(0, str(root))
    try:
        import SKELETON_WEB          # noqa: E402
    except Exception as exc:         # flask is there, so this is a real break
        return bad + ["cannot import SKELETON_WEB to render its pages: {}".format(exc)]
    client = SKELETON_WEB.app.test_client()
    for url, name in (("/", "launcher"), ("/terminal", "terminal"),
                      ("/module/enum_nmap", "module page")):
        try:
            html = client.get(url).get_data(as_text=True)
        except Exception as exc:
            bad.append("{}: could not render {}: {}".format(name, url, exc))
            continue
        # 2. every /web asset it asks for exists.
        wanted = _ASSET_RE.findall(html)
        if not wanted:
            bad.append("{}: {} pulls in no /web asset at all".format(name, url))
        for ref in wanted:
            if not (root / ref.lstrip("/")).is_file():
                bad.append("{}: {} asks for {}, which is not there".format(
                    name, url, ref))
        # 3. an inline block, if a page still has one, parses too.
        for i, script in enumerate(_SCRIPT_RE.findall(html)):
            why = _node_check(script)
            if why is not None:
                bad.append("{}: inline script {} does not parse: {}".format(
                    name, i, why))
    return bad


def _node_check(script):
    """None if node parses this source, else the first line that says why."""
    fd, path = tempfile.mkstemp(suffix=".mjs")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(script)
        proc = subprocess.run(["node", "--check", path],
                              capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return "node --check failed to run: {}".format(exc)
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass
    if proc.returncode == 0:
        return None
    detail = [l for l in proc.stderr.strip().splitlines()
              if "SyntaxError" in l or l.strip().startswith("^")]
    return (detail or proc.stderr.strip().splitlines())[0][:120]


CHECKS = [
    ("compile", check_compile, False),
    ("names", check_names, False),
    ("quoting", check_quoting, False),
    ("shadowed", check_shadowed, False),
    ("paths", check_paths, False),
    ("relocate", check_relocate, False),
    ("glossary", check_glossary, False),
    ("stages", check_stages, False),
    ("scripts", check_scripts, False),
    ("describe", check_describe, True),      # slow: opt in with --describe
    ("build", check_build, True),            # slow: opt in with --describe
]


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--describe", action="store_true",
                    help="also run the slow head-less describe pass")
    ap.add_argument("--only", metavar="NAME",
                    help="run just one check ({})".format(
                        ", ".join(n for n, _, _ in CHECKS)))
    args = ap.parse_args()

    paths = modules()
    print("SKELETON self-check - {} modules\n".format(len(paths)))

    failed = 0
    for name, fn, slow in CHECKS:
        if args.only and name != args.only:
            continue
        if slow and not (args.describe or args.only == name):
            print("  {:<9} skipped (use --describe)".format(name))
            continue
        problems = fn(paths)
        if problems:
            failed += 1
            print("  {:<9} FAIL ({})".format(name, len(problems)))
            for line in problems[:40]:
                print("      " + line)
            if len(problems) > 40:
                print("      ... and {} more".format(len(problems) - 40))
        else:
            print("  {:<9} ok".format(name))

    print()
    if failed:
        print("{} check(s) failed".format(failed))
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
