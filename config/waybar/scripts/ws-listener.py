#!/usr/bin/env python3
# Escucha eventos de Hyprland, guarda el estado de los workspaces y avisa a waybar (RTMIN+8)
import json, os, signal, socket, subprocess

STATE = os.path.join(os.environ.get("XDG_RUNTIME_DIR", "/tmp"), "waybar-ws.json")
SOCK = os.path.join(os.environ["XDG_RUNTIME_DIR"], "hypr",
                    os.environ["HYPRLAND_INSTANCE_SIGNATURE"], ".socket2.sock")
EVENTS = ("workspace", "focusedmon", "createworkspace", "destroyworkspace",
          "moveworkspace", "openwindow", "closewindow", "movewindow", "urgent",
          "activespecial", "activespecialv2")

def hyprctl(what):
    return json.loads(subprocess.run(["hyprctl", "-j", what], capture_output=True, text=True).stdout)

URGENT = set()  # workspaces con una ventana urgente, hasta que se enfocan

def mark_urgent(addr):
    addr = addr if addr.startswith("0x") else "0x" + addr
    for c in hyprctl("clients"):
        if c.get("address") == addr:
            URGENT.add(c["workspace"]["id"])

def update():
    mons, wss = hyprctl("monitors"), hyprctl("workspaces")
    active = {m["activeWorkspace"]["id"] for m in mons}
    focused = next((m["activeWorkspace"]["id"] for m in mons if m["focused"]), None)
    URGENT.discard(focused)
    occupied = {w["id"] for w in wss if w["windows"] > 0}
    state = {}
    for i in range(1, 11):
        cls = ["focused"] if i == focused else ["active"] if i in active else []
        cls.append("occupied" if i in occupied else "empty")
        if i in URGENT:
            cls.append("urgent")
        state[str(i)] = cls
    # workspace especial visible en cada monitor (indicador 特 de waybar)
    state["special"] = {m["name"]: bool(m.get("specialWorkspace", {}).get("name"))
                        for m in mons}
    tmp = STATE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(state, f)
    os.replace(tmp, STATE)
    subprocess.run(["pkill", "-RTMIN+8", "-x", "waybar"])

signal.signal(signal.SIGTERM, lambda *_: os._exit(0))
update()
s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
s.connect(SOCK)
buf = b""
while True:
    data = s.recv(4096)
    if not data:
        break
    buf += data
    *lines, buf = buf.split(b"\n")
    hit = False
    for l in lines:
        ev, _, arg = l.decode(errors="ignore").partition(">>")
        if ev == "urgent":
            mark_urgent(arg.strip())
        hit = hit or ev in EVENTS
    if hit:
        update()
