#!/usr/bin/env python3
"""Mini menú del módulo de música de waybar (click en el ícono 󰝚).

Popup GTK3 + layer-shell que aparece debajo del ícono: carátula, título,
artista, álbum, barra de progreso (click/arrastre = ir a ese punto),
anterior / pausa / siguiente, de qué reproductor viene (con botón para
alternar si están abiertos tidal-hifi y DeaDBeeF) y volumen del reproductor
(MPRIS, lo mismo que la rueda sobre el ícono: la rueda sobre el slider usa
music-ctl.sh volume, así los pasos son iguales).

Sigue al reproductor activo que elige music.py
($XDG_RUNTIME_DIR/waybar-music/state). Colores: los de matugen
(~/.config/waybar/colors.css), así cambia con el fondo de pantalla.

Se cierra cuando el mouse se aleja del popup (y del ícono) un momento, o con
otro click en el ícono (music-ctl.sh menu). No toma el foco del teclado:
Hyprland se lo da al abrir y se lo saca enseguida, así que en vez de
"perder el foco" se mira la posición del cursor por el socket de Hyprland.
"""
import hashlib
import json
import os
import signal
import socket
import subprocess
import threading
import time
import urllib.request
from urllib.parse import unquote, urlparse

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("GtkLayerShell", "0.1")
gi.require_version("Playerctl", "2.0")
from gi.repository import (Gdk, GdkPixbuf, Gio, GLib, Gtk,  # noqa: E402
                           GtkLayerShell, Playerctl)

try:                                    # PyGObject >= 3.52
    gi.require_version("GLibUnix", "2.0")
    from gi.repository import GLibUnix  # noqa: E402
    unix_signal_add = GLibUnix.signal_add
except (ImportError, ValueError):
    unix_signal_add = GLib.unix_signal_add

RUN = os.path.join(os.environ.get("XDG_RUNTIME_DIR", "/tmp"), "waybar-music")
STATE = os.path.join(RUN, "state")
PIDFILE = os.path.join(RUN, "popup.pid")
CLOSED = os.path.join(RUN, "popup.closed")
VOLFILE = os.path.join(RUN, "volume")      # "reproductor valor ms" (music-ctl.sh volume)
CTL = os.path.join(os.path.dirname(os.path.realpath(__file__)), "music-ctl.sh")
CACHE = os.path.join(os.environ.get("XDG_CACHE_HOME") or os.path.expanduser("~/.cache"),
                     "waybar-music")
COLORS = os.path.expanduser("~/.config/waybar/colors.css")

WIDTH = 340          # ancho del popup
ART = 84             # lado de la carátula
GAP = 6              # separación con la barra
AWAY_CLOSE_MS = 700  # mouse lejos del popup/ícono durante esto -> se cierra
ZONE_PAD = 16        # margen alrededor del popup que todavía cuenta como "adentro"
HYPR_SOCK = os.path.join(os.environ.get("XDG_RUNTIME_DIR", "/tmp"), "hypr",
                         os.environ.get("HYPRLAND_INSTANCE_SIGNATURE", ""), ".socket.sock")

ALLOWED = {"tidal-hifi", "deadbeef"}
SOURCES = {"tidal": "TIDAL", "deadbeef": "DeaDBeeF"}
I_MUSIC, I_DISK = "\U000f075a", "\U000f02ca"
I_PREV, I_NEXT = "\U000f04ae", "\U000f04ad"
I_PLAY, I_PAUSE = "\U000f040a", "\U000f03e4"
I_SWAP = "\U000f04e1"
# volumen: 0 / bajo / medio / alto  (󰝟 󰕿 󰖀 󰕾)
I_VOL = ("\U000f075f", "\U000f057f", "\U000f0580", "\U000f057e")
VOL_HOLD = 1.5       # s tras cambiarlo nosotros en que se ignora lo que reporta el
                     # reproductor (tidal tarda en reflejarlo y haría saltar el slider)

CSS = """
@import url("file://%(colors)s");
* {
    font-family: "JetBrainsMono Nerd Font Propo";
    text-shadow: none;
    -gtk-icon-shadow: none;
}
window { background-color: transparent; }
#card {
    background-color: alpha(@surface_container, 0.95);
    border: 1px solid alpha(@primary, 0.22);
    border-radius: 20px;
    padding: 14px 14px 10px 14px;
    color: @on_surface;
}
#art-ph {
    background-color: alpha(@primary, 0.12);
    border-radius: 12px;
    color: @primary;
    font-size: 30px;
}
#title  { font-weight: bold; font-size: 112%%; color: @on_surface; }
#artist { color: @secondary; }
#album  { color: @outline; font-style: italic; font-size: 92%%; }
#time   { color: @outline; font-size: 85%%; font-weight: bold; }
#source { color: @outline; font-size: 85%%; font-weight: bold; }

scale { padding: 6px 0; margin: 0; }
scale trough {
    min-height: 4px;
    border: none;
    border-radius: 4px;
    background-image: none;
    background-color: alpha(@on_surface, 0.14);
    box-shadow: none;
}
scale highlight {
    border: none;
    border-radius: 4px;
    background-image: none;
    background-color: @primary;
}
scale slider {
    min-width: 12px;
    min-height: 12px;
    margin: -4px;
    border: none;
    border-radius: 6px;
    background-image: none;
    background-color: @primary;
    box-shadow: 0 0 0 0 alpha(@primary, 0);
    transition: box-shadow 0.2s ease;
}
scale:hover slider { box-shadow: 0 0 0 4px alpha(@primary, 0.18); }

button {
    min-width: 0;
    min-height: 0;
    padding: 4px 10px;
    border: none;
    border-radius: 12px;
    background-image: none;
    background-color: transparent;
    box-shadow: inset 0 0 0 1px alpha(@primary, 0);
    color: @on_surface;
    font-size: 125%%;
    font-weight: normal;
    outline: none;
    transition: color 0.2s ease, background-color 0.2s ease, box-shadow 0.25s ease;
}
button:hover {
    color: @primary;
    background-color: alpha(@primary, 0.12);
    box-shadow: inset 0 0 0 1px alpha(@primary, 0.25);
}
button:active { background-color: alpha(@primary, 0.22); }
#play {
    min-width: 40px;
    min-height: 40px;
    padding: 0;
    border-radius: 20px;
    background-color: @primary;
    color: @on_primary;
    font-size: 140%%;
}
#play:hover {
    background-color: @primary_fixed_dim;
    color: @on_primary;
    box-shadow: inset 0 0 0 1px alpha(@primary, 0), 0 0 6px 0 alpha(@primary, 0.45);
}
#swap { font-size: 100%%; padding: 2px 8px; color: @outline; }
#swap:hover { color: @primary; }

#vol-icon { color: @secondary; font-size: 115%%; min-width: 22px; }
#vol-pct  { color: @outline; font-size: 85%%; font-weight: bold; }
""" % {"colors": COLORS}


def fmt_time(us):
    if us is None or us < 0:
        return "-:--"
    s = int(us // 1_000_000)
    h, m, s = s // 3600, s // 60 % 60, s % 60
    return f"{h}:{m:02}:{s:02}" if h else f"{m}:{s:02}"


def hypr(cmd):
    """Consulta JSON al socket de Hyprland (sin lanzar hyprctl)."""
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sk:
        sk.settimeout(1)
        sk.connect(HYPR_SOCK)
        sk.sendall(f"j/{cmd}".encode())
        buf = b""
        while chunk := sk.recv(65536):
            buf += chunk
    return json.loads(buf)


def read_state():
    try:
        with open(STATE) as f:
            lines = f.read().split("\n")
    except OSError:
        return "", "", ""
    lines += ["", "", ""]
    return lines[0], lines[1], lines[2]


def allowed_players():
    try:
        return [n for n in Playerctl.list_players() if n.name.lower() in ALLOWED]
    except GLib.Error:
        return []


def rounded(cr, w, h, r):
    cr.new_sub_path()
    cr.arc(w - r, r, r, -1.5708, 0)
    cr.arc(w - r, h - r, r, 0, 1.5708)
    cr.arc(r, h - r, r, 1.5708, 3.1416)
    cr.arc(r, r, r, 3.1416, 4.7124)
    cr.close_path()


class Popup(Gtk.Window):
    def __init__(self):
        super().__init__()
        self.player = None
        self.inst = None
        self.handlers = []
        self.art_url = None
        self.art_pb = None
        self.length = None
        self.dragging = False
        self.pending_seek = None
        self.vol_dragging = False
        self.vol_pending = None      # valor (0-100) a mandar, con throttle
        self.vol_timer = 0
        self.vol_set_at = 0.0        # monotonic() del último cambio nuestro / de la rueda
        self.scroll_acc = 0.0
        self.closing = False
        self.geo = None
        self.zone = None
        self.away_since = None
        self.ticks = 0

        self.setup_layer()
        self.build()
        self.connect("destroy", lambda *_: self.quit())

        mon = Gio.File.new_for_path(RUN).monitor_directory(Gio.FileMonitorFlags.WATCH_MOVES, None)
        mon.connect("changed", self.on_state_file)
        self._mon = mon  # que no lo junte el GC

        self.bind()
        GLib.timeout_add(500, self.tick)
        GLib.timeout_add_seconds(2, self.refresh_swap)
        GLib.timeout_add(200, self.watch_cursor)

    # ---- ventana ------------------------------------------------------------
    def setup_layer(self):
        screen = self.get_screen()
        visual = screen.get_rgba_visual()
        if visual:
            self.set_visual(visual)
        self.set_app_paintable(True)

        GtkLayerShell.init_for_window(self)
        GtkLayerShell.set_namespace(self, "waybar-music")
        GtkLayerShell.set_layer(self, GtkLayerShell.Layer.TOP)
        GtkLayerShell.set_keyboard_mode(self, GtkLayerShell.KeyboardMode.NONE)
        GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.TOP, True)
        GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.LEFT, True)
        GtkLayerShell.set_margin(self, GtkLayerShell.Edge.TOP, GAP)

        # centrado bajo el mouse (que está sobre el ícono al hacer click)
        try:
            c = hypr("cursorpos")
            cx, cy = int(c["x"]), int(c["y"])
        except Exception:
            cx = cy = None
        display = Gdk.Display.get_default()
        geo = None
        for i in range(display.get_n_monitors()):
            m = display.get_monitor(i)
            g = m.get_geometry()
            if cx is not None and g.x <= cx < g.x + g.width and g.y <= cy < g.y + g.height:
                GtkLayerShell.set_monitor(self, m)
                geo = g
                break
        self.geo = geo
        self.mon_name = ""
        try:
            for mo in hypr("monitors"):
                if (cx is not None and mo["x"] <= cx < mo["x"] + mo["width"]
                        and mo["y"] <= cy < mo["y"] + mo["height"]):
                    self.mon_name = mo["name"]
        except Exception:
            pass
        if geo is None:
            left = 8
        else:
            left = cx - geo.x - WIDTH // 2
            left = max(8, min(left, geo.width - WIDTH - 8))
        GtkLayerShell.set_margin(self, GtkLayerShell.Edge.LEFT, left)

        prov = Gtk.CssProvider()
        prov.load_from_data(CSS.encode())
        Gtk.StyleContext.add_provider_for_screen(screen, prov,
                                                 Gtk.STYLE_PROVIDER_PRIORITY_USER + 1)
        # Super+W (matugen) reescribe colors.css: recargar en vivo si el menú
        # sigue abierto (el @import se vuelve a leer en cada load_from_data)
        self.css_prov, self.css_reload_id = prov, 0
        self.colors_mon = Gio.File.new_for_path(COLORS).monitor_file(
            Gio.FileMonitorFlags.WATCH_MOVES, None)
        self.colors_mon.connect("changed", self.on_colors_changed)

    def on_colors_changed(self, *_):
        if self.css_reload_id:                 # matugen escribe en varios pasos
            GLib.source_remove(self.css_reload_id)
        self.css_reload_id = GLib.timeout_add(150, self.reload_css)

    def reload_css(self):
        self.css_reload_id = 0
        try:
            self.css_prov.load_from_data(CSS.encode())
        except GLib.Error:
            pass                               # archivo a medio escribir: el próximo evento lo arregla
        return False

    def label(self, name, xalign=0.0):
        lb = Gtk.Label(xalign=xalign)
        lb.set_name(name)
        lb.set_ellipsize(3)            # Pango.EllipsizeMode.END
        lb.set_max_width_chars(1)      # que no estire la ventana; hexpand la llena
        lb.set_hexpand(True)
        return lb

    def build(self):
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        card.set_name("card")
        card.set_size_request(WIDTH, -1)
        self.add(card)

        top = Gtk.Box(spacing=12)
        # click en la carátula / el título: ir a la ventana del reproductor
        top_ev = Gtk.EventBox()
        top_ev.add(top)
        top_ev.set_tooltip_text("Open app")
        top_ev.connect("button-release-event", self.on_top_click)
        top_ev.connect("realize", lambda w: w.get_window().set_cursor(
            Gdk.Cursor.new_from_name(w.get_display(), "pointer")))
        card.pack_start(top_ev, False, False, 0)

        self.art_stack = Gtk.Stack()
        self.art_stack.set_size_request(ART, ART)
        self.art_stack.set_valign(Gtk.Align.CENTER)
        ph = Gtk.Label(label=I_MUSIC)
        ph.set_name("art-ph")
        self.art_area = Gtk.DrawingArea()
        self.art_area.connect("draw", self.draw_art)
        self.art_stack.add_named(ph, "ph")
        self.art_stack.add_named(self.art_area, "art")
        # visibles ya: si la carátula está en caché se carga antes del show_all
        # y GtkStack ignora set_visible_child de un hijo oculto
        ph.show()
        self.art_area.show()
        top.pack_start(self.art_stack, False, False, 0)

        info = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        info.set_valign(Gtk.Align.CENTER)
        info.set_hexpand(True)
        self.l_title = self.label("title")
        self.l_title.set_line_wrap(True)            # título: hasta 2 líneas
        self.l_title.set_line_wrap_mode(2)          # Pango.WrapMode.WORD_CHAR
        self.l_title.set_lines(2)
        self.l_artist = self.label("artist")
        self.l_album = self.label("album")
        for w in (self.l_title, self.l_artist, self.l_album):
            info.pack_start(w, False, False, 0)
        top.pack_start(info, True, True, 0)

        prog = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        card.pack_start(prog, False, False, 0)
        self.scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 1, 1)
        self.scale.set_draw_value(False)
        self.scale.connect("button-press-event", self.on_scale_press)
        self.scale.connect("button-release-event", self.on_scale_release)
        self.scale.connect("change-value", self.on_scale_change)
        prog.pack_start(self.scale, False, False, 0)
        times = Gtk.Box()
        self.l_pos = Gtk.Label(label="-:--", xalign=0)
        self.l_len = Gtk.Label(label="-:--", xalign=1)
        for w in (self.l_pos, self.l_len):
            w.set_name("time")
        times.pack_start(self.l_pos, True, True, 0)
        times.pack_end(self.l_len, True, True, 0)
        prog.pack_start(times, False, False, 0)

        ctl = Gtk.Box()
        card.pack_start(ctl, False, False, 0)
        self.l_source = Gtk.Label(xalign=0)
        self.l_source.set_name("source")
        self.l_source.set_size_request(90, -1)
        ctl.pack_start(self.l_source, False, False, 0)

        mid = Gtk.Box(spacing=8)
        mid.set_halign(Gtk.Align.CENTER)
        self.b_prev = self.button(I_PREV, "prev", "Previous", lambda: self.call("previous"))
        self.b_play = self.button(I_PLAY, "play", "Play / pause", lambda: self.call("play_pause"))
        self.b_next = self.button(I_NEXT, "next", "Next", lambda: self.call("next"))
        for b in (self.b_prev, self.b_play, self.b_next):
            b.set_valign(Gtk.Align.CENTER)
            mid.pack_start(b, False, False, 0)
        ctl.set_center_widget(mid)

        self.b_swap = self.button(I_SWAP, "swap", "Switch player", self.swap)
        self.b_swap.set_valign(Gtk.Align.CENTER)
        self.b_swap.set_no_show_all(True)
        ctl.pack_end(self.b_swap, False, False, 0)

        vol = Gtk.Box(spacing=6)
        card.pack_start(vol, False, False, 0)
        self.l_vol_icon = Gtk.Label(label=I_VOL[3])
        self.l_vol_icon.set_name("vol-icon")
        vol.pack_start(self.l_vol_icon, False, False, 0)
        self.vscale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1)
        self.vscale.set_draw_value(False)
        self.vscale.set_hexpand(True)
        self.vscale.connect("button-press-event", self.on_vol_press)
        self.vscale.connect("button-release-event", self.on_vol_release)
        self.vscale.connect("change-value", self.on_vol_change)
        self.vscale.connect("scroll-event", self.on_vol_scroll)
        vol.pack_start(self.vscale, True, True, 0)
        self.l_vol = Gtk.Label(label="", xalign=1)
        self.l_vol.set_name("vol-pct")
        self.l_vol.set_width_chars(4)          # "100%": que el slider no se corra
        vol.pack_start(self.l_vol, False, False, 0)

    def button(self, glyph, name, tip, fn):
        b = Gtk.Button(label=glyph)
        b.set_name(name)
        b.set_tooltip_text(tip)
        b.set_can_focus(False)
        b.set_relief(Gtk.ReliefStyle.NONE)
        b.connect("clicked", lambda *_: fn())
        return b

    # ---- reproductor -------------------------------------------------------
    def on_state_file(self, _mon, f, other, event):
        names = {f.get_basename() if f else None, other.get_basename() if other else None}
        if "state" in names:
            self.bind()
        if "volume" in names:           # rueda sobre el ícono / el slider: al instante
            self.volume_from_file()

    def bind(self):
        inst, _status, cls = read_state()
        self.cls = cls
        if inst == self.inst and self.player is not None:
            self.refresh()
            return
        for h in self.handlers:
            try:
                self.player.disconnect(h)
            except Exception:
                pass
        self.handlers, self.player, self.inst = [], None, inst
        for n in allowed_players():
            if n.instance == inst:
                try:
                    self.player = Playerctl.Player.new_from_name(n)
                except GLib.Error:
                    self.player = None
                break
        if self.player is not None:
            for sig in ("metadata", "playback-status", "seeked"):
                self.handlers.append(self.player.connect(sig, lambda *_: self.refresh()))
            self.handlers.append(self.player.connect("volume", lambda *_: self.sync_volume()))
        self.vol_set_at = 0.0           # otro reproductor: tomar su volumen ya
        self.refresh_swap()
        self.refresh()

    def meta(self):
        try:
            md = self.player.props.metadata
            return md.unpack() if md else {}
        except Exception:
            return {}

    def refresh(self):
        p = self.player
        if p is None:
            self.l_title.set_text("Nothing playing")
            self.l_artist.set_text("")
            self.l_album.set_text("")
            self.l_source.set_text("")
            self.set_art(None)
            self.length = None
            self.l_len.set_text("-:--")
            self.sync_volume()
            return False
        m = self.meta()
        title = m.get("xesam:title") or ""
        if not title and m.get("xesam:url"):
            title = os.path.basename(unquote(urlparse(m["xesam:url"]).path))
        artist = m.get("xesam:artist") or ""
        if isinstance(artist, (list, tuple)):
            artist = ", ".join(a for a in artist if a)
        album = m.get("xesam:album") or ""
        self.l_title.set_text(title or "—")
        self.l_artist.set_text(artist)
        self.l_album.set_text(album)
        self.l_title.set_tooltip_text(title or None)
        for w, t in ((self.l_artist, artist), (self.l_album, album)):
            w.set_visible(bool(t))

        icon = I_DISK if self.cls == "deadbeef" else I_MUSIC
        self.l_source.set_text(f"{icon} {SOURCES.get(self.cls, '')}")

        try:
            playing = p.props.playback_status == Playerctl.PlaybackStatus.PLAYING
        except Exception:
            playing = False
        self.b_play.set_label(I_PAUSE if playing else I_PLAY)

        length = m.get("mpris:length")
        self.length = int(length) if length else None
        self.scale.set_sensitive(bool(self.length))
        self.scale.set_range(0, max(1, (self.length or 1_000_000) / 1_000_000))
        self.l_len.set_text(fmt_time(self.length))

        url = m.get("mpris:artUrl") or ""
        if "resources.tidal.com" in url:     # 320px alcanza y baja mucho menos
            url = url.replace("1280x1280", "320x320")
        if url != self.art_url:
            self.art_url = url
            self.set_art(None)
            if url:
                self.fetch_art(url)
        self.tick(update_only=True)
        self.sync_volume()
        return False

    def refresh_swap(self):
        self.b_swap.set_visible(len(allowed_players()) > 1)
        return True

    def tick(self, update_only=False):
        if self.player is not None and not self.dragging:
            try:
                pos = self.player.get_position()
            except Exception:
                pos = None
            if pos is not None:
                self.scale.set_value(pos / 1_000_000)
            self.l_pos.set_text(fmt_time(pos))
        return True if not update_only else False

    def call(self, method):
        if self.player is None:
            return
        try:
            getattr(self.player, method)()
        except GLib.Error:
            pass

    def on_top_click(self, _w, ev):
        if ev.button == 1:
            subprocess.Popen([CTL, "focus"])
            self.quit()
        return True

    def swap(self):
        subprocess.Popen([CTL, "cycle"])

    # ---- carátula ----------------------------------------------------------
    def fetch_art(self, url):
        if url.startswith("file://"):
            self.art_loaded(url, unquote(urlparse(url).path))
            return
        if not url.startswith(("http://", "https://")):
            return
        os.makedirs(CACHE, exist_ok=True)
        path = os.path.join(CACHE, hashlib.sha1(url.encode()).hexdigest() + ".img")
        if os.path.exists(path):
            self.art_loaded(url, path)
            return

        def worker():
            try:
                with urllib.request.urlopen(url, timeout=6) as r:
                    data = r.read(8 * 1024 * 1024)
                tmp = path + ".tmp"
                with open(tmp, "wb") as f:
                    f.write(data)
                os.replace(tmp, path)
                GLib.idle_add(self.art_loaded, url, path)
            except Exception:
                pass
        threading.Thread(target=worker, daemon=True).start()

    def art_loaded(self, url, path):
        if url != self.art_url:
            return False
        try:
            sc = self.get_scale_factor()
            pb = GdkPixbuf.Pixbuf.new_from_file_at_scale(path, ART * sc, ART * sc, True)
        except Exception:
            pb = None
        self.set_art(pb)
        return False

    def set_art(self, pb):
        self.art_pb = pb
        self.art_stack.set_visible_child_name("art" if pb else "ph")
        self.art_area.queue_draw()

    def draw_art(self, w, cr):
        pb = self.art_pb
        if pb is None:
            return False
        a, b = w.get_allocated_width(), w.get_allocated_height()
        rounded(cr, a, b, 12)
        cr.clip()
        pw, ph = pb.get_width(), pb.get_height()
        s = max(a / pw, b / ph)        # "cover": llena el cuadrado
        cr.scale(s, s)
        Gdk.cairo_set_source_pixbuf(cr, pb, (a / s - pw) / 2, (b / s - ph) / 2)
        cr.paint()
        return False

    # ---- barra de progreso -------------------------------------------------
    def on_scale_press(self, *_):
        self.dragging = True
        return False

    def on_scale_change(self, _scale, _scroll, value):
        value = max(0.0, min(value, (self.length or 0) / 1_000_000))
        self.l_pos.set_text(fmt_time(value * 1_000_000))
        if self.dragging:
            self.pending_seek = value
        else:                           # teclado / rueda
            self.seek_to(value)
        return False

    def on_scale_release(self, *_):
        self.dragging = False
        if self.pending_seek is not None:
            self.seek_to(self.pending_seek)
            self.pending_seek = None
        return False

    def seek_to(self, secs):
        if self.player is None:
            return
        try:
            self.player.set_position(int(secs * 1_000_000))
        except GLib.Error:
            try:
                self.player.seek(int(secs * 1_000_000) - self.player.get_position())
            except GLib.Error:
                pass

    # ---- volumen (MPRIS del reproductor, igual que la rueda sobre el ícono) --
    def show_volume(self, pct):
        pct = max(0, min(100, int(round(pct))))
        self.l_vol.set_text(f"{pct}%")
        self.l_vol_icon.set_text(I_VOL[0 if pct == 0 else 1 if pct < 34 else 2 if pct < 67 else 3])
        return pct

    def sync_volume(self):
        """Toma el volumen que reporta el reproductor (si no lo estamos cambiando)."""
        p = self.player
        try:
            v = p.props.volume if p is not None else None
        except Exception:
            v = None
        ok = v is not None and v >= 0
        self.vscale.set_sensitive(ok)
        if not ok:
            self.l_vol.set_text("")
            return False
        if self.vol_dragging or self.vol_pending is not None or \
                time.monotonic() - self.vol_set_at < VOL_HOLD:
            return False
        self.vscale.set_value(self.show_volume(v * 100))
        return False

    def volume_from_file(self):
        """music-ctl.sh volume (rueda) escribió el valor nuevo: mostrarlo ya."""
        try:
            with open(VOLFILE) as f:
                who, val, _ms = f.read().split()
            val = float(val)
        except (OSError, ValueError):
            return
        if who != self.inst or self.vol_dragging:
            return
        self.vol_set_at = time.monotonic()
        self.vscale.set_value(self.show_volume(val * 100))

    def set_volume(self, pct):
        """Manda el volumen al reproductor y lo anota para music-ctl.sh (así la
        rueda sigue desde acá y no desde un valor viejo)."""
        if self.player is None:
            return
        v = round(pct) / 100
        try:
            self.player.set_volume(v)
        except GLib.Error:
            return
        self.vol_set_at = time.monotonic()
        try:
            tmp = f"{VOLFILE}.{os.getpid()}.tmp"
            with open(tmp, "w") as f:
                f.write(f"{self.inst} {v:.2f} {int(time.time() * 1000)}\n")
            os.replace(tmp, VOLFILE)
        except OSError:
            pass

    def flush_volume(self):
        self.vol_timer = 0
        if self.vol_pending is not None:
            pct, self.vol_pending = self.vol_pending, None
            self.set_volume(pct)
        return False

    def on_vol_press(self, *_):
        self.vol_dragging = True
        return False

    def on_vol_change(self, _scale, _scroll, value):
        self.vol_pending = self.show_volume(value)
        if not self.vol_timer:           # arrastrando: como mucho cada 60 ms
            self.vol_timer = GLib.timeout_add(60, self.flush_volume)
        return False

    def on_vol_release(self, *_):
        self.vol_dragging = False
        if self.vol_timer:
            GLib.source_remove(self.vol_timer)
        self.flush_volume()
        return False

    def on_vol_scroll(self, _w, ev):
        """Rueda sobre el slider = rueda sobre el ícono (mismos pasos 1/2/5 %)."""
        ok, direction = ev.get_scroll_direction()
        steps = 0
        if ok and direction == Gdk.ScrollDirection.UP:
            steps = 1
        elif ok and direction == Gdk.ScrollDirection.DOWN:
            steps = -1
        else:
            ok, _dx, dy = ev.get_scroll_deltas()
            if ok:
                self.scroll_acc -= dy
                steps = int(self.scroll_acc)          # cada 1.0 de delta = un paso
                self.scroll_acc -= steps
        if self.player is not None and self.vscale.get_sensitive():
            for _ in range(abs(steps)):
                subprocess.Popen([CTL, "volume", "up" if steps > 0 else "down"])
        return True                       # no dejar que GTK mueva el slider por su cuenta

    # ---- cierre ------------------------------------------------------------
    def find_zone(self):
        """Rectángulo (global) donde el mouse cuenta como "en el menú": el popup
        con un margen, estirado hacia arriba hasta el borde de la pantalla para
        incluir el ícono de la barra (que queda justo encima)."""
        for mon in hypr("layers").values():
            for layer in mon.get("levels", {}).values():
                for l in layer:
                    if l.get("namespace") == "waybar-music" and l.get("pid") in (None, os.getpid()):
                        top = self.geo.y if self.geo else l["y"] - 60
                        return (l["x"] - ZONE_PAD, top,
                                l["x"] + l["w"] + ZONE_PAD, l["y"] + l["h"] + ZONE_PAD)
        return None

    def watch_cursor(self):
        if self.closing:
            return False
        self.ticks += 1
        try:
            if self.zone is None or self.ticks % 5 == 0:   # el alto puede cambiar
                self.zone = self.find_zone() or self.zone
            c = hypr("cursorpos")
        except Exception:
            return True
        if self.zone is None or self.dragging or self.vol_dragging:
            self.away_since = None
            return True
        x0, y0, x1, y1 = self.zone
        if x0 <= c["x"] <= x1 and y0 <= c["y"] <= y1:
            self.away_since = None
        elif self.away_since is None:
            self.away_since = time.monotonic()
        elif time.monotonic() - self.away_since >= AWAY_CLOSE_MS / 1000:
            self.quit()
            return False
        return True

    def quit(self, *_):
        if self.closing:
            return False
        self.closing = True
        try:
            with open(CLOSED, "w") as f:
                f.write(str(int(time.time() * 1000)))
            if os.path.exists(PIDFILE) and \
                    open(PIDFILE).read().split("\n")[0].strip() == str(os.getpid()):
                os.remove(PIDFILE)
        except OSError:
            pass
        Gtk.main_quit()
        return False


def main():
    os.makedirs(RUN, exist_ok=True)
    win = Popup()
    with open(PIDFILE, "w") as f:      # el monitor: para resaltar el ícono de esa barra
        f.write(f"{os.getpid()}\n{win.mon_name}\n")
    for sig in (signal.SIGTERM, signal.SIGINT):
        unix_signal_add(GLib.PRIORITY_DEFAULT, sig, win.quit)
    win.show_all()
    win.b_swap.set_visible(len(allowed_players()) > 1)
    Gtk.main()


if __name__ == "__main__":
    main()
