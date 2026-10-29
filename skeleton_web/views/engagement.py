"""The engagement: the active target, the targets seen so far, the credentials.

The session carries the one *active* target - the value every module pre-fills
from.  An engagement is rarely one host, though, so the launcher also keeps the
list of targets seen so far and the pairs gathered on the box, and switches the
active one between them.
"""
from flask import Blueprint, jsonify, request

import skeleton_core as core


def blueprint(svc):
    bp = Blueprint("engagement", __name__)

    @bp.get("/api/session")
    def api_session_get():
        """The engagement target shared by every module and both front-ends."""
        return jsonify(ok=True, session=core.load_session())

    @bp.post("/api/session")
    def api_session_set():
        session = core.save_session(request.json or {})
        # Setting a target is also how one joins the list, so the tester types
        # a host once and can come back to it from the picker afterwards.
        targets = core.add_target(session.get("target", ""))
        filled = {k: v for k, v in session.items() if v}
        return jsonify(ok=True, session=session, targets=targets,
                       log=core.stamp(" - engagement target set: " + (
                           ", ".join("{}={}".format(k, v)
                                     for k, v in sorted(filled.items()))
                           or "(cleared)")))

    @bp.get("/api/targets")
    def api_targets_get():
        """Every target this engagement has been pointed at.  The session holds
        the active one; this is the list the launcher's picker switches
        between."""
        return jsonify(ok=True, targets=core.load_targets())

    @bp.post("/api/targets")
    def api_targets_add():
        target = ((request.json or {}).get("target") or "").strip()
        if not target:
            return jsonify(ok=False, error="need a target"), 400
        return jsonify(ok=True, targets=core.add_target(target),
                       log=core.stamp(" - target saved: " + target))

    @bp.post("/api/targets/delete")
    def api_targets_delete():
        target = ((request.json or {}).get("target") or "").strip()
        return jsonify(ok=True, targets=core.remove_target(target))

    @bp.get("/api/creds")
    def api_creds_get():
        """The saved user / password pairs behind the launcher's creds manager."""
        return jsonify(ok=True, creds=core.load_creds())

    @bp.post("/api/creds")
    def api_creds_add():
        body = request.json or {}
        user = (body.get("user") or "").strip()
        pw = (body.get("pass") or "").strip()
        if not (user or pw):
            return jsonify(ok=False, error="need a user name or a password"), 400
        creds = core.add_cred(user, pw)
        return jsonify(ok=True, creds=creds, log=core.stamp(
            " - credential saved: {} / {}".format(
                user or "(no user)", pw or "(no pass)")))

    @bp.post("/api/creds/delete")
    def api_creds_delete():
        body = request.json or {}
        creds = core.remove_cred(body.get("user") or "", body.get("pass") or "")
        return jsonify(ok=True, creds=creds)

    return bp
