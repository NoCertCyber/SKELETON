"""The console itself: the catalogue, the glossary, the notes poll."""
import json

from flask import Blueprint, jsonify, render_template, request

from config import reclaim_soon
import skeleton_core as core

from ..settings import MAIN_TAB, POLL_INTERVAL_MS


def blueprint(svc):
    bp = Blueprint("launcher", __name__)

    @bp.get("/")
    def index():
        return render_template("launcher.html")

    @bp.get("/api/catalog")
    def api_catalog():
        """Everything the browser needs to render the three columns once."""
        return jsonify(
            isDemo=core.IS_DEMO,
            payhipUrl=core.PAYHIP_URL,
            priceStr=core.PRICE_STR,
            stages=core.PENTEST_CHAIN,
            modules=[{"name": m, "desc": core.describe_module(m),
                      "isDemo": (m in core.DEMO_MODULES) if core.IS_DEMO else True}
                     for m in core.MODULE_NAMES],
            banner=core.BANNER,
            pollMs=POLL_INTERVAL_MS,
            tabs=svc.workspace.tabs(),
        )

    @bp.get("/api/glossary")
    def api_glossary():
        module = request.args.get("module", "")
        if module not in core.MODULE_SET:
            return jsonify(text="")
        return jsonify(text=core.glossary_block(module))

    @bp.get("/api/poll")
    def api_poll():
        """What each tab's channel has gained since the offsets the caller
        sends - mirrors the Tk launcher's load_file()."""
        try:
            since = json.loads(request.args.get("since") or "{}")
            if not isinstance(since, dict):
                since = {}
        except ValueError:
            since = {}

        # Whatever the tools have written into the work folder since the last
        # poll is still root's; this is the tick that gives it back (throttled,
        # so it is not a walk of working/ every second).
        reclaim_soon()

        chunks, offsets = svc.workspace.poll(since)
        # keep `chunk` for the built-in tab so an older page keeps working
        return jsonify(chunks=chunks, chunk=chunks.get(MAIN_TAB, ""), offsets=offsets)

    @bp.post("/api/run")
    def api_run():
        """RUN_Click(), web edition: open the module as its own page (a new tab)."""
        module = (request.json or {}).get("module", "")
        if module not in core.MODULE_SET:
            return jsonify(ok=False, log="\nRUN MODULE: select a module first\n"), 400
        if core.IS_DEMO and module not in core.DEMO_MODULES:
            return jsonify(
                ok=False,
                isPro=True,
                module=module,
                payhipUrl=core.PAYHIP_URL,
                priceStr=core.PRICE_STR,
                log=core.stamp(" - " + module + " is a PRO module (Demo mode)"),
            ), 403
        return jsonify(
            ok=True,
            url="/module/" + module,
            log=core.stamp(" - " + module + " module opened"),
        )

    return bp
