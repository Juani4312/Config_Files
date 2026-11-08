#!/usr/bin/env python3
"""
autoscroll-indicator.py - small click-through bubble next to the pointer while
autoscroll.py is active. Listens on $XDG_RUNTIME_DIR/autoscroll.sock (datagram):
  "start"        show at the current pointer position
  "v <float>"    signed speed (notches/s, + = scrolling down)
  "stop"         fade out
Colors come from the matugen palette and are re-read on every show.
"""
import ctypes
ctypes.CDLL("libgtk4-layer-shell.so")       # must load before libwayland-client

import json
import math
import os
import re
import socket
import sys
import time

import cairo
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
gi.require_version("Gtk4LayerShell", "1.0")
from gi.repository import Gdk, GLib, Gtk, Gtk4LayerShell as LS

SOCK = os.path.join(os.environ.get("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}"), "autoscroll.sock")
COLORS_JSON = os.path.expanduser("~/.config/hypr/scripts/cursor/colors.json")
COLORS_LUA = os.path.expanduser("~/.config/hypr/colors.lua")

SIZE = 34            # surface size (logical px)
RADIUS = 12.5        # bubble radius
OFFSET = (22, 26)    # bubble center relative to the pointer hotspot
FADE_IN = 0.14
FADE_OUT = 0.16
FULL_SPEED = 25.0    # notches/s at which the chevron is fully lit


def hex2rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))


def load_palette():
    c = {}
    try:
        with open(COLORS_JSON) as f:
            c = json.load(f)
    except (OSError, ValueError):
        try:
            with open(COLORS_LUA) as f:
                for n, v in re.findall(r'(\w+)\s*=\s*"rgba\(([0-9a-fA-F]{6})', f.read()):
                    c[n] = "#" + v
        except OSError:
            pass
    g = lambda k, d: hex2rgb(c.get(k, d))
    return {
        "bg": g("surface_container_high", "#322826"),
        "rim": g("outline_variant", "#534341"),
        "dim": g("on_surface_variant", "#d8c2be"),
        "acc": g("primary", "#ffb4a9"),
    }


def hypr(cmd):
    sig = os.environ.get("HYPRLAND_INSTANCE_SIGNATURE")
    path = os.path.join(os.environ.get("XDG_RUNTIME_DIR", ""), "hypr", sig or "", ".socket.sock")
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.settimeout(0.3)
    s.connect(path)
    s.sendall(cmd.encode())
    out = b""
    while True:
        chunk = s.recv(65536)
        if not chunk:
            break
        out += chunk
    s.close()
    return json.loads(out)


def ease(t):
    return 1 - (1 - t) ** 3


class Indicator:
    def __init__(self, app):
        self.app = app
        self.pal = load_palette()
        self.state = "hidden"     # hidden | in | shown | out
        self.t0 = 0.0
        self.alpha = 0.0
        self.speed = 0.0          # smoothed
        self.target = 0.0
        self.monitor = None

        w = self.win = Gtk.Window(application=app)
        w.set_decorated(False)
        w.set_default_size(SIZE, SIZE)
        w.add_css_class("autoscroll-indicator")
        LS.init_for_window(w)
        LS.set_namespace(w, "autoscroll-indicator")
        LS.set_layer(w, LS.Layer.OVERLAY)
        LS.set_keyboard_mode(w, LS.KeyboardMode.NONE)
        LS.set_exclusive_zone(w, -1)
        LS.set_anchor(w, LS.Edge.TOP, True)
        LS.set_anchor(w, LS.Edge.LEFT, True)

        self.area = Gtk.DrawingArea()
        self.area.set_content_width(SIZE)
        self.area.set_content_height(SIZE)
        self.area.set_draw_func(self.draw)
        w.set_child(self.area)
        w.connect("map", self.on_map)

        css = Gtk.CssProvider()
        css.load_from_string("window.autoscroll-indicator, window.autoscroll-indicator.background, "
                             "window.autoscroll-indicator > * { background: none; box-shadow: none; border: none; }")
        Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(), css,
                                                  Gtk.STYLE_PROVIDER_PRIORITY_USER + 10)
        self.area.add_tick_callback(self.on_tick)

    # ----------------------------------------------------------- window ---
    def on_map(self, *_):
        surf = self.win.get_surface()
        if surf:
            surf.set_input_region(cairo.Region())     # fully click-through

    def gdk_monitor(self, name):
        mons = Gdk.Display.get_default().get_monitors()
        for i in range(mons.get_n_items()):
            m = mons.get_item(i)
            if m.get_connector() == name:
                return m
        return None

    def place(self):
        pos = hypr("j/cursorpos")
        x, y = pos["x"], pos["y"]
        mon = None
        for m in hypr("j/monitors"):
            w, h = m["width"] / m["scale"], m["height"] / m["scale"]
            if m["x"] <= x < m["x"] + w and m["y"] <= y < m["y"] + h:
                mon = m
                break
        if not mon:
            return
        gm = self.gdk_monitor(mon["name"])
        if gm is not None and gm != self.monitor:
            if self.win.get_visible():
                self.win.set_visible(False)
            LS.set_monitor(self.win, gm)
            self.monitor = gm
        lx = int(x - mon["x"] + OFFSET[0] - SIZE / 2)
        ly = int(y - mon["y"] + OFFSET[1] - SIZE / 2)
        LS.set_margin(self.win, LS.Edge.LEFT, max(0, lx))
        LS.set_margin(self.win, LS.Edge.TOP, max(0, ly))

    # ---------------------------------------------------------- control ---
    def start(self):
        self.pal = load_palette()
        self.speed = self.target = 0.0
        try:
            self.place()
        except (OSError, ValueError, KeyError):
            pass
        self.state, self.t0 = "in", time.monotonic()
        self.alpha = 0.0
        self.win.set_visible(True)
        self.area.queue_draw()

    def stop(self):
        if self.state in ("in", "shown"):
            self.state, self.t0 = "out", time.monotonic()
            self.out_from = self.alpha

    def set_speed(self, v):
        self.target = v

    def on_tick(self, *_):
        now = time.monotonic()
        if self.state == "in":
            t = min(1.0, (now - self.t0) / FADE_IN)
            self.alpha = ease(t)
            if t >= 1:
                self.state = "shown"
        elif self.state == "out":
            t = min(1.0, (now - self.t0) / FADE_OUT)
            self.alpha = self.out_from * (1 - ease(t))
            if t >= 1:
                self.state = "hidden"
                self.alpha = 0.0
                self.win.set_visible(False)
        self.speed += (self.target - self.speed) * 0.25
        if self.state != "hidden":
            self.area.queue_draw()
        return GLib.SOURCE_CONTINUE

    # ------------------------------------------------------------- draw ---
    def draw(self, area, cr, w, h):
        a = self.alpha
        if a <= 0.001:
            return
        p = self.pal
        cx, cy = w / 2, h / 2
        r = RADIUS * (0.82 + 0.18 * a)

        # soft shadow
        for i, (grow, al) in enumerate(((2.5, 0.10), (1.3, 0.16))):
            cr.arc(cx, cy + 1, r + grow, 0, 2 * math.pi)
            cr.set_source_rgba(0, 0, 0, al * a)
            cr.fill()
        # body
        cr.arc(cx, cy, r, 0, 2 * math.pi)
        cr.set_source_rgba(*p["bg"], 0.92 * a)
        cr.fill_preserve()
        cr.set_line_width(1.0)
        cr.set_source_rgba(*p["rim"], 0.9 * a)
        cr.stroke()

        s = self.speed
        k = min(1.0, abs(s) / FULL_SPEED)
        down = s > 0
        # center dot
        cr.arc(cx, cy, 1.6, 0, 2 * math.pi)
        cr.set_source_rgba(*p["dim"], 0.55 * a)
        cr.fill()
        # chevrons
        cr.set_line_width(1.8)
        cr.set_line_cap(cairo.LINE_CAP_ROUND)
        cr.set_line_join(cairo.LINE_JOIN_ROUND)
        for d in (-1, 1):                       # -1 up, +1 down
            active = abs(s) > 0.05 and ((d > 0) == down)
            push = 1.6 * k if active else 0.0
            yb = cy + d * (5.2 + push)
            cr.move_to(cx - 3.6, yb - d * 2.4)
            cr.line_to(cx, yb + d * 0.9)
            cr.line_to(cx + 3.6, yb - d * 2.4)
            if active:
                mix = 0.35 + 0.65 * k
                col = tuple(p["dim"][i] * (1 - mix) + p["acc"][i] * mix for i in range(3))
                cr.set_source_rgba(*col, a)
            else:
                cr.set_source_rgba(*p["dim"], (0.75 - 0.4 * k) * a)
            cr.stroke()


class App(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="local.autoscroll.indicator")
        self.ind = None

    def do_activate(self):
        if self.ind:
            return
        self.hold()
        self.ind = Indicator(self)
        try:
            os.unlink(SOCK)
        except FileNotFoundError:
            pass
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        self.sock.bind(SOCK)
        self.sock.setblocking(False)
        try:
            gi.require_version("GLibUnix", "2.0")
            from gi.repository import GLibUnix
            add = GLibUnix.fd_add_full
        except (ValueError, ImportError):
            add = GLib.unix_fd_add_full
        add(GLib.PRIORITY_HIGH, self.sock.fileno(), GLib.IOCondition.IN, self.on_msg)

    def on_msg(self, *_):
        while True:
            try:
                msg = self.sock.recv(64).decode(errors="ignore").strip()
            except BlockingIOError:
                break
            if msg == "start":
                self.ind.start()
            elif msg == "stop":
                self.ind.stop()
            elif msg.startswith("v "):
                try:
                    self.ind.set_speed(float(msg[2:]))
                except ValueError:
                    pass
        return GLib.SOURCE_CONTINUE


if __name__ == "__main__":
    sys.exit(App().run([]))
