#!/bin/bash
# Escribe el tema de matugen en Enhancer for YouTube (storage.local de la extension).
# Solo funciona con LibreWolf CERRADO (la base IndexedDB esta abierta mientras corre).
# Lo llama theme-reload.sh entre el cierre y el relanzamiento de LibreWolf.
set -e
SRC=~/.config/youtube-enhancer
# perfil activo de LibreWolf (Default= de installs.ini), igual que lib.sh de ~/Laptop/Sync
PROFILE=
for base in ~/.librewolf ~/.config/librewolf/librewolf; do
  [[ -f $base/installs.ini ]] || continue
  def=$(grep -m1 '^Default=' "$base/installs.ini" | cut -d= -f2-)
  [[ -n $def && -d $base/$def ]] && { PROFILE=$base/$def; break; }
done
[[ -n $PROFILE ]] || { echo "youtube-enhancer: perfil de librewolf no encontrado"; exit 1; }
EXT_ID=enhancerforyoutube@maximerf.addons.mozilla.org
PY=~/.config/matugen/scripts/moz_ext_storage.py

if pgrep -x librewolf >/dev/null; then echo "youtube-enhancer: librewolf abierto, no se escribe"; exit 1; fi
[[ -f $SRC/custom.css && -f $SRC/colors.json ]] || { echo "youtube-enhancer: faltan $SRC/custom.css/colors.json"; exit 1; }

# UUID interno de la extension (cambia si se reinstala)
uuid=$(sed -n 's/.*extensions\.webextensions\.uuids", "\(.*\)");/\1/p' "$PROFILE/prefs.js" | sed 's/\\"/"/g' |
       jq -r --arg id "$EXT_ID" '.[$id] // empty')
[[ -n $uuid ]] || { echo "youtube-enhancer: extension no encontrada"; exit 1; }
db=$(ls "$PROFILE/storage/default/moz-extension+++$uuid^userContextId=4294967295/idb/"*.sqlite 2>/dev/null | head -1)
[[ -n $db ]] || { echo "youtube-enhancer: no hay base de storage (abrir las opciones de la extension una vez)"; exit 1; }

[[ -f $db.bak-matugen ]] || cp "$db" "$db.bak-matugen"   # backup de la primera vez

python3 -I "$PY" "$db" set-str  customcssrules "$SRC/custom.css"
python3 -I "$PY" "$db" set-json customcolors   "$SRC/colors.json"
python3 -I "$PY" "$db" set-bool customtheme    true
python3 -I "$PY" "$db" set-bool darktheme      true
printf '"youtube-deep-dark-custom"' >"$SRC/.theme.json"
python3 -I "$PY" "$db" set-json theme          "$SRC/.theme.json"
echo "youtube-enhancer: tema escrito"
