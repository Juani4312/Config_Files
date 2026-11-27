#!/usr/bin/env bash
# Controles del módulo de música de waybar (el estado lo escribe music.py).
# Solo actúa sobre el reproductor que muestra la barra (tidal-hifi o DeaDBeeF).
#   music-ctl.sh menu                   -> abre/cierra el mini menú (music-popup.py)
#   music-ctl.sh play-pause|next|previous
#   music-ctl.sh seek +5|-10            -> adelanta/atrasa N segundos
#   music-ctl.sh volume up|down         -> volumen propio del reproductor (MPRIS),
#                                          no el del sistema; paso 1/2/5 % según nivel
#   music-ctl.sh focus                  -> enfoca la ventana del reproductor
#   music-ctl.sh cycle                  -> alterna entre tidal y DeaDBeeF (todas las barras)
run="${XDG_RUNTIME_DIR:-/tmp}/waybar-music"
player='' status='' cls=''
[ -r "$run/state" ] && { read -r player; read -r status; read -r cls; } < "$run/state"

case "$1" in
menu)
  pid=$(head -n1 "$run/popup.pid" 2>/dev/null)
  if [ -n "$pid" ] && grep -qs music-popup "/proc/$pid/cmdline"; then
    kill "$pid"                         # ya estaba abierto: cerrar
    exit 0
  fi
  # si el mismo click lo acaba de cerrar (perdió el foco), no reabrir
  closed=$(cat "$run/popup.closed" 2>/dev/null)
  [ -n "$closed" ] && [ $(( $(date +%s%3N) - closed )) -lt 400 ] && exit 0
  "$(dirname "$(readlink -f "$0")")/popups.sh" close-except music   # uno a la vez
  setsid -f "$(dirname "$(readlink -f "$0")")/music-popup.py" >/dev/null 2>&1 ;;
play-pause|next|previous)
  [ -n "$player" ] && playerctl -p "$player" "$1" ;;
seek)
  # playerctl quiere "5+" / "5-"
  [ -n "$player" ] && playerctl -p "$player" position "${2#[+-]}${2:0:1}" ;;
volume)
  [ -n "$player" ] || exit 0
  case "$2" in up) dir=1 ;; down) dir=-1 ;; *) exit 1 ;; esac
  # la rueda dispara varios a la vez: uno por vez
  exec 9>"$run/volume.lock"; flock -w 2 9 || exit 0
  now=$(date +%s%3N) cur=''
  # tidal-hifi tarda en reflejar el valor nuevo por MPRIS: si recién lo
  # cambiamos, seguir desde lo que pusimos (si no, la rueda rápida no suma)
  if [ -r "$run/volume" ]; then
    read -r vp vv vt < "$run/volume"
    [ "$vp" = "$player" ] && [ $(( now - ${vt:-0} )) -lt 1500 ] && cur=$vv
  fi
  [ -n "$cur" ] || cur=$(playerctl -p "$player" volume 2>/dev/null) || exit 0
  # pasos finos abajo (1 % hasta 10, 2 % hasta 30, 5 % después), alineados
  new=$(awk -v v="$cur" -v d="$dir" 'BEGIN {
    e = 1e-6; x = (d > 0) ? v + e : v - e
    s = (x < 0.10) ? 0.01 : (x < 0.30) ? 0.02 : 0.05
    k = x / s
    if (d > 0) n = (int(k) + 1) * s
    else { c = int(k); if (c < k) c++; n = (c - 1) * s }
    if (n < 0) n = 0; if (n > 1) n = 1
    printf "%.2f", n }')
  playerctl -p "$player" volume "$new" && echo "$player $new $now" > "$run/volume" ;;
focus)
  case "$cls" in
    tidal)    win='class:tidal-hifi' ;;
    deadbeef) win='class:(?i)deadbeef' ;;
    *)        exit 0 ;;
  esac
  hyprctl dispatch "hl.dsp.focus({ window = \"$win\" })" >/dev/null ;;
cycle)
  # una instancia de music.py por barra: avisar a todas (el "\." evita que
  # el patrón coincida con este mismo shell)
  pkill -USR1 -f 'waybar/scripts/music\.py' ;;
esac
exit 0
