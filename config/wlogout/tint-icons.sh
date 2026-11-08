#!/bin/sh
# Tiñe los íconos de wlogout con el "primary" de matugen (wlogout usa PNG y el CSS
# de GTK no puede recolorearlos). Lo llama theme-reload.sh al cambiar el wallpaper.
dir="$HOME/.config/wlogout/icons"
out="$dir/matugen"
color=$(awk '$1 == "@define-color" && $2 == "primary" { sub(/;/, "", $3); print $3 }' \
  "$HOME/.config/waybar/colors.css")
[ -n "$color" ] || exit 1
mkdir -p "$out"
for name in lock logout sleep power restart hibernate; do
  # -colorize 100 pinta todo del color y conserva el canal alfa (la forma del ícono)
  magick "$dir/$name.png" -fill "$color" -colorize 100 "$out/$name.png"
done
