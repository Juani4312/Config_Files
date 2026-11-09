#!/bin/bash
# Super+M / tecla de mute de mic: alterna el microfono y notifica
pactl set-source-mute @DEFAULT_SOURCE@ toggle
sleep 0.1
"$HOME/.config/hypr/scripts/mute-notify.sh" mic
swaync-client --reload-css
