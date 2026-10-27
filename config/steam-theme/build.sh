#!/bin/sh
# Arma el tema "matugen" de Millennium: colores de matugen + reglas generadas.
# client.css va a la ventana principal y menus; webkit.css a tienda/comunidad.
# La ventana de inicio de sesion no recibe nada (ver skin.json).
# Uso: build.sh [--regen]   (--regen vuelve a leer el CSS de Steam, p.ej. tras una actualizacion)
dir="$(dirname "$(readlink -f "$0")")"
theme="$HOME/.local/share/Steam/millennium/themes/matugen"
if [ "$1" = "--regen" ] || [ ! -f "$dir/rules-client.css" ]; then
	python3 "$dir/generate.py"
fi
cat "$dir/colors.css" "$dir/rules-client.css" > "$theme/client.css"
cat "$dir/colors.css" "$dir/rules-web.css" > "$theme/webkit.css"
