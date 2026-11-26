#!/usr/bin/env python3
"""Temperatura actual en Buenos Aires para waybar (Open-Meteo, sin API key).

Salida JSON: text = ícono + temperatura, tooltip con detalles (en inglés),
class = condición (clear/cloudy/fog/rain/storm/snow) + day/night.
Si falla la red, muestra el último valor cacheado (marcado como stale).
También guarda el pronóstico por hora en el cache: lo usa weather-popup.py
(click derecho), que además importa fetch/describe de acá.
"""
import json
import os
import sys
import time
import urllib.request

LAT, LON = -34.61, -58.38
TZ = "America/Argentina/Buenos_Aires"
URL = (
    "https://api.open-meteo.com/v1/forecast"
    f"?latitude={LAT}&longitude={LON}&timezone={TZ}&forecast_days=7"
    "&current=temperature_2m,apparent_temperature,relative_humidity_2m,"
    "weather_code,is_day,wind_speed_10m"
    "&hourly=temperature_2m,apparent_temperature,precipitation_probability,"
    "weather_code,is_day"
    "&daily=temperature_2m_max,temperature_2m_min,sunrise,sunset,"
    "weather_code,precipitation_probability_max"
)
CACHE = os.path.join(
    os.environ.get("XDG_CACHE_HOME", os.path.expanduser("~/.cache")),
    "waybar-weather.json",
)

# WMO weather codes -> (descripción, grupo)
CODES = {
    0: ("Clear sky", "clear"),
    1: ("Mainly clear", "clear"),
    2: ("Partly cloudy", "partly"),
    3: ("Overcast", "cloudy"),
    45: ("Fog", "fog"),
    48: ("Rime fog", "fog"),
    51: ("Light drizzle", "rain"),
    53: ("Drizzle", "rain"),
    55: ("Dense drizzle", "rain"),
    56: ("Freezing drizzle", "rain"),
    57: ("Freezing drizzle", "rain"),
    61: ("Light rain", "rain"),
    63: ("Rain", "rain"),
    65: ("Heavy rain", "pour"),
    66: ("Freezing rain", "rain"),
    67: ("Freezing rain", "pour"),
    71: ("Light snow", "snow"),
    73: ("Snow", "snow"),
    75: ("Heavy snow", "snow"),
    77: ("Snow grains", "snow"),
    80: ("Rain showers", "rain"),
    81: ("Rain showers", "rain"),
    82: ("Violent showers", "pour"),
    85: ("Snow showers", "snow"),
    86: ("Snow showers", "snow"),
    95: ("Thunderstorm", "storm"),
    96: ("Thunderstorm, hail", "storm"),
    99: ("Thunderstorm, hail", "storm"),
}

# íconos Material Design (Nerd Font)
ICONS = {
    ("clear", 1): "\U000F0599",   # weather-sunny
    ("clear", 0): "\U000F0594",   # weather-night
    ("partly", 1): "\U000F0595",  # weather-partly-cloudy
    ("partly", 0): "\U000F0F31",  # weather-night-partly-cloudy
    "cloudy": "\U000F0590",
    "fog": "\U000F0591",
    "rain": "\U000F0597",
    "pour": "\U000F0596",
    "snow": "\U000F0598",
    "storm": "\U000F0593",
}


def fetch():
    req = urllib.request.Request(URL, headers={"User-Agent": "waybar-weather"})
    with urllib.request.urlopen(req, timeout=10) as r:
        data = json.load(r)
    data["_fetched"] = time.time()
    return data


def save_cache(data):
    tmp = CACHE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f)
    os.replace(tmp, CACHE)


def load_cache():
    with open(CACHE) as f:
        return json.load(f)


def describe(code, is_day=1):
    """(descripción, grupo, ícono) de un código WMO."""
    desc, group = CODES.get(code, ("Unknown", "cloudy"))
    icon = ICONS.get((group, int(is_day))) or ICONS.get(group, "\U000F0590")
    return desc, group, icon


def render(data, stale=False):
    cur = data["current"]
    day = data["daily"]
    is_day = int(cur.get("is_day", 1))
    desc, group, icon = describe(cur["weather_code"], is_day)
    temp = round(cur["temperature_2m"])
    tooltip = (
        f"<b>Buenos Aires</b> · {desc}\n"
        f"Temperature: {cur['temperature_2m']:.1f}°C\n"
        f"Feels like: {cur['apparent_temperature']:.1f}°C\n"
        f"Min / Max: {round(day['temperature_2m_min'][0])}° / "
        f"{round(day['temperature_2m_max'][0])}°\n"
        f"Humidity: {cur['relative_humidity_2m']}%\n"
        f"Wind: {round(cur['wind_speed_10m'])} km/h\n"
        f"<small>Updated {cur['time'][-5:]}"
        + (" (offline, cached)" if stale else "")
        + "\nClick: refresh · Right-click: today's chart</small>"
    )
    classes = [group, "day" if is_day else "night"]
    if stale:
        classes.append("stale")
    return {"text": f"{icon} {temp}°", "tooltip": tooltip, "class": classes}


def main():
    try:
        data = fetch()
        save_cache(data)
        out = render(data)
    except Exception:
        try:
            out = render(load_cache(), stale=True)
        except Exception:
            out = {"text": "\U000F0590 --°", "tooltip": "Weather unavailable",
                   "class": ["stale"]}
    print(json.dumps(out, ensure_ascii=False))
    sys.stdout.flush()


if __name__ == "__main__":
    main()
