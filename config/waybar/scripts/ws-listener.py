#!/usr/bin/env python3
# Escucha eventos de Hyprland, guarda el estado de los workspaces y avisa a waybar (RTMIN+8)
import json, os, signal, socket, subprocess, sys, time

STATE = os.path.join(os.environ.get("XDG_RUNTIME_DIR", "/tmp"), "waybar-ws.json")
SOCK = os.path.join(os.environ["XDG_RUNTIME_DIR"], "hypr",
                    os.environ["HYPRLAND_INSTANCE_SIGNATURE"], ".socket2.sock")
EVENTS = ("workspace", "focusedmon", "createworkspace", "destroyworkspace",
          "moveworkspace", "openwindow", "closewindow", "movewindow", "urgent",
          "activespecial", "activespecialv2")

def hyprctl(what):
    return json.loads(subprocess.run(["hyprctl", "-j", what], capture_output=True, text=True).stdout)

def ws_id(w):
    # Hyprland 0.57+ no incluye "id" en los workspaces especiales -> None
    return w.get("id") if isinstance(w, dict) else None

URGENT = set()  # workspaces con una ventana urgente, hasta que se enfocan

def mark_urgent(addr):
    addr = addr if addr.startswith("0x") else "0x" + addr
    for c in hyprctl("clients"):
        if c.get("address") == addr and ws_id(c.get("workspace")) is not None:
            URGENT.add(ws_id(c["workspace"]))

def update():
    mons, wss = hyprctl("monitors"), hyprctl("workspaces")
    active = {ws_id(m.get("activeWorkspace")) for m in mons}
    focused = next((ws_id(m.get("activeWorkspace")) for m in mons if m.get("focused")), None)
    URGENT.discard(focused)
    occupied = {ws_id(w) for w in wss if w.get("windows", 0) > 0}
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
    # cuál: "magic" (SUPER+S, burbuja 特 izquierda) / "claude" (SUPER+Z, 智 derecha)
    state["special_name"] = {m["name"]: (m.get("specialWorkspace", {}).get("name") or "")
                             .removeprefix("special:") for m in mons}
    tmp = f"{STATE}.{os.getpid()}.tmp"   # con varias barras corre un listener por barra
    with open(tmp, "w") as f:
        json.dump(state, f)
    os.replace(tmp, STATE)
    subprocess.run(["pkill", "-RTMIN+8", "-x", "waybar"])

def safe(fn, *a):
    # un error puntual (JSON vacío de hyprctl, formato nuevo...) no debe matar el
    # listener: si muere, waybar deja todos los workspaces congelados
    try:
        fn(*a)
        return True
    except Exception as e:
        print(f"ws-listener: {fn.__name__}: {e!r}", file=sys.stderr, flush=True)
        return False

def listen():
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.connect(SOCK)
    safe(update)  # resincroniza tras (re)conectar
    buf = b""
    while True:
        data = s.recv(4096)
        if not data:
            return
        buf += data
        *lines, buf = buf.split(b"\n")
        hit = False
        for l in lines:
            ev, _, arg = l.decode(errors="ignore").partition(">>")
            if ev == "urgent":
                safe(mark_urgent, arg.strip())
            hit = hit or ev in EVENTS
        if hit and not safe(update):
            time.sleep(0.2)  # reintento: hyprctl a veces responde vacío en transiciones
            safe(update)

signal.signal(signal.SIGTERM, lambda *_: os._exit(0))
while True:
    try:
        listen()
    except OSError as e:
        print(f"ws-listener: socket: {e!r}", file=sys.stderr, flush=True)
    time.sleep(1)
