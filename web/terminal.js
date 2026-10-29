// SKELETON - the /terminal page.
//
// The whole page is one shell, so there is almost nothing here: SkeletonTerm
// (web/skeleton-term.js) is the terminal, and this wires it to the three
// buttons in the header and the hint line under it.
(() => {
  const $ = (id) => document.getElementById(id);
  const HINT = $("hint").textContent;

  const T = new SkeletonTerm({
    sidKey: "skelTermSid",
    mount: "term",
    tabSelect: "notesTab",
    record: "rec",
    // The stream is shared with every other page now, so say when it is down:
    // a terminal that has quietly stopped updating is the worst of both.
    onState: (up) => {
      $("hint").textContent = up ? HINT : "stream stalled - reconnecting";
    },
  });
  T.open();

  $("kill").onclick = () => T.restart();
  $("clear").onclick = () => T.clear();
  $("dl").onclick = () => T.saveLog("terminal");

  T.start(true);
})();
