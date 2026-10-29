// SKELETON - the console.
//
// The notes pane and its tabs, the engagement target / creds rows, the button
// bar, the stage -> module -> glossary browser, and the Runs panel.  Every
// action is one /api/* call; the page holds no state the server needs.
//
// Wrapped in an IIFE so nothing here is a global: the terminal pages load
// web/skeleton-term.js alongside their own script, and two files sharing one
// script scope must not both declare $ .
(() => {
  const $ = (id) => document.getElementById(id);
  const notes = $("notes");
  let BANNER = "";
  let ALL_MODULES = [];       // [{name, desc}]
  let curStage = "ALL";
  let curModule = null;
  let TABS = [{id: "main", name: "Notes"}];   // named notes tabs
  let activeTab = "main";
  const tabText = {};         // tab id -> the full notes text kept for that tab

  // Notes pane rendering: timestamp lines orange, "$ <command>" lines green with
  // their switches picked out in orange - the same highlighting the glossary uses.
  function hlEsc(s) {
    return s.replace(/[&<>]/g, (c) => ({"&": "&amp;", "<": "&lt;", ">": "&gt;"}[c]));
  }
  function hl(text) {
    return text.split("\n").map((line) => {
      if (/^Time stamp:/.test(line)) return '<span class="ts">' + hlEsc(line) + "</span>";
      if (/^\$ /.test(line))
        return '<span class="cmd"><span class="sig">$</span> ' + gCode(line.slice(2)) + "</span>";
      return hlEsc(line);
    }).join("\n");
  }
  function getNotes() { return notes.innerText; }
  // Already reading the newest output?  Then keep following it.  Otherwise the
  // operator has scrolled back to look at something and must be left there.
  function pinned(el, slack) {
    return el.scrollHeight - el.scrollTop - el.clientHeight <= (slack || 24);
  }
  let notesTail = null;   // trailing partial line, re-rendered as it grows
  function setNotes(text) {
    notes.innerHTML = hl(text);
    notesTail = null;
    notes.scrollTop = notes.scrollHeight;
    tabText[activeTab] = text;          // keep the active tab's buffer in step
  }
  function appendNotes(text) {
    if (!text) return;
    // Append the new lines as their own nodes.  Rewriting innerHTML for the
    // whole buffer - which is what this used to do, once a second - threw away
    // the caret and any selection, so a note could not be typed while a scan was
    // running, and it re-pinned the view to the bottom, so earlier output could
    // not be read either.  The buffer string is re-read from the pane when it is
    // actually needed (tab switch, save), not on every chunk.
    const follow = pinned(notes);
    // hl() styles whole lines ("$ cmd", "Time stamp:"), so only complete lines
    // are highlighted and appended.  A trailing partial line - a module writing
    // through `tee -a` outside the notes lock can be caught mid-line - is parked
    // in a plain span and re-rendered when the rest of it arrives, which is what
    // keeps incremental appends looking identical to a full re-render.
    let buf = (notesTail ? notesTail.textContent : "") + text;
    if (notesTail) { notesTail.remove(); notesTail = null; }
    const cut = buf.lastIndexOf("\n");
    const whole = cut >= 0 ? buf.slice(0, cut + 1) : "";
    const rest = cut >= 0 ? buf.slice(cut + 1) : buf;
    if (whole) {
      notes.appendChild(document.createRange().createContextualFragment(hl(whole)));
    }
    if (rest) {
      notesTail = document.createElement("span");
      notesTail.textContent = rest;
      notes.appendChild(notesTail);
    }
    if (follow) notes.scrollTop = notes.scrollHeight;
  }

  // --- notes tabs ------------------------------------------------------------
  function renderTabs() {
    const bar = $("tabbar");
    bar.innerHTML = "";
    for (const t of TABS) {
      const b = document.createElement("button");
      b.className = "tabbtn" + (t.id === activeTab ? " active" : "");
      b.title = "click to switch · double-click to rename";
      const lbl = document.createElement("span");
      lbl.className = "lbl";
      lbl.textContent = t.name;
      b.appendChild(lbl);
      b.onclick = () => { if (!lbl.isContentEditable) switchTab(t.id); };
      b.ondblclick = () => beginRename(lbl, t.id);
      if (t.id !== "main") {
        const x = document.createElement("span");
        x.className = "x"; x.textContent = "×"; x.title = "delete this tab";
        x.onclick = (e) => { e.stopPropagation(); deleteTab(t.id); };
        b.appendChild(x);
      }
      bar.appendChild(b);
    }
    const add = document.createElement("button");
    add.className = "tabadd"; add.textContent = "+ TAB";
    add.title = "add a notes tab";
    add.onclick = addTab;
    bar.appendChild(add);
  }
  function switchTab(id) {
    if (id === activeTab) return;
    tabText[activeTab] = getNotes();
    activeTab = id;
    setNotes(tabText[id] != null ? tabText[id] : BANNER);
    renderTabs();
    refreshRuns();          // each tab keeps its own runs.jsonl
  }
  // double-click a tab to rename it inline; Enter or click-away commits, Esc cancels
  function beginRename(lbl, id) {
    lbl.contentEditable = "true";
    lbl.spellcheck = false;
    const sel = window.getSelection();
    const range = document.createRange();
    range.selectNodeContents(lbl);
    sel.removeAllRanges(); sel.addRange(range);
    lbl.focus();
    let done = false;
    const finish = async (commit) => {
      if (done) return;
      done = true;
      lbl.contentEditable = "false";
      lbl.removeEventListener("blur", onBlur);
      lbl.removeEventListener("keydown", onKey);
      const cur = (TABS.find((t) => t.id === id) || {}).name || "";
      const name = lbl.textContent.trim().slice(0, 80);
      if (commit && name && name !== cur) {
        const r = await postJSON("/api/tabs/" + encodeURIComponent(id), {name});
        if (r.ok) TABS = r.tabs;
      }
      renderTabs();
    };
    const onBlur = () => finish(true);
    const onKey = (e) => {
      if (e.key === "Enter") { e.preventDefault(); finish(true); }
      else if (e.key === "Escape") { e.preventDefault(); finish(false); }
    };
    lbl.addEventListener("blur", onBlur);
    lbl.addEventListener("keydown", onKey);
  }
  async function addTab() {
    let n = 1;
    while (TABS.some((t) => t.name === "New_" + n)) n++;
    const r = await postJSON("/api/tabs", {name: "New_" + n});
    if (!r.ok) return;
    TABS = r.tabs;
    tabText[r.tab.id] = BANNER;
    switchTab(r.tab.id);
  }
  async function deleteTab(id) {
    if (id === "main") return;
    if (!confirm("Delete this notes tab?  Its notes in this page are lost.")) return;
    const r = await postJSON("/api/tabs/" + encodeURIComponent(id), {delete: true});
    if (!r.ok) return;
    TABS = r.tabs;
    delete tabText[id];
    if (activeTab === id) {
      activeTab = "main";
      setNotes(tabText["main"] != null ? tabText["main"] : BANNER);
    }
    renderTabs();
  }

  function log(text) {
    appendNotes(text.endsWith("\n") ? text : text + "\n");
  }
  // Every API failure used to arrive as an unhandled promise rejection: an
  // abort(4xx) or a 500 returns HTML, .json() threw, and callers with no catch
  // simply did nothing - a dead button and no message anywhere.  These parse
  // once, and turn anything that is not a JSON success into an Error carrying
  // the server's own words.
  async function readJSON(r, url) {
    const text = await r.text();
    let data = null;
    try { data = JSON.parse(text); } catch (e) {}
    if (data === null) {
      throw new Error((r.ok ? "unreadable reply from " : "HTTP " + r.status + " from ")
                      + url + (text ? ": " + text.slice(0, 200).trim() : ""));
    }
    if (!r.ok) throw new Error(data.error || data.log || ("HTTP " + r.status + " from " + url));
    return data;
  }
  async function getJSON(url) { return readJSON(await fetch(url), url); }
  async function postJSON(url, body) {
    const r = await fetch(url, {
      method: "POST", headers: {"Content-Type": "application/json"},
      body: JSON.stringify(body || {}),
    });
    return readJSON(r, url);
  }
  // Report a failure where the operator is already looking.
  function warn(what, e) {
    log("\n" + what + ": " + ((e && e.message) || e || "failed"));
  }
  // Wrap a click handler so a rejection lands in the notes pane, not the console.
  function guard(what, fn) {
    return async (...a) => {
      try { return await fn(...a); } catch (e) { warn(what, e); }
    };
  }

  function modulesForStage(stage) {
    return stage === "ALL"
      ? ALL_MODULES
      : ALL_MODULES.filter((m) => m.name.startsWith(stage));
  }
  function showProModal(name) {
    const modal = $("proModal");
    if (!modal) return;
    const titleEl = $("proModuleName");
    if (titleEl) titleEl.textContent = name || "Pro Module";
    modal.classList.remove("hidden");
  }
  function hideProModal() {
    const modal = $("proModal");
    if (modal) modal.classList.add("hidden");
  }
  function renderModules(items) {
    const ul = $("modules");
    ul.innerHTML = "";
    for (const m of items) {
      const li = document.createElement("li");
      const cut = m.name.indexOf("_");            // <stage>_<tool>
      if (cut > 0) {
        const pre = document.createElement("span");
        pre.className = "p";
        pre.textContent = m.name.slice(0, cut + 1);
        li.append(pre, m.name.slice(cut + 1));
      } else {
        li.textContent = m.name;
      }
      if (m.isDemo === false) {
        const pro = document.createElement("span");
        pro.className = "badge-pro";
        pro.textContent = "PRO";
        li.append(pro);
      }
      li.title = m.desc || "";
      li.tabIndex = 0;
      if (m.name === curModule) li.className = "sel";
      li.onclick = () => selectModule(m.name, li);
      li.ondblclick = () => runModule();
      li.onkeydown = (e) => {
        if (e.key === "Enter") { e.preventDefault(); selectModule(m.name, li); }
      };
      ul.appendChild(li);
    }
    $("count").textContent = items.length + (items.length === 1 ? " module" : " modules");
    if (!items.length) {
      const li = document.createElement("li");
      li.className = "empty";
      li.textContent = "Nothing matches that. Try a tool name, a protocol or a technique.";
      ul.appendChild(li);
    }
  }
  function applyFilter() {
    const q = $("search").value.trim().toLowerCase();
    if (!q) { renderModules(modulesForStage(curStage)); return; }
    renderModules(ALL_MODULES.filter(
      (m) => m.name.toLowerCase().includes(q) || (m.desc || "").toLowerCase().includes(q)
    ));
  }
  async function selectModule(name, li) {
    try { await _selectModule(name, li); }
    catch (e) { warn("could not open " + name, e); }
  }
  async function _selectModule(name, li) {
    curModule = name;
    $("refTitle").textContent = name;
    for (const el of $("modules").children) el.classList.toggle("sel", el === li);
    const r = await getJSON("/api/glossary?module=" + encodeURIComponent(name));
    renderGlossary(r.text || "");
  }
  function gEsc(s) {
    return s.replace(/[&<>]/g, (c) => ({"&": "&amp;", "<": "&lt;", ">": "&gt;"}[c]));
  }
  function gCode(s) {
    // Highlight `backticked spans`, -x / --long switches, /flag(:value) and
    // mimikatz-style module::function tokens - each as ONE span so a line full of
    // them (e.g. kerberos::golden /user:.. /domain:.. /ptt) stays readable when
    // it wraps instead of fragmenting at every colon.
    let h = gEsc(s).replace(/`([^`]+)`/g, "<code>$1</code>");
    h = h.replace(
      /(^|[\s(\[])(-{1,2}[A-Za-z][\w-]*|\/[A-Za-z][\w-]*(?::(?:&[a-z]+;|[^\s)\],;&])+)?|[A-Za-z][\w-]*::[\w:]*)(?=$|[\s)\].,;:])/g,
      "$1<code>$2</code>");
    return h;
  }
  function renderGlossary(text) {
    const box = $("glossary");
    box.innerHTML = "";
    const raw = (text || "").replace(/\r/g, "");
    if (!raw.trim()) {
      box.innerHTML = '<div class="empty">This module has no reference text.</div>';
      return;
    }
    for (const line of raw.split("\n")) {
      if (!line.trim()) continue;
      const body = line.trim();
      if (body.startsWith("•")) {          // "• ..." functionality bullet
        const d = document.createElement("div");
        d.className = "g-item";
        // one wrapper span so the flex row is [marker][text], not a separate
        // flex item per <code> (which stacked the switches vertically)
        const t = document.createElement("span");
        t.className = "g-text";
        t.innerHTML = gCode(body.replace(/^•\s?/, ""));
        d.appendChild(t);
        box.appendChild(d);
      } else if (!/^\s/.test(line) && / - /.test(line)) {   // "name - description" head
        const cut = line.indexOf(" - ");
        const d = document.createElement("div");
        d.className = "g-head";
        d.innerHTML = '<span class="g-name">' + gEsc(line.slice(0, cut).trim()) +
                      '</span><span class="g-sub"> — ' +
                      gEsc(line.slice(cut + 3).trim()) + "</span>";
        box.appendChild(d);
      } else {
        const d = document.createElement("div");
        d.className = "g-more";
        d.innerHTML = gCode(body);
        box.appendChild(d);
      }
    }
  }
  async function runModule() {
    if (!curModule) { log("\nRUN MODULE: select a module first"); return; }
    const curModObj = ALL_MODULES.find((m) => m.name === curModule);
    if (curModObj && curModObj.isDemo === false) {
      showProModal(curModule);
      return;
    }
    // Open the tab synchronously so the browser treats it as user-initiated,
    // then point it at the module page once the server has logged the run.
    const tab = window.open("about:blank", "_blank");
    let r;
    try {
      r = await postJSON("/api/run", {module: curModule});
    } catch (e) {
      // postJSON throws on anything but a JSON 2xx, and this was the one
      // caller with no catch: the rejection went to the console and the blank
      // tab it had just opened stayed open, empty, for ever.
      if (tab) tab.close();
      warn("Run module", e);
      return;
    }
    if (r.log) log(r.log);
    if (r.ok && tab) tab.location = r.url;
    else {
      if (tab) tab.close();
      if (r && r.isPro) showProModal(curModule);
    }
  }
  // Runs are read back from working/<tab>/runs.jsonl, so they outlive the page
  // and the server.  Each row opens its module, its log, or copies the command.
  let RUNS = [];

  function renderHistory(items) {
    RUNS = items || [];
    const ul = $("history");
    // Re-rendered every 3s, so the same rule as the notes pane: only jump to the
    // newest row if the operator was already looking at it.
    const follow = pinned(ul);
    ul.innerHTML = "";
    $("runCount").textContent = RUNS.length ? RUNS.length : "";
    if (!RUNS.length) {
      const li = document.createElement("li");
      li.className = "empty";
      li.textContent = "No runs on this tab yet. Run a module and the command it " +
                       "typed into its terminal lands here.";
      ul.appendChild(li);
      return;
    }
    for (const r of RUNS) {
      const li = document.createElement("li");
      li.className = "run";
      const top = document.createElement("div");
      top.className = "r-top";

      const when = document.createElement("span");
      when.className = "r-when";
      when.textContent = r.started
        ? new Date(r.started * 1000).toLocaleTimeString([], {hour: "2-digit", minute: "2-digit"})
        : "";
      const mod = document.createElement("span");
      mod.className = "r-mod";
      mod.textContent = r.module;
      const st = document.createElement("span");
      st.className = "r-state";
      if (r.where === "shell") { st.textContent = "shell"; }
      else { st.textContent = "ok"; }
      top.append(when, mod, st);
      li.appendChild(top);

      if (r.command) {
        const cmd = document.createElement("div");
        cmd.className = "r-cmd";
        cmd.textContent = r.command;
        cmd.title = r.command;
        li.appendChild(cmd);
      }

      const acts = document.createElement("div");
      acts.className = "r-acts";
      const act = (text, fn) => {
        const a = document.createElement("a");
        a.href = "#"; a.textContent = text;
        a.onclick = (e) => { e.preventDefault(); fn(); };
        acts.appendChild(a);
      };
      act("re-run", () => window.open("/module/" + encodeURIComponent(r.module), "_blank"));
      if (r.command) act("copy", () => navigator.clipboard &&
        navigator.clipboard.writeText(r.command));
      li.appendChild(acts);
      ul.appendChild(li);
    }
    if (follow) ul.scrollTop = ul.scrollHeight;
  }

  async function refreshRuns() {
    try {
      const r = await getJSON("/api/jobs?tab=" + encodeURIComponent(activeTab));
      renderHistory(r.jobs || []);
    } catch (e) {}
  }
  // The stage list is the module list's filter: ALL, then each PENTEST_CHAIN
  // step by name.
  function renderStages(stages) {
    const ul = $("stages");
    ul.innerHTML = "";
    for (const s of stages) {
      const li = document.createElement("li");
      li.textContent = s;
      li.title = s === "ALL" ? "every module in the catalogue" : s + " stage";
      li.tabIndex = 0;
      if (s === curStage) li.className = "sel";
      const pick = () => {
        curStage = s;
        $("search").value = "";       // a stage choice clears any active search
        for (const el of ul.children) el.classList.toggle("sel", el === li);
        applyFilter();
      };
      li.onclick = pick;
      li.onkeydown = (e) => { if (e.key === "Enter") { e.preventDefault(); pick(); } };
      ul.appendChild(li);
    }
  }

  // --- top bar -------------------------------------------------------------
  // NEW starts the selected notes tab over: the notes go back to the banner and
  // the tab's run history is erased on the server as well as in the panel.
  $("btnNew").onclick = guard("New", async () => {
    setNotes(BANNER);
    await postJSON("/api/jobs/clear", {tab: activeTab});
    refreshRuns();
  });
  $("btnTime").onclick = guard("Time", async () => log((await postJSON("/api/time")).log));
  $("btnFindIp").onclick = guard("Find my IP", async () => {
    const r = await postJSON("/api/find-ip");
    if (r.log) log(r.log);
    if (r.ok) { $("ip").value = r.ip; }
  });
  $("btnChangeIp").onclick = guard("Change my IP", async () => {
    const ip = $("ip").value.trim();
    const r = await postJSON("/api/change-ip", {ip});
    if (r.log) log(r.log);
  });

  // --- save / load / insert / open port ----------------------------------
  // Inputs show their default as placeholder text (type over it); fall back to
  // that default when the field is left blank.
  const jobName = () => $("jobName").value.trim() || "Current_Job";
  const insertName = () => $("insertName").value.trim() || "file.txt";
  $("btnSave").onclick = guard("Save", async () => {
    // /api/save appends ".txt" itself, as /api/load and the Tk launcher do -
    // appending it here too wrote Current_Job.txt.txt, which LOAD never found
    const r = await postJSON("/api/save",
                             {name: jobName(), text: getNotes(), tab: activeTab});
    if (r.log) log(r.log);
  });
  $("btnLoad").onclick = guard("Load", async () => {
    setNotes((await getJSON("/api/load?name=" + encodeURIComponent(jobName()))).text);
  });
  $("btnInsert").onclick = guard("Insert", async () => {
    log((await getJSON("/api/insert?name=" + encodeURIComponent(insertName()))).text);
  });
  $("btnOpenPort").onclick = guard("Open port", async () => {
    const r = await postJSON("/api/open-port", {port: $("port").value});
    if (r.log) log(r.log);
  });
  $("btnRun").onclick = runModule;
  $("btnNewTerm").onclick = () => window.open("/terminal", "_blank");

  // --- engagement target ------------------------------------------------
  // One target for the whole engagement.  Modules pre-fill from it, and the Tk
  // launcher hands it to module processes as SKELETON_* environment variables.
  // The session carries "target" and "url" as separate keys - a module field
  // pre-fills from whichever its label maps to - but this row asks for the host
  // once and saveSession() writes that one box to both, so a url/domain-typed
  // field opens filled rather than on the module's own example.
  // The callback pair is deliberately not here: this front-end does not set
  // lhost/lport, so a reverse-shell module opens on the session's own values
  // (lport defaults to 4444) or on its own example, and whatever the Tk
  // launcher stored is left alone.
  const SESSION_FIELDS = ["target", "user", "pass", "iface", "wlan"];

  function showSession(s) {
    for (const k of SESSION_FIELDS) {
      const el = $("s_" + k);
      if (el) el.value = s[k] || "";
    }
  }

  async function saveSession() {
    const body = {};
    for (const k of SESSION_FIELDS) body[k] = $("s_" + k).value;
    // The Target box is the whole answer to "what are we pointed at", so it
    // sets the url key too - this front-end has no separate box that a mirror
    // could contradict.  A tester who wants a path or a scheme types it here:
    // "https://host/app" is as good a target as "10.10.14.5".
    body.url = body.target;
    const r = await postJSON("/api/session", body);
    showSession(r.session);
    if (r.targets) TARGETS = r.targets;
    renderTargets();
    if (r.log) log(r.log);
  }

  $("btnSession").onclick = saveSession;
  for (const k of SESSION_FIELDS) {
    $("s_" + k).addEventListener("keydown", (e) => {
      if (e.key === "Enter") saveSession();
    });
  }

  // --- target list ----------------------------------------------------------
  // An engagement is rarely one host.  The session still carries the one ACTIVE
  // target - the value every module pre-fills from - and this keeps the list of
  // targets it has been pointed at, so moving to the next host is a pick rather
  // than a retype.  Setting a target also files it in the list, and the one
  // button does both ends of "manage": "add" for a target that is not in the
  // list yet, "forget" once it is.
  let TARGETS = [];
  function targetSaved() {
    return TARGETS.indexOf($("s_target").value.trim()) >= 0;
  }
  function syncTargetButton() {
    const b = $("btnTargetAdd");
    b.textContent = targetSaved() ? "forget" : "add";
    b.title = targetSaved()
      ? "Drop this target from the list"
      : "Remember this target so it can be picked again";
  }
  function renderTargets() {
    const sel = $("targetPick"), cur = TARGETS.indexOf($("s_target").value.trim());
    sel.innerHTML = "";
    // Numbered like the credential pairs, and for the same reason: a host name in
    // a select this narrow is only ever a clipped one, and the box beside it
    // already shows the active target in full.  The name rides each row as a
    // tooltip, and the number shown is the target that is active.
    const ph = document.createElement("option");
    ph.value = "";
    ph.textContent = "#";
    ph.title = TARGETS.length ? TARGETS.length + " saved" : "nothing saved yet";
    sel.appendChild(ph);
    TARGETS.forEach((t, i) => {
      const o = document.createElement("option");
      o.value = String(i);
      o.textContent = "#" + (i + 1);
      o.title = t;
      sel.appendChild(o);
    });
    sel.value = cur >= 0 ? String(cur) : "";
    sel.title = "Targets this engagement has been pointed at"
              + (TARGETS.length ? " (" + TARGETS.length + ")" : "")
              + " - pick one to make it the active target";
    syncTargetButton();
  }
  // Typing edits the active target, so the picker follows the box.
  $("s_target").addEventListener("input", renderTargets);
  // Picking IS the switch: the chosen target becomes the active one right away.
  $("targetPick").onchange = () => {
    const v = $("targetPick").value;
    if (v === "") { renderTargets(); return; }
    const t = TARGETS[+v];
    if (t) { $("s_target").value = t; saveSession(); }
  };
  $("btnTargetAdd").onclick = guard("Targets", async () => {
    const target = $("s_target").value.trim();
    if (!target) { log("\nTargets: type a target first"); return; }
    const saved = targetSaved();
    const r = await postJSON(saved ? "/api/targets/delete" : "/api/targets", {target});
    if (r.log) log(r.log);
    if (r.ok) { TARGETS = r.targets || []; renderTargets(); }
  });

  // --- credential manager ---------------------------------------------------
  // The engagement session carries one working user / password; this keeps the
  // wider list gathered on the box, so any pair can be recalled into the fields.
  // The dropdown loads a saved pair back into the fields.  The one button does
  // both ends of "manage": it reads "add" for a new pair and "remove" once the
  // pair in the fields is one that is already saved.
  let CREDS = [];
  function credIndex() {
    const u = $("s_user").value.trim(), p = $("s_pass").value.trim();
    return CREDS.findIndex((c) => c.user === u && c.pass === p);
  }
  function syncCredButton() {
    $("btnCredAdd").textContent = credIndex() >= 0 ? "remove" : "add";
  }
  function renderCreds() {
    const sel = $("credPick");
    const cur = credIndex();
    sel.innerHTML = "";
    // Pairs are listed as #1, #2, ... rather than "user / password" - a saved
    // password is as wide as the row can spare, and the whole point of this box
    // is that it is narrow.  The pair itself rides each row as a tooltip, and
    // picking one puts it in the fields beside the box anyway.  The number is the
    // tester's count, so it starts at 1; the option's value stays the index.
    const ph = document.createElement("option");
    ph.value = "";
    ph.textContent = "#";
    ph.title = CREDS.length ? CREDS.length + " saved" : "nothing saved yet";
    sel.appendChild(ph);
    CREDS.forEach((c, i) => {
      const o = document.createElement("option");
      o.value = String(i);
      o.textContent = "#" + (i + 1);   // the list is counted from 1, the array from 0
      o.title = (c.user || "∅") + "  /  " + (c.pass || "∅");
      sel.appendChild(o);
    });
    // The number shown is the pair in the fields, so the box says which one is
    // loaded rather than snapping back to a placeholder.
    sel.value = cur >= 0 ? String(cur) : "";
    sel.title = "Saved user / password pairs" + (CREDS.length ? " (" + CREDS.length + ")" : "")
              + " - pick one to load it into the fields";
    syncCredButton();
  }
  $("s_user").addEventListener("input", renderCreds);
  $("s_pass").addEventListener("input", renderCreds);
  $("credPick").onchange = () => {
    const v = $("credPick").value;
    if (v === "") { renderCreds(); return; }
    const c = CREDS[+v];
    if (c) { $("s_user").value = c.user; $("s_pass").value = c.pass; }
    renderCreds();
  };
  $("btnCredAdd").onclick = guard("Credentials", async () => {
    const user = $("s_user").value.trim(), pass = $("s_pass").value.trim();
    if (!user && !pass) { log("\nCreds: type a user name or a password first"); return; }
    const saved = credIndex() >= 0;
    const r = await postJSON(saved ? "/api/creds/delete" : "/api/creds", {user, pass});
    if (r.log) log(r.log);
    if (r.ok) { CREDS = r.creds || []; renderCreds(); }
  });

  // --- folding panels ---------------------------------------------------
  // The reference folds away to leave the browser and the notes the room.  It
  // always starts folded, whatever you left it at: open it when you need it, and
  // it keeps the selected module's name on its folded bar so it is not
  // anonymous.
  function collapsible(panelId, toggleId, what, apply) {
    const p = $(panelId), b = $(toggleId);
    function set(open) {
      p.classList.toggle("off", !open);
      apply(open);
      b.innerHTML = open ? "&rsaquo;" : "&lsaquo;";
      b.title = (open ? "Collapse the " : "Expand the ") + what;
      b.setAttribute("aria-expanded", open ? "true" : "false");
    }
    b.onclick = (e) => { e.stopPropagation(); set(p.classList.contains("off")); };
    p.onclick = () => { if (p.classList.contains("off")) set(true); };
    set(false);          // always folded on load, however you left it last time
  }

  collapsible("refPanel", "refToggle", "reference",
              (open) => document.querySelector("main").classList.toggle("ref-on", open));

  const modalClose = $("modalClose");
  if (modalClose) modalClose.onclick = hideProModal;
  const proModal = $("proModal");
  if (proModal) {
    proModal.onclick = (e) => {
      if (e.target === proModal) hideProModal();
    };
  }
  window.addEventListener("keydown", (e) => {
    if (e.key === "Escape") hideProModal();
  });

  $("search").addEventListener("keyup", applyFilter);
  $("search").addEventListener("keydown", (e) => {
    if (e.key === "Escape") { $("search").value = ""; applyFilter(); }
  });

  // --- boot -------------------------------------------------------------
  (async function init() {
    // Whatever happens in here, the notes poll at the foot of this function has
    // to be installed.  It used to be the last statement of one unguarded async
    // run, so a single failed fetch during start-up left the pane dead for the
    // life of the page with nothing said.
    let cat = null;
    try {
      cat = await getJSON("/api/catalog");
      BANNER = cat.banner;
      ALL_MODULES = cat.modules;
      if (cat.tabs && cat.tabs.length) TABS = cat.tabs;
      for (const t of TABS) tabText[t.id] = BANNER;
      activeTab = "main";
      setNotes(BANNER);
      renderTabs();
      renderStages(cat.stages);
      applyFilter();
      refreshRuns();
      setInterval(refreshRuns, 3000);
      showSession((await getJSON("/api/session")).session);
    } catch (e) {
      warn("console did not finish loading", e);
    }
    try { TARGETS = (await getJSON("/api/targets")).targets || []; } catch (e) {}
    renderTargets();
    try { CREDS = (await getJSON("/api/creds")).creds || []; } catch (e) {}
    renderCreds();

    // Follow each tab's channel from where we got to, like watch_file() in the
    // GUI.  Offsets are per browser tab, so two launcher tabs both see everything.
    let offsets = {};
    // One poll in flight at a time.  /api/poll holds the notes lock across every
    // tab's rotate+read and can sweep working/, so a tick can outlast the
    // interval; a second request sent with the same offsets returns the same
    // bytes and writes them into the pane twice.
    let polling = false;
    setInterval(async () => {
      if (polling) return;
      polling = true;
      let r;
      try {
        r = await getJSON("/api/poll?since=" + encodeURIComponent(JSON.stringify(offsets)));
      } catch (e) {
        return;                       // transient; the next tick tries again
      } finally {
        polling = false;
      }
      if (r.offsets) offsets = r.offsets;
      const chunks = r.chunks || (r.chunk ? {main: r.chunk} : {});
      for (const id of Object.keys(chunks)) {
        const chunk = chunks[id];
        if (!chunk) continue;
        if (tabText[id] == null) tabText[id] = BANNER;   // tab added from elsewhere
        if (id === activeTab) appendNotes(chunk);
        else tabText[id] += chunk;
      }
    }, (cat && cat.pollMs) || 1000);
  })();})();
