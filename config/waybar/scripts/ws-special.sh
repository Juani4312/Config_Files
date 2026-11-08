#!/usr/bin/env bash
# Indicador del workspace especial para waybar.
# Uso: ws-special.sh <monitor> [pad]
#   sin "pad": muestra 特 cuando el workspace especial está abierto en <monitor>
#   con "pad": espaciador invisible del mismo ancho, del otro lado, para no descentrar
# Sin special abierto imprime texto vacío -> waybar oculta el módulo (ancho 0).
state="${XDG_RUNTIME_DIR:-/tmp}/waybar-ws.json"
on=$(jq -r --arg m "$1" '.special[$m] // false' "$state" 2>/dev/null)
if [ "$on" = true ]; then
  cls='["active"]'; [ "$2" = pad ] && cls='["active","pad"]'
  printf '{"text":"特","class":%s,"tooltip":"Workspace especial (SUPER+S)"}\n' "$cls"
else
  printf '{"text":"","class":["inactive"]}\n'
fi
