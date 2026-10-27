#!/usr/bin/env bash
# Deshace una instalación usando backups/<fecha>/ creado por install.sh.
#   - restaura los archivos que se habían pisado
#   - borra los archivos que install.sh creó (no existían antes)
#   - muestra cómo recrear los symlinks originales (ej. ~/.config/hypr -> ~/dotfiles/...)
#
# Uso: ./revert.sh [-l] [fecha]     (sin fecha: el backup más reciente)
#   -l   lista los backups disponibles
set -euo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$REPO/backups"
# shellcheck source=lib.sh
source "$REPO/lib.sh"

if [ "${1:-}" = "-l" ]; then ls -1 "$ROOT" 2>/dev/null || echo "(no hay backups)"; exit 0; fi

name="${1:-$(ls -1 "$ROOT" 2>/dev/null | tail -1)}"
B="$ROOT/${name:-}"
[ -n "${name:-}" ] && [ -d "$B/files" ] || { echo "No encuentro ese backup. Usá ./revert.sh -l"; exit 1; }

echo "Backup: $name"
echo "  - $(find "$B/files" \( -type f -o -type l \) | wc -l) archivos a restaurar"
echo "  - $(wc -l < "$B/created.txt") archivos creados por la instalación a borrar"
read -rp "¿Revertir? [s/N] " ans
[[ "$ans" =~ ^[sSyY]$ ]] || { echo "Cancelado."; exit 1; }

# restaurar (cp -a conserva permisos y symlinks internos)
(cd "$B/files" && find . \( -type f -o -type l \) -print0) | while IFS= read -r -d '' f; do
  mkdir -p "$HOME/$(dirname "$f")"
  cp -a "$B/files/$f" "$HOME/$f"
done
# borrar lo que no existía antes
while IFS= read -r f; do [ -n "$f" ] && rm -f "$HOME/$f"; done < "$B/created.txt"

# dconf (tema GTK, íconos, cursor)
if [ -f "$B/dconf-interface.ini" ] && command -v dconf >/dev/null; then
  dconf load "$DCONF_PATH" < "$B/dconf-interface.ini"
fi

echo "Restaurado."
if [ -s "$B/manifest.txt" ]; then
  echo; echo "Estos destinos eran symlinks antes de instalar. Si querés volver a enlazarlos:"
  while read -r _ link _ target; do echo "  rm -rf '$link' && ln -s '$target' '$link'"; done < "$B/manifest.txt"
fi
