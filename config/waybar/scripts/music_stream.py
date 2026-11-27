#!/usr/bin/env python3
"""Volumen de la APP del reproductor en PipeWire (su stream / sink-input, como
el mezclador de pavucontrol), NO el volumen interno del reproductor: el slider
de TIDAL (o de DeaDBeeF) queda independiente y nunca se toca.

Antes la rueda usaba el Volume de MPRIS, y para que TIDAL no lo pisara en el
tema siguiente un userscript (volume-sync.js) lo copiaba a TIDAL. Pero TIDAL
hace rampas de volumen en sus dos <audio> al cambiar de tema (crossfade,
volume=0 al soltar uno) y el userscript las copiaba también → TIDAL quedaba
en 0 (muteado) de vez en cuando al pasar de tema.

WirePlumber recuerda el volumen del stream por app, así que sobrevive a los
cambios de tema y a que Chromium cierre el stream en pausa (~12 s) y lo abra
de nuevo al seguir. Sin stream (en pausa larga / cerrado) no hay qué cambiar.

Uso (music-ctl.sh):  music_stream.py step tidal|deadbeef up|down
                     music_stream.py get  tidal|deadbeef
                     music_stream.py set  tidal|deadbeef PCT
Como módulo: volumes(), set_pct(), step_pct(), Watcher (pactl subscribe).
"""
import json
import math
import os
import subprocess
import sys

# clase de music.py -> nombres con los que aparece el stream
# (tidal-hifi: application.name/binary "tidal-hifi"; DeaDBeeF va por
#  pipewire-alsa: application.id "music.deadbeef.player", binary "deadbeef")
APPS = {"tidal": ("tidal-hifi",), "deadbeef": ("deadbeef",)}

RUN = os.path.join(os.environ.get("XDG_RUNTIME_DIR", "/tmp"), "waybar-music")


def _inputs():
    try:
        out = subprocess.run(["pactl", "-f", "json", "list", "sink-inputs"],
                             capture_output=True, text=True, timeout=3).stdout
        data = json.loads(out)
    except (OSError, subprocess.SubprocessError, ValueError):
        return []
    return data if isinstance(data, list) else []


def _cls_of(s):
    p = s.get("properties") or {}
    binary = os.path.basename(p.get("application.process.binary") or "").lower()
    name = (p.get("application.name") or "").lower()
    appid = (p.get("application.id") or "").lower()
    for cls, names in APPS.items():
        if binary in names or name in names or any(n in appid for n in names):
            return cls
    return None


def _pct(s):
    vals = [c.get("value") for c in (s.get("volume") or {}).values() if isinstance(c, dict)]
    vals = [v for v in vals if isinstance(v, (int, float))]
    return round(max(vals) / 65536 * 100) if vals else None


def streams():
    """{clase: [(índice, %), ...]} de los streams de cada reproductor."""
    out = {}
    for s in _inputs():
        cls = _cls_of(s)
        if cls and isinstance(s.get("index"), int):
            out.setdefault(cls, []).append((s["index"], _pct(s)))
    return out


def volumes(found=None):
    """{clase: %} (el stream más nuevo); falta la clase si no tiene stream."""
    found = streams() if found is None else found
    return {cls: max(lst)[1] for cls, lst in found.items() if lst}


def set_pct(cls, pct, ids=None):
    """Pone todos los streams del reproductor en pct %. Devuelve el % puesto,
    o None si no había stream."""
    pct = max(0, min(100, int(round(pct))))
    if ids is None:
        ids = [i for i, _v in streams().get(cls, [])]
    for i in ids:
        subprocess.run(["pactl", "set-sink-input-volume", str(i), f"{pct}%"],
                       capture_output=True, timeout=3)
    return pct if ids else None


def step_pct(cur, d):
    """Paso fino abajo: 1 % hasta 10, 2 % hasta 30, 5 % después, alineado a la
    grilla (de 13 sube a 14, de 31 baja a 30)."""
    x = cur + (1e-6 if d > 0 else -1e-6)
    s = 1 if x < 10 else 2 if x < 30 else 5
    n = (math.floor(x / s) + 1) * s if d > 0 else (math.ceil(x / s) - 1) * s
    return max(0, min(100, n))


def step(cls, d):
    import fcntl
    os.makedirs(RUN, exist_ok=True)
    # la rueda dispara varios a la vez: de a uno (pactl es sincrónico, así que
    # cada uno lee lo que dejó el anterior y la rueda rápida suma bien)
    with open(os.path.join(RUN, "volume.lock"), "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        lst = streams().get(cls, [])
        if not lst:
            return None
        cur = max(lst)[1]
        if cur is None:
            return None
        return set_pct(cls, step_pct(cur, d), [i for i, _v in lst])


class Watcher:
    """`pactl subscribe` dentro de un loop GLib: llama a callback(volumes)
    cuando cambia algo de los sink-inputs (con debounce). Se relanza si pactl
    muere (reinicio de PipeWire)."""

    def __init__(self, callback, delay_ms=80):
        from gi.repository import GLib
        self.GLib = GLib
        self.callback = callback
        self.delay = delay_ms
        self.proc = None
        self.timer = 0
        self.last = None
        self.found = {}
        self.start()
        self.poke()

    def start(self):
        GLib = self.GLib
        try:
            import ctypes
            import signal
            libc = ctypes.CDLL(None, use_errno=True)
            # que pactl muera con nosotros aunque nos maten con SIGKILL
            pre = lambda: libc.prctl(1, signal.SIGTERM)   # PR_SET_PDEATHSIG
            self.proc = subprocess.Popen(["pactl", "subscribe"], stdout=subprocess.PIPE,
                                         stderr=subprocess.DEVNULL, preexec_fn=pre)
        except OSError:
            GLib.timeout_add_seconds(5, self._restart)
            return
        os.set_blocking(self.proc.stdout.fileno(), False)
        self.buf = b""
        GLib.io_add_watch(self.proc.stdout.fileno(), GLib.PRIORITY_DEFAULT,
                          GLib.IO_IN | GLib.IO_HUP | GLib.IO_ERR, self._on_io)

    def _restart(self):
        self.start()
        self.poke()
        return False

    def _on_io(self, fd, cond):
        try:
            chunk = os.read(fd, 65536)
        except BlockingIOError:
            return True
        except OSError:
            chunk = b""
        if not chunk:                       # pactl terminó
            try:
                self.proc.wait(timeout=1)
            except Exception:
                pass
            self.proc = None
            self.GLib.timeout_add_seconds(2, self._restart)
            return False
        self.buf += chunk
        *lines, self.buf = self.buf.split(b"\n")
        if any(b"sink-input" in l for l in lines):
            self.poke()
        return True

    def poke(self):
        """Releer ya (con debounce)."""
        if not self.timer:
            self.timer = self.GLib.timeout_add(self.delay, self._fire)

    def _fire(self):
        self.timer = 0
        self.found = streams()
        vols = volumes(self.found)
        if vols != self.last:
            self.last = vols
            self.callback(vols)
        return False

    def ids(self, cls):
        return [i for i, _v in self.found.get(cls, [])]

    def stop(self):
        if self.proc is not None:
            try:
                self.proc.terminate()
            except OSError:
                pass
            self.proc = None


def main(argv):
    if len(argv) < 3 or argv[2] not in APPS:
        print("usage: music_stream.py get|set|step tidal|deadbeef [PCT|up|down]",
              file=sys.stderr)
        return 2
    cmd, cls = argv[1], argv[2]
    if cmd == "get":
        v = volumes().get(cls)
        if v is None:
            return 1
        print(v)
    elif cmd == "set" and len(argv) > 3:
        return 0 if set_pct(cls, float(argv[3])) is not None else 1
    elif cmd == "step" and len(argv) > 3 and argv[3] in ("up", "down"):
        return 0 if step(cls, 1 if argv[3] == "up" else -1) is not None else 1
    else:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
