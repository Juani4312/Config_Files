#!/usr/bin/env python3
"""Calendario de la waybar (click derecho en la hora).

Popup GTK3 + layer-shell que baja desde la esquina, debajo del reloj, en el monitor
del mouse. Mes con números de semana; se navega por meses y años, y tocando el mes
o el año se abre una grilla para elegirlos. La capa cubre la pantalla (transparente)
solo para que un click afuera lo cierre; también se cierra si el mouse se aleja.

  ← / →  (h / l, rueda)        mes anterior / siguiente
  ↑ / ↓  (k / j)               año anterior / siguiente
  m / y                        elegir mes / elegir año
  Home / t                     volver a hoy
  Esc                          vuelve a los días; en los días cierra
  click afuera / alejar mouse  cierra

Toggle: correrlo otra vez lo cierra (pid en $XDG_RUNTIME_DIR/waybar-calendar).
Colores: ~/.config/waybar/colors.css (matugen), se recargan en vivo con Super+W.

Prueba sin molestar a quien usa la compu: CALENDAR_POPUP_TEST=<segundos>
(no toma teclado ni mouse y se cierra solo), CALENDAR_POPUP_MONTH=AAAA-MM,
CALENDAR_POPUP_VIEW=days|months|years, CALENDAR_POPUP_WATCH=1 (en modo prueba, igual
vigila el mouse para probar el cierre al alejarse).
"""

import calendar
import datetime as dt
import json
import os
import socket
import subprocess
import sys

RUN = os.path.join(os.environ.get("XDG_RUNTIME_DIR", "/tmp"), "waybar-calendar")
PIDFILE = os.path.join(RUN, "popup.pid")
COLORS = os.path.expanduser("~/.config/waybar/colors.css")
HYPR_SOCK = os.path.join(os.environ.get("XDG_RUNTIME_DIR", "/tmp"), "hypr",
                         os.environ.get("HYPRLAND_INSTANCE_SIGNATURE", ""), ".socket.sock")
HERE = os.path.dirname(os.path.realpath(__file__))
TOP, LEFT = 44, 14   # esquina de la tarjeta (debajo del reloj, alineada con la barra)
SHADOW = 14          # margen CSS de la tarjeta (lugar para la sombra)
AWAY_CLOSE = 0.7     # s con el mouse lejos -> se cierra
ZONE_PAD = 16

I_PREV, I_NEXT = "\uf104", "\uf105"                    # FA angle-left / angle-right
I_PREV2, I_NEXT2 = "\uf100", "\uf101"                  # FA angles-left / angles-right
I_TODAY = "\U000F00F6"                                 # 󰃶  calendar-today
MONTHS = [calendar.month_name[i] for i in range(1, 13)]
MONTHS_SHORT = [calendar.month_abbr[i] for i in range(1, 13)]


def week_start():
    """Primer día de la semana según el locale (LC_TIME): 0 = lunes ... 6 = domingo."""
    try:
        out = subprocess.run(["locale", "-k", "LC_TIME"], capture_output=True, text=True,
                             timeout=1).stdout
        vals = dict(l.split("=", 1) for l in out.splitlines() if "=" in l)
        # week-1stday = una fecha que cae en el "día 1" del locale (19971130 = domingo);
        # first_weekday = cuál de esos días abre la semana (1 = ese mismo)
        d = vals.get("week-1stday", "19971130").strip('"')
        base = dt.date(int(d[:4]), int(d[4:6]), int(d[6:8]))
        return (base.weekday() + int(vals.get("first_weekday", "1")) - 1) % 7
    except Exception:
        return 6


def hypr(cmd):
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        s.connect(HYPR_SOCK)
        s.sendall(f"j/{cmd}".encode())
        buf = b""
        while chunk := s.recv(65536):
            buf += chunk
    return json.loads(buf)


def running_pid():
    try:
        pid = int(open(PIDFILE).read().split()[0])
        if b"calendar-popup" in open(f"/proc/{pid}/cmdline", "rb").read() and pid != os.getpid():
            return pid
    except (OSError, ValueError, IndexError):
        pass
    return None


CSS = """
@import url("file://%(colors)s");
* {
    font-family: "JetBrainsMono Nerd Font Propo";
    text-shadow: none;
    -gtk-icon-shadow: none;
}
window { background-color: transparent; }
stack, grid { background-color: transparent; }   /* adw-gtk3 le pone fondo al stack */
#card {
    background-color: @surface_container;
    border: 1px solid alpha(@primary, 0.22);
    border-radius: 24px;
    padding: 16px 18px 12px 18px;
    color: @on_surface;
    box-shadow: 0 6px 16px 0 alpha(@shadow, 0.45);
    margin: 14px;
}
button {
    min-width: 0;
    min-height: 0;
    padding: 4px 8px;
    border: none;
    border-radius: 10px;
    background-image: none;
    background-color: transparent;
    box-shadow: inset 0 0 0 1px alpha(@primary, 0);
    color: @on_surface;
    outline: none;
    transition: color 0.2s ease, background-color 0.2s ease, box-shadow 0.25s ease;
}
button:hover {
    color: @primary;
    background-color: alpha(@primary, 0.12);
    box-shadow: inset 0 0 0 1px alpha(@primary, 0.25);
}
button:active { background-color: alpha(@primary, 0.22); }
.nav     { color: @outline; font-size: 115%%; padding: 4px 6px; }
#title-m { font-weight: bold; font-size: 125%%; padding: 4px 6px; }
#title-y { color: @secondary; font-size: 125%%; padding: 4px 6px; }
#title-m.open, #title-y.open { color: @primary; background-color: alpha(@primary, 0.12); }
.wd      { color: @outline; font-size: 80%%; font-weight: bold; }
.wk      { color: alpha(@outline, 0.6); font-size: 75%%; }
.day {
    min-width: 34px;
    min-height: 30px;
    padding: 0;
    border-radius: 12px;
    font-size: 95%%;
}
.day.wkend  { color: @secondary; }
.day.other  { color: alpha(@outline, 0.55); }
.day.today  {
    color: @on_primary;
    background-color: @primary;
    font-weight: bold;
    box-shadow: inset 0 0 0 1px alpha(@primary, 0), 0 0 6px 0 alpha(@primary, 0.40);
}
.day.today:hover { background-color: @primary_fixed_dim; color: @on_primary; }
.pick {
    min-width: 60px;
    min-height: 40px;
    border-radius: 14px;
}
.pick.cur   { color: @primary; box-shadow: inset 0 0 0 1px alpha(@primary, 0.45); }
.pick.sel   { color: @on_primary; background-color: @primary; font-weight: bold; }
.pick.sel:hover { background-color: @primary_fixed_dim; color: @on_primary; }
#foot       { color: @outline; font-size: 85%%; }
#today-btn  { color: @outline; font-size: 90%%; padding: 3px 10px; }
#today-btn:hover { color: @primary; }
""" % {"colors": COLORS}


def run_popup():
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

    WS = week_start()
    cal = calendar.Calendar(firstweekday=WS)

    class Popup(Gtk.Window):
        def __init__(self):
            super().__init__()
            today = dt.date.today()
            self.today = today
            self.year, self.month = today.year, today.month
            m = os.environ.get("CALENDAR_POPUP_MONTH")
            if m:
                self.year, self.month = int(m[:4]), int(m[5:7])
            self.year_page = self.year - (self.year % 12)       # grilla de años: 12 por página
            self.view = "days"
            self.mon_x = self.mon_y = 0
            self.page = 0                                        # página visible del stack de días
            self.fade = 0.0
            self.anim_id = 0
            self.scroll_acc = 0.0

            self.setup_layer()
            self.build()
            self.connect("destroy", lambda *_: Gtk.main_quit())
            self.connect("key-press-event", self.on_key)
            self.connect("button-press-event", lambda *_: (self.destroy(), True)[1])
            self.connect("draw", self.draw_backdrop)
            self.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)

            self.fill_days(self.day_pages[0])
            self.fill_months()          # todas las vistas llenas desde el principio: el stack
            self.fill_years()           # homogéneo toma el tamaño mayor y la tarjeta no salta
            self.update_title()
            self.show_all()
            # GtkStack ignora el hijo visible elegido antes de mostrarse: fijarlo ahora
            self.days.set_visible_child_name("p0")
            self.views.set_visible_child_name("days")
            v = os.environ.get("CALENDAR_POPUP_VIEW")
            if v in ("months", "years"):
                self.set_view(v)
            self.t0 = GLib.get_monotonic_time()
            self.anim_id = GLib.timeout_add(16, self.step_fade)
            self.armed, self.away, self.closing = False, None, False
            if not self.test or os.environ.get("CALENDAR_POPUP_WATCH"):
                GLib.timeout_add(150, self.watch_cursor)
            if self.test:
                self.input_shape_combine_region(cairo.Region())   # clicks pasan de largo
                GLib.timeout_add(int(self.test * 1000), self.destroy)

        # ---- ventana --------------------------------------------------------
        def setup_layer(self):
            screen = self.get_screen()
            visual = screen.get_rgba_visual()
            if visual:
                self.set_visual(visual)
            self.set_app_paintable(True)
            L = GtkLayerShell
            L.init_for_window(self)
            L.set_namespace(self, "calendar-popup")   # no "waybar*": esa layer_rule (regex) le pondría blur
            L.set_layer(self, L.Layer.OVERLAY)
            self.test = float(os.environ.get("CALENDAR_POPUP_TEST") or 0)
            L.set_keyboard_mode(self, L.KeyboardMode.NONE if self.test
                                else L.KeyboardMode.EXCLUSIVE)
            L.set_exclusive_zone(self, -1)
            for e in (L.Edge.TOP, L.Edge.BOTTOM, L.Edge.LEFT, L.Edge.RIGHT):
                L.set_anchor(self, e, True)
            try:                                   # monitor del mouse (el de la barra clickeada)
                c = hypr("cursorpos")
                cx, cy = int(c["x"]), int(c["y"])
                display = Gdk.Display.get_default()
                for i in range(display.get_n_monitors()):
                    mo = display.get_monitor(i)
                    g = mo.get_geometry()
                    if g.x <= cx < g.x + g.width and g.y <= cy < g.y + g.height:
                        L.set_monitor(self, mo)
                        self.mon_x, self.mon_y = g.x, g.y
                        break
            except Exception:
                pass
            self.css = Gtk.CssProvider()
            self.css.load_from_data(CSS.encode())
            Gtk.StyleContext.add_provider_for_screen(
                screen, self.css, Gtk.STYLE_PROVIDER_PRIORITY_USER + 1)
            self.css_reload_id = 0
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
                self.css.load_from_data(CSS.encode())
                self.queue_draw()
            except GLib.Error:
                pass
            return False

        def color(self, name, alpha=1.0):
            ok, c = self.get_style_context().lookup_color(name)
            return (c.red, c.green, c.blue, c.alpha * alpha) if ok else (0, 0, 0, alpha)

        def draw_backdrop(self, _w, cr):
            # capa transparente (atrapa los clicks de afuera para cerrar); sin oscurecer
            cr.set_operator(cairo.OPERATOR_SOURCE)
            cr.set_source_rgba(0, 0, 0, 0)
            cr.paint()
            cr.set_operator(cairo.OPERATOR_OVER)
            return False

        def step_fade(self):
            # entrada: la tarjeta baja 10 px desde la barra mientras aparece
            t = (GLib.get_monotonic_time() - self.t0) / 260_000
            a = 1 - (1 - min(t, 1.0)) ** 3                   # ease-out cubic
            self.ev.set_opacity(a)
            self.ev.set_margin_top(TOP - SHADOW - int(round(10 * (1 - a))))
            if t >= 1.0:
                self.anim_id = 0
                return False
            return True

        def watch_cursor(self):
            """Como el menú de música: se cierra si el mouse está lejos de la tarjeta (y
            del reloj, arriba) un momento, pero recién después de haber estado adentro."""
            if self.closing:
                return False
            try:
                c = hypr("cursorpos")
                a = self.ev.get_allocation()
                x0 = self.mon_x + a.x + SHADOW - ZONE_PAD
                x1 = self.mon_x + a.x + a.width - SHADOW + ZONE_PAD
                y0 = self.mon_y
                y1 = self.mon_y + a.y + a.height - SHADOW + ZONE_PAD
            except Exception:
                return True
            if x0 <= c["x"] <= x1 and y0 <= c["y"] <= y1:
                self.armed, self.away = True, None
            elif self.armed:
                now = GLib.get_monotonic_time() / 1e6
                if self.away is None:
                    self.away = now
                elif now - self.away >= AWAY_CLOSE:
                    self.closing = True
                    self.destroy()
                    return False
            return True

        # ---- armado ---------------------------------------------------------
        def nav_button(self, glyph, tip, fn):
            b = Gtk.Button(label=glyph)
            b.get_style_context().add_class("nav")
            b.set_tooltip_text(tip)
            b.set_can_focus(False)
            b.set_relief(Gtk.ReliefStyle.NONE)
            b.connect("clicked", lambda *_: fn())
            return b

        def build(self):
            ev = Gtk.EventBox()                # frena los clicks: adentro de la tarjeta no cierra
            ev.set_halign(Gtk.Align.START)
            ev.set_valign(Gtk.Align.START)
            ev.set_margin_start(LEFT - SHADOW)
            ev.set_margin_top(TOP - SHADOW - 10)
            ev.set_opacity(0)
            self.ev = ev
            ev.connect("button-press-event", lambda *_: True)
            ev.connect("scroll-event", self.on_scroll)
            ev.add_events(Gdk.EventMask.SCROLL_MASK | Gdk.EventMask.SMOOTH_SCROLL_MASK)
            self.add(ev)
            card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
            card.set_name("card")
            ev.add(card)

            head = Gtk.Box(spacing=2)
            card.pack_start(head, False, False, 0)
            self.b_prev2 = self.nav_button(I_PREV2, "Previous year", lambda: self.shift(-12))
            self.b_prev = self.nav_button(I_PREV, "Previous month", lambda: self.shift(-1))
            self.b_next = self.nav_button(I_NEXT, "Next month", lambda: self.shift(1))
            self.b_next2 = self.nav_button(I_NEXT2, "Next year", lambda: self.shift(12))
            head.pack_start(self.b_prev2, False, False, 0)
            head.pack_start(self.b_prev, False, False, 0)
            mid = Gtk.Box(spacing=2)
            mid.set_halign(Gtk.Align.CENTER)
            self.t_month = Gtk.Button()
            self.t_month.set_name("title-m")
            self.t_month.set_tooltip_text("Pick a month")
            self.t_year = Gtk.Button()
            self.t_year.set_name("title-y")
            self.t_year.set_tooltip_text("Pick a year")
            for b, v in ((self.t_month, "months"), (self.t_year, "years")):
                b.set_can_focus(False)
                b.set_relief(Gtk.ReliefStyle.NONE)
                b.connect("clicked", lambda _b, v=v: self.set_view("days" if self.view == v else v))
                mid.pack_start(b, False, False, 0)
            head.set_center_widget(mid)
            head.pack_end(self.b_next2, False, False, 0)
            head.pack_end(self.b_next, False, False, 0)

            # vistas: días (dos páginas para deslizar entre meses) / meses / años
            self.views = Gtk.Stack()
            self.views.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
            self.views.set_transition_duration(160)
            self.views.set_homogeneous(True)
            card.pack_start(self.views, False, False, 0)

            self.days = Gtk.Stack()
            self.days.set_transition_duration(220)
            self.day_pages = []
            for i in range(2):
                g = Gtk.Grid(row_spacing=2, column_spacing=2)
                self.day_pages.append(g)
                self.days.add_named(g, f"p{i}")
            self.views.add_named(self.days, "days")

            self.months_grid = Gtk.Grid(row_spacing=6, column_spacing=6)
            self.months_grid.set_halign(Gtk.Align.CENTER)
            self.months_grid.set_valign(Gtk.Align.CENTER)
            self.views.add_named(self.months_grid, "months")
            self.years_grid = Gtk.Grid(row_spacing=6, column_spacing=6)
            self.years_grid.set_halign(Gtk.Align.CENTER)
            self.years_grid.set_valign(Gtk.Align.CENTER)
            self.views.add_named(self.years_grid, "years")

            foot = Gtk.Box()
            card.pack_start(foot, False, False, 0)
            self.l_foot = Gtk.Label(xalign=0)
            self.l_foot.set_name("foot")
            foot.pack_start(self.l_foot, True, True, 4)
            tb = Gtk.Button(label=f"{I_TODAY}  Today")
            tb.set_name("today-btn")
            tb.set_can_focus(False)
            tb.set_relief(Gtk.ReliefStyle.NONE)
            tb.set_tooltip_text("Back to today (Home)")
            tb.connect("clicked", lambda *_: self.go_today())
            foot.pack_end(tb, False, False, 0)

        def clear(self, grid):
            for ch in grid.get_children():
                grid.remove(ch)

        def fill_days(self, g):
            self.clear(g)
            # encabezado: columna de semana + nombres de los días
            lw = Gtk.Label(label="")
            lw.get_style_context().add_class("wk")
            g.attach(lw, 0, 0, 1, 1)
            for c in range(7):
                wd = (WS + c) % 7
                l = Gtk.Label(label=calendar.day_abbr[wd][:2])
                l.get_style_context().add_class("wd")
                g.attach(l, c + 1, 0, 1, 1)
            weeks = cal.monthdatescalendar(self.year, self.month)
            while len(weeks) < 6:                              # siempre 6 filas: el alto no salta
                last = weeks[-1][-1]
                weeks.append([last + dt.timedelta(days=i + 1) for i in range(7)])
            for r, week in enumerate(weeks, start=1):
                # número de semana ISO (la del jueves, como manda ISO 8601)
                thu = next((d for d in week if d.weekday() == 3), week[0])
                wl = Gtk.Label(label=str(thu.isocalendar()[1]))
                wl.get_style_context().add_class("wk")
                wl.set_margin_end(4)
                g.attach(wl, 0, r, 1, 1)
                for c, d in enumerate(week):
                    b = Gtk.Button(label=str(d.day))
                    b.set_can_focus(False)
                    b.set_relief(Gtk.ReliefStyle.NONE)
                    ctx = b.get_style_context()
                    ctx.add_class("day")
                    if d.month != self.month:
                        ctx.add_class("other")
                        b.connect("clicked", lambda _b, d=d: self.goto(d.year, d.month))
                    elif d.weekday() >= 5:
                        ctx.add_class("wkend")
                    if d == self.today:
                        ctx.add_class("today")
                    b.set_tooltip_text(d.strftime("%A, %d %B %Y"))
                    g.attach(b, c + 1, r, 1, 1)
            g.show_all()

        def fill_months(self):
            self.clear(self.months_grid)
            for i, name in enumerate(MONTHS_SHORT):
                b = Gtk.Button(label=name)
                b.set_can_focus(False)
                b.set_relief(Gtk.ReliefStyle.NONE)
                ctx = b.get_style_context()
                ctx.add_class("pick")
                if i + 1 == self.month:
                    ctx.add_class("sel")
                if (self.year, i + 1) == (self.today.year, self.today.month):
                    ctx.add_class("cur")
                b.connect("clicked", lambda _b, m=i + 1: (self.goto(self.year, m), self.set_view("days")))
                self.months_grid.attach(b, i % 4, i // 4, 1, 1)
            self.months_grid.show_all()

        def fill_years(self):
            self.clear(self.years_grid)
            for i in range(12):
                y = self.year_page + i
                b = Gtk.Button(label=str(y))
                b.set_can_focus(False)
                b.set_relief(Gtk.ReliefStyle.NONE)
                ctx = b.get_style_context()
                ctx.add_class("pick")
                if y == self.year:
                    ctx.add_class("sel")
                if y == self.today.year:
                    ctx.add_class("cur")
                b.connect("clicked", lambda _b, y=y: (self.goto(y, self.month), self.set_view("months")))
                self.years_grid.attach(b, i % 4, i // 4, 1, 1)
            self.years_grid.show_all()

        # ---- navegación ----------------------------------------------------
        def update_title(self):
            self.t_month.set_label(MONTHS[self.month - 1])
            if self.view == "years":
                self.t_year.set_label(f"{self.year_page} – {self.year_page + 11}")
            else:
                self.t_year.set_label(str(self.year))
            for b, v in ((self.t_month, "months"), (self.t_year, "years")):
                ctx = b.get_style_context()
                (ctx.add_class if self.view == v else ctx.remove_class)("open")
            self.t_month.set_visible(self.view != "years")
            days_only = self.view == "days"
            self.b_prev2.set_visible(days_only)
            self.b_next2.set_visible(days_only)
            tips = {"days": ("Previous month", "Next month"),
                    "months": ("Previous year", "Next year"),
                    "years": ("Previous 12 years", "Next 12 years")}[self.view]
            self.b_prev.set_tooltip_text(tips[0])
            self.b_next.set_tooltip_text(tips[1])
            t = self.today
            delta = (self.year - t.year) * 12 + (self.month - t.month)
            if delta == 0:
                self.l_foot.set_text(t.strftime("%A, %d %B"))
            else:
                n = abs(delta)
                unit = "month" if n == 1 else "months"
                self.l_foot.set_text(f"{n} {unit} {'ahead' if delta > 0 else 'ago'}")

        def goto(self, y, m, direction=None):
            y = max(1, min(9999, y))
            if (y, m) == (self.year, self.month):
                return
            if direction is None:
                direction = 1 if (y, m) > (self.year, self.month) else -1
            self.year, self.month = y, m
            if self.view == "days":
                # el mes nuevo se arma en la página oculta y se desliza
                self.page = 1 - self.page
                self.fill_days(self.day_pages[self.page])
                T = Gtk.StackTransitionType
                self.days.set_visible_child_full(
                    f"p{self.page}", T.SLIDE_LEFT if direction > 0 else T.SLIDE_RIGHT)
            else:
                self.fill_days(self.day_pages[self.page])
                self.days.set_visible_child_name(f"p{self.page}")
            if self.view == "months":
                self.fill_months()
            self.update_title()

        def shift(self, n):
            """n meses en la vista de días; en meses mueve años y en años, páginas de 12."""
            if self.view == "months":
                n = 12 if n > 0 else -12
            elif self.view == "years":
                self.year_page += 12 if n > 0 else -12
                self.fill_years()
                self.update_title()
                return
            idx = self.year * 12 + (self.month - 1) + n
            self.goto(idx // 12, idx % 12 + 1, 1 if n > 0 else -1)

        def go_today(self):
            self.set_view("days")
            self.goto(self.today.year, self.today.month)

        def set_view(self, v):
            self.view = v
            if v == "months":
                self.fill_months()
            elif v == "years":
                self.year_page = self.year - (self.year % 12)
                self.fill_years()
            self.views.set_visible_child_name(v)
            self.update_title()

        def on_scroll(self, _w, ev):
            step = 0
            if ev.direction in (Gdk.ScrollDirection.DOWN, Gdk.ScrollDirection.RIGHT):
                step = 1
            elif ev.direction in (Gdk.ScrollDirection.UP, Gdk.ScrollDirection.LEFT):
                step = -1
            elif ev.direction == Gdk.ScrollDirection.SMOOTH:
                ok, dx, dy = ev.get_scroll_deltas()
                self.scroll_acc += dy or dx
                if abs(self.scroll_acc) >= 1:
                    step = 1 if self.scroll_acc > 0 else -1
                    self.scroll_acc = 0.0
            if step:
                self.shift(step)
            return True

        def on_key(self, _w, ev):
            k = ev.keyval
            K = Gdk
            if k == K.KEY_Escape:
                if self.view != "days":
                    self.set_view("days")
                else:
                    self.destroy()
            elif k in (K.KEY_Right, K.KEY_l, K.KEY_Page_Down):
                self.shift(1)
            elif k in (K.KEY_Left, K.KEY_h, K.KEY_Page_Up):
                self.shift(-1)
            elif k in (K.KEY_Down, K.KEY_j):
                self.shift(12)
            elif k in (K.KEY_Up, K.KEY_k):
                self.shift(-12)
            elif k in (K.KEY_Home, K.KEY_t, K.KEY_T):
                self.go_today()
            elif k in (K.KEY_m, K.KEY_M):
                self.set_view("days" if self.view == "months" else "months")
            elif k in (K.KEY_y, K.KEY_Y):
                self.set_view("days" if self.view == "years" else "years")
            else:
                return False
            return True

    win = Popup()

    def bye(*_):
        win.destroy()
        return False
    unix_signal_add(GLib.PRIORITY_DEFAULT, 15, bye)
    unix_signal_add(GLib.PRIORITY_DEFAULT, 2, bye)
    Gtk.main()


def close_other_popups(me):
    """Ventanas de la waybar: solo una abierta a la vez (popups.sh)."""
    try:
        subprocess.run([os.path.join(HERE, "popups.sh"), "close-except", me], timeout=3)
    except Exception:
        pass


def main():
    pid = running_pid()
    if pid:                         # ya abierto: cerrarlo (toggle)
        os.kill(pid, 15)
        return
    close_other_popups("calendar")
    os.makedirs(RUN, exist_ok=True)
    with open(PIDFILE, "w") as f:
        f.write(str(os.getpid()))
    try:
        run_popup()
    finally:
        try:
            if int(open(PIDFILE).read().split()[0]) == os.getpid():
                os.remove(PIDFILE)
        except (OSError, ValueError, IndexError):
            pass


if __name__ == "__main__":
    main()
