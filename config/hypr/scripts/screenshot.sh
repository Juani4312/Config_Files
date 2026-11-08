#!/bin/bash
# Captura de una región: la guarda en ~/Pictures/Screenshots y la copia al portapapeles

dir="$HOME/Pictures/Screenshots"
mkdir -p "$dir"
file="$dir/$(date +%Y%m%d_%Hh%Mm%Ss).png"

region=$(slurp) || exit 1
grim -g "$region" "$file" && wl-copy < "$file" && notify-send -e -u low -i "$file" "Screenshot" "Guardada y copiada al portapapeles"
