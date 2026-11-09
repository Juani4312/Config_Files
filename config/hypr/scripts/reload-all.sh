#!/usr/bin/env bash
# reload-all.sh — Super+O: recarga Hyprland y reinicia swaync y waybar.
# swaync se reinicia entero (no -R) porque algunas opciones, como el ancho de
# los popups, solo se leen al arrancar. Se pierde el historial de notificaciones.

hyprctl reload >/dev/null   # config de Hyprland (el bloque de autostart no se repite)

for p in swaync waybar; do pkill -x "$p"; done
for ((i = 0; i < 25; i++)); do   # esperar hasta ~5s a que cierren
  pgrep -x swaync >/dev/null || pgrep -x waybar >/dev/null || break
  sleep 0.2
done
pkill -KILL -x swaync; pkill -KILL -x waybar   # por si alguno se colgo

# lanzarlos desde Hyprland para que no dependan de este script
hyprctl dispatch 'hl.dsp.exec_cmd("swaync")' >/dev/null
hyprctl dispatch 'hl.dsp.exec_cmd("waybar")' >/dev/null

sleep 1
notify-send -a "Sistema" -i view-refresh -t 2000 "Recargado" "Hyprland, swaync y waybar"
