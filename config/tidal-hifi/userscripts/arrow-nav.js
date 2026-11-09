// Arrow-key navigation for tidal-hifi (loaded by the userscripts patch in app.asar).
// ↑/↓/←/→ move a highlight between visible buttons, links, cards and track rows
// (the page scrolls along with it); Enter activates / plays; Esc drops the highlight.
// Arrows are left alone while typing, on sliders (←/→) and inside open menus/dialogs.
(() => {
  if (window.__tnav) window.removeEventListener("keydown", window.__tnav, true);
  if (window.__tnavClear) window.removeEventListener("pointerdown", window.__tnavClear, true);
  document.querySelectorAll(".tnav-focus").forEach((e) => e.classList.remove("tnav-focus"));

  const STYLE_ID = "tnav-style";
  document.getElementById(STYLE_ID)?.remove();
  const style = document.createElement("style");
  style.id = STYLE_ID;
  style.textContent = `
    .tnav-focus {
      outline: 2px solid var(--player-control-active-button, #93cdf6) !important;
      outline-offset: 2px !important;
      border-radius: 6px;
      scroll-margin: 180px 0 40px 0;
    }`;
  document.head.appendChild(style);

  const FOCUSABLE =
    'a[href], button:not([disabled]), [role="button"], [role="link"], [role="tab"], ' +
    '[role="switch"], [role="slider"], [role="row"][tabindex], [tabindex]:not([tabindex="-1"])';
  const ROW = '[data-test="tracklist-row"], [role="row"][tabindex]';
  // Cards (album/artist/playlist tiles, home shortcuts) — each is one stop.
  const CARD = 'article[data-test^="grid-item"], #main [data-test*="-card-"], #main [class*="_linkOverlay_"]';
  const GROUP = ROW + ', ' + CARD; // composite items = one stop each
  const SKIP = 'input, textarea, select, [contenteditable=""], [contenteditable="true"]';

  const region = (el) =>
    el.closest("#sidebar") ? "side" :
    el.closest("#main") ? "main" :
    el.closest('[data-test="footer-player"]') ? "player" : "top";

  // Fixed/sticky overlays inside #main (TIDAL's compact header copy) are not stops.
  const inOverlay = (el) => {
    for (let a = el; a && a.id !== "main"; a = a.parentElement) {
      const p = getComputedStyle(a).position;
      if (p === "fixed" || p === "sticky") return a.id !== "main";
    }
    return false;
  };

  const candidates = (reg) => {
    const out = [], seen = new Set();
    for (const raw of document.querySelectorAll(FOCUSABLE + ", " + CARD)) {
      if (raw.matches(SKIP)) continue;
      const el = stopOf(raw);
      if (seen.has(el)) continue;
      seen.add(el);
      if (reg && region(el) !== reg) continue;
      // Plain [tabindex] wrappers around real controls would be double stops.
      if (!el.matches(GROUP) && !el.matches('a, button, [role]') && el.querySelector('a[href], button')) continue;
      if (el.closest('[class*="_arrowsCont"]')) continue; // carousel ‹ › (←/→ on cards scroll it)
      if (!el.matches(GROUP) && !el.textContent.trim() && !el.getAttribute("aria-label") && !el.title) continue;
      const r = el.getBoundingClientRect();
      if (r.width < 4 || r.height < 4) continue;
      if (!el.checkVisibility({ opacityProperty: true, visibilityProperty: true })) continue;
      if (region(el) === "main" && inOverlay(el)) continue;
      out.push({ el, r });
    }
    return out;
  };

  // What actually receives DOM focus for a stop.
  const area = (e) => { const r = e.getBoundingClientRect(); return r.width * r.height; };
  const focusTarget = (el) => {
    if (!el.matches(CARD)) return el;
    if (el.matches("a[href]")) return el;
    const links = [...el.querySelectorAll("a[href]")];
    return el.querySelector('a[data-test="cell-cover"]') ?? links.sort((a, b) => area(b) - area(a))[0] ?? el;
  };
  const stopOf = (node) => {
    let g = node?.closest?.(GROUP);
    for (let up = g?.parentElement?.closest(GROUP); up; up = up.parentElement?.closest(GROUP)) g = up;
    return g ?? node;
  };

  const scroller = () => document.getElementById("main");

  // Starting rectangle when nothing is focused: an edge of the main viewport.
  const virtualStart = (dir) => {
    const m = scroller()?.getBoundingClientRect() ?? { left: 0, right: innerWidth, top: 0, bottom: innerHeight };
    const top = dir === "Up" ? m.bottom : m.top;
    const left = dir === "Left" ? m.right : m.left;
    if (dir === "Up" || dir === "Down") return { left: m.left, right: m.right, top, bottom: top, width: m.right - m.left, height: 0 };
    return { left, right: left, top: m.top, bottom: m.bottom, width: 0, height: m.bottom - m.top };
  };

  const pick = (from, dir, list, self) => {
    let best = null, bestScore = Infinity;
    const cx = (r) => r.left + r.width / 2, cy = (r) => r.top + r.height / 2;
    for (const c of list) {
      if (c.el === self || (self && (self.contains(c.el) || c.el.contains(self)))) continue;
      const r = c.r;
      let main, cross;
      if (dir === "Down" || dir === "Up") {
        main = dir === "Down" ? r.top - from.bottom : from.top - r.bottom;
        if ((dir === "Down" ? cy(r) <= cy(from) : cy(r) >= cy(from))) continue;
        const overlap = Math.min(r.right, from.right) - Math.max(r.left, from.left);
        cross = overlap > 0 ? 0 : Math.abs(cx(r) - cx(from));
      } else {
        main = dir === "Right" ? r.left - from.right : from.left - r.right;
        if ((dir === "Right" ? cx(r) <= cx(from) : cx(r) >= cx(from))) continue;
        const overlap = Math.min(r.bottom, from.bottom) - Math.max(r.top, from.top);
        if (overlap <= 0) continue; // ←/→ stay on the same visual line
        cross = 0;
      }
      if (main < -8) continue; // must actually lie in that direction
      const score = Math.max(main, 0) + cross * 3;
      if (score < bestScore) { bestScore = score; best = c; }
    }
    return best;
  };

  let current = null;
  const setCurrent = (el) => {
    current?.classList.remove("tnav-focus");
    current = el;
    if (!el) return;
    el.classList.add("tnav-focus");
    focusTarget(el).focus({ preventScroll: true, focusVisible: true });
    el.scrollIntoView({ block: "nearest", inline: "nearest", behavior: "instant" });
    // #main runs under the player bar: keep the item above it.
    const m = scroller();
    const footer = document.querySelector('[data-test="footer-player"]');
    if (m?.contains(el) && footer?.checkVisibility()) {
      const limit = footer.getBoundingClientRect().top - 24;
      const r = el.getBoundingClientRect();
      if (r.bottom > limit) {
        m.scrollTop += r.bottom - limit;
        // Already at the very end: give the page some room under the last row.
        const still = el.getBoundingClientRect().bottom - limit;
        if (still > 1) {
          m.style.paddingBottom = (parseFloat(getComputedStyle(m).paddingBottom) || 0) + still + "px";
          m.scrollTop += still;
        }
      }
    }
  };
  const clear = () => { current?.classList.remove("tnav-focus"); current = null; };
  // Mouse use hands control back to the pointer.
  window.addEventListener("pointerdown", clear, true);
  window.__tnavClear = clear;

  const blocked = (t, key) => {
    if (t?.closest?.(SKIP)) return true;
    // Focus inside a popup (context menu, dropdown, dialog): TIDAL handles arrows there.
    const pop = t?.closest?.('[role="menu"], [role="listbox"], [role="dialog"]');
    if (pop && !pop.closest("#sidebar, nav")) return true;
    if ((key === "ArrowLeft" || key === "ArrowRight") && t?.closest?.('[role="slider"], [class*="progressBar"]')) return true;
    return false;
  };

  // Ctrl+↑/↓: jump to the first/last track of the list. Long playlists render rows
  // lazily, so keep jumping to the edge until no new rows show up.
  let jumpId = 0;
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const tableOf = () => {
    const fromCurrent = current?.matches(ROW) ? current.closest('[role="table"], [role="grid"]') : null;
    if (fromCurrent?.isConnected) return fromCurrent;
    const row = [...document.querySelectorAll("#main " + ROW)].find((r) => r.checkVisibility());
    return row ? row.closest('[role="table"], [role="grid"]') ?? row.parentElement : null;
  };
  const jump = async (toEnd) => {
    const id = ++jumpId;
    const m = scroller();
    let table = tableOf();
    if (!m || !table) return;
    const rowsOf = (tb) => [...(tb?.querySelectorAll(ROW) ?? [])].filter((r) => r.checkVisibility());
    const total = +table.getAttribute("aria-rowcount") || 0;
    if (!toEnd) {
      const tr = table.getBoundingClientRect(), mr = m.getBoundingClientRect();
      m.scrollTop += tr.top - mr.top - 200;
      await sleep(60);
    } else if (total > rowsOf(table).length + 1) {
      // Long playlist: TIDAL appends ~20 rows each time the page hits bottom,
      // so keep hitting bottom until the table stops growing.
      let lastH = -1, idle = 0;
      for (let i = 0; i < 400 && id === jumpId; i++) {
        if (!table.isConnected) table = tableOf();
        if (!table) return;
        m.scrollTop = m.scrollHeight;
        await sleep(80);
        const lastNum = rowsOf(table).at(-1)?.querySelector('[role="cell"]')?.textContent.trim();
        if (lastNum === String(total)) break; // reached the real last track
        const h = Math.round(table.getBoundingClientRect().height);
        if (h === lastH) { if (++idle >= 10) break; } else idle = 0;
        lastH = h;
      }
    }
    if (id !== jumpId) return;
    if (!table?.isConnected) table = tableOf();
    const rows = rowsOf(table);
    const edge = toEnd ? rows.at(-1) : rows[0];
    if (edge) setCurrent(edge);
  };

  const onKey = (e) => {
    if (e.isComposing) return;
    const t = document.activeElement;
    if (e.ctrlKey && !e.altKey && !e.metaKey && !e.shiftKey && (e.key === "ArrowUp" || e.key === "ArrowDown")) {
      if (blocked(t, e.key) || !tableOf()) return; // no track list: Ctrl+↑/↓ stays volume
      e.preventDefault();
      e.stopImmediatePropagation();
      jump(e.key === "ArrowDown");
      return;
    }
    if (e.ctrlKey || e.altKey || e.metaKey || e.shiftKey) return;
    jumpId++; // any plain navigation cancels a running jump
    if (e.key === "Escape" && current) { clear(); t?.blur?.(); return; }
    if (e.key === "Enter" && current && stopOf(t) === current && current.matches(ROW)) {
      const play = current.querySelector('[data-test="play-button"]');
      if (play) { e.preventDefault(); e.stopPropagation(); play.click(); }
      return;
    }
    const dir = { ArrowUp: "Up", ArrowDown: "Down", ArrowLeft: "Left", ArrowRight: "Right" }[e.key];
    if (!dir || blocked(t, e.key)) return;

    e.preventDefault();
    e.stopPropagation();

    // Re-sync if focus moved elsewhere (Tab, clicks, TIDAL re-rendering the node).
    if (current && (!current.isConnected || stopOf(t) !== current)) clear();
    let fromEl = current;
    if (!fromEl && t && t !== document.body) {
      const s = stopOf(t);
      if (s.matches(FOCUSABLE + ", " + CARD)) fromEl = s;
    }
    const reg = fromEl ? region(fromEl) : "main";
    const fromRect = fromEl ? fromEl.getBoundingClientRect() : virtualStart(dir);
    let next = pick(fromRect, dir, candidates(reg), fromEl);
    // Hop between sidebar and content with ←/→ when nothing is left in this region.
    if (!next && (dir === "Left" || dir === "Right")) {
      const other = reg === "main" && dir === "Left" ? "side" : reg === "side" && dir === "Right" ? "main" : null;
      if (other) {
        const list = candidates(other).filter((c) => c.r.bottom > 0 && c.r.top < innerHeight);
        next = pick({ ...fromRect.toJSON?.() ?? fromRect, left: fromRect.left, right: fromRect.right }, dir, list, fromEl)
          ?? list.sort((x, y) => Math.abs(x.r.top - fromRect.top) - Math.abs(y.r.top - fromRect.top))[0];
      }
    }

    const m = reg === "main" ? scroller() : null;
    if (m && (dir === "Up" || dir === "Down")) {
      const step = Math.round(m.clientHeight * 0.6);
      const mr = m.getBoundingClientRect();
      // Next stop is far off-screen (long text/art without buttons): just scroll a page.
      const far = next && (dir === "Down" ? next.r.top > mr.bottom + step : next.r.bottom < mr.top - step);
      if (!next || far) {
        if (dir === "Up" && m.scrollTop === 0 && !next) return;
        m.scrollBy({ top: dir === "Down" ? step : -step, behavior: "smooth" });
        return;
      }
    }
    if (next) setCurrent(next.el);
  };

  window.__tnav = onKey;
  window.addEventListener("keydown", onKey, true);
})();
