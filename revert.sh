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
# servicios de usuario que habilitó install.sh (antes de borrar su .service)
if [ -s "$B/enabled.txt" ]; then
  while IFS= read -r u; do systemctl --user disable --now "$u" || true; done < "$B/enabled.txt"
fi
# borrar lo que no existía antes
while IFS= read -r f; do [ -n "$f" ] && rm -f "$HOME/$f"; done < "$B/created.txt"

# dconf (tema GTK, íconos, cursor)
if [ -f "$B/dconf-interface.ini" ] && command -v dconf >/dev/null; then
  dconf load "$DCONF_PATH" < "$B/dconf-interface.ini"
fi

# Archivos del sistema (los que install.sh instaló con sudo)
sys_restore=(); sys_remove=()
[ -d "$B/system" ] && while IFS= read -r -d '' f; do sys_restore+=("/$f"); done < <(cd "$B/system" && find . -type f -printf '%P\0')
[ -s "$B/system-created.txt" ] && mapfile -t sys_remove < "$B/system-created.txt"
if [ $((${#sys_restore[@]} + ${#sys_remove[@]})) -gt 0 ]; then
  echo "Archivos del sistema (necesitan sudo):"
  for f in "${sys_restore[@]}"; do echo "  restaurar $f"; done
  for f in "${sys_remove[@]}";  do echo "  borrar    $f"; done
  read -rp "¿Revertirlos también? [s/N] " ans
  if [[ "$ans" =~ ^[sSyY]$ ]]; then
    for f in "${sys_restore[@]}"; do
      sudo install -D -o root -g root -m "$(stat -c %a "$B/system$f")" "$B/system$f" "$f" && echo "ok    $f"
    done
    for f in "${sys_remove[@]}"; do [ -n "$f" ] && sudo rm -f "$f" && echo "rm    $f"; done
    case " ${sys_restore[*]} ${sys_remove[*]} " in *udev/rules.d*) sudo udevadm control --reload && sudo udevadm trigger ;; esac
    case " ${sys_remove[*]} " in *tidal-hifi-userscripts*)
      echo "tidal-hifi sigue parcheado: para sacarlo, reinstalalo (yay -S tidal-hifi-bin)." ;; esac
  fi
fi

echo "Restaurado."
if [ -s "$B/manifest.txt" ]; then
  echo; echo "Estos destinos eran symlinks antes de instalar. Si querés volver a enlazarlos:"
  while read -r _ link _ target; do echo "  rm -rf '$link' && ln -s '$target' '$link'"; done < "$B/manifest.txt"
fi
