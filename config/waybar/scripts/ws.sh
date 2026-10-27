#!/usr/bin/env bash
# Imprime el JSON del botón del workspace $1 para waybar
icons=(_ 一 二 三 四 五 六 七 八 九 十)
state="${XDG_RUNTIME_DIR:-/tmp}/waybar-ws.json"
cls=$(jq -c --arg n "$1" '.[$n] // ["empty"]' "$state" 2>/dev/null || echo '["empty"]')
printf '{"text":"%s","class":%s,"tooltip":"Workspace %s"}\n' "${icons[$1]}" "$cls" "$1"
