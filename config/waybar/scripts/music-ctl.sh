#!/usr/bin/env bash
# Controles del módulo de música de waybar (el estado lo escribe music.py).
# Solo actúa sobre el reproductor que muestra la barra (tidal-hifi o DeaDBeeF).
#   music-ctl.sh menu                   -> abre/cierra el mini menú (music-popup.py)
#   music-ctl.sh play-pause|next|previous
#   music-ctl.sh seek +5|-10            -> adelanta/atrasa N segundos
#   music-ctl.sh volume up|down         -> volumen del stream del reproductor en
#                                          PipeWire (no el del sistema ni el slider
#                                          interno del reproductor); paso 1/2/5 %
#   music-ctl.sh focus                  -> enfoca la ventana del reproductor
#   music-ctl.sh cycle                  -> alterna entre tidal y DeaDBeeF (todas las barras)
run="${XDG_RUNTIME_DIR:-/tmp}/waybar-music"
player='' cls=''
[ -r "$run/state" ] && { read -r player; read -r _; read -r cls; } < "$run/state"

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
  # volumen del stream de la app en PipeWire (como pavucontrol), no el interno
  # del reproductor (ver music_stream.py); paso 1/2/5 % según nivel
  case "$2" in up|down) ;; *) exit 1 ;; esac
  case "$cls" in tidal|deadbeef) ;; *) exit 0 ;; esac
  exec "$(dirname "$(readlink -f "$0")")/music_stream.py" step "$cls" "$2" ;;
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
