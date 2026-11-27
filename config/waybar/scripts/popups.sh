#!/usr/bin/env bash
# Ventanas que se abren desde la waybar: solo una a la vez.
# Uso: popups.sh close-except <music|weather|weather-search|calendar|swaync|rofi|wlogout>
# Lo llaman los popups propios al abrirse (music-ctl.sh, weather-*.py) y los on-click
# de la barra que abren cosas ajenas (swaync, menú wifi en rofi, wlogout).
[ "$1" = close-except ] || { echo "uso: $0 close-except <nombre>" >&2; exit 1; }
keep=$2
run=${XDG_RUNTIME_DIR:-/tmp}

killpid() {  # <pidfile> <patrón en cmdline>: SIGTERM (los popups cierran prolijo)
  local pid
  pid=$(head -n1 "$1" 2>/dev/null | awk '{print $1}')
  [ -n "$pid" ] && [ "$pid" != "$$" ] && grep -qs "$2" "/proc/$pid/cmdline" && kill "$pid"
}

[ "$keep" != music ]          && killpid "$run/waybar-music/popup.pid" music-popup
[ "$keep" != weather ]        && killpid "$run/waybar-weather/popup.pid" weather-popup
[ "$keep" != weather-search ] && killpid "$run/waybar-weather/search.pid" weather-search
[ "$keep" != calendar ]       && killpid "$run/waybar-calendar/popup.pid" calendar-popup
[ "$keep" != swaync ]         && swaync-client -cp -sw >/dev/null 2>&1
[ "$keep" != rofi ]           && pkill -x rofi
[ "$keep" != wlogout ]        && pkill -x wlogout
exit 0
