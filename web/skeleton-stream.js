// SKELETON - one EventSource for every page in this browser.
//
// A browser allows six HTTP/1.1 connections per origin, and each module page
// used to hold one open for ever for its own terminal.  The sixth tab took the
// last slot: the console's notes poll stopped returning, the seventh page
// never finished loading, and nothing on screen said why.  In a launcher whose
// design is one tab per module that is an ordinary morning's work.
//
// This worker is shared by every SKELETON page in the browser.  It keeps a
// single multiplexed stream open (GET /api/terminal/multi) and posts each page
// only the frames tagged with its own sid, so the number of terminals that can
// be open at once is the server's business again rather than the browser's.
//
// Frames in:  "data: <sid> <base64>", and an `exit` event whose data is
//             "<sid> <token>" - which terminal, and which of the shells that
//             have held it.
// Messages out to a page:
//   {op:"data",  sid, b64}   pty output
//   {op:"exit",  sid}        that shell has gone
//   {op:"state", sid, up}    is the stream connected?  (drives the stall hint)
// Messages in from a page:
//   {op:"sub",  sid, tab, record}   start following this shell
//   {op:"keep", sid}                still here (a page that stops saying so is
//                                   dropped: SharedWorker has no reliable
//                                   "port closed", and a subscriber left
//                                   behind makes its shell look watched, so
//                                   the server would never reap it)
//   {op:"bye",  sid}                this page is going away

const CLIENTS = new Map();        // client id -> {port, sid, tab, record, seen}
// sid -> the token of the shell we are actually attached to.  A sid outlives
// the shell behind it - "restart shell" kills one and opens another under the
// same sid - and the dead one's exit arrives AFTER the page has re-subscribed.
// Forwarding that told the page its live shell had exited: it stopped reading,
// stopped its keep-alive, and showed a working terminal as a dead one.
const TOKENS = new Map();
const STREAM = "w" + Date.now().toString(36) + Math.random().toString(36).slice(2, 8);
const KEEP_MS = 300000;           // a page silent for five minutes has gone
let nextClient = 1;
let es = null;
let up = false;

function post(url, body) {
  return fetch(url, {
    method: "POST", headers: {"Content-Type": "application/json"},
    body: JSON.stringify(body),
  }).then((r) => r.json()).catch(() => null);
}

function tell(sid, msg) {
  for (const [id, c] of Array.from(CLIENTS)) {
    if (c.sid !== sid) continue;
    try { c.port.postMessage(msg); } catch (e) { CLIENTS.delete(id); }
  }
}

function watching(sid) {
  for (const c of CLIENTS.values()) if (c.sid === sid) return c;
  return null;
}

// A duplicated browser tab copies sessionStorage, so two pages can share a sid.
// Subscribe once for it and post both; the shell is the same shell.
async function subscribe(sid) {
  const c = watching(sid);
  if (!c || !up) return;
  // Forget the token BEFORE asking, not after being told: an exit already on
  // its way belongs to the shell being replaced, and between the ask and the
  // answer there is no shell here whose exit we would want to act on.
  TOKENS.delete(sid);
  const r = await post("/api/terminal/multi/sub",
                       {stream: STREAM, sid: sid, tab: c.tab, record: c.record});
  if (r && r.ok && r.token) TOKENS.set(sid, r.token);
}

function announce(state) {
  up = state;
  for (const c of CLIENTS.values()) {
    try { c.port.postMessage({op: "state", sid: c.sid, up: state}); } catch (e) {}
  }
}

function connect() {
  es = new EventSource("/api/terminal/multi?stream=" + encodeURIComponent(STREAM));
  es.addEventListener("ready", () => {
    // Also the reconnect path: the far side of a re-established EventSource
    // has nothing subscribed, and subscribing replays the scrollback.
    announce(true);
    const seen = new Set();
    for (const c of CLIENTS.values()) {
      if (!seen.has(c.sid)) { seen.add(c.sid); subscribe(c.sid); }
    }
  });
  es.onmessage = (ev) => {
    const cut = ev.data.indexOf(" ");
    if (cut < 0) return;
    const sid = ev.data.slice(0, cut);
    tell(sid, {op: "data", sid: sid, b64: ev.data.slice(cut + 1)});
  };
  es.addEventListener("exit", (ev) => {
    const cut = ev.data.indexOf(" ");
    const sid = cut < 0 ? ev.data : ev.data.slice(0, cut);
    const token = cut < 0 ? "" : ev.data.slice(cut + 1);
    if (TOKENS.get(sid) !== token) return;   // a shell we have already replaced
    TOKENS.delete(sid);
    tell(sid, {op: "exit", sid: sid});
  });
  es.onerror = () => { announce(false); };  // it reconnects on its own
}

function drop(id) {
  const c = CLIENTS.get(id);
  if (!c) return;
  CLIENTS.delete(id);
  if (!watching(c.sid)) {
    TOKENS.delete(c.sid);
    post("/api/terminal/multi/unsub", {stream: STREAM, sid: c.sid});
  }
}

onconnect = (e) => {
  const port = e.ports[0];
  const id = nextClient++;
  port.onmessage = (ev) => {
    const m = ev.data || {};
    if (!m.sid) return;
    if (m.op === "sub") {
      CLIENTS.set(id, {port: port, sid: m.sid, tab: m.tab,
                       record: m.record, seen: Date.now()});
      if (!es) connect(); else subscribe(m.sid);
      try { port.postMessage({op: "state", sid: m.sid, up: up}); } catch (err) {}
    } else if (m.op === "keep") {
      const c = CLIENTS.get(id);
      if (c) { c.seen = Date.now(); c.tab = m.tab; c.record = m.record; }
      else { port.postMessage({op: "resub", sid: m.sid}); }
    } else if (m.op === "bye") {
      drop(id);
    }
  };
  port.start();
};

setInterval(() => {
  const now = Date.now();
  for (const [id, c] of Array.from(CLIENTS)) if (now - c.seen > KEEP_MS) drop(id);
}, 60000);
