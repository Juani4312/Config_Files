#!/usr/bin/env python3
"""Módulo de volumen para waybar (reemplaza a pulseaudio en group/audio).

El parlante NO es texto: el texto lleva un glifo invisible que reserva el lugar
(mismo layout que el módulo pulseaudio original) y el CSS dibuja el parlante
como background-image con los íconos simbólicos waybar-spk-{0,1,2}
(generados por gen-speaker-icons.py, pintados con el color del tema).
Así el CSS puede animar las ondas al pasar el mouse.

Clases: spk-0 / spk-1 / spk-2 (cuadro estático según volumen), muted,
headphone, bluetooth. Eventos: `pactl subscribe`.
"""
import ctypes
import json
import re
import signal
import subprocess
import sys
import threading

PLACEHOLDER = '<span alpha="1"></span>'   # reserva el ancho del parlante
HEADPHONE = ""
MUTED = "\U000f0581"
BT = "\U000f00b0"

wake = threading.Event()


def _pdeathsig():
    try:
        ctypes.CDLL("libc.so.6").prctl(1, signal.SIGTERM)
    except Exception:
        pass


def run(*cmd):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=3).stdout
    except Exception:
        return ""


def read_sink():
    name = run("pactl", "get-default-sink").strip()
    m = re.search(r"(\d+)%", run("pactl", "get-sink-volume", "@DEFAULT_SINK@"))
    vol = int(m.group(1)) if m else 0
    muted = "yes" in run("pactl", "get-sink-mute", "@DEFAULT_SINK@")
    desc, port = name, ""
    try:
        for s in json.loads(run("pactl", "-f", "json", "list", "sinks") or "[]"):
            if s.get("name") == name:
                desc = s.get("description", name)
                port = (s.get("active_port") or "").lower()
                break
    except ValueError:
        pass

    bt = name.startswith("bluez")
    classes = ["bluetooth"] if bt else []
    btxt = f"{BT} " if bt else ""
    if muted:
        text = MUTED
        classes.append("muted")
    elif "headphone" in port:
        text = f"{HEADPHONE} {btxt}{vol}%"
        classes.append("headphone")
    else:
        text = f"{PLACEHOLDER} {btxt}{vol}%"
        classes.append("spk-0" if vol <= 0 else "spk-1" if vol < 50 else "spk-2")
    tip = f"{desc} | {vol}%" + (" (mute)" if muted else "")
    return json.dumps({"text": text, "tooltip": tip, "class": classes})


def follow():
    while True:
        try:
            p = subprocess.Popen(["pactl", "subscribe"], stdout=subprocess.PIPE,
                                 stderr=subprocess.DEVNULL, text=True,
                                 preexec_fn=_pdeathsig)
            pat = re.compile(r"on (sink|server|card) #")
            for line in p.stdout:
                if pat.search(line):
                    wake.set()
            p.wait()
        except Exception:
            pass
        wake.set()
        threading.Event().wait(2)   # pipewire reiniciado: reintentar


def main():
    signal.signal(signal.SIGPIPE, signal.SIG_DFL)
    threading.Thread(target=follow, daemon=True).start()
    last = None
    while True:
        out = read_sink()
        if out != last:
            sys.stdout.write(out + "\n")
            sys.stdout.flush()
            last = out
        wake.wait(60)
        wake.clear()


if __name__ == "__main__":
    main()
