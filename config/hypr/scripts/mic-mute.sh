#!/bin/bash
pactl set-source-mute @DEFAULT_SOURCE@ toggle
sleep 0.1

if pactl get-source-mute @DEFAULT_SOURCE@ | grep -q yes; then
    notify-send -i microphone-sensitivity-muted "Microphone" "Muted"
else
    notify-send -i microphone-sensitivity-high "Microphone" "Unmuted"
fi

swaync-client --reload-css
