#!/usr/bin/env bash
# SUPER+SHIFT+S: manda la ventana activa al workspace especial y recuerda de qué
# workspace venía. Si la ventana ya está en el especial, la devuelve a ese workspace.
# Origen guardado por dirección de ventana en $XDG_RUNTIME_DIR/special-origin.json
# (se borra al reiniciar, igual que las ventanas).
set -u
SPECIAL="special:magic"
STATE="${XDG_RUNTIME_DIR:-/tmp}/special-origin.json"
[ -s "$STATE" ] || echo '{}' > "$STATE"

win=$(hyprctl -j activewindow)
addr=$(jq -r '.address // empty' <<<"$win")
[ -n "$addr" ] || exit 0
ws_id=$(jq -r '.workspace.id' <<<"$win")
ws_name=$(jq -r '.workspace.name' <<<"$win")

save() { # <jq filter> — actualiza el estado y olvida ventanas que ya no existen
  local alive
  alive=$(hyprctl -j clients | jq -c '[.[].address]')
  jq --argjson alive "$alive" --arg a "$addr" --argjson w "${2:-null}" "$1"' | with_entries(select(.key as $k | $alive | index($k)))' \
    "$STATE" > "$STATE.tmp" && mv "$STATE.tmp" "$STATE"
}

if [[ "$ws_name" == special:* ]]; then
  # Volver: workspace guardado, o el workspace normal visible en ese monitor
  dest=$(jq -r --arg a "$addr" '.[$a] // empty' "$STATE")
  if [ -z "$dest" ]; then
    mon=$(jq -r '.monitor' <<<"$win")
    dest=$(hyprctl -j monitors | jq -r --argjson m "$mon" '.[] | select(.id == $m) | .activeWorkspace.id')
  fi
  save 'del(.[$a])'
  hyprctl dispatch "hl.dsp.window.move({ workspace = $dest, window = \"address:$addr\" })" >/dev/null
else
  save '.[$a] = $w' "$ws_id"
  hyprctl dispatch "hl.dsp.window.move({ workspace = \"$SPECIAL\", window = \"address:$addr\" })" >/dev/null
fi
