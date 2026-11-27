#!/usr/bin/env bash
# Indicadores de los workspaces especiales para waybar (a los costados de la isla).
# Uso: ws-special.sh <monitor|any> [pad|click|pad-click|flag]
#   sin arg:   burbuja 智 (izquierda) = especial "claude" (SUPER+Z, Claude Code)
#   pad:       burbuja 特 (derecha)   = especial "magic"  (SUPER+S)
#   click / pad-click: cierra ese especial si está abierto ahí
#   flag:      marcador invisible: visible con CUALQUIER especial abierto (ver abajo)
# Siempre imprimen el glifo para que el módulo ocupe su lugar; el CSS lo vuelve
# transparente con la clase "inactive" (así la isla de workspaces nunca se mueve).
state="${XDG_RUNTIME_DIR:-/tmp}/waybar-ws.json"
# <monitor> = "any": abierto en cualquier monitor (barra de respaldo, ej. notebook)
if [ "$1" = any ]; then
  on=$(jq -r '[.special[]?] | any' "$state" 2>/dev/null)
  names=$(jq -r '[.special_name[]?] | join(" ")' "$state" 2>/dev/null)
else
  on=$(jq -r --arg m "$1" '.special[$m] // false' "$state" 2>/dev/null)
  names=$(jq -r --arg m "$1" '.special_name[$m] // ""' "$state" 2>/dev/null)
fi
is_open() { [[ " $names " == *" $1 "* ]]; }

case "$2" in
  click)     is_open claude && hyprctl dispatch 'hl.dsp.workspace.toggle_special("claude")' >/dev/null; exit 0 ;;
  pad-click) is_open magic  && hyprctl dispatch 'hl.dsp.workspace.toggle_special("magic")' >/dev/null; exit 0 ;;
  # flag: módulo de ancho cero que solo existe (visible) con un especial abierto.
  # Corre la isla de workspaces a :nth-child(3) y el CSS la hace más transparente
  # (las clases de los custom quedan en el label interno, no se pueden usar con ~ / +).
  flag)
    if [ "$on" = true ]; then
      printf '{"text":"\\u200b","class":["flag"],"tooltip":""}\n'
    else
      printf '{"text":""}\n'
    fi
    exit 0 ;;
  pad)
    st=inactive; is_open magic && st=active
    printf '{"text":"特","class":["%s","magic"],"tooltip":""}\n' "$st" ;;
  *)
    st=inactive; is_open claude && st=active
    printf '{"text":"智","class":["%s","claude"],"tooltip":""}\n' "$st" ;;
esac
