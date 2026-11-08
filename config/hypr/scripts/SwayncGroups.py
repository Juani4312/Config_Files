#!/usr/bin/env python3
# Salida para waybar como `swaync-client -swb`, pero contando grupos de
# notificaciones (por app, como el panel de swaync) en vez de individuales.
import json
import os
import subprocess
import threading

STATE = os.path.expanduser("~/.cache/swaync-groups.json")

groups = {}   # id de notificación -> clave de grupo
pending = {}  # (sender, cookie) de un Notify -> clave de grupo
count = dnd = cc_open = inhibited = False
ring = None          # "ring-a"/"ring-b" mientras la campana suena (CSS de waybar)
ring_timer = None
lock = threading.Lock()


def load_state():
    try:
        with open(STATE) as f:
            return {int(k): v for k, v in json.load(f).items()}
    except (OSError, ValueError):
        return {}


def save_state():
    try:
        with open(STATE, "w") as f:
            json.dump(groups, f)
    except OSError:
        pass


def emit():
    # Notificaciones que existían antes de empezar a escuchar: cuentan como un grupo
    unknown = count - len(groups)
    n = len(set(groups.values())) + (1 if unknown > 0 else 0)
    if count == 0:
        n = 0
    alt = ("dnd-" if dnd else "") + ("inhibited-" if inhibited else "")
    alt += "notification" if count else "none"
    out = {
        "text": str(n) if n else "",
        "alt": alt,
        "tooltip": f"{count} Notifications ({n} grupos)" if count else "No Notifications",
        "class": [alt, ring] if ring else alt,
    }
    with lock:
        print(json.dumps(out), flush=True)


def ring_bell():
    # Alterna ring-a/ring-b para que la animación CSS reinicie con cada notificación
    global ring, ring_timer
    ring = "ring-b" if ring == "ring-a" else "ring-a"
    emit()
    if ring_timer:
        ring_timer.cancel()
    ring_timer = threading.Timer(2.0, stop_ring)
    ring_timer.daemon = True
    ring_timer.start()


def stop_ring():
    global ring
    ring = None
    emit()


def initial_data():
    global dnd, cc_open, count, inhibited
    r = subprocess.run(
        ["busctl", "--user", "--json=short", "call", "org.erikreider.swaync.cc",
         "/org/erikreider/swaync/cc", "org.erikreider.swaync.cc", "GetSubscribeData"],
        capture_output=True, text=True,
    )
    try:
        dnd, cc_open, count, inhibited = json.loads(r.stdout)["data"][0]
    except (ValueError, KeyError, IndexError):
        pass


def group_key(app_name, hints):
    entry = hints.get("desktop-entry", {}).get("data")
    return (entry or app_name or "unknown").lower()


def main():
    global count, dnd, cc_open, inhibited, groups
    groups = load_state()
    initial_data()
    if count == 0:
        groups = {}
    emit()

    mon = subprocess.Popen(
        ["busctl", "--user", "monitor", "--json=short",
         "org.freedesktop.Notifications", "org.erikreider.swaync.cc"],
        stdout=subprocess.PIPE, text=True,
    )
    for line in mon.stdout:
        try:
            msg = json.loads(line)
        except ValueError:
            continue
        member = msg.get("member")
        data = msg.get("payload", {}).get("data", [])

        if msg["type"] == "method_call" and member == "Notify" \
                and msg.get("interface") == "org.freedesktop.Notifications":
            app_name, _, _, _, _, _, hints, _ = data
            if hints.get("transient", {}).get("data"):
                continue
            pending[(msg["sender"], msg["cookie"])] = group_key(app_name, hints)

        elif msg["type"] == "method_return":
            key = pending.pop((msg.get("destination"), msg.get("reply_cookie")), None)
            if key is not None and data:
                groups[data[0]] = key
                save_state()
                emit()

        elif msg["type"] == "signal" and member == "NotificationClosed":
            if groups.pop(data[0], None) is not None:
                save_state()
                emit()

        elif msg["type"] == "signal" and member == "SubscribeV2":
            prev = count
            count, dnd, cc_open, inhibited = data
            if count == 0 and groups:
                groups = {}
                save_state()
            if count > prev and not dnd and not cc_open:
                ring_bell()
            else:
                emit()


if __name__ == "__main__":
    main()
