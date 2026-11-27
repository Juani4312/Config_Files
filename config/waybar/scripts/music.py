#!/usr/bin/env python3
"""Módulo de música para waybar: SOLO tidal-hifi y DeaDBeeF (MPRIS).

Escucha los reproductores con libplayerctl (GObject) e ignora todo lo demás
(navegadores, zapzap, el `chromium.instanceN` que expone Electron, etc.).

- stdout: JSON del módulo custom/music: solo el ícono 󰝚 (clase tidal/deadbeef
  + playing/paused); el detalle está en el mini menú (music-popup.py).
- $XDG_RUNTIME_DIR/waybar-music/state: reproductor activo, estado y clase;
  lo leen el mini menú y los controles (music-ctl.sh).

Uso: music.py [SALIDA]  (ej. DP-3). Corre una instancia por barra; todas ven
los mismos eventos y eligen igual. Con SALIDA, la clase `open` (ícono
resaltado, sin tooltip) solo aparece si el menú está abierto en ese monitor.

Reproductor activo: el último que empezó a sonar. Si se cierra (o se detiene)
pasa al otro. Click del medio en el ícono o 󰓡 en el menú (SIGUSR1 a todas
las instancias, music-ctl.sh cycle) alterna a mano.
"""
import json
import os
import signal
import sys
import time
from urllib.parse import unquote, urlparse

import gi

gi.require_version("Playerctl", "2.0")
from gi.repository import Gio, GLib, Playerctl  # noqa: E402

import music_stream  # noqa: E402  (volumen del stream de la app en PipeWire)

try:                                    # PyGObject >= 3.52
    gi.require_version("GLibUnix", "2.0")
    from gi.repository import GLibUnix  # noqa: E402
    unix_signal_add = GLibUnix.signal_add
except (ImportError, ValueError):
    unix_signal_add = GLib.unix_signal_add

# nombre MPRIS en minúscula -> (etiqueta, clase css)
SOURCES = {
    "tidal-hifi": ("TIDAL", "tidal"),
    "deadbeef": ("DeaDBeeF", "deadbeef"),   # archivos locales
}
ICON = "\U000f075a"   # 󰝚

RUN = os.path.join(os.environ.get("XDG_RUNTIME_DIR", "/tmp"), "waybar-music")
STATE = os.path.join(RUN, "state")
POPUP_PID = os.path.join(RUN, "popup.pid")   # "pid\nmonitor\n"
MY_OUTPUT = sys.argv[1] if len(sys.argv) > 1 else None

PS = Playerctl.PlaybackStatus
STATUS = {PS.PLAYING: "Playing", PS.PAUSED: "Paused", PS.STOPPED: "Stopped"}

manager = Playerctl.PlayerManager()
players = {}          # instance -> Player
started = {}          # instance -> monotonic() de la última vez que arrancó
active = None
last_out = None
last_state = None
loop = GLib.MainLoop()


def esc(s):
    return GLib.markup_escape_text(s or "")


def status_of(p):
    try:
        return STATUS.get(p.props.playback_status, "Stopped")
    except Exception:
        return "Stopped"


stream_vol = {}       # clase -> % del stream en PipeWire (falta si no suena)


def on_stream_vols(vols):
    """music_stream.Watcher: cambió el volumen de algún stream (rueda,
    pavucontrol) o apareció / se cerró uno."""
    global stream_vol
    stream_vol = vols
    render()


def source(p):
    return SOURCES[p.props.player_name.lower()]


def meta(p):
    try:
        return p.props.metadata.unpack() if p.props.metadata else {}
    except Exception:
        return {}


def track_info(p):
    m = meta(p)
    title = m.get("xesam:title") or ""
    artist = m.get("xesam:artist") or ""
    if isinstance(artist, (list, tuple)):
        artist = ", ".join(a for a in artist if a)
    album = m.get("xesam:album") or ""
    if not title and m.get("xesam:url"):          # archivo sin tags
        title = os.path.basename(unquote(urlparse(m["xesam:url"]).path))
    return title, artist, album, m.get("mpris:length")


def pick_fallback(exclude=None):
    """Otro reproductor: primero el que suena, si no uno pausado con tema."""
    cands = [i for i in players if i != exclude]
    playing = [i for i in cands if status_of(players[i]) == "Playing"]
    if playing:
        return max(playing, key=lambda i: started.get(i, 0))
    paused = [i for i in cands
              if status_of(players[i]) == "Paused" and track_info(players[i])[0]]
    if paused:
        return max(paused, key=lambda i: started.get(i, 0))
    return cands[0] if cands else None


def write_state(inst, status, cls):
    global last_state
    st = (inst or "", status or "", cls or "")
    if st == last_state:
        return
    last_state = st
    os.makedirs(RUN, exist_ok=True)
    tmp = f"{STATE}.{os.getpid()}.tmp"   # varias instancias escriben a la vez
    with open(tmp, "w") as f:
        f.write("\n".join(st) + "\n")
    os.replace(tmp, STATE)


def emit(text, tooltip, classes):
    global last_out
    out = json.dumps({"text": text, "tooltip": tooltip, "class": classes},
                     ensure_ascii=False)
    if out != last_out:
        sys.stdout.write(out + "\n")
        sys.stdout.flush()
        last_out = out


def popup_open():
    """¿Está abierto el mini menú en el monitor de esta barra?"""
    try:
        with open(POPUP_PID) as f:
            lines = f.read().split("\n")
        pid, mon = int(lines[0]), (lines[1] if len(lines) > 1 else "")
        with open(f"/proc/{pid}/cmdline", "rb") as f:
            alive = b"music-popup" in f.read()
    except (OSError, ValueError):
        return False
    return alive and (MY_OUTPUT is None or not mon or mon == MY_OUTPUT)


def on_run_dir(_mon, f, other, _event):
    names = {x.get_basename() for x in (f, other) if x is not None}
    if "popup.pid" in names:
        render()


def render():
    p = players.get(active)
    if p is None:
        write_state(None, None, None)
        emit("", "", ["none"])
        return
    label, cls = source(p)
    status = status_of(p)
    title, artist, _album, _length = track_info(p)
    song = title + (f" · {artist}" if artist and title else artist)
    state = {"Playing": "", "Paused": "  (paused)"}.get(status, "  (stopped)")
    vol = stream_vol.get(cls)
    vol = f" · \U000f057e {vol}%" if vol is not None else ""      # 󰕾
    tip = (f"<b>{esc(song)}</b>{state}\n" if song else "") + \
        f"<span alpha='55%' size='small'>{label}{vol} · Click: controls · Scroll: volume</span>"
    write_state(active, status, cls)
    classes = [cls, status.lower()]
    if popup_open():        # sin tooltip: taparía el menú; ícono resaltado
        tip = ""
        classes.append("open")
    emit(ICON, tip, classes)


# ---- eventos ---------------------------------------------------------------
def on_status(p, st, *_):
    global active
    inst = p.props.player_instance
    if st == PS.PLAYING:
        started[inst] = time.monotonic()
        active = inst
    elif inst == active and st == PS.STOPPED:
        other = pick_fallback(exclude=inst)
        if other and status_of(players[other]) != "Stopped":
            active = other
    render()


def on_change(p, *_):
    if p.props.player_instance == active:
        render()


def add_player(name):
    global active
    if name.name.lower() not in SOURCES or name.instance in players:
        return
    p = Playerctl.Player.new_from_name(name)
    p.connect("playback-status", on_status)
    p.connect("metadata", on_change)
    p.connect("seeked", on_change)
    manager.manage_player(p)
    players[name.instance] = p
    if status_of(p) == "Playing":
        started[name.instance] = time.monotonic()
        if active is None or status_of(players[active]) != "Playing":
            active = name.instance
    elif active is None:
        active = name.instance
    render()


def on_vanished(_mgr, p):
    global active
    inst = p.props.player_instance
    if players.pop(inst, None) is None:
        return
    started.pop(inst, None)
    if inst == active:
        active = pick_fallback()
    render()


def cycle():
    """SIGUSR1 (click derecho): pasa al otro reproductor."""
    global active
    names = sorted(players)
    if len(names) > 1:
        i = names.index(active) if active in names else -1
        active = names[(i + 1) % len(names)]
        render()
    return True


def tick():
    if os.getppid() == 1:          # waybar murió
        loop.quit()
        return False
    return True


def main():
    signal.signal(signal.SIGPIPE, signal.SIG_DFL)
    os.makedirs(RUN, exist_ok=True)
    mon = Gio.File.new_for_path(RUN).monitor_directory(Gio.FileMonitorFlags.WATCH_MOVES, None)
    mon.connect("changed", on_run_dir)
    main.mon = mon          # que no lo junte el GC
    unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGUSR1, cycle)
    unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGTERM, loop.quit)
    unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGINT, loop.quit)
    manager.connect("name-appeared", lambda _m, name: add_player(name))
    manager.connect("player-vanished", on_vanished)
    for name in manager.props.player_names:
        add_player(name)
    render()
    GLib.timeout_add_seconds(5, tick)
    watcher = music_stream.Watcher(on_stream_vols)
    try:
        loop.run()
    finally:
        watcher.stop()


if __name__ == "__main__":
    main()
