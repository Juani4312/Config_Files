#!/usr/bin/env bash
# resize.sh — agranda/achica el panel de swaync (flechas al pie del panel).
# Uso: resize.sh w+|w-|h+|h-
# Las flechas mueven la esquina inferior izquierda: ◂ ensancha, ▸ angosta,
# ▾ alarga, ▴ acorta. swaync no deja arrastrar el panel (layer-shell), por eso
# se cambia control-center-width/height en config.json y se recarga con -R.
cfg="$HOME/.config/swaync/config.json"
step=40
read -r w h < <(jq -r '"\(."control-center-width") \(."control-center-height")"' "$cfg")
# alto maximo: el del monitor enfocado menos la barra y los margenes
mon_h=$(hyprctl monitors -j | jq -r '[.[] | select(.focused)][0] | (.height / .scale | floor)')
max_h=$(( ${mon_h:-1080} - 90 ))
case $1 in
  w+) w=$((w + step)) ;;
  w-) w=$((w - step)) ;;
  h+) h=$((h + step)) ;;
  h-) h=$((h - step)) ;;
  *) echo "uso: $0 w+|w-|h+|h-" >&2; exit 1 ;;
esac
(( w < 320 )) && w=320; (( w > 900 )) && w=900
(( h < 400 )) && h=400; (( h > max_h )) && h=$max_h
tmp=$(mktemp)
jq --argjson w "$w" --argjson h "$h" \
  '."control-center-width" = $w | ."control-center-height" = $h' "$cfg" >"$tmp" \
  && cat "$tmp" >"$cfg"   # cat > conserva el inodo del archivo
rm -f "$tmp"
swaync-client -R >/dev/null
