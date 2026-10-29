"""A module as a web page, and the two ways of pressing one of its buttons.

The normal path is /send: the command the button would fire is built without
running it, then *typed into the page's own shell*, where it can be answered,
interrupted and followed up on like anything else at a prompt.  There is no
separate process to follow, so the shell's own transcript machinery copies the
command and everything it prints to the notes tab, and RunLog adds the line
that makes it findable afterwards.

Actions that do not map to a plain command - opening a terminal, launching a
browser, starting a background server - fall through to the buffered /run path,
which already knows how to finish each of them.
"""
import os
import shlex

from flask import Blueprint, abort, jsonify, render_template, request

from config import SKELETON_ROOT, WORKING_DIR
import skeleton_core as core

from ..settings import MAIN_TAB


def _no_such(module):
    """404 for an unknown module, in JSON like every other reply here."""
    return jsonify(ok=False, error="no such module: {}".format(module)), 404


def _button_index(body):
    """The button a request names.  Anything unparseable is the first one -
    every other endpoint here answers in JSON, and an int() ValueError used to
    escape as a Werkzeug HTML 500 that the browser then failed to parse."""
    try:
        return max(0, int(body.get("button", 0)))
    except (TypeError, ValueError):
        return 0


def blueprint(svc):
    bp = Blueprint("modules", __name__)

    @bp.get("/module/<module>")
    def module_page(module):
        """The web version of an imports2/<module>.py Tk window."""
        if module not in core.MODULE_SET:
            abort(404)
        return render_template("module.html")

    @bp.get("/api/module/<module>")
    def api_module(module):
        """Describe a module: its cheatsheet, input fields and buttons."""
        if module not in core.MODULE_SET:
            return _no_such(module)
        data, err = svc.introspect.describe(module)
        if err:
            return jsonify(ok=False, error=err), 502
        data["ok"] = True
        return jsonify(data)

    @bp.post("/api/module/<module>/run")
    def api_module_run(module):
        """Fill the module's fields, invoke a button, run the command it builds."""
        if module not in core.MODULE_SET:
            return _no_such(module)
        if core.IS_DEMO and module not in core.DEMO_MODULES:
            return jsonify(ok=False, isPro=True, payhipUrl=core.PAYHIP_URL,
                           error="{} is part of the SKELETON Full Version ({})".format(module, core.PRICE_STR)), 403
        body = request.json or {}
        tab = body.get("tab") or MAIN_TAB
        payload = {
            "button": _button_index(body),
            "fields": body.get("fields", []),
            # module file output -> working/<tab>/
            "out_dir": svc.workspace.folder(svc.workspace.resolve(tab)),
        }
        data, err = svc.introspect.run(module, payload)
        if err:
            svc.workspace.append(
                core.stamp(" - {} module run FAILED".format(module))
                + err.rstrip() + "\n", tab)
            return jsonify(ok=False, error=err), 502

        # Post the finished run to the launcher's notes pane as one atomic
        # block: timestamp, the command that ran, then its output.
        block = core.stamp(" - {} module ran".format(module))
        if data.get("command"):
            block += "$ " + data["command"] + "\n"
        block += data.get("output", "")
        if not block.endswith("\n"):
            block += "\n"
        svc.workspace.append(block, tab)

        # Put it on the module page's terminal too, so this run is part of that
        # shell's transcript - the page's Download hands back the whole session,
        # not just the parts that went through a pty.
        sh = svc.terminals.get(body.get("sid") or "", tab, create=False)
        if sh is not None:
            echo = "\n"
            if data.get("command"):
                echo += "\x1b[38;5;79m$ \x1b[0m" + data["command"] + "\n"
            echo += ("\x1b[38;5;244m" + (data.get("output") or "").rstrip("\n")
                     + "\x1b[0m\n")
            sh.emit(echo)
            data["echoed"] = True

        data["ok"] = True
        return jsonify(data)

    @bp.post("/api/module/<module>/send")
    def api_module_send(module):
        """Build the command the chosen button would fire and type it into the
        module page's shell."""
        if module not in core.MODULE_SET:
            return _no_such(module)
        if core.IS_DEMO and module not in core.DEMO_MODULES:
            return jsonify(ok=False, isPro=True, payhipUrl=core.PAYHIP_URL,
                           error="{} is part of the SKELETON Full Version ({})".format(module, core.PRICE_STR)), 403
        body = request.json or {}
        tab = svc.workspace.resolve(body.get("tab") or MAIN_TAB)
        sid = body.get("sid") or ""
        if not sid:
            # Every reply here is JSON, and the page parses it as JSON: an
            # abort() escapes as a Werkzeug HTML page, which the fetch then
            # fails to read and reports as "could not reach the server".
            return jsonify(ok=False,
                           error="this page has no terminal yet - reload it"), 400
        payload = {
            "button": _button_index(body),
            "fields": body.get("fields", []),
            "out_dir": svc.workspace.folder(tab),
        }
        built, err = svc.introspect.build(module, payload)
        if err:
            svc.workspace.append(
                core.stamp(" - {} module run FAILED".format(module))
                + err.rstrip() + "\n", tab)
            return jsonify(ok=False, error=err), 502

        kind = built.get("kind")
        if kind != "plain":
            # terminal / browser / popen / none - the buffered path handles these.
            return jsonify(ok=True, sent=False, kind=kind,
                           fallback="/api/module/{}/run".format(module))

        # `record` matters only if this is what starts the shell - a /send that
        # beats the page's own subscribe.  Getting it wrong there wrote a
        # "terminal session" header into the notes of somebody who had turned
        # recording off.
        sh = svc.terminals.get(sid, tab, record=bool(body.get("record", True)))
        sh.tab = tab              # the module page's dropdown is the one to trust
        # An argv command has to be quoted back into a single line before a
        # shell can be asked to run it, or an argument with a space in it would
        # split.
        command = built.get("command_sh") or built.get("command", "")
        # A module that names a working directory of its own gets a cd in front
        # of its command.  The directories every module is given by default do
        # not: the shell already opened in this notes tab's folder, which is
        # where a relative output path should land, and where the operator's own
        # `cd` has the last word.
        where = built.get("cwd") or ""
        ran_in = sh.cwd_now() or sh.cwd
        routine = {os.path.realpath(str(SKELETON_ROOT)),
                   os.path.realpath(str(WORKING_DIR)),
                   os.path.realpath(svc.workspace.folder(tab))}
        if where and os.path.isdir(where) and os.path.realpath(where) not in routine \
                and os.path.realpath(where) != ran_in:
            command = "cd {} && {}".format(shlex.quote(where), command)
            ran_in = where
        # The run's output is this shell's output, so the shell carries the
        # module's name until the operator types something of their own into it
        # - that is what a "(cont.)" stamp says when a second terminal cuts into
        # a long scan.
        sh.note_label = "{} module run".format(module)
        sh.note_run = True
        if sh.record:
            svc.workspace.append(core.stamp(" - " + sh.note_label), sh.tab,
                                 sh.note_src)
        sh.write(command + "\n")   # the shell's own recorder logs it as "$ ..."
        svc.runs.record(module, command, ran_in, sh.tab)
        return jsonify(ok=True, sent=True, command=command)

    return bp
