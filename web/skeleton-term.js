// SKELETON - the terminal client, shared by /terminal and every module page.
//
// Both pages put the same shell on screen: xterm.js in front, one pty-backed
// login shell on the server behind, and a SharedWorker between them holding
// the single EventSource this browser is allowed to spend on the job.  All of
// that used to be written out twice, ~230 lines each and byte-identical in the
// parts that mattered, so a fix to one was a fix to one.  It is a class now,
// and the two pages differ only in what they pass it.
//
//   const T = new SkeletonTerm({sidKey: "skelTermSid", mount: "term", ...});
//   T.open(); T.start();
//
// The sid is the whole trick: it lives in sessionStorage, so reloading the
// page reattaches to the shell you were working in rather than starting a new
// one - which is what makes a reload during an hour-long scan cost nothing.

const SKEL_TAB_KEY = "skeletonNotesTab";     // which notes tab, per browser
const SKEL_REC_KEY = "skeletonTermRecord";   // is the transcript being kept

const SKEL_THEME = {
  background: "#05090d", foreground: "#e6e0d2", cursor: "#e0a458",
  cursorAccent: "#05090d", selectionBackground: "#22303c",
  black: "#0f1720", red: "#d9564f", green: "#5fbfa8", yellow: "#e0a458",
  blue: "#6f9fd8", magenta: "#b08cc7", cyan: "#63b6bd", white: "#e6e0d2",
  brightBlack: "#66787f", brightRed: "#e8756e", brightGreen: "#7fd6c1",
  brightYellow: "#f0bd7a", brightBlue: "#8fb8e6", brightMagenta: "#c7a6d9",
  brightCyan: "#84cdd3", brightWhite: "#f5f1e6",
};

// One shared worker link per page, whichever terminal asked for it first.
let SKEL_PORT = null;

class SkeletonTerm {
  /* opts:
       sidKey    sessionStorage key for this page's shell id (required)
       mount     id of the element xterm.js draws into
       observe   id of the element whose size decides the terminal's (default: mount)
       tabSelect id of the <select> naming the notes tab
       record    id of the "record" checkbox
       dim       the escape sequence this page writes its own notices in
       onExit    () -> void, after the shell has gone
       onState   (up) -> void, is the stream connected?
       onConnect () -> void, after (re)attaching to the shell
       onFit     () -> void, page-specific sizing, called before every fit  */
  constructor(opts) {
    this.opts = opts;
    this.dim = opts.dim || "\x1b[90m";
    this.exited = false;
    this.stream = null;
    this.term = null;
    this.fitAddon = null;
    this.sid = SkeletonTerm.makeSid(opts.sidKey);
  }

  // --- helpers the pages use too -------------------------------------------
  static post(url, obj) {
    return fetch(url, {method: "POST", headers: {"Content-Type": "application/json"},
                       body: JSON.stringify(obj)}).catch(() => {});
  }

  static b64bytes(s) {
    const bin = atob(s), u = new Uint8Array(bin.length);
    for (let i = 0; i < bin.length; i++) u[i] = bin.charCodeAt(i);
    return u;
  }

  // one server-side shell per browser terminal tab; survives a reload
  static makeSid(key) {
    try {
      let s = sessionStorage.getItem(key);
      if (!s) {
        s = (crypto.randomUUID && crypto.randomUUID()) ||
            (Date.now() + "-" + Math.random().toString(36).slice(2));
        sessionStorage.setItem(key, s);
      }
      return s;
    } catch (e) { return "s" + Math.random().toString(36).slice(2); }
  }

  // Fill a <select> with the launcher's notes tabs and remember the choice.
  static async loadTabs(sel, onChange) {
    let tabs = [{id: "main", name: "Notes"}];
    try {
      const r = await (await fetch("/api/tabs")).json();
      if (r.tabs && r.tabs.length) tabs = r.tabs;
    } catch (e) {}
    sel.innerHTML = "";
    for (const t of tabs) {
      const o = document.createElement("option");
      o.value = t.id; o.textContent = t.name;
      sel.appendChild(o);
    }
    let saved = "";
    try { saved = localStorage.getItem(SKEL_TAB_KEY) || ""; } catch (e) {}
    if (saved && tabs.some((t) => t.id === saved)) sel.value = saved;
    sel.onchange = () => {
      try { localStorage.setItem(SKEL_TAB_KEY, sel.value); } catch (e) {}
      if (onChange) onChange();
    };
  }

  // --- the page's own bits, by id ------------------------------------------
  el(which) { return document.getElementById(this.opts[which]); }
  get tabValue() { const s = this.el("tabSelect"); return (s && s.value) || "main"; }
  get recording() { const c = this.el("record"); return !c || c.checked; }

  // --- the terminal ---------------------------------------------------------
  open() {
    this.term = new Terminal({
      fontFamily: '"Fira Code", ui-monospace, SFMono-Regular, Menlo, Consolas, monospace',
      fontSize: 13, cursorBlink: true, scrollback: 20000, theme: SKEL_THEME,
    });
    this.fitAddon = new FitAddon.FitAddon();
    this.term.loadAddon(this.fitAddon);
    this.term.open(document.getElementById(this.opts.mount));
    this.fit();

    this.term.onData((d) => SkeletonTerm.post("/api/terminal/input",
                                              {sid: this.sid, data: d}));
    this.term.onResize(() => SkeletonTerm.post(
      "/api/terminal/resize", {sid: this.sid, rows: this.term.rows, cols: this.term.cols}));
    const box = document.getElementById(this.opts.observe || this.opts.mount);
    new ResizeObserver(() => this.sendSize()).observe(box);
    window.addEventListener("resize", () => this.sendSize());

    // once the shell has exited, Enter starts a fresh one
    this.term.attachCustomKeyEventHandler((e) => {
      if (this.exited && e.type === "keydown" && e.key === "Enter") {
        this.restart();
        return false;
      }
      return true;
    });

    // The record checkbox is remembered across pages: a tester who turns the
    // transcript off does not want it back on in the next module tab.
    const rec = this.el("record");
    if (rec) {
      try { rec.checked = localStorage.getItem(SKEL_REC_KEY) !== "0"; }
      catch (e) { rec.checked = true; }
      rec.onchange = () => {
        try { localStorage.setItem(SKEL_REC_KEY, rec.checked ? "1" : "0"); } catch (e) {}
        this.pushConfig();
      };
    }
    return this;
  }

  /** Load the tab list, then attach to the shell.

    `focus` only where the terminal is the page - a module page wants the
    caret in its first input box, not down in the shell. */
  async start(focus) {
    const sel = this.el("tabSelect");
    if (sel) await SkeletonTerm.loadTabs(sel, () => this.pushConfig());
    this.connect();
    if (focus) this.focus();
  }

  // our own notices: a terminal wants CRLF, and text from the server may not
  say(text, colour) {
    this.term.write((colour || "") + String(text).replace(/\r?\n/g, "\r\n") +
                    (colour ? "\x1b[0m" : ""));
  }

  write(data) { this.term.write(data); }
  focus() { this.term.focus(); }
  clear() { this.term.clear(); this.focus(); }
  interrupt() {
    SkeletonTerm.post("/api/terminal/input", {sid: this.sid, data: "\x03"});
    this.focus();
  }

  fit() {
    try {
      if (this.opts.onFit) this.opts.onFit();
      else this.fitAddon.fit();
    } catch (e) {}
  }

  sendSize() {
    this.fit();
    SkeletonTerm.post("/api/terminal/resize",
                      {sid: this.sid, rows: this.term.rows, cols: this.term.cols});
  }

  /** Tell the server which notes tab this shell records to, and whether. */
  pushConfig() {
    SkeletonTerm.post("/api/terminal/config",
                      {sid: this.sid, tab: this.tabValue, record: this.recording});
  }

  connect() {
    if (this.stream) this.stream.close();
    this.exited = false;
    this.stream = this._stream();
    if (this.opts.onConnect) this.opts.onConnect();
    setTimeout(() => this.sendSize(), 150);
  }

  async restart() {
    await SkeletonTerm.post("/api/terminal/kill", {sid: this.sid});
    this.term.reset();
    this.connect();
    this.focus();
  }

  // The log is a download, not a page: fetching it lets a shell that is no
  // longer there (killed, or reaped after an idle hour) say so in the terminal
  // instead of the click doing nothing at all.
  async saveLog(name) {
    try {
      const r = await fetch("/api/terminal/log?sid=" + encodeURIComponent(this.sid) +
                            "&name=" + encodeURIComponent(name));
      if (!r.ok) {
        this.say("\nnothing to download - this shell is gone; restart it\n", this.dim);
        return;
      }
      const blob = await r.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = (r.headers.get("Content-Disposition") || "").match(/filename="([^"]+)"/)?.[1]
                   || name + ".txt";
      document.body.appendChild(a);
      a.click();
      a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 10000);
    } catch (e) {
      this.say("\ncould not download the log: " + e + "\n", this.dim);
    }
  }

  // --- one connection for every terminal in this browser --------------------
  // A page does not open a stream of its own.  A SharedWorker
  // (web/skeleton-stream.js) keeps one for every SKELETON page in the browser
  // and posts this page only the frames tagged with its sid, because six
  // HTTP/1.1 connections per origin is all a browser will give and each module
  // tab used to spend one of them for good.  A browser with no SharedWorker
  // falls back to a stream of its own - which is the old behaviour, ceiling
  // included, so it is the fallback and not the plan.
  _stream() {
    const self = this;
    const onState = this.opts.onState || function () {};
    const onData = (b64) => self.term.write(SkeletonTerm.b64bytes(b64));
    const onExit = () => {
      self.exited = true;
      self.say("\n[shell exited - press Enter, or 'restart shell']\n", self.dim);
      if (self.opts.onExit) self.opts.onExit();
      self.stream.close();
    };
    let es = null, keep = null, shut = false;

    function send(op) {
      if (!SKEL_PORT) return;
      try {
        SKEL_PORT.postMessage({op: op, sid: self.sid,
                               tab: self.tabValue, record: self.recording});
      } catch (e) {}
    }

    function direct() {
      es = new EventSource("/api/terminal/stream?sid=" + encodeURIComponent(self.sid) +
                           "&tab=" + encodeURIComponent(self.tabValue) +
                           "&record=" + (self.recording ? "1" : "0"));
      es.onmessage = (ev) => { if (!shut) onData(ev.data); };
      es.addEventListener("exit", () => { if (!shut) onExit(); });
      es.onerror = () => {};     // EventSource reconnects unless we closed it
      onState(true);
    }

    function shared() {
      if (!SKEL_PORT) {
        SKEL_PORT = new SharedWorker("/web/skeleton-stream.js").port;
        SKEL_PORT.start();
        // A SharedWorker is never told that a port has closed, and a subscriber
        // left behind keeps its shell looking watched - a watched shell is
        // never reaped.  So say goodbye while there is still something to say
        // it with.
        window.addEventListener("pagehide", () => {
          try { SKEL_PORT.postMessage({op: "bye", sid: self.sid}); } catch (e) {}
        });
      }
      SKEL_PORT.onmessage = (ev) => {
        const m = ev.data || {};
        if (shut || m.sid !== self.sid) return;
        if (m.op === "data") onData(m.b64);
        else if (m.op === "exit") onExit();
        else if (m.op === "state") onState(!!m.up);
        else if (m.op === "resub") send("sub");
      };
      send("sub");
      // The worker drops a page that stops saying it is there; this is that.
      keep = setInterval(() => send("keep"), 25000);
    }

    try {
      if (window.SharedWorker) shared(); else direct();
    } catch (e) { direct(); }

    return {
      // Stop delivering, but stay subscribed: connect() is called again
      // straight after this on the restart path, and an unsubscribe racing
      // that re-subscribe would take the new shell off the stream.
      close() {
        shut = true;
        if (keep) { clearInterval(keep); keep = null; }
        if (es) { es.close(); es = null; }
      },
    };
  }
}
