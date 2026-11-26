// Volume sync for tidal-hifi (loaded by the userscripts patch in app.asar).
// tidal-hifi applies volume coming from MPRIS / its web API / its hotkeys straight to the
// <audio>/<video> element, behind TIDAL's back: TIDAL's slider doesn't move and TIDAL puts
// its own value back on the next track. This pushes those outside changes into TIDAL's
// Redux store (playbackControls/SET_VOLUME, 0-100) so TIDAL itself applies them.
// Used by the waybar music module (mouse wheel -> playerctl volume).
(() => {
  if (window.__volSync) document.removeEventListener("volumechange", window.__volSync, true);

  let store = null;
  // same lookup as tidal-hifi's ReduxController: walk React fibers up to the <Provider store>
  const findStore = () => {
    for (const el of document.body.querySelectorAll("*")) {
      const key = Object.keys(el).find((k) => k.startsWith("__reactFiber"));
      for (let f = key && el[key]; f; f = f.return) {
        const s = f.memoizedProps?.store;
        if (s?.dispatch && s.getState) return s;
      }
    }
    return null;
  };
  const reduxVolume = () => {
    try {
      const v = store?.getState()?.playbackControls?.volume;
      return typeof v === "number" && Number.isFinite(v) ? v : null;
    } catch {
      return null;
    }
  };
  // the element tidal-hifi talks to (its getActivePlayer): the one playing, else any loaded one
  const activePlayer = () => {
    const all = [...document.querySelectorAll("video, audio")];
    const loaded = (p) => Number.isFinite(p.duration) && p.duration > 0;
    return all.find((p) => !p.paused && loaded(p)) ?? all.find(loaded) ?? null;
  };

  window.__volSync = (e) => {
    const el = e.target;
    if (!(el instanceof HTMLMediaElement) || el !== activePlayer()) return;
    if (!store) store = findStore();
    const cur = reduxVolume();
    if (cur === null) return;
    const want = Math.round(el.volume * 100);
    const diff = Math.abs(want - cur);
    // TIDAL's own changes already match (the event is queued after its handler updated both).
    // Never follow a big jump: outside steps are small, and a stray 100 % would blast.
    if (diff < 1 || diff > 25) return;
    store.dispatch({ type: "playbackControls/SET_VOLUME", payload: { volume: want } });
  };
  document.addEventListener("volumechange", window.__volSync, true);
})();
