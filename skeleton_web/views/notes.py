"""The notes pane's own actions: the tabs, and NEW / TIME / SAVE / LOAD / Insert."""
from flask import Blueprint, jsonify, request

from config import own
import skeleton_core as core

from ..settings import MAIN_TAB


def blueprint(svc):
    bp = Blueprint("notes", __name__)

    @bp.get("/api/tabs")
    def api_tabs():
        """The notes-tab list, for the dropdown on module / terminal pages."""
        return jsonify(tabs=svc.workspace.tabs())

    @bp.post("/api/tabs")
    def api_tabs_add():
        tab, tabs = svc.workspace.add_tab((request.json or {}).get("name"))
        return jsonify(ok=True, tab=tab, tabs=tabs)

    @bp.post("/api/tabs/<tab_id>")
    def api_tabs_edit(tab_id):
        """Rename ({name: ...}) or remove ({delete: true}) one tab."""
        body = request.json or {}
        if body.get("delete"):
            if tab_id == MAIN_TAB:
                return jsonify(ok=False, error="cannot delete the default tab"), 400
            done, tabs = svc.workspace.delete_tab(tab_id)
        else:
            done, tabs = svc.workspace.rename_tab(tab_id, body.get("name"))
        if done is None:
            return jsonify(ok=False, error="no such tab"), 404
        return jsonify(ok=True, tabs=tabs)

    @bp.get("/api/jobs")
    def api_jobs():
        """The runs recorded for this notes tab."""
        tab = svc.workspace.resolve(request.args.get("tab") or MAIN_TAB)
        return jsonify(ok=True, jobs=svc.runs.recent(tab))

    @bp.post("/api/jobs/clear")
    def api_jobs_clear():
        """NEW_Click's other half: throw this tab's run history away."""
        tab = svc.workspace.resolve((request.json or {}).get("tab") or MAIN_TAB)
        err = svc.runs.clear(tab)
        if err:
            return jsonify(
                ok=False,
                log="\nNEW: could not erase the run history: {}\n".format(err)), 500
        return jsonify(ok=True)

    @bp.post("/api/time")
    def api_time():
        return jsonify(log=core.stamp(""))

    @bp.post("/api/save")
    def api_save():
        data = request.json or {}
        # ".txt" to match LOAD and the Tk launcher - without it a saved job
        # could never be loaded back.
        path = core.safe_working_path(data.get("name", ""), ".txt")
        if path is None:
            return jsonify(ok=False, log="\nSAVE failed: bad file name\n"), 400
        # Drop a run-history block from an earlier save/load so it does not
        # stack up, then append the current one at the end of the file.
        text = data.get("text", "")
        cut = text.rfind("\n\n### RUN HISTORY ###\n")
        if cut != -1:
            text = text[:cut]
        elif text.startswith("### RUN HISTORY ###\n"):
            text = ""
        hist = svc.runs.history_text(data.get("tab") or MAIN_TAB)
        if hist:
            text = text.rstrip("\n") + "\n\n" + hist
        try:
            path.write_text(text, encoding="utf-8")
        except OSError as exc:
            return jsonify(ok=False, log="\nSAVE failed: {}\n".format(exc)), 500
        own(path)
        return jsonify(
            ok=True,
            log="\nMy job is saved in working directory: {}{}\n".format(
                path.name, " (run history appended)" if hist else ""),
        )

    @bp.get("/api/load")
    def api_load():
        """LOAD_Click(): <name>.txt replaces the notes pane."""
        path = core.safe_working_path(request.args.get("name", ""), ".txt")
        if path is None:
            return jsonify(ok=False, log="\nLOAD failed: bad file name\n"), 400
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            return jsonify(ok=False, log="\nLOAD failed: {}\n".format(exc)), 404
        return jsonify(ok=True, text=text)

    @bp.get("/api/insert")
    def api_insert():
        """Insert_File(): <name> from the working dir is appended to the pane."""
        path = core.safe_working_path(request.args.get("name", ""))
        if path is None:
            return jsonify(ok=False, log="\nInsert File failed: bad file name\n"), 400
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            return jsonify(ok=False, log="\nInsert File failed: {}\n".format(exc)), 404
        return jsonify(ok=True, text="\n" + text + "\n")

    return bp
