#!/usr/bin/env python3
"""Buscador de ciudad para el módulo de clima de waybar (click derecho).

Popup GTK3 + layer-shell estilo spotlight (mismo look que weather-popup.py):
se escribe el nombre, busca en el geocoding de Open-Meteo (sin API key) y al
elegir una (Enter / click) queda guardada como ciudad actual en
~/.local/state/waybar-weather/location.json (weather.py la lee), junto con
las recientes, que se muestran cuando la búsqueda está vacía.
Después refresca la barra (señal RTMIN+9) y, si se abrió desde el popup del
pronóstico (--then-forecast), lo vuelve a abrir con la ciudad nueva.

Teclas: ↑/↓ elegir, Enter confirmar, Esc cerrar. Click fuera = cerrar.
Toggle: correrlo otra vez lo cierra (pid en $XDG_RUNTIME_DIR/waybar-weather).
Sin layer-shell: lo mismo con rofi -dmenu.

Prueba sin tomar teclado/mouse: WEATHER_POPUP_TEST=<segundos>
WEATHER_SEARCH_QUERY=<texto> (lo escribe solo).
"""

import json
import os
import subprocess
import sys
import threading
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
import weather as W  # noqa: E402

HERE = os.path.dirname(os.path.realpath(__file__))
RUN = os.path.join(os.environ.get("XDG_RUNTIME_DIR", "/tmp"), "waybar-weather")
PIDFILE = os.path.join(RUN, "search.pid")
COLORS = os.path.expanduser("~/.config/waybar/colors.css")
HYPR_SOCK = os.path.join(os.environ.get("XDG_RUNTIME_DIR", "/tmp"), "hypr",
                         os.environ.get("HYPRLAND_INSTANCE_SIGNATURE", ""), ".socket.sock")
GEO_URL = "https://geocoding-api.open-meteo.com/v1/search?count=8&language=en&format=json&name="
MAX_RECENT = 7
KEEP = ("name", "admin1", "country", "country_code", "latitude", "longitude", "timezone")

I_SEARCH = "\U000F0349"    # magnify
I_HISTORY = "\U000F02DA"   # history
I_CHECK = "\U000F012C"     # check


# ---- datos ------------------------------------------------------------------
def geocode(query):
    req = urllib.request.Request(GEO_URL + urllib.parse.quote(query),
                                 headers={"User-Agent": "waybar-weather"})
    with urllib.request.urlopen(req, timeout=8) as r:
        res = json.load(r).get("results") or []
    return [{k: x.get(k) for k in KEEP} for x in res
            if x.get("latitude") is not None and x.get("longitude") is not None]


def flag(cc):
    if not cc or len(cc) != 2 or not cc.isalpha():
        return "\U0001F3F3"   # bandera blanca
    return "".join(chr(0x1F1E6 + ord(c) - ord("A")) for c in cc.upper())


def local_time(loc):
    """Hora actual en esa ciudad ("21:04"), para distinguir homónimas."""
    try:
        from zoneinfo import ZoneInfo
        import datetime as dt
        return dt.datetime.now(ZoneInfo(loc["timezone"])).strftime("%H:%M")
    except Exception:
        return ""


def place_line(loc):
    parts = [p for p in (loc.get("admin1"), loc.get("country")) if p and p != loc.get("name")]
    return ", ".join(parts)


def choose(loc):
    """Guarda la ciudad (y la anterior en recientes) y avisa a la barra."""
    st = W.load_state()
    old = st.get("current")
    recent = [loc] + ([old] if old else []) + st.get("recent", [])
    seen, uniq = set(), []
    for r in recent:
        k = W.loc_key(r)
        if k not in seen:
            seen.add(k)
            uniq.append(r)
    W.save_state({"current": loc, "recent": uniq[:MAX_RECENT]})
    subprocess.Popen(["pkill", "-RTMIN+9", "-x", "waybar"])


def running_pid():
    try:
        pid = int(open(PIDFILE).read().split()[0])
        if b"weather-search" in open(f"/proc/{pid}/cmdline", "rb").read() and pid != os.getpid():
            return pid
    except (OSError, ValueError, IndexError):
        pass
    return None


def hypr(cmd):
    import socket
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        s.connect(HYPR_SOCK)
        s.sendall(f"j/{cmd}".encode())
        buf = b""
        while True:
            chunk = s.recv(65536)
            if not chunk:
                break
            buf += chunk
    return json.loads(buf)


def after_choose(then_forecast):
    if then_forecast:
        subprocess.Popen([os.path.join(HERE, "weather-popup.py")], start_new_session=True,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


# ---- respaldo con rofi ------------------------------------------------------
def rofi_search(then_forecast):
    def dmenu(prompt, lines=(), mesg=None):
        cmd = ["rofi", "-dmenu", "-i", "-p", prompt, "-format", "i:s"]
        if mesg:
            cmd += ["-mesg", mesg]
        r = subprocess.run(cmd, input="\n".join(lines), capture_output=True, text=True)
        if r.returncode != 0 or not r.stdout.strip():
            return None, None
        i, _, s = r.stdout.strip().partition(":")
        return int(i), s

    recent = W.load_state().get("recent", [])
    labels = [f"{x['name']} — {place_line(x)}" for x in recent]
    i, text = dmenu("City", labels, "Type a city name, or pick a recent one")
    if text is None:
        return
    if 0 <= i < len(recent) and text == labels[i]:
        choose(recent[i])
        return after_choose(then_forecast)
    try:
        res = geocode(text)
    except Exception:
        subprocess.run(["notify-send", "-a", "Weather", "City search failed",
                        "Couldn't reach Open-Meteo."])
        return
    if not res:
        subprocess.run(["notify-send", "-a", "Weather", "No results", text])
        return
    labels = [f"{x['name']} — {place_line(x)}" for x in res]
    i, _ = dmenu("Choose", labels)
    if i is not None and 0 <= i < len(res):
        choose(res[i])
        after_choose(then_forecast)


# ---- popup GTK --------------------------------------------------------------
CSS = """
@import url("file://%(colors)s");
* {
    font-family: "JetBrainsMono Nerd Font Propo";
    text-shadow: none;
    -gtk-icon-shadow: none;
}
window { background-color: transparent; }
#card {
    background-color: @surface_container;
    border: 1px solid alpha(@primary, 0.22);
    border-radius: 24px;
    padding: 14px;
    color: @on_surface;
    box-shadow: 0 8px 28px 0 alpha(@shadow, 0.45);
    margin: 30px;
}
#search-box {
    background-color: alpha(@on_surface, 0.05);
    border-radius: 16px;
    padding: 2px 6px 2px 14px;
    box-shadow: inset 0 0 0 1px alpha(@primary, 0.18);
    transition: box-shadow 0.2s ease;
}
#search-box.focused { box-shadow: inset 0 0 0 1px alpha(@primary, 0.45); }
#search-icon { color: @primary; font-size: 130%%; }
entry {
    background-color: transparent;
    background-image: none;
    border: none;
    box-shadow: none;
    outline: none;
    min-height: 40px;
    padding: 0 6px;
    color: @on_surface;
    caret-color: @primary;
    font-size: 115%%;
}
entry selection { background-color: alpha(@primary, 0.35); color: @on_surface; }
entry placeholder, entry .placeholder { color: @outline; }
#section { color: @outline; font-size: 80%%; font-weight: bold; margin: 4px 8px 0 8px; }
#status  { color: @outline; font-size: 90%%; margin: 10px 8px 6px 8px; }
list { background-color: transparent; }
row {
    padding: 7px 10px;
    border-radius: 14px;
    background-color: transparent;
    box-shadow: inset 0 0 0 1px alpha(@primary, 0);
    transition: background-color 0.15s ease, box-shadow 0.2s ease;
    outline: none;
}
row:hover { background-color: alpha(@primary, 0.07); }
row:selected {
    background-color: alpha(@primary, 0.14);
    box-shadow: inset 0 0 0 1px alpha(@primary, 0.30);
}
.flag  { font-family: "Noto Color Emoji"; font-size: 140%%; }
.name  { font-weight: bold; color: @on_surface; }
.place { color: @outline; font-size: 88%%; }
.mark  { color: @primary; font-size: 115%%; }
.tz    { color: @outline; font-size: 80%%; }
""" % {"colors": COLORS}


def run_gtk(then_forecast):
    import gi
    gi.require_version("Gtk", "3.0")
    gi.require_version("Gdk", "3.0")
    gi.require_version("GtkLayerShell", "0.1")
    from gi.repository import Gdk, Gio, GLib, Gtk, GtkLayerShell
    import cairo

    try:                                    # PyGObject >= 3.52
        gi.require_version("GLibUnix", "2.0")
        from gi.repository import GLibUnix
        unix_signal_add = GLibUnix.signal_add
    except (ImportError, ValueError):
        unix_signal_add = GLib.unix_signal_add

    if not Gtk.init_check()[0] or not GtkLayerShell.is_supported():
        raise RuntimeError("no layer-shell")

    class Search(Gtk.Window):
        def __init__(self):
            super().__init__()
            self.test = float(os.environ.get("WEATHER_POPUP_TEST") or 0)
            self.seq = 0               # descarta respuestas viejas
            self.debounce = 0
            self.results = []
            self.fade = 0.0
            self.cur_key = W.loc_key(W.location())
            self.setup_layer()
            self.build()
            self.connect("destroy", lambda *_: Gtk.main_quit())
            self.connect("key-press-event", self.on_key)
            self.connect("button-press-event", lambda *_: self.destroy() or True)
            self.connect("draw", self.draw_backdrop)
            self.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
            self.show_recent()
            self.show_all()
            self.entry.grab_focus()
            self.t0 = GLib.get_monotonic_time()
            GLib.timeout_add(16, self.step_fade)
            if self.test:
                self.input_shape_combine_region(cairo.Region())
                GLib.timeout_add(int(self.test * 1000), self.destroy)
            q = os.environ.get("WEATHER_SEARCH_QUERY")
            if q:
                self.entry.set_text(q)

        # ---- ventana --------------------------------------------------------
        def setup_layer(self):
            screen = self.get_screen()
            visual = screen.get_rgba_visual()
            if visual:
                self.set_visual(visual)
            self.set_app_paintable(True)
            L = GtkLayerShell
            L.init_for_window(self)
            L.set_namespace(self, "weather-popup")   # no "waybar*" (layer_rule regex con blur)
            L.set_layer(self, L.Layer.OVERLAY)
            L.set_keyboard_mode(self, L.KeyboardMode.NONE if self.test
                                else L.KeyboardMode.EXCLUSIVE)
            L.set_exclusive_zone(self, -1)
            for e in (L.Edge.TOP, L.Edge.BOTTOM, L.Edge.LEFT, L.Edge.RIGHT):
                L.set_anchor(self, e, True)
            self.mon_h = 1080
            try:
                c = hypr("cursorpos")
                cx, cy = int(c["x"]), int(c["y"])
                display = Gdk.Display.get_default()
                for i in range(display.get_n_monitors()):
                    m = display.get_monitor(i)
                    g = m.get_geometry()
                    if g.x <= cx < g.x + g.width and g.y <= cy < g.y + g.height:
                        L.set_monitor(self, m)
                        self.mon_h = g.height
                        break
            except Exception:
                pass
            self.css = Gtk.CssProvider()
            self.css.load_from_data(CSS.encode())
            Gtk.StyleContext.add_provider_for_screen(
                screen, self.css, Gtk.STYLE_PROVIDER_PRIORITY_USER + 1)
            self.colors_mon = Gio.File.new_for_path(COLORS).monitor_file(
                Gio.FileMonitorFlags.WATCH_MOVES, None)
            self.colors_mon.connect("changed", lambda *_: GLib.timeout_add(150, self.reload_css))

        def reload_css(self):
            try:
                self.css.load_from_data(CSS.encode())
                self.queue_draw()
            except GLib.Error:
                pass
            return False

        def color(self, name, alpha=1.0):
            ok, c = self.get_style_context().lookup_color(name)
            return (c.red, c.green, c.blue, c.alpha * alpha) if ok else (0, 0, 0, alpha)

        def draw_backdrop(self, _w, cr):
            cr.set_operator(cairo.OPERATOR_SOURCE)
            cr.set_source_rgba(*self.color("scrim", 0.32 * self.fade))
            cr.paint()
            cr.set_operator(cairo.OPERATOR_OVER)
            return False

        def step_fade(self):
            t = (GLib.get_monotonic_time() - self.t0) / 300_000
            self.fade = 1 - (1 - min(t, 1.0)) ** 3
            self.queue_draw()
            return t < 1.0

        # ---- widgets --------------------------------------------------------
        def build(self):
            ev = Gtk.EventBox()
            ev.set_halign(Gtk.Align.CENTER)
            # arriba del centro y crece hacia abajo (la lista cambia de alto)
            ev.set_valign(Gtk.Align.START)
            ev.set_margin_top(int(self.mon_h * 0.22))
            ev.connect("button-press-event", lambda *_: True)
            card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
            card.set_name("card")
            card.set_size_request(500, -1)
            ev.add(card)
            self.add(ev)

            box = Gtk.Box(spacing=4)
            box.set_name("search-box")
            icon = Gtk.Label(label=I_SEARCH)
            icon.set_name("search-icon")
            box.pack_start(icon, False, False, 0)
            self.entry = Gtk.Entry()
            self.entry.set_placeholder_text("Search a city…")
            self.entry.set_hexpand(True)
            self.entry.connect("changed", self.on_changed)
            self.entry.connect("activate", lambda *_: self.activate_selected())
            self.entry.connect("focus-in-event", lambda *_: box.get_style_context().add_class("focused"))
            self.entry.connect("focus-out-event", lambda *_: box.get_style_context().remove_class("focused"))
            box.pack_start(self.entry, True, True, 0)
            card.pack_start(box, False, False, 0)

            self.section = Gtk.Label(xalign=0)
            self.section.set_name("section")
            card.pack_start(self.section, False, False, 0)

            self.listbox = Gtk.ListBox()
            self.listbox.set_selection_mode(Gtk.SelectionMode.BROWSE)
            self.listbox.set_activate_on_single_click(True)
            self.listbox.connect("row-activated", lambda _l, row: self.pick(row.get_index()))
            card.pack_start(self.listbox, False, False, 0)

            self.status = Gtk.Label(xalign=0.5)
            self.status.set_name("status")
            self.status.set_no_show_all(True)
            card.pack_start(self.status, False, False, 0)

        def lab(self, text, cls, xalign=0.0):
            lb = Gtk.Label(label=text, xalign=xalign)
            lb.get_style_context().add_class(cls)
            lb.set_ellipsize(3)
            return lb

        def fill(self, items, section):
            for r in self.listbox.get_children():
                self.listbox.remove(r)
            self.results = items
            self.section.set_text(section)
            self.section.set_visible(bool(section and items))
            for loc in items:
                row = Gtk.ListBoxRow()
                h = Gtk.Box(spacing=12)
                h.pack_start(self.lab(flag(loc.get("country_code")), "flag"), False, False, 0)
                v = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
                v.pack_start(self.lab(loc["name"], "name"), False, False, 0)
                pl = place_line(loc)
                if pl:
                    v.pack_start(self.lab(pl, "place"), False, False, 0)
                h.pack_start(v, True, True, 0)
                if W.loc_key(loc) == self.cur_key:
                    h.pack_end(self.lab(I_CHECK, "mark"), False, False, 0)
                elif local_time(loc):
                    h.pack_end(self.lab(local_time(loc), "tz", 1.0), False, False, 0)
                row.add(h)
                self.listbox.add(row)
            self.listbox.show_all()
            first = self.listbox.get_row_at_index(0)
            if first:
                self.listbox.select_row(first)

        def set_status(self, text):
            self.status.set_text(text or "")
            self.status.set_visible(bool(text))

        def show_recent(self):
            st = W.load_state()
            items = st.get("recent") or [st["current"]]
            self.fill(items, f"{I_HISTORY}  RECENT")
            self.set_status("" if items else "Type a city name")

        # ---- búsqueda -------------------------------------------------------
        def on_changed(self, *_):
            if self.debounce:
                GLib.source_remove(self.debounce)
                self.debounce = 0
            q = self.entry.get_text().strip()
            self.seq += 1
            if len(q) < 2:
                self.show_recent()
                return
            self.set_status("Searching…")
            self.debounce = GLib.timeout_add(250, self.search, q, self.seq)

        def search(self, q, seq):
            self.debounce = 0

            def worker():
                try:
                    res, err = geocode(q), None
                except Exception as e:
                    res, err = [], e
                GLib.idle_add(self.got, seq, res, err)
            threading.Thread(target=worker, daemon=True).start()
            return False

        def got(self, seq, res, err):
            if seq != self.seq:        # ya se escribió otra cosa
                return False
            self.fill(res, "")
            if err:
                self.set_status("Couldn't reach Open-Meteo")
            else:
                self.set_status("" if res else "No cities found")
            return False

        # ---- elegir ---------------------------------------------------------
        def on_key(self, _w, ev):
            k = ev.keyval
            if k == Gdk.KEY_Escape:
                self.destroy()
                return True
            if k in (Gdk.KEY_Down, Gdk.KEY_Up, Gdk.KEY_Tab, Gdk.KEY_ISO_Left_Tab):
                n = len(self.results)
                if n:
                    row = self.listbox.get_selected_row()
                    i = row.get_index() if row else -1
                    step = -1 if k in (Gdk.KEY_Up, Gdk.KEY_ISO_Left_Tab) else 1
                    self.listbox.select_row(self.listbox.get_row_at_index((i + step) % n))
                return True
            return False   # el resto lo maneja el entry

        def activate_selected(self):
            row = self.listbox.get_selected_row()
            if row:
                self.pick(row.get_index())

        def pick(self, i):
            if 0 <= i < len(self.results):
                choose(self.results[i])
                after_choose(then_forecast)
                self.destroy()

    win = Search()

    def bye(*_):
        win.destroy()
        return False
    unix_signal_add(GLib.PRIORITY_DEFAULT, 15, bye)
    unix_signal_add(GLib.PRIORITY_DEFAULT, 2, bye)
    Gtk.main()


def main():
    pid = running_pid()
    if pid:                         # ya abierto: cerrarlo (toggle)
        os.kill(pid, 15)
        return
    then_forecast = "--then-forecast" in sys.argv[1:]
    os.makedirs(RUN, exist_ok=True)
    with open(PIDFILE, "w") as f:
        f.write(str(os.getpid()))
    try:
        run_gtk(then_forecast)
    except Exception as e:
        print(f"weather-search: {e!r}, falling back to rofi", file=sys.stderr)
        rofi_search(then_forecast)
    finally:
        try:
            if int(open(PIDFILE).read().split()[0]) == os.getpid():
                os.remove(PIDFILE)
        except (OSError, ValueError, IndexError):
            pass


if __name__ == "__main__":
    main()
