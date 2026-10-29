#!/usr/bin/env python3
"""The tester's X session, and putting a browser window on it.

Two jobs that are really one: work out which desktop a window of ours should
open on, then open the console there at the size the tester already works at.
Under `sudo` - which port 80 needs - DISPLAY, XAUTHORITY and the session bus
are all stripped, and a browser started without them either uses root's profile
or refuses to start, so most of this is putting them back.
"""
import glob
import os
import re
import shutil
import socket
import subprocess
import time

# The chromium family places its own window from the command line; firefox and
# xdg-open take no geometry, so those get moved with xdotool afterwards.
BROWSERS = ("chromium", "chromium-browser", "google-chrome", "google-chrome-stable",
            "brave-browser", "firefox", "firefox-esr", "xdg-open")


class Desktop:
    """Where a window of ours goes, and how it gets there.

    On start-up the server opens its own console down the left of the screen,
    at the size of the browser window already running (half the desktop when
    there is none), which leaves the rest for the terminal it was started from.
    """

    def __init__(self):
        self.display, self.xauthority = self._real_x_env()

    @staticmethod
    def _real_x_env():
        """(DISPLAY, XAUTHORITY) of the desktop a module's window should open on.

        Trivial when the server runs in a normal session; under `sudo` (needed for
        port 80) both are stripped, so fall back to the invoking user's :0 session
        and their ~/.Xauthority cookie."""
        display = os.environ.get("DISPLAY")
        xauth = os.environ.get("XAUTHORITY")
        sudo_user = os.environ.get("SUDO_USER")
        if sudo_user:
            home = os.path.expanduser("~" + sudo_user)
            if home.startswith("~"):
                home = None
            uid = os.environ.get("SUDO_UID")
            if not display:
                display = ":0"
            if not xauth:
                cands = []
                if home:
                    cands.append(os.path.join(home, ".Xauthority"))
                if uid:
                    run = "/run/user/" + uid
                    cands.append(os.path.join(run, "gdm", "Xauthority"))
                    cands += sorted(glob.glob(os.path.join(run, ".mutter-Xwaylandauth.*")))
                    cands += sorted(glob.glob(os.path.join(run, "xauth_*")))
                for cand in cands:
                    if os.path.exists(cand):
                        xauth = cand
                        break
        return display, xauth


    def command(self, argv, extra_env=None):
        """(argv, env) that runs argv on the tester's desktop rather than on ours.

        Under `sudo` (needed for port 80) the browser must not stay root: it would
        use root's profile, and the chromium family refuses to start at all - so
        hand it back to SUDO_USER, with the desktop's DISPLAY/XAUTHORITY."""
        env = os.environ.copy()
        if self.display:
            env["DISPLAY"] = self.display
        if self.xauthority:
            env["XAUTHORITY"] = self.xauthority
        env.update(extra_env or {})
        sudo_user = os.environ.get("SUDO_USER")
        if sudo_user and os.geteuid() == 0 and shutil.which("sudo"):
            uid = os.environ.get("SUDO_UID")
            if uid and os.path.exists("/run/user/{}/bus".format(uid)):
                # sudo strips the session bus too, and a browser without it cannot
                # reach the copy of itself the tester already has open: it finds
                # the profile locked and puts up "Close Firefox" instead of a
                # window.  Point it back at the invoking user's session.
                env["XDG_RUNTIME_DIR"] = "/run/user/" + uid
                env["DBUS_SESSION_BUS_ADDRESS"] = "unix:path=/run/user/{}/bus".format(uid)
            keys = ["DISPLAY", "XAUTHORITY", "XDG_RUNTIME_DIR",
                    "DBUS_SESSION_BUS_ADDRESS"] + sorted(extra_env or {})
            passthrough = ["{}={}".format(k, env[k]) for k in keys if k in env]
            argv = ["sudo", "-H", "-u", sudo_user, "env"] + passthrough + list(argv)
        return list(argv), env


    def run(self, argv, timeout=10):
        """Run one short desktop command, return its stdout ('' if it did not run)."""
        cmd, env = self.command(argv)
        try:
            proc = subprocess.run(cmd, env=env, capture_output=True, text=True,
                                  timeout=timeout)
        except (OSError, subprocess.SubprocessError):
            return ""
        return proc.stdout


    def work_area(self):
        """(x, y, width, height) of the desktop minus its panels, best effort.

        _NET_WORKAREA is what the window manager itself reserves, so the console
        starts below a top bar instead of under it; the screen size is the fallback
        when nothing publishes one, and 1920x1080 when X answers nothing at all."""
        found = re.search(r"=\s*(\d+),\s*(\d+),\s*(\d+),\s*(\d+)",
                          self.run(["xprop", "-root", "_NET_WORKAREA"]))
        if found:
            return tuple(int(n) for n in found.groups())
        found = re.search(r"dimensions:\s+(\d+)x(\d+)", self.run(["xdpyinfo"]))
        if not found:
            found = re.search(r"current\s+(\d+)\s+x\s+(\d+)", self.run(["xrandr"]))
        if found:
            return (0, 0, int(found.group(1)), int(found.group(2)))
        return (0, 0, 1920, 1080)


    def frame_extents(self, window):
        """(left, right, top, bottom) invisible margin around a window, or zeroes.

        GTK apps draw their own shadow inside the window they ask X for, so a
        window sized 960 wide only shows 888 of it - every geometry we read or set
        has to add or take that margin back off, or the console lands short of the
        edge it was aimed at."""
        found = re.search(r"=\s*(\d+),\s*(\d+),\s*(\d+),\s*(\d+)",
                          self.run(["xprop", "-id", window, "_GTK_FRAME_EXTENTS"]))
        return tuple(int(n) for n in found.groups()) if found else (0, 0, 0, 0)


    def browser_size(self):
        """(width, height) of a browser window already open on the desktop, or None.

        The console is sized to match it, so it comes up at whatever size the
        tester already works at rather than at some size of our own; matched by
        class, so any firefox/chromium window counts, and the biggest one wins
        (pop-ups and pickers are windows of that class too)."""
        if not shutil.which("xdotool"):
            return None
        ids = self.run(["xdotool", "search", "--onlyvisible", "--class",
                            "(firefox|chrom|brave)"]).split()
        best = None
        for window in ids:
            found = re.search(r"WIDTH=(\d+)\s+HEIGHT=(\d+)",
                              self.run(["xdotool", "getwindowgeometry", "--shell", window]))
            if not found:
                continue
            left, right, top, bottom = self.frame_extents(window)
            size = (int(found.group(1)) - left - right,
                    int(found.group(2)) - top - bottom)
            if min(size) < 200:          # a menu or a picker, not a browser window
                continue
            if best is None or size[0] * size[1] > best[0] * best[1]:
                best = size
        return best


    def _place(self, box, deadline):
        """Move the console window so that box is what it covers, once it has mapped.

        For the browsers that cannot be told where to open.  The window is the one
        the console page titles itself, so it is found by name - and it only shows
        up here at all when it is an X window (see _open_console).  box is what the
        tester sees, so the window's own shadow goes back on before it is set."""
        x, y, width, height = box
        while time.time() < deadline:
            ids = self.run(["xdotool", "search", "--onlyvisible", "--name",
                                "^SKELETON"]).split()
            if ids:
                window = ids[-1]
                left, right, top, bottom = self.frame_extents(window)
                self.run(["xdotool", "windowsize", window,
                              str(width + left + right), str(height + top + bottom)])
                self.run(["xdotool", "windowmove", window,
                              str(x - left), str(y - top)])
                return True
            time.sleep(0.3)
        return False


    def open_console(self, url):
        """Open url on the left of the screen, browser-sized; say why when we cannot."""
        x, y, width, height = self.work_area()
        # Same size as the browser already running; half the desktop when there is
        # none to copy, which is also what the first console of the day gets.
        size = self.browser_size() or (max(640, width // 2), height)
        box = (x, y, size[0], size[1])
        browser = next((b for b in BROWSERS if shutil.which(b)), None)
        if not browser:
            print("no browser found - open {} yourself".format(url))
            return
        chromium_like = "chrom" in browser or "brave" in browser
        env = {}
        if chromium_like:
            # Chromium places itself, on X and on wayland alike.
            argv = [browser, "--new-window", "--window-position={},{}".format(x, y),
                    "--window-size={},{}".format(box[2], box[3]), url]
        else:
            argv = [browser, url] if browser == "xdg-open" else [browser, "--new-window", url]
            if shutil.which("xdotool"):
                # Nothing can place a wayland window from outside the compositor,
                # so the console opens on X (XWayland under a wayland session) and
                # xdotool moves it there.  An already-running browser ignores this
                # and answers on whichever backend it started with - then the
                # window simply lands wherever the window manager wants it.
                env = {"GDK_BACKEND": "x11", "MOZ_ENABLE_WAYLAND": "0"}
        cmd, environ = self.command(argv, env)
        try:
            subprocess.Popen(cmd, env=environ, stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL, start_new_session=True)
        except OSError as exc:
            print("could not start {}: {} - open {} yourself".format(browser, exc, url))
            return
        # 20s is a cold browser start on a loaded box; whatever has not appeared as
        # an X window by then is one we cannot place, which is not worth a fuss.
        if not chromium_like and env and not self._place(box, time.time() + 20):
            print("opened {} - could not place or size its window".format(url))


    def open_when_up(self, host, port):
        """Wait for our own socket to answer, then open the console beside us."""
        host = "127.0.0.1" if host in ("0.0.0.0", "::", "") else host
        url = "http://{}{}/".format(host, "" if port == 80 else ":{}".format(port))
        deadline = time.time() + 20
        while time.time() < deadline:
            try:
                with socket.create_connection((host, port), 0.5):
                    break
            except OSError:
                time.sleep(0.2)
        else:
            print("the server did not come up in 20s - not opening a browser")
            return
        self.open_console(url)
