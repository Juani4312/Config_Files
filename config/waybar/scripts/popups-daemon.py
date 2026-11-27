#!/usr/bin/env python3
# Daemon (lo lanza waybar, como ws-listener) para las ventanas que se abren desde la barra:
#  - al abrirse el centro de notificaciones (click o atajo) cierra los otros popups
#    (música, clima, rofi, wlogout) -> popups.sh close-except swaync
#  - lo cierra si el mouse se va del panel (+ la franja de la barra encima) 0.7 s.
#    Solo empieza a contar después de que el mouse estuvo adentro, así abrirlo con
#    el teclado con el mouse lejos no lo cierra solo. Click afuera ya lo cierra swaync
#    (layer-shell-cover-screen).
# El popup de música tiene su propio vigilante (music-popup.py, misma lógica).
import json, os, socket, subprocess, sys, threading, time

HERE = os.path.dirname(os.path.realpath(__file__))
SOCK = os.path.join(os.environ["XDG_RUNTIME_DIR"], "hypr",
                    os.environ["HYPRLAND_INSTANCE_SIGNATURE"], ".socket.sock")
SWAYNC_CFG = os.path.expanduser("~/.config/swaync/config.json")
AWAY_CLOSE = 0.7   # s fuera de la zona -> se cierra
PAD = 16           # margen alrededor del panel que cuenta como "adentro"
POLL = 0.15

lock = threading.Lock()
st = {"visible": False, "since": 0.0, "zone": None, "armed": False, "away": None}


def hypr(cmd):
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sk:
        sk.settimeout(1)
        sk.connect(SOCK)
        sk.sendall(f"j/{cmd}".encode())
        buf = b""
        while chunk := sk.recv(65536):
            buf += chunk
    return json.loads(buf)


def cc_size():
    try:
        c = json.load(open(SWAYNC_CFG))
    except Exception:
        c = {}
    return (c.get("control-center-width", 500), c.get("control-center-height", 600),
            c.get("control-center-margin-top", 0), c.get("control-center-margin-right", 0))


def find_zone():
    """Panel del centro de notificaciones en el monitor con foco (las capas de
    swaync cubren todos los monitores; el panel va arriba a la derecha)."""
    w, h, mtop, mright = cc_size()
    mon = next((m for m in hypr("monitors") if m.get("focused")), None)
    if mon is None:
        return None
    for lv in hypr("layers").values():
        for layer in lv.get("levels", {}).values():
            for l in layer:
                if l.get("namespace") != "swaync-control-center":
                    continue
                if not (mon["x"] <= l["x"] < mon["x"] + mon["width"]):
                    continue
                right = l["x"] + l["w"] - mright
                return (right - w - PAD, mon["y"],                 # hasta arriba: incluye la campana
                        right + PAD, l["y"] + mtop + h + PAD)
    return None


def on_visible(vis):
    with lock:
        if vis == st["visible"]:
            return
        st.update(visible=vis, since=time.monotonic(), zone=None, armed=False, away=None)
    if vis:
        subprocess.run([os.path.join(HERE, "popups.sh"), "close-except", "swaync"])


def swaync_watch():
    while True:
        try:
            p = subprocess.Popen(["swaync-client", "-s"], stdout=subprocess.PIPE,
                                 stderr=subprocess.DEVNULL, text=True)
            for line in p.stdout:
                try:
                    on_visible(bool(json.loads(line).get("visible")))
                except ValueError:
                    pass
        except Exception as e:
            print(f"popups-daemon: swaync: {e!r}", file=sys.stderr, flush=True)
        on_visible(False)
        time.sleep(1)          # swaync reiniciándose (Super+O): reintentar


def cursor_watch():
    while True:
        time.sleep(POLL)
        with lock:
            if not st["visible"]:
                continue
        try:
            zone = st["zone"]
            if zone is None or time.monotonic() - st["since"] < 1.0:   # el panel recién aparece
                zone = find_zone() or zone
            c = hypr("cursorpos")
        except Exception:
            continue
        with lock:
            if not st["visible"]:
                continue
            st["zone"] = zone
            if zone is None:
                continue
            x0, y0, x1, y1 = zone
            if x0 <= c["x"] <= x1 and y0 <= c["y"] <= y1:
                st["armed"], st["away"] = True, None
                continue
            if not st["armed"]:
                continue
            if st["away"] is None:
                st["away"] = time.monotonic()
                continue
            if time.monotonic() - st["away"] < AWAY_CLOSE:
                continue
            st["visible"] = False
        subprocess.run(["swaync-client", "-cp", "-sw"], stdout=subprocess.DEVNULL)


threading.Thread(target=swaync_watch, daemon=True).start()
cursor_watch()
