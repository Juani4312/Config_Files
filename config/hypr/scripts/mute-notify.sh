#!/usr/bin/env bash
# mute-notify.sh audio|mic — notificacion de mute/unmute con el mismo diseño
# para audio y microfono. Lee el estado real (no alterna nada).
# Los cambios de nivel de volumen no notifican (ver volume.sh).
case $1 in
  audio) name="Audio";      state=$(pactl get-sink-mute @DEFAULT_SINK@)
         icon_on=audio-volume-high;           icon_off=audio-volume-muted ;;
  mic)   name="Microphone"; state=$(pactl get-source-mute @DEFAULT_SOURCE@)
         icon_on=microphone-sensitivity-high; icon_off=microphone-sensitivity-muted ;;
  *) echo "uso: $0 audio|mic" >&2; exit 1 ;;
esac
if [[ $state == *yes* ]]; then text="Muted"; icon=$icon_off; else text="Unmuted"; icon=$icon_on; fi
# synchronous: si alternas rapido, la notificacion nueva reemplaza a la anterior
notify-send -e -u low -i "$icon" -h "string:x-canonical-private-synchronous:mute-$1" "$name" "$text"
