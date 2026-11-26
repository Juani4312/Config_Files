#!/usr/bin/env python3
"""Popup del clima (click derecho en el módulo de temperatura de waybar).

Tarjeta centrada en el monitor donde está el mouse, con la temperatura de
Buenos Aires hora por hora, para hoy y los próximos 6 días (fila de días
arriba del gráfico; también ← / → o la rueda del mouse). Cada día va de las
00 a las 00 del día siguiente: curva suave (Cairo), sensación térmica
punteada, marca de "ahora" (hoy), mín/máx, horas de noche sombreadas y una
tira cada 3 h con ícono, temperatura y probabilidad de lluvia. Al pasar el
mouse por el gráfico (o por la tira) muestra el detalle de esa hora.

GTK3 + layer-shell a pantalla completa con el fondo apenas oscurecido:
se cierra con Esc, con click fuera de la tarjeta o volviendo a correr
este script (toggle, por el pid en $XDG_RUNTIME_DIR/waybar-weather).
Colores de matugen (~/.config/waybar/colors.css), se recarga en vivo.
Namespace "weather-popup": la layer_rule de Hyprland `namespace = "waybar"`
es una regex y también agarraría "waybar-*" (blur + ignore_alpha).

Si no hay layer-shell (u otra cosa falla al abrir GTK) o con --html, genera
~/.cache/waybar-weather/today.html con la misma información (pestañas por
día) y lo abre en el navegador.

Datos: el cache de weather.py (~/.cache/waybar-weather.json, 7 días); si
tiene más de 15 min o es de otro día, los pide de nuevo a Open-Meteo.

Prueba sin molestar a quien usa la compu: WEATHER_POPUP_TEST=<segundos>
(no toma teclado ni mouse y se cierra solo), WEATHER_POPUP_HOVER=<hora>,
WEATHER_POPUP_DAY=<índice de día>.
"""

import datetime as dt
import html
import json
import math
import os
import re
import socket
import subprocess
import sys
import threading
import time
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
import weather as W  # noqa: E402

RUN = os.path.join(os.environ.get("XDG_RUNTIME_DIR", "/tmp"), "waybar-weather")
PIDFILE = os.path.join(RUN, "popup.pid")
COLORS = os.path.expanduser("~/.config/waybar/colors.css")
HTML_DIR = os.path.join(os.environ.get("XDG_CACHE_HOME") or os.path.expanduser("~/.cache"),
                        "waybar-weather")
FRESH = 15 * 60
TZ = ZoneInfo(W.TZ)
HYPR_SOCK = os.path.join(os.environ.get("XDG_RUNTIME_DIR", "/tmp"), "hypr",
                         os.environ.get("HYPRLAND_INSTANCE_SIGNATURE", ""), ".socket.sock")

I_RAIN = "\U000F058C"      # water
I_SUNRISE = "\U000F059C"   # weather-sunset-up
I_SUNSET = "\U000F059B"    # weather-sunset-down
I_WEB = "\U000F059F"       # web
I_REFRESH = "\U000F0450"   # refresh

CARD_W = 680
CHART_H = 230


# ---- datos ------------------------------------------------------------------
def now_local():
    return dt.datetime.now(TZ)


def is_usable(data):
    try:
        return (data["hourly"]["time"][0][:10] == now_local().strftime("%Y-%m-%d")
                and len(data["hourly"]["temperature_2m"]) >= 24)
    except (KeyError, IndexError, TypeError):
        return False


def is_fresh(data):
    return is_usable(data) and time.time() - data.get("_fetched", 0) < FRESH


def cached():
    try:
        return W.load_cache()
    except Exception:
        return None


def fetch_and_cache():
    data = W.fetch()
    W.save_cache(data)
    return data


def frac_hour(iso):
    """'2026-11-26T05:35' -> 5.583"""
    t = iso[11:16]
    return int(t[:2]) + int(t[3:]) / 60


def n_days(data):
    return min(len(data["daily"]["time"]), len(data["hourly"]["time"]) // 24)


def day_names(data, d):
    """(nombre corto para la fila de días, fecha larga)."""
    date = dt.date.fromisoformat(data["daily"]["time"][d])
    short = "Today" if d == 0 else "Tomorrow" if d == 1 else date.strftime("%a %-d")
    return short, date.strftime("%A, %B %-d")


def days(data):
    """Lo que muestra cada botón de la fila de días."""
    dl = data["daily"]
    out = []
    for d in range(n_days(data)):
        _desc, _g, icon = W.describe(dl.get("weather_code", [0] * 7)[d], 1)
        out.append({"d": d, "name": day_names(data, d)[0], "icon": icon,
                    "tmax": dl["temperature_2m_max"][d], "tmin": dl["temperature_2m_min"][d]})
    return out


def summary(data, d=0):
    """Todo lo que muestran el popup y la página para el día d, ya masticado.

    hours tiene 25 puntos (00..24, el último es las 00 del día siguiente) si
    hay datos; si no, 24.
    """
    hr, cur, dl = data["hourly"], data["current"], data["daily"]
    start = d * 24
    end = min(start + 25, len(hr["time"]))
    hours = []
    for k, i in enumerate(range(start, end)):
        desc, _g, icon = W.describe(hr["weather_code"][i], hr["is_day"][i])
        hours.append({
            "h": k,
            "t": hr["temperature_2m"][i],
            "feels": hr["apparent_temperature"][i],
            "pop": hr["precipitation_probability"][i] or 0,
            "desc": desc, "icon": icon,
        })
    s = {
        "d": d,
        "hours": hours,
        "tmin": dl["temperature_2m_min"][d], "tmax": dl["temperature_2m_max"][d],
        "sunrise": frac_hour(dl["sunrise"][d]), "sunset": frac_hour(dl["sunset"][d]),
        "sunrise_s": dl["sunrise"][d][11:16], "sunset_s": dl["sunset"][d][11:16],
        "updated": cur["time"][11:16],
        "name": day_names(data, d)[0],
        "date": day_names(data, d)[1],
        "now": None,
    }
    if d == 0:
        desc, _g, icon = W.describe(cur["weather_code"], cur.get("is_day", 1))
        now = now_local()
        s.update({
            "icon": icon, "desc": desc,
            "sub": f"{desc} · Feels like {round(cur['apparent_temperature'])}°",
            "cur_t": cur["temperature_2m"],
            "humidity": cur.get("relative_humidity_2m"), "wind": cur.get("wind_speed_10m"),
            "now": now.hour + now.minute / 60,
        })
    else:
        desc, _g, icon = W.describe(dl.get("weather_code", [0] * 7)[d], 1)
        pop = (dl.get("precipitation_probability_max") or [0] * 7)[d] or 0
        s.update({
            "icon": icon, "desc": desc,
            "sub": desc + (f" · {I_RAIN} {pop}%" if pop else ""),
            "cur_t": None, "humidity": None, "wind": None,
        })
    return s


# ---- curva monótona (Fritsch-Carlson: suave y sin pasarse de mín/máx) -------
def tangents(ys):
    n = len(ys)
    d = [ys[i + 1] - ys[i] for i in range(n - 1)]
    m = [d[0]] + [0.0] * (n - 2) + [d[-1]]
    for i in range(1, n - 1):
        m[i] = 0.0 if d[i - 1] * d[i] <= 0 else (d[i - 1] + d[i]) / 2
    for i in range(n - 1):
        if d[i] == 0:
            m[i] = m[i + 1] = 0.0
            continue
        a, b = m[i] / d[i], m[i + 1] / d[i]
        s = a * a + b * b
        if s > 9:
            k = 3 / math.sqrt(s)
            m[i], m[i + 1] = k * a * d[i], k * b * d[i]
    return m


def segments(ys, X, Y):
    """Bezier cúbicas en píxeles: [(c1, c2, p2), ...] desde (X(0), Y(ys[0]))."""
    m = tangents(ys)
    out = []
    for i in range(len(ys) - 1):
        out.append(((X(i + 1 / 3), Y(ys[i] + m[i] / 3)),
                    (X(i + 2 / 3), Y(ys[i + 1] - m[i + 1] / 3)),
                    (X(i + 1), Y(ys[i + 1]))))
    return out


def curve_at(ys, fh):
    """Valor de la curva en una hora fraccionaria (Hermite, igual que el dibujo)."""
    m = tangents(ys)
    i = max(0, min(int(fh), len(ys) - 2))
    t = fh - i
    t2, t3 = t * t, t * t * t
    return ((2 * t3 - 3 * t2 + 1) * ys[i] + (t3 - 2 * t2 + t) * m[i]
            + (-2 * t3 + 3 * t2) * ys[i + 1] + (t3 - t2) * m[i + 1])


def y_range(vals):
    lo, hi = min(vals), max(vals)
    for step in (1, 2, 5, 10):
        if (hi - lo + 2) / step <= 5:
            break
    lo = math.floor((lo - 1) / step) * step
    hi = math.ceil((hi + 1) / step) * step
    return lo, hi, step


def minmax_idx(temps):
    """Índices de mín/máx dentro del día (sin el punto de las 00 siguiente)."""
    day = temps[:24]
    return day.index(max(day)), day.index(min(day))


# ---- página HTML (respaldo) -------------------------------------------------
def read_colors():
    cols = {}
    try:
        for name, val in re.findall(r"@define-color\s+(\w+)\s+(#[0-9a-fA-F]{6})", open(COLORS).read()):
            cols[name] = val
    except OSError:
        pass
    base = {"surface": "#121416", "surface_container": "#1e2022",
            "surface_container_high": "#282a2c", "on_surface": "#e2e2e5",
            "on_surface_variant": "#c4c6cf", "primary": "#a8c8ff",
            "secondary": "#bec6dc", "tertiary": "#ddbce0", "outline": "#8e9099",
            "outline_variant": "#44474e", "scrim": "#000000"}
    base.update(cols)
    return base


def html_day(s):
    """Panel de un día: encabezado, gráfico SVG, leyenda y tira."""
    hours = s["hours"]
    temps = [h["t"] for h in hours]
    feels = [h["feels"] for h in hours]
    N = len(hours) - 1
    lo, hi, step = y_range(temps + feels)
    W_, H_ = 620, 240
    pl, pr, pt, pb = 38, 16, 28, 28
    cw, ch = W_ - pl - pr, H_ - pt - pb
    X = lambda i: pl + i * cw / N  # noqa: E731
    Y = lambda v: pt + (hi - v) / (hi - lo) * ch  # noqa: E731

    def path(ys):
        d = f"M{X(0):.1f},{Y(ys[0]):.1f}"
        for (a, b, p) in segments(ys, X, Y):
            d += f" C{a[0]:.1f},{a[1]:.1f} {b[0]:.1f},{b[1]:.1f} {p[0]:.1f},{p[1]:.1f}"
        return d

    svg = []
    for x0, x1 in ((0, s["sunrise"]), (s["sunset"], N)):
        if x1 > x0:
            svg.append(f'<rect x="{X(x0):.1f}" y="{pt}" width="{X(x1) - X(x0):.1f}" '
                       f'height="{ch}" class="night"/>')
    v = lo
    while v <= hi + 1e-9:
        svg.append(f'<line x1="{pl}" x2="{W_ - pr}" y1="{Y(v):.1f}" y2="{Y(v):.1f}" class="grid"/>'
                   f'<text x="{pl - 8}" y="{Y(v) + 4:.1f}" class="ylab">{v:g}°</text>')
        v += step
    for i in range(0, N + 1, 3):
        svg.append(f'<text x="{X(i):.1f}" y="{H_ - 8}" class="xlab">{i % 24:02d}</text>')
    tp = path(temps)
    svg.append(f'<path d="{tp} L{X(N):.1f},{pt + ch} L{X(0):.1f},{pt + ch} Z" fill="url(#fill)"/>')
    svg.append(f'<path d="{path(feels)}" class="feels"/>')
    svg.append(f'<path d="{tp}" class="temp"/>')
    imax, imin = minmax_idx(temps)
    for i, dy in ((imax, -10), (imin, 18)):
        svg.append(f'<circle cx="{X(i):.1f}" cy="{Y(temps[i]):.1f}" r="3.5" class="mm"/>'
                   f'<text x="{X(i):.1f}" y="{Y(temps[i]) + dy:.1f}" class="mmlab">{round(temps[i])}°</text>')
    if s["now"] is not None:
        nx, ny = X(s["now"]), Y(curve_at(temps, s["now"]))
        svg.append(f'<line x1="{nx:.1f}" x2="{nx:.1f}" y1="{pt}" y2="{pt + ch}" class="now"/>'
                   f'<text x="{nx:.1f}" y="{pt - 10}" class="nowlab">Now</text>'
                   f'<circle cx="{nx:.1f}" cy="{ny:.1f}" r="5.5" class="nowdot"/>')
    for h in hours:
        i = h["h"]
        x0 = max(pl, X(i - 0.5))
        x1 = min(W_ - pr, X(i + 0.5))
        bx = min(max(X(i) - 62, pl), W_ - pr - 124)
        pop = f" · {I_RAIN} {h['pop']}%" if h["pop"] else ""
        svg.append(
            f'<g class="hov"><rect x="{x0:.1f}" y="{pt}" width="{x1 - x0:.1f}" height="{ch}" class="hit"/>'
            f'<g class="tip"><line x1="{X(i):.1f}" x2="{X(i):.1f}" y1="{pt}" y2="{pt + ch}" class="hl"/>'
            f'<circle cx="{X(i):.1f}" cy="{Y(h["t"]):.1f}" r="4.5" class="nowdot"/>'
            f'<rect x="{bx:.1f}" y="2" width="124" height="22" rx="8" class="bub"/>'
            f'<text x="{bx + 62:.1f}" y="17" class="bubt">{i % 24:02d}:00 · {h["t"]:.1f}°{pop}</text></g></g>')

    strip = []
    for h in hours[:24:3]:
        now_cls = " now" if s["now"] is not None and h["h"] <= s["now"] < h["h"] + 3 else ""
        pop = f'{I_RAIN} {h["pop"]}%' if h["pop"] else "&nbsp;"
        strip.append(f'<div class="col{now_cls}" title="{html.escape(h["desc"])}">'
                     f'<div class="hh">{h["h"]:02d}:00</div><div class="ic">{h["icon"]}</div>'
                     f'<div class="tt">{round(h["t"])}°</div><div class="pp">{pop}</div></div>')

    if s["cur_t"] is not None:
        big = f'{round(s["cur_t"])}°'
        foot = f'Humidity {s["humidity"]}% · Wind {round(s["wind"] or 0)} km/h'
    else:
        big = f'{round(s["tmax"])}°<span class="big-lo"> / {round(s["tmin"])}°</span>'
        foot = ""
    return f"""
<div class="panel p{s['d']}">
  <div class="head">
    <div class="big-ic">{s['icon']}</div>
    <div><div class="city">Buenos Aires</div>
      <div class="sub">{html.escape(s['sub'])}</div>
      <div class="date">{s['date']}</div></div>
    <div class="right"><div class="temp-big">{big}</div>
      <div class="hl-lo">H {round(s['tmax'])}° · L {round(s['tmin'])}°</div></div>
  </div>
  <svg viewBox="0 0 {W_} {H_}">
    <defs><linearGradient id="fill{s['d']}" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="var(--primary)" stop-opacity=".32"/>
      <stop offset="1" stop-color="var(--primary)" stop-opacity="0"/></linearGradient></defs>
    {''.join(svg).replace('url(#fill)', f"url(#fill{s['d']})")}
  </svg>
  <div class="legend"><span><i></i>Temperature</span><span><i class="d"></i>Feels like</span>
    <span>{I_SUNRISE} {s['sunrise_s']}  {I_SUNSET} {s['sunset_s']}</span></div>
  <div class="strip">{''.join(strip)}</div>
  <div class="foot"><span>{foot}</span><span>Updated {s['updated']} · Open-Meteo</span></div>
</div>"""


def write_html(data, sel=0):
    c = read_colors()
    nd = n_days(data)
    radios = "".join(f'<input type="radio" name="day" id="d{d}"{" checked" if d == sel else ""}>'
                     for d in range(nd))
    tabs = "".join(
        f'<label for="d{x["d"]}"><span class="dn">{x["name"]}</span>'
        f'<span class="di">{x["icon"]}</span>'
        f'<span class="dt">{round(x["tmax"])}° <em>{round(x["tmin"])}°</em></span></label>'
        for x in days(data))
    panels = "".join(html_day(summary(data, d)) for d in range(nd))
    sel_css = "\n".join(
        f"#d{d}:checked ~ .card .p{d} {{ display: block; }}\n"
        f"#d{d}:checked ~ .card label[for=d{d}] {{ background: {c['primary']}24; "
        f"box-shadow: inset 0 0 0 1px {c['primary']}55; color: {c['on_surface']}; }}"
        for d in range(nd))

    page = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Buenos Aires · Temperature</title>
<style>
:root {{ color-scheme: dark; --primary: {c['primary']}; }}
* {{ box-sizing: border-box; }}
body {{ margin: 0; min-height: 100vh; display: grid; place-items: center;
  background: {c['surface']}; color: {c['on_surface']};
  font-family: "JetBrainsMono Nerd Font Propo", "JetBrainsMono Nerd Font", monospace; }}
input[name=day] {{ position: absolute; opacity: 0; pointer-events: none; }}
.card {{ width: 700px; max-width: calc(100vw - 24px); padding: 22px 22px 14px;
  background: {c['surface_container']}; border: 1px solid {c['primary']}38;
  border-radius: 24px; }}
.days {{ display: grid; grid-template-columns: repeat({nd}, 1fr); gap: 4px; margin-bottom: 14px; }}
.days label {{ display: flex; flex-direction: column; align-items: center; gap: 2px;
  padding: 6px 0; border-radius: 14px; cursor: pointer; color: {c['outline']};
  transition: background .2s, box-shadow .2s, color .2s; }}
.days label:hover {{ background: {c['primary']}14; color: {c['on_surface']}; }}
.dn {{ font-size: 11px; }}
.di {{ font-size: 18px; color: {c['primary']}; }}
.dt {{ font-size: 12px; font-weight: bold; color: {c['on_surface']}; }}
.dt em {{ font-style: normal; font-weight: normal; color: {c['outline']}; }}
.panel {{ display: none; }}
{sel_css}
.head {{ display: flex; align-items: center; gap: 14px; }}
.big-ic {{ font-size: 42px; color: {c['primary']}; }}
.city {{ font-weight: bold; font-size: 18px; }}
.sub {{ color: {c['secondary']}; margin-top: 2px; }}
.date {{ color: {c['outline']}; font-size: 12px; margin-top: 2px; }}
.right {{ margin-left: auto; text-align: right; }}
.temp-big {{ font-size: 44px; font-weight: bold; line-height: 1; }}
.big-lo {{ font-size: 22px; color: {c['outline']}; font-weight: normal; }}
.hl-lo {{ color: {c['outline']}; font-size: 13px; margin-top: 4px; }}
svg {{ width: 100%; height: auto; display: block; margin-top: 12px; }}
.night {{ fill: {c['on_surface']}; fill-opacity: .04; }}
.grid {{ stroke: {c['outline_variant']}; stroke-opacity: .6; stroke-width: 1; }}
.ylab {{ fill: {c['outline']}; font-size: 11px; text-anchor: end; }}
.xlab {{ fill: {c['outline']}; font-size: 11px; text-anchor: middle; }}
.temp {{ fill: none; stroke: {c['primary']}; stroke-width: 2.5; stroke-linecap: round; }}
.feels {{ fill: none; stroke: {c['secondary']}; stroke-opacity: .7; stroke-width: 1.5; stroke-dasharray: 4 4; }}
.mm {{ fill: {c['on_surface']}; }}
.mmlab {{ fill: {c['on_surface']}; font-size: 12px; font-weight: bold; text-anchor: middle; }}
.now {{ stroke: {c['on_surface']}; stroke-opacity: .35; stroke-dasharray: 3 4; }}
.nowlab {{ fill: {c['primary']}; font-size: 11px; font-weight: bold; text-anchor: middle; }}
.nowdot {{ fill: {c['primary']}; stroke: {c['surface_container']}; stroke-width: 2.5; }}
.hit {{ fill: transparent; }}
.tip {{ opacity: 0; transition: opacity .15s; pointer-events: none; }}
.hov:hover .tip {{ opacity: 1; }}
.hl {{ stroke: {c['primary']}; stroke-opacity: .45; }}
.bub {{ fill: {c['surface_container_high']}; stroke: {c['primary']}55; }}
.bubt {{ fill: {c['on_surface']}; font-size: 11px; text-anchor: middle; }}
.legend {{ display: flex; gap: 16px; color: {c['outline']}; font-size: 11px; margin: 4px 0 0 38px; }}
.legend i {{ display: inline-block; width: 18px; height: 0; vertical-align: middle; margin-right: 6px;
  border-top: 2.5px solid {c['primary']}; }}
.legend i.d {{ border-top: 1.5px dashed {c['secondary']}; }}
.strip {{ display: grid; grid-template-columns: repeat(8, 1fr); gap: 4px; margin-top: 14px; }}
.col {{ text-align: center; padding: 8px 0; border-radius: 14px; }}
.col.now {{ background: {c['primary']}1f; box-shadow: inset 0 0 0 1px {c['primary']}40; }}
.hh {{ color: {c['outline']}; font-size: 11px; }}
.ic {{ color: {c['primary']}; font-size: 22px; margin: 4px 0; }}
.tt {{ font-weight: bold; }}
.pp {{ color: {c['secondary']}; font-size: 11px; margin-top: 2px; }}
.foot {{ display: flex; justify-content: space-between; color: {c['outline']}; font-size: 11px;
  margin-top: 12px; }}
</style></head><body>
{radios}
<div class="card">
  <div class="days">{tabs}</div>
  {panels}
</div></body></html>
"""
    os.makedirs(HTML_DIR, exist_ok=True)
    out = os.path.join(HTML_DIR, "today.html")
    with open(out, "w") as f:
        f.write(page)
    return out


def open_html(data, sel=0):
    path = write_html(data, sel)
    subprocess.Popen(["xdg-open", path], stdout=subprocess.DEVNULL,
                     stderr=subprocess.DEVNULL, start_new_session=True)


def data_for_html():
    data = cached()
    if not is_fresh(data or {}):
        try:
            data = fetch_and_cache()
        except Exception:
            pass
    return data if is_usable(data or {}) else None


# ---- toggle -----------------------------------------------------------------
def running_pid():
    try:
        pid = int(open(PIDFILE).read().split()[0])
        if b"weather-popup" in open(f"/proc/{pid}/cmdline", "rb").read() and pid != os.getpid():
            return pid
    except (OSError, ValueError, IndexError):
        pass
    return None


def hypr(cmd):
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
    padding: 16px 22px 12px 22px;
    color: @on_surface;
    box-shadow: 0 8px 28px 0 alpha(@shadow, 0.45);
    margin: 30px;
}
#big-icon { color: @primary; font-size: 300%%; }
#city     { font-weight: bold; font-size: 125%%; }
#sub      { color: @secondary; }
#date     { color: @outline; font-size: 85%%; }
#big-temp { font-weight: bold; font-size: 310%%; }
#hilo     { color: @outline; font-size: 90%%; }
#legend   { color: @outline; font-size: 80%%; }
#foot     { color: @outline; font-size: 80%%; }
.col {
    padding: 8px 0;
    border-radius: 14px;
    background-color: transparent;
    box-shadow: inset 0 0 0 1px alpha(@primary, 0);
    transition: background-color 0.2s ease, box-shadow 0.2s ease;
}
.col.now  { background-color: alpha(@primary, 0.12); box-shadow: inset 0 0 0 1px alpha(@primary, 0.25); }
.col.hover { background-color: alpha(@primary, 0.07); }
.col.now.hover { background-color: alpha(@primary, 0.17); }
.col-h  { color: @outline; font-size: 80%%; }
.col-ic { color: @primary; font-size: 160%%; }
.col-t  { font-weight: bold; }
.col-p  { color: @secondary; font-size: 80%%; }
button {
    min-width: 0;
    min-height: 0;
    padding: 2px 8px;
    border: none;
    border-radius: 10px;
    background-image: none;
    background-color: transparent;
    box-shadow: inset 0 0 0 1px alpha(@primary, 0);
    color: @outline;
    outline: none;
    transition: color 0.2s ease, background-color 0.2s ease, box-shadow 0.25s ease;
}
button:hover {
    color: @primary;
    background-color: alpha(@primary, 0.12);
    box-shadow: inset 0 0 0 1px alpha(@primary, 0.25);
}
/* fila de días */
button.day { padding: 6px 0; border-radius: 14px; }
button.day.sel {
    background-color: alpha(@primary, 0.14);
    box-shadow: inset 0 0 0 1px alpha(@primary, 0.32);
}
button.day.sel:hover { background-color: alpha(@primary, 0.18); }
.day-n  { color: @outline; font-size: 80%%; }
button.day.sel .day-n, button.day:hover .day-n { color: @on_surface; }
.day-ic { color: @primary; font-size: 130%%; }
.day-t  { color: @on_surface; font-size: 85%%; font-weight: bold; }
""" % {"colors": COLORS}


def run_popup(data):
    import gi
    gi.require_version("Gtk", "3.0")
    gi.require_version("Gdk", "3.0")
    gi.require_version("GtkLayerShell", "0.1")
    gi.require_version("PangoCairo", "1.0")
    from gi.repository import Gdk, Gio, GLib, Gtk, GtkLayerShell, Pango, PangoCairo
    import cairo

    try:                                    # PyGObject >= 3.52
        gi.require_version("GLibUnix", "2.0")
        from gi.repository import GLibUnix
        unix_signal_add = GLibUnix.signal_add
    except (ImportError, ValueError):
        unix_signal_add = GLib.unix_signal_add

    if not Gtk.init_check()[0] or not GtkLayerShell.is_supported():
        raise RuntimeError("no layer-shell")

    class Popup(Gtk.Window):
        def __init__(self, data):
            super().__init__()
            self.data = None
            self.s = None
            self.day = int(os.environ.get("WEATHER_POPUP_DAY") or 0)
            self.hover = None          # hora resaltada (gráfico o tira)
            self.anim = 0.0            # 0..1, entrada (fade + la curva se "dibuja")
            self.anim_t0 = None
            self.anim_len = 550_000    # µs
            self.anim_id = 0
            self.cols = []
            self.day_btns = []
            self.loading = False

            self.setup_layer()
            self.build()
            self.connect("destroy", lambda *_: Gtk.main_quit())
            self.connect("key-press-event", self.on_key)
            self.connect("button-press-event", self.on_backdrop)
            self.connect("draw", self.draw_backdrop)
            self.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)

            if data and is_usable(data):
                self.set_data(data)
            if not (data and is_fresh(data)):
                self.refresh()
            GLib.timeout_add_seconds(60, self.minute)
            self.show_all()
            self.start_anim(550_000)
            if self.test:
                self.input_shape_combine_region(cairo.Region())   # clicks pasan de largo
                GLib.timeout_add(int(self.test * 1000), self.destroy)
                if os.environ.get("WEATHER_POPUP_HOVER"):
                    self.set_hover(int(os.environ["WEATHER_POPUP_HOVER"]))

        # ---- ventana --------------------------------------------------------
        def setup_layer(self):
            screen = self.get_screen()
            visual = screen.get_rgba_visual()
            if visual:
                self.set_visual(visual)
            self.set_app_paintable(True)

            L = GtkLayerShell
            L.init_for_window(self)
            L.set_namespace(self, "weather-popup")   # no "waybar*": esa layer_rule (regex) le pondría blur
            L.set_layer(self, L.Layer.OVERLAY)
            # WEATHER_POPUP_TEST=segundos: no toma teclado ni mouse y se cierra solo
            # (para probarlo sin interrumpir a quien está usando la compu)
            self.test = float(os.environ.get("WEATHER_POPUP_TEST") or 0)
            L.set_keyboard_mode(self, L.KeyboardMode.NONE if self.test
                                else L.KeyboardMode.EXCLUSIVE)
            L.set_exclusive_zone(self, -1)
            for e in (L.Edge.TOP, L.Edge.BOTTOM, L.Edge.LEFT, L.Edge.RIGHT):
                L.set_anchor(self, e, True)
            # monitor donde está el mouse (el de la barra en la que se hizo click)
            try:
                c = hypr("cursorpos")
                cx, cy = int(c["x"]), int(c["y"])
                display = Gdk.Display.get_default()
                for i in range(display.get_n_monitors()):
                    m = display.get_monitor(i)
                    g = m.get_geometry()
                    if g.x <= cx < g.x + g.width and g.y <= cy < g.y + g.height:
                        L.set_monitor(self, m)
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
            if self.css_reload_id:
                GLib.source_remove(self.css_reload_id)
            self.css_reload_id = GLib.timeout_add(150, self.reload_css)

        def reload_css(self):
            self.css_reload_id = 0
            try:
                self.css.load_from_data(CSS.encode())
                if self.s:
                    self.show_day()            # la leyenda tiene colores en el markup
                self.queue_draw()
            except GLib.Error:
                pass
            return False

        def on_key(self, _w, ev):
            k = ev.keyval
            if k == Gdk.KEY_Escape:
                self.destroy()
            elif k in (Gdk.KEY_Right, Gdk.KEY_l, Gdk.KEY_L, Gdk.KEY_Page_Down):
                self.select_day(self.day + 1)
            elif k in (Gdk.KEY_Left, Gdk.KEY_h, Gdk.KEY_H, Gdk.KEY_Page_Up):
                self.select_day(self.day - 1)
            elif k == Gdk.KEY_Home:
                self.select_day(0)
            elif Gdk.KEY_1 <= k <= Gdk.KEY_7:
                self.select_day(k - Gdk.KEY_1)
            elif k in (Gdk.KEY_r, Gdk.KEY_R, Gdk.KEY_F5):
                self.refresh()
            else:
                return False
            return True

        def on_scroll(self, _w, ev):
            if ev.direction in (Gdk.ScrollDirection.DOWN, Gdk.ScrollDirection.RIGHT):
                self.select_day(self.day + 1)
            elif ev.direction in (Gdk.ScrollDirection.UP, Gdk.ScrollDirection.LEFT):
                self.select_day(self.day - 1)
            elif ev.direction == Gdk.ScrollDirection.SMOOTH:
                ok, dx, dy = ev.get_scroll_deltas()
                self.scroll_acc = getattr(self, "scroll_acc", 0.0) + (dy or dx)
                if abs(self.scroll_acc) >= 1:
                    self.select_day(self.day + (1 if self.scroll_acc > 0 else -1))
                    self.scroll_acc = 0.0
            return True

        def draw_backdrop(self, _w, cr):
            # app_paintable: GTK no pinta el fondo de la ventana, lo oscurecemos acá
            cr.set_operator(cairo.OPERATOR_SOURCE)
            cr.set_source_rgba(*self.color("scrim", 0.32 * min(1.0, self.fade * 1.6)))
            cr.paint()
            cr.set_operator(cairo.OPERATOR_OVER)
            return False

        def on_backdrop(self, _w, _ev):
            # los clicks dentro de la tarjeta los frena su EventBox
            self.destroy()
            return True

        # ---- widgets --------------------------------------------------------
        def lab(self, name=None, cls=None, xalign=0.0):
            lb = Gtk.Label(xalign=xalign)
            if name:
                lb.set_name(name)
            if cls:
                lb.get_style_context().add_class(cls)
            return lb

        def build(self):
            ev = Gtk.EventBox()
            ev.set_halign(Gtk.Align.CENTER)
            ev.set_valign(Gtk.Align.CENTER)
            ev.connect("button-press-event", lambda *_: True)
            ev.add_events(Gdk.EventMask.SCROLL_MASK | Gdk.EventMask.SMOOTH_SCROLL_MASK)
            ev.connect("scroll-event", self.on_scroll)
            card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
            card.set_name("card")
            card.set_size_request(CARD_W, -1)
            ev.add(card)
            self.add(ev)
            self.card = card

            # fila de días (hoy + 6)
            self.days_box = Gtk.Box(spacing=4, homogeneous=True)
            self.days_box.set_margin_bottom(4)
            card.pack_start(self.days_box, False, False, 0)

            head = Gtk.Box(spacing=14)
            self.big_icon = self.lab("big-icon")
            head.pack_start(self.big_icon, False, False, 0)
            txt = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            txt.set_valign(Gtk.Align.CENTER)
            self.city = self.lab("city")
            self.city.set_text("Buenos Aires")
            self.sub = self.lab("sub")
            self.date = self.lab("date")
            for w in (self.city, self.sub, self.date):
                txt.pack_start(w, False, False, 0)
            head.pack_start(txt, True, True, 0)
            right = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
            right.set_valign(Gtk.Align.CENTER)
            self.big_temp = self.lab("big-temp", xalign=1.0)
            self.hilo = self.lab("hilo", xalign=1.0)
            right.pack_start(self.big_temp, False, False, 0)
            right.pack_start(self.hilo, False, False, 0)
            head.pack_end(right, False, False, 0)
            card.pack_start(head, False, False, 0)

            self.chart = Gtk.DrawingArea()
            self.chart.set_size_request(-1, CHART_H)
            self.chart.add_events(Gdk.EventMask.POINTER_MOTION_MASK
                                  | Gdk.EventMask.LEAVE_NOTIFY_MASK)
            self.chart.connect("draw", self.draw_chart)
            self.chart.connect("motion-notify-event", self.on_chart_motion)
            self.chart.connect("leave-notify-event", lambda *_: self.set_hover(None))
            card.pack_start(self.chart, False, False, 0)

            self.legend = self.lab("legend")
            self.legend.set_margin_start(40)
            card.pack_start(self.legend, False, False, 0)

            self.strip = Gtk.Box(spacing=4, homogeneous=True)
            self.strip.set_margin_top(4)
            card.pack_start(self.strip, False, False, 0)

            foot = Gtk.Box(spacing=6)
            self.foot = self.lab("foot")
            foot.pack_start(self.foot, True, True, 0)
            for glyph, tip, fn in ((I_REFRESH, "Refresh (R)", lambda *_: self.refresh()),
                                   (I_WEB, "Open in browser", self.open_browser)):
                b = Gtk.Button(label=glyph)
                b.set_tooltip_text(tip)
                b.set_relief(Gtk.ReliefStyle.NONE)
                b.connect("clicked", fn)
                foot.pack_end(b, False, False, 0)
            card.pack_start(foot, False, False, 0)

        def build_days(self):
            for c in self.days_box.get_children():
                self.days_box.remove(c)
            self.day_btns = []
            for x in days(self.data):
                b = Gtk.Button()
                b.set_relief(Gtk.ReliefStyle.NONE)
                b.get_style_context().add_class("day")
                b.set_tooltip_text(day_names(self.data, x["d"])[1])
                col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
                for text, cls, markup in (
                        (x["name"], "day-n", False),
                        (x["icon"], "day-ic", False),
                        (f"{round(x['tmax'])}° <span alpha='60%' weight='normal'>"
                         f"{round(x['tmin'])}°</span>", "day-t", True)):
                    lb = self.lab(cls=cls, xalign=0.5)
                    lb.set_markup(text) if markup else lb.set_text(text)
                    col.pack_start(lb, False, False, 0)
                b.add(col)
                b.connect("clicked", lambda _b, d=x["d"]: self.select_day(d))
                self.days_box.pack_start(b, True, True, 0)
                self.day_btns.append(b)
            self.days_box.show_all()

        def build_strip(self):
            for c in self.strip.get_children():
                self.strip.remove(c)
            self.cols = []
            for h in self.s["hours"][:24:3]:
                ev = Gtk.EventBox()
                col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
                col.get_style_context().add_class("col")
                if self.s["now"] is not None and h["h"] <= self.s["now"] < h["h"] + 3:
                    col.get_style_context().add_class("now")
                col.set_tooltip_text(h["desc"])
                for text, cls in ((f"{h['h']:02d}:00", "col-h"), (h["icon"], "col-ic"),
                                  (f"{round(h['t'])}°", "col-t"),
                                  (f"{I_RAIN} {h['pop']}%" if h["pop"] else " ", "col-p")):
                    lb = self.lab(cls=cls, xalign=0.5)
                    lb.set_text(text)
                    col.pack_start(lb, False, False, 0)
                ev.add(col)
                ev.connect("enter-notify-event", lambda *_a, i=h["h"]: self.set_hover(i))
                ev.connect("leave-notify-event", lambda *_a: self.set_hover(None))
                self.strip.pack_start(ev, True, True, 0)
                self.cols.append((h["h"], col))
            self.strip.show_all()

        # ---- datos ----------------------------------------------------------
        def set_data(self, data):
            self.data = data
            self.day = max(0, min(self.day, n_days(data) - 1))
            self.build_days()
            self.show_day()
            return False

        def select_day(self, d):
            if not self.data:
                return
            d = max(0, min(d, n_days(self.data) - 1))
            if d == self.day:
                return
            self.day = d
            self.hover = None
            self.show_day()
            self.start_anim(380_000, fade=False)

        def show_day(self):
            self.s = s = summary(self.data, self.day)
            for i, b in enumerate(self.day_btns):
                ctx = b.get_style_context()
                ctx.add_class("sel") if i == self.day else ctx.remove_class("sel")
            self.big_icon.set_text(s["icon"])
            self.sub.set_text(s["sub"])
            self.date.set_text(s["date"])
            if s["cur_t"] is not None:
                self.big_temp.set_text(f"{round(s['cur_t'])}°")
            else:
                self.big_temp.set_markup(
                    f"{round(s['tmax'])}°<span size='55%' weight='normal' "
                    f"foreground='{self.hex('outline')}'> / {round(s['tmin'])}°</span>")
            self.hilo.set_text(f"H {round(s['tmax'])}° · L {round(s['tmin'])}°")
            self.legend.set_markup(
                f"<span foreground='{self.hex('primary')}'>━━</span> Temperature    "
                f"<span foreground='{self.hex('secondary')}'>╍╍</span> Feels like    "
                f"{I_SUNRISE} {s['sunrise_s']}   {I_SUNSET} {s['sunset_s']}")
            self.update_foot()
            self.build_strip()
            self.chart.queue_draw()

        def update_foot(self):
            if not self.s:
                self.foot.set_text("Loading…" if self.loading else "Weather unavailable")
                return
            extra = "  ·  updating…" if self.loading else ""
            parts = []
            if self.s["humidity"] is not None:
                parts.append(f"Humidity {self.s['humidity']}%  ·  "
                             f"Wind {round(self.s['wind'] or 0)} km/h")
            parts.append(f"Updated {self.s['updated']} · Open-Meteo{extra}")
            self.foot.set_text("  ·  ".join(parts))

        def refresh(self):
            if self.loading:
                return
            self.loading = True
            self.update_foot()

            def worker():
                try:
                    d = fetch_and_cache()
                except Exception:
                    d = None
                GLib.idle_add(self.fetched, d)
            threading.Thread(target=worker, daemon=True).start()

        def fetched(self, d):
            self.loading = False
            if d and is_usable(d):
                self.set_data(d)
                # que la barra muestre lo mismo
                subprocess.Popen(["pkill", "-RTMIN+9", "-x", "waybar"])
            self.update_foot()
            return False

        def minute(self):
            if self.s and self.day == 0:
                n = now_local()
                self.s["now"] = n.hour + n.minute / 60
                self.chart.queue_draw()
            return True

        def open_browser(self, *_):
            if self.data:
                open_html(self.data, self.day)
            self.destroy()

        # ---- gráfico --------------------------------------------------------
        def color(self, name, alpha=1.0):
            ok, c = self.chart.get_style_context().lookup_color(name)
            if not ok:
                return (0.85, 0.85, 0.85, alpha)
            return (c.red, c.green, c.blue, c.alpha * alpha)

        def hex(self, name):
            r, g, b, _ = self.color(name)
            return "#%02x%02x%02x" % (int(r * 255), int(g * 255), int(b * 255))

        fade = 0.0

        def start_anim(self, length, fade=True):
            self.anim_len = length
            self.anim_fade = fade
            self.anim = 0.0
            self.anim_t0 = GLib.get_monotonic_time()
            if not self.anim_id:
                self.anim_id = GLib.timeout_add(16, self.step_anim)

        def step_anim(self):
            t = (GLib.get_monotonic_time() - self.anim_t0) / self.anim_len
            self.anim = 1 - (1 - min(t, 1.0)) ** 3     # ease-out cubic
            if self.anim_fade:
                self.fade = self.anim
                self.queue_draw()
            else:
                self.chart.queue_draw()
            if t >= 1.0:
                self.anim_id = 0
                return False
            return True

        def geom(self):
            a = self.chart.get_allocation()
            pl, pr, pt, pb = 40, 14, 30, 24
            cw, ch = a.width - pl - pr, a.height - pt - pb
            temps = [h["t"] for h in self.s["hours"]]
            feels = [h["feels"] for h in self.s["hours"]]
            N = len(temps) - 1
            lo, hi, step = y_range(temps + feels)
            X = lambda i: pl + i * cw / N  # noqa: E731
            Y = lambda v: pt + (hi - v) / (hi - lo) * ch  # noqa: E731
            return a, pl, pr, pt, pb, cw, ch, temps, feels, N, lo, hi, step, X, Y

        def on_chart_motion(self, _w, ev):
            if not self.s:
                return
            _a, pl, _pr, _pt, _pb, cw, _ch, _t, _f, N, *_ = self.geom()
            i = round((ev.x - pl) / cw * N)
            self.set_hover(max(0, min(N, i)))

        def set_hover(self, i):
            if i == self.hover:
                return
            self.hover = i
            for h, col in self.cols:
                ctx = col.get_style_context()
                if i is not None and h <= i < h + 3:
                    ctx.add_class("hover")
                else:
                    ctx.remove_class("hover")
            self.chart.queue_draw()

        def text(self, cr, s, x, y, rgba, size=9, bold=False, align=0.5, valign=0.5):
            lay = PangoCairo.create_layout(cr)
            fd = Pango.FontDescription(f"JetBrainsMono Nerd Font Propo {'Bold ' if bold else ''}{size}")
            lay.set_font_description(fd)
            lay.set_text(s, -1)
            w, h = lay.get_pixel_size()
            cr.set_source_rgba(*rgba)
            cr.move_to(x - w * align, y - h * valign)
            PangoCairo.show_layout(cr, lay)
            return w, h

        def curve(self, cr, ys, X, Y):
            cr.move_to(X(0), Y(ys[0]))
            for (a, b, p) in segments(ys, X, Y):
                cr.curve_to(a[0], a[1], b[0], b[1], p[0], p[1])

        def draw_chart(self, w, cr):
            if not self.s:
                a = w.get_allocation()
                self.text(cr, "Loading…" if self.loading else "Weather unavailable",
                          a.width / 2, a.height / 2, self.color("outline"), 11)
                return
            s = self.s
            a, pl, pr, pt, pb, cw, ch, temps, feels, N, lo, hi, step, X, Y = self.geom()
            bottom = pt + ch

            # noche (antes del amanecer / después del atardecer)
            cr.set_source_rgba(*self.color("on_surface", 0.04))
            for x0, x1 in ((0, s["sunrise"]), (s["sunset"], N)):
                if x1 > x0:
                    cr.rectangle(X(x0), pt, X(x1) - X(x0), ch)
            cr.fill()

            # grilla + etiquetas
            cr.set_line_width(1)
            v = lo
            while v <= hi + 1e-9:
                y = round(Y(v)) + 0.5
                cr.set_source_rgba(*self.color("outline_variant", 0.6))
                cr.move_to(pl, y)
                cr.line_to(pl + cw, y)
                cr.stroke()
                self.text(cr, f"{v:g}°", pl - 8, y, self.color("outline"), 8, align=1.0)
                v += step
            for i in range(0, N + 1, 3):
                self.text(cr, f"{i % 24:02d}", X(i), bottom + 13, self.color("outline"), 8)

            # la curva aparece de izquierda a derecha (al abrir y al cambiar de día)
            cr.save()
            cr.rectangle(0, 0, pl + cw * self.anim + 6, a.height)
            cr.clip()

            self.curve(cr, temps, X, Y)
            cr.line_to(X(N), bottom)
            cr.line_to(X(0), bottom)
            cr.close_path()
            grad = cairo.LinearGradient(0, Y(max(temps)), 0, bottom)
            grad.add_color_stop_rgba(0, *self.color("primary", 0.32))
            grad.add_color_stop_rgba(1, *self.color("primary", 0.0))
            cr.set_source(grad)
            cr.fill()

            cr.set_line_cap(cairo.LINE_CAP_ROUND)
            cr.set_line_join(cairo.LINE_JOIN_ROUND)
            self.curve(cr, feels, X, Y)
            cr.set_source_rgba(*self.color("secondary", 0.7))
            cr.set_line_width(1.5)
            cr.set_dash([4, 4])
            cr.stroke()
            cr.set_dash([])

            self.curve(cr, temps, X, Y)
            cr.set_source_rgba(*self.color("primary"))
            cr.set_line_width(2.6)
            cr.stroke()

            # mín / máx del día
            imax, imin = minmax_idx(temps)
            for i, dy in ((imax, -13), (imin, 14)):
                cr.set_source_rgba(*self.color("on_surface"))
                cr.arc(X(i), Y(temps[i]), 3.5, 0, 2 * math.pi)
                cr.fill()
                self.text(cr, f"{round(temps[i])}°", X(i), Y(temps[i]) + dy,
                          self.color("on_surface"), 9, bold=True)
            cr.restore()

            def dot(x, y, r):
                cr.set_source_rgba(*self.color("surface_container"))
                cr.arc(x, y, r + 2.5, 0, 2 * math.pi)
                cr.fill()
                cr.set_source_rgba(*self.color("primary"))
                cr.arc(x, y, r, 0, 2 * math.pi)
                cr.fill()

            # ahora (solo hoy)
            if s["now"] is not None and (self.anim >= 1 or X(s["now"]) <= pl + cw * self.anim):
                nx, ny = X(s["now"]), Y(curve_at(temps, s["now"]))
                cr.set_source_rgba(*self.color("on_surface", 0.35))
                cr.set_line_width(1)
                cr.set_dash([3, 4])
                cr.move_to(round(nx) + 0.5, pt)
                cr.line_to(round(nx) + 0.5, bottom)
                cr.stroke()
                cr.set_dash([])
                if self.hover is None:
                    self.text(cr, "Now", nx, pt - 10, self.color("primary"), 8, bold=True)
                dot(nx, ny, 5)

            # hora bajo el mouse
            if self.hover is not None and self.hover <= N:
                h = s["hours"][self.hover]
                hx, hy = X(self.hover), Y(h["t"])
                cr.set_source_rgba(*self.color("primary", 0.45))
                cr.set_line_width(1)
                cr.move_to(round(hx) + 0.5, pt)
                cr.line_to(round(hx) + 0.5, bottom)
                cr.stroke()
                dot(hx, hy, 4)
                msg = (f"{h['icon']}  {self.hover % 24:02d}:00  ·  {h['t']:.1f}°  ·  "
                       f"feels {round(h['feels'])}°")
                if h["pop"]:
                    msg += f"  ·  {I_RAIN} {h['pop']}%"
                lay = PangoCairo.create_layout(cr)
                lay.set_font_description(Pango.FontDescription("JetBrainsMono Nerd Font Propo 8"))
                lay.set_text(msg, -1)
                tw, th = lay.get_pixel_size()
                bw, bh = tw + 18, th + 8
                bx = min(max(hx - bw / 2, pl), pl + cw - bw)
                by = 1
                r = bh / 2
                cr.new_sub_path()
                cr.arc(bx + bw - r, by + r, r, -math.pi / 2, math.pi / 2)
                cr.arc(bx + r, by + r, r, math.pi / 2, 3 * math.pi / 2)
                cr.close_path()
                cr.set_source_rgba(*self.color("surface_container_highest"))
                cr.fill_preserve()
                cr.set_source_rgba(*self.color("primary", 0.35))
                cr.set_line_width(1)
                cr.stroke()
                cr.set_source_rgba(*self.color("on_surface"))
                cr.move_to(bx + 9, by + 4)
                PangoCairo.show_layout(cr, lay)

    win = Popup(data)

    def bye(*_):
        win.destroy()
        return False
    unix_signal_add(GLib.PRIORITY_DEFAULT, 15, bye)
    unix_signal_add(GLib.PRIORITY_DEFAULT, 2, bye)
    Gtk.main()


def main():
    force_html = "--html" in sys.argv[1:]
    if not force_html:
        pid = running_pid()
        if pid:                     # ya abierto: cerrarlo (toggle)
            os.kill(pid, 15)
            return
    if force_html:
        data = data_for_html()
        if data:
            open_html(data)
        return

    os.makedirs(RUN, exist_ok=True)
    with open(PIDFILE, "w") as f:
        f.write(str(os.getpid()))
    try:
        data = cached()
        run_popup(data if data and is_usable(data) else None)
    except Exception as e:
        # sin layer-shell / sin GTK: página en el navegador con lo mismo
        print(f"weather-popup: {e!r}, falling back to HTML", file=sys.stderr)
        data = data_for_html()
        if data:
            open_html(data)
        else:
            subprocess.run(["notify-send", "-a", "Weather", "Weather unavailable",
                            "Couldn't fetch the forecast for Buenos Aires."])
    finally:
        try:
            if running_pid() is None and int(open(PIDFILE).read().split()[0]) == os.getpid():
                os.remove(PIDFILE)
        except (OSError, ValueError, IndexError):
            pass


if __name__ == "__main__":
    main()
