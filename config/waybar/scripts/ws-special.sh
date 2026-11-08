#!/usr/bin/env bash
# Indicador del workspace especial para waybar.
# Uso: ws-special.sh <monitor> [pad]
#   sin "pad": burbuja 特 a la izquierda de los workspaces de <monitor>
#   con "pad": espaciador invisible del mismo ancho a la derecha (centrado simétrico)
# Siempre imprime el glifo para que el módulo ocupe su lugar; el CSS lo vuelve
# transparente con la clase "inactive" (así la isla de workspaces nunca se mueve).
#   ws-special.sh <monitor> click  -> cierra el especial solo si está abierto ahí
state="${XDG_RUNTIME_DIR:-/tmp}/waybar-ws.json"
on=$(jq -r --arg m "$1" '.special[$m] // false' "$state" 2>/dev/null)
if [ "$2" = click ]; then
  [ "$on" = true ] && hyprctl dispatch 'hl.dsp.workspace.toggle_special("magic")' >/dev/null
  exit 0
fi
st=inactive; [ "$on" = true ] && st=active
if [ "$2" = pad ]; then
  printf '{"text":"特","class":["%s","pad"],"tooltip":""}\n' "$st"
elif [ "$st" = active ]; then
  printf '{"text":"特","class":["active"],"tooltip":"Workspace especial (SUPER+S)"}\n'
else
  printf '{"text":"特","class":["inactive"],"tooltip":""}\n'
fi
