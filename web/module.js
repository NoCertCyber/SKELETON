(() => {
// SKELETON - a module rendered as a page.
//
// The cheatsheet, the input fields the module's Tk window would have shown,
// its buttons - and under them the shell those buttons type into.  The shell
// is SkeletonTerm (web/skeleton-term.js), shared with /terminal.

const $ = (id) => document.getElementById(id);
const MODULE = decodeURIComponent(location.pathname.split("/").pop());
let FIELDS = [];

// Colour the module cheatsheet like the launcher glossary: ###SECTION### heads
// green, trailing "# comments" dimmed, -x / --long / /win switches and
// `backticked spans` orange.
function iEsc(s) {
  return s.replace(/[&<>]/g, (c) => ({"&": "&amp;", "<": "&lt;", ">": "&gt;"}[c]));
}
function hlInfo(text) {
  return (text || "").split("\n").map((line) => {
    if (/^\s*#{2,}.*#{2,}\s*$/.test(line))
      return '<span class="i-head">' + iEsc(line) + "</span>";
    let code = line, tail = "";
    const m = line.match(/\s#.*$/);          // split off a trailing " # comment"
    if (m) { code = line.slice(0, m.index); tail = '<span class="i-cmt">' + iEsc(m[0]) + "</span>"; }
    let h = iEsc(code).replace(/`([^`]+)`/g, "<code>$1</code>");
    h = h.replace(/(^|[\s(\[])(-{1,2}[A-Za-z][\w-]*|\/[A-Za-z][\w-]*)(?=$|[\s)\].,;:=])/g,
                  "$1<code>$2</code>");
    return h + tail;
  }).join("\n");
}

/* A module's tick label is written the way its cheatsheet is - "-sV #version
   scan": a switch, then a gloss on it.  Splitting the two lets each be set in
   its own face (mono for the switch, the UI face for the gloss), which reads
   better AND is narrow enough to keep a whole frame of ticks on one line. */
function ckText(lab, text) {
  lab.title = text;
  const m = text.match(/\s*#.*$/);
  const code = (m ? text.slice(0, m.index) : text).trim();
  if (code) {
    const sw = document.createElement("span");
    sw.className = "sw"; sw.textContent = code;
    lab.appendChild(sw);
  }
  if (m) {
    const gl = document.createElement("span");
    gl.className = "gl"; gl.textContent = m[0].trim();
    lab.appendChild(gl);
  }
}

/* A module's window title reads "<category>_<name>  -  <tool> - <purpose>".
   The category prefix is dead weight on a page that is already that module,
   and when the name that is left just repeats the tool the whole first half
   is repetition - so drop it and let the tool name carry the blue instead. */
function headline(title, module) {
  const cut = (title || "").split(/\s+\u2014\s+/);           // split on the em dash
  const rest = cut.slice(1).join(" \u2014 ").trim();
  if (!rest) return iEsc(title || module);
  const name = cut[0].trim().replace(/^[^_]+_/, "");        // info_glossary -> glossary
  const tool = rest.split(/\s+-\s+/)[0];                    // "CyberChef", "dig AXFR ..."
  const bare = tool.replace(/\s*\(.*\)$/, "");              // "NetExec (nxc)" -> "NetExec"
  if (bare.toLowerCase() === name.toLowerCase())
    return '<span class="name">' + iEsc(tool) + "</span>" + iEsc(rest.slice(tool.length));
  return '<span class="name">' + iEsc(name) + "</span> \u2014 " + iEsc(rest);
}

async function load() {
  let r;
  try {
    r = await (await fetch("/api/module/" + encodeURIComponent(MODULE))).json();
  } catch (e) {
    // Unguarded, this left the page on "loading..." for good with nothing
    // said - the same silent dead end guard() was added to the console for.
    $("title").textContent = MODULE;
    T.say("\ncould not load this module: " + e + "\n", DIM);
    return;
  }
  if (!r.ok) {
    $("title").textContent = MODULE;
    T.say("\ndescribe failed: " + r.error + "\n", DIM);
    return;
  }
  document.title = r.module;
  $("title").innerHTML = headline(r.title || r.module, r.module);
  $("info").innerHTML = r.info ? hlInfo(r.info)
                              : '<span class="i-cmt">(no cheatsheet text)</span>';

  FIELDS = r.fields || [];
  // The engagement target set once in the launcher fills the fields it matches,
  // so a module opens ready to run instead of asking for the target again.
  let session = {};
  try { session = (await (await fetch("/api/session")).json()).session || {}; } catch (e) {}
  const box = $("fields");
  box.innerHTML = "";
  // A Tk frame holding nothing but ticks is a switch BANK - the module grouped
  // it that way and it keeps a line of its own.  Every other frame is just
  // where the module happened to break its grid, and on a page a row can hold
  // far more than a 950px Tk window could: consecutive ones flow into a single
  // wrapping row, so the Input panel costs the fewest lines it can.
  const bank = {}, ticks = {};
  FIELDS.forEach((f) => {
    if (bank[f.group] === undefined) { bank[f.group] = true; ticks[f.group] = 0; }
    if (f.kind !== "check") bank[f.group] = false; else ticks[f.group]++;
  });
  // one tick on its own is not a bank, it is a field - it joins the flow
  Object.keys(bank).forEach((g) => { if (ticks[g] < 2) bank[g] = false; });
  // A frame the module gave both a field AND one of its action buttons is its
  // ACTION row - the switches the run goes out with, the file it will write,
  // the button that fires it.  The module grouped those three as one thought,
  // so the row keeps a line of its own rather than letting the prompts above
  // spill into it and push the button off the end.
  const action = {};
  (r.buttons || []).forEach((b) => { if (b.group) action[b.group] = true; });
  let row = null, rowGroup = null, rowIsBank = null, rowIsAction = null;
  const rowFor = {};                       // Tk frame -> the row it became
  FIELDS.forEach((f, i) => {
    const isBank = bank[f.group];
    const isAction = !isBank && !!action[f.group];
    if (row === null || isBank !== rowIsBank || isAction !== rowIsAction ||
        ((isBank || isAction) && f.group !== rowGroup)) {   // bank / action row,
      row = document.createElement("div");                  // or the flow resuming
      row.className = isBank ? "frow ticks" : "frow";
      box.appendChild(row);
      rowIsBank = isBank;
      rowIsAction = isAction;
      rowGroup = f.group;
    }
    rowFor[f.group] = row;
    if (f.kind === "check") {
      const lab = document.createElement("label");
      lab.className = "ck";
      const inp = document.createElement("input");
      inp.type = "checkbox"; inp.id = "f" + i;
      inp.checked = !!f.checked;
      inp.dataset.on = f.on != null ? f.on : "";
      inp.dataset.off = f.off != null ? f.off : "";
      lab.appendChild(inp);
      ckText(lab, f.label || ("field " + (i + 1)));
      row.appendChild(lab);
      return;
    }
    const lab = document.createElement("label");
    lab.className = "fl";
    lab.textContent = f.label || ("field " + (i + 1));
    lab.htmlFor = "f" + i;
    let inp;
    if (f.kind === "option") {
      inp = document.createElement("select");
      (f.options || []).forEach((o) => {
        const op = document.createElement("option");
        op.value = o; op.textContent = o;
        if (o === f.default) op.selected = true;
        inp.appendChild(op);
      });
    } else {
      inp = document.createElement("input");
      // module default shown as placeholder so you can just type over it
      inp.placeholder = f.default || "";
      inp.dataset.default = f.default || "";
      const fromSession = f.session_key ? (session[f.session_key] || "") : "";
      if (fromSession) {
        inp.value = fromSession;
        inp.classList.add("from-session");
        inp.title = "from the engagement target (" + f.session_key + ") - edit to override";
      }
    }
    inp.id = "f" + i;
    // label and its box are one unit: a row wraps BETWEEN pairs, never
    // between a prompt and the field it is asking for.
    const pair = document.createElement("div");
    pair.className = "fpair";
    pair.appendChild(lab);
    pair.appendChild(inp);
    // What this pair asks a row for, and the most it may take.  It asks for
    // its prompt plus a 14-character stub of box - enough to read, small
    // enough that several fit on a line - and may grow to the prompt plus the
    // width the module declared for the box, never past it.
    // The room a row has left over is then shared out in proportion to those
    // declared widths, not equally: the wordlist path the module sized at 52
    // characters takes the slack ahead of the 12-character file name beside
    // it, which needs none of it.  The ceiling is 96 rather than the width of
    // any real box, so a module that declares a box wide enough to want a line
    // of its own - msfvenom's additional switches, ida's target path - gets
    // the whole of the line it wraps onto.
    if (f.kind !== "option") {
      const cap = Math.max(6, Math.min(f.width || 26, 96));
      const lw = (f.label || "").length + 5;      // label, gap, box padding
      pair.style.flexBasis = (lw + Math.min(14, cap)) + "ch";
      pair.style.maxWidth = (lw + cap) + "ch";
      pair.style.flexGrow = cap;
      // A box the module declared narrower than the 8-character size the CSS
      // packs a line by - msfvenom's six-character LPORT, which holds a port
      // and nothing else - keeps the size it declared, so the prompt beside it
      // comes up onto the same row instead of being pushed off it.
      if (cap < 8) { inp.style.width = cap + "ch"; inp.style.minWidth = cap + "ch"; }
    } else {
      pair.style.maxWidth = "max-content";
    }
    row.appendChild(pair);
  });

  const btns = $("btns");
  const lone = $("loneBtn");
  btns.innerHTML = "";
  lone.innerHTML = "";
  const made = (r.buttons || []).map((b) => {
    const el = document.createElement("button");
    el.textContent = b.text || ("button " + b.index);
    if (/run|decode|encode|scan|start|\bgo\b/i.test(b.text || "")) el.className = "primary";
    el.onclick = () => run(b.index, el);
    return {el: el, group: b.group || ""};
  });
  // One button and nothing to fill in - a one-shot tool like info_cyberchef.
  // A whole Input panel around a single button is all frame and no content, so
  // the button goes into the terminal head, left of the word "Terminal", where
  // the output of pressing it appears anyway.
  const solo = !FIELDS.length && made.length === 1;
  // A button the module put in the same Tk frame as some fields belongs with
  // them - nmap's "Start Nmap" / "VULN Scan" sit in the frame that holds the
  // additional-switches entry, and read as that entry's actions - so it goes
  // on that row, to the right of its fields, not into the bar at the foot.
  // A button whose Tk frame held no fields has no row of its own to go to -
  // but the last field row almost always has space left at its right-hand end,
  // and a bar of its own would cost another line for nothing.  So it rides
  // there too, and only drops to the foot when there are no fields at all.
  const rows = [...box.children];
  const lastFlow = rows.filter((rw) => !rw.classList.contains("ticks")).pop();
  // Buttons bound for the same row travel as one block (.btnset), so the row
  // may push them all to the next line but never split them across two.
  const sets = new Map();
  made.forEach((m) => {
    const home = !solo && ((m.group && rowFor[m.group]) || lastFlow);
    if (!home) { (solo ? lone : btns).appendChild(m.el); return; }
    let set = sets.get(home);
    if (!set) {
      set = document.createElement("div");
      set.className = "btnset";
      sets.set(home, set);
      home.appendChild(set);
    }
    set.appendChild(m.el);
  });
  // Nothing left for the Input panel to hold - the reference modules (70 of the
  // 235, since the web drops their one "NEW Terminal" button) and now the
  // one-shot tools too - so it goes entirely and the cheatsheet takes the room.
  const panel = $("inputPanel");
  const hasBtns = made.length > 0;
  const noInput = !FIELDS.length && (!hasBtns || solo);
  panel.classList.toggle("gone", noInput);
  document.body.classList.toggle("no-input", noInput);
  // Several buttons but no fields: keep them, drop the empty field box and the
  // rule that separated them.
  panel.classList.toggle("bare", !FIELDS.length && hasBtns && !solo);
}

// --- the hint bar ---------------------------------------------------------
let hintTimer = null;
function setHint(text, live) {
  clearTimeout(hintTimer);
  $("hint").textContent = text;
  $("hint").classList.toggle("live", !!live);
}
// a state we cannot observe - the shell never tells us a command has ended -
// so a run's notice just fades away, leaving the bar empty as it starts
function flashHint(text) {
  setHint(text, true);
  hintTimer = setTimeout(() => setHint(""), 8000);
}

// --- the terminal ---------------------------------------------------------
// The output pane is not a viewer: it is the same pty-backed login shell the
// launcher's "NEW Terminal" button opens, one per module tab (its id lives in
// sessionStorage, so a reload reattaches to the shell you were working in).
// A button press types its command into that shell - which is why a run can be
// answered when it asks for a password, stopped with Ctrl-C, and followed up
// on with your own commands against what it printed.
//
// The shell itself is SkeletonTerm, shared with /terminal; what is left here
// is what this page does differently - the hint bar and the 30-row floor.
const DIM = "\x1b[38;5;244m", GRN = "\x1b[38;5;79m", RST = "\x1b[0m";

// The CSS floor under the pane is written in em - an approximation of a row.
// The real row height comes from the font metrics, so fit first and, if that
// came up short of the 30 rows this pane promises, grow the box by the rows
// it is missing and fit again.  It only ever grows, so dragging the handle
// down stops at 30 rows instead of squeezing the shell.
const MIN_ROWS = 30;
function fitTerm() {
  T.fitAddon.fit();
  const scr = $("term").querySelector(".xterm-screen");
  if (scr && T.term.rows > 0 && T.term.rows < MIN_ROWS) {
    const rowH = scr.clientHeight / T.term.rows;
    const wrap = $("termWrap");
    wrap.style.height =
      Math.ceil(wrap.clientHeight + (MIN_ROWS - T.term.rows) * rowH) + "px";
    T.fitAddon.fit();
  }
}

const T = new SkeletonTerm({
  sidKey: "skelModSid:" + MODULE,
  mount: "term",
  observe: "termWrap",
  tabSelect: "notesTab",
  record: "rec",
  dim: DIM,
  onFit: fitTerm,
  onConnect: () => setHint(""),
  onExit: () => setHint("shell exited"),
  // One stalled connection is now every module tab's problem, so it says so
  // rather than going quiet - which is what the six-tab ceiling used to do.
  onState: (up) => {
    if (!up) setHint("stream stalled - reconnecting");
    else if ($("hint").textContent.indexOf("stalled") >= 0) setHint("");
  },
});
T.open();

$("btnInt").onclick = () => T.interrupt();
$("btnClear").onclick = () => T.clear();
$("btnKill").onclick = () => T.restart();
$("dl").onclick = () => T.saveLog(MODULE);

// --- running --------------------------------------------------------------
function fieldValues() {
  return FIELDS.map((f, i) => {
    const el2 = $("f" + i);
    if (f.kind === "check") return el2.checked ? el2.dataset.on : el2.dataset.off;
    if (f.kind === "option") return el2.value;
    // left-blank text field falls back to the module's default
    return el2.value !== "" ? el2.value : el2.dataset.default;
  });
}

// A button press does not start anything of its own: the server builds the
// command the module would have handed to gnome-terminal and types it into the
// shell below, which then runs it in front of you.
async function run(index, el) {
  const old = el.textContent;
  el.disabled = true; el.textContent = "sending…";
  $("olink").innerHTML = "";
  if (T.exited) { T.term.reset(); T.connect(); }   // nothing to type into: open a shell
  try {
    let r;
    try {
      r = await (await fetch("/api/module/" + encodeURIComponent(MODULE) + "/send", {
        method: "POST", headers: {"Content-Type": "application/json"},
        body: JSON.stringify({button: index, fields: fieldValues(),
                              tab: $("notesTab").value, sid: T.sid,
                              record: T.recording}),
      })).json();
    } catch (e) {
      T.say("\ncould not reach the server: " + e + "\n", DIM);
      setHint("not sent");
      return;
    }
    if (!r.ok) {
      T.say("\nrun failed: " + r.error + "\n", DIM);
      setHint("could not build the command");
      return;
    }
    // Not a plain command - opening a terminal, a browser, a background server
    // - so there is nothing a shell line could say; the one-shot path runs it.
    if (!r.sent) return await runBuffered(index, el, old);
    flashHint("sent to the shell — type to answer it, Ctrl-C to stop it");
    T.focus();
  } finally {
    el.disabled = false; el.textContent = old;
  }
}

// The one-shot path, still used for the actions a shell line cannot represent.
async function runBuffered(index, el, old) {
  el.disabled = true; el.textContent = "running…";
  setHint("running…", true);
  try {
    const r = await (await fetch("/api/module/" + encodeURIComponent(MODULE) + "/run", {
      method: "POST", headers: {"Content-Type": "application/json"},
      body: JSON.stringify({button: index, fields: fieldValues(),
                            tab: $("notesTab").value, sid: T.sid,
                            record: T.recording}),
    })).json();
    if (!r.ok) { T.say("\nrun failed: " + r.error + "\n", DIM); setHint("failed"); return; }
    // The server writes the run into the shell itself when it can reach it, so
    // it is in the scrollback the Download button hands back; only print it
    // here when it could not (no shell of ours left to write to).
    if (!r.echoed) {
      if (r.command) T.say("\n" + GRN + "$ " + RST + r.command + "\n");
      T.say((r.output || "").trimEnd() + "\n", DIM);
    }
    flashHint("finished");
    if (r.url) {
      // Background server / console (CyberChef, Nessus, ...) - open it in a
      // maximised window, and leave a link in case the pop-up is blocked.
      const feat = "noopener,left=0,top=0,width=" + screen.availWidth +
                   ",height=" + screen.availHeight;
      const w = window.open(r.url, "_blank", feat);
      try { if (w) w.moveTo(0, 0), w.resizeTo(screen.availWidth, screen.availHeight); } catch (e) {}
      // the link lives below the terminal, where it stays clickable
      const a = document.createElement("a");
      a.href = r.url; a.target = "_blank"; a.textContent = "open " + r.url;
      $("olink").appendChild(a);
    }
  } finally {
    el.disabled = false; el.textContent = old;
  }
}

load().catch((e) => T.say("\ncould not load this module: " + e + "\n", DIM));
T.start();
})();
