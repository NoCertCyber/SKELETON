"""The button bar's three system actions: Find my IP, Change my IP, OPEN PORT.

Each runs its command directly rather than through a terminal, because each is
one short argv whose whole output belongs in the notes pane.
"""
import shlex
import subprocess

from flask import Blueprint, jsonify, request

import skeleton_core as core


def blueprint(svc):
    bp = Blueprint("system", __name__)

    @bp.post("/api/find-ip")
    def api_find_ip():
        """my_IP_Click(): ifconfig -> notes pane, field 5 as the guessed IP."""
        ip, content, err = core.find_ip()
        if err and not content:
            return jsonify(ok=False, log="\n{}\n".format(err)), 500
        if err:
            content += "\n" + err + "\n"
        return jsonify(
            ok=True,
            ip=ip,
            log=core.stamp(" - current Ethernet interfaces:") + "\n" + content,
        )

    @bp.post("/api/change-ip")
    def api_change_ip():
        """my_IP_Click_Change(): ifconfig <iface> <ip>.  Runs it directly."""
        ip = (request.json or {}).get("ip", "").strip()
        if not core.valid_ip(ip):
            return jsonify(ok=False, log="\nChange my IP: '{}' is not an "
                                         "address\n".format(ip)), 400
        # The session's wired NIC, not a hard-coded eth0 - the same UI sets it
        # two groups along, and ignoring it silently reconfigured the wrong
        # interface.
        iface = (core.load_session().get("iface") or "eth0").strip() or "eth0"
        cmd = core.change_ip_argv(ip, iface)
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True)
        except OSError as exc:
            return jsonify(ok=False, log="\nChange my IP failed: {}\n".format(exc)), 500
        tail = (proc.stdout + proc.stderr).strip()
        log = "\nMy IP set to {}  ({})\n".format(ip, shlex.join(cmd))
        if tail:
            log += tail + "\n"
        return jsonify(ok=True, log=log)

    @bp.post("/api/open-port")
    def api_open_port():
        """OPEN_Click(): iptables -I INPUT -p tcp --dport <port> -j ACCEPT."""
        port = (request.json or {}).get("port", "").strip()
        if not core.valid_port(port):
            return jsonify(
                ok=False,
                log="\nOPEN PORT: '{}' is not a valid TCP port number\n".format(port),
            ), 400
        cmd = core.open_port_argv(port)
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True)
        except OSError as exc:
            return jsonify(ok=False, log="\nOPEN PORT failed: {}\n".format(exc)), 500
        tail = (proc.stdout + proc.stderr).strip()
        log = "\nOpening port: {}  ({})\n".format(port, shlex.join(cmd))
        if tail:
            log += tail + "\n"
        return jsonify(ok=True, log=log)

    return bp
