#!/usr/bin/env bash
# Copia tu customización actual (home + ~/.config) a este repo, siguiendo symlinks.
#
# Uso: ./update.sh [-n] [-p]
#   -n   dry-run (muestra qué copiaría)
#   -p   commit + push al terminar
set -euo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib.sh
source "$REPO/lib.sh"

PUSH=0
while getopts "np" opt; do
  case $opt in n) DRY=1 ;; p) PUSH=1 ;; *) exit 1 ;; esac
done

for d in "${CONFIG_DIRS[@]}"; do copy_tree "$HOME/.config/$d" "$REPO/config/$d" delete; done
for f in "${CONFIG_FILES[@]}"; do copy_file "$HOME/.config/$f" "$REPO/config/$f"; done
for f in "${HOME_FILES[@]}"; do copy_file "$HOME/$f" "$REPO/home/$f"; done
for d in "${HOME_DIRS[@]}"; do copy_tree "$HOME/$d" "$REPO/home/$d" delete; done
for e in "${EXTRA_FILES[@]}"; do copy_file "$HOME/${e%%|*}" "$REPO/${e##*|}"; done
for e in "${EXTRA_DIRS[@]}"; do copy_tree "$HOME/${e%%|*}" "$REPO/${e##*|}" delete; done
for f in "${SYSTEM_FILES[@]}"; do copy_file "$f" "$REPO/extra/system$f"; done

# Temas de LibreWolf del perfil activo (solo chrome/*.css, nunca el perfil)
if prof=$(librewolf_profile); then
  for css in "$prof"/chrome/*.css; do
    [ -e "$css" ] && copy_file "$css" "$REPO/extra/librewolf-chrome/$(basename "$css")"
  done
fi

[ "$DRY" -eq 1 ] && { echo "(dry-run: nada copiado)"; exit 0; }

# Tema GTK / íconos / cursor / fuentes
command -v dconf >/dev/null && dconf dump "$DCONF_PATH" > "$REPO/extra/dconf-interface.ini"

# Los symlinks absolutos se reemplazan: current_wallpaper lo crea install.sh.
rm -f "$REPO/config/hypr/current_wallpaper"
# monitors.lua (resolución, posición y scale/zoom) es propio de cada máquina: no se sincroniza.
rm -f "$REPO/config/hypr/monitors.lua"
# waybar: config y style.css son hardlinks (o symlinks) a un archivo de configs/ y style/;
# en el repo quedan como symlink relativo a ese archivo.
link_variant() { # <archivo> <subcarpeta>
  local f="$REPO/config/waybar/$1" src="$HOME/.config/waybar/$1" v
  [ -e "$src" ] || return 0
  v=$(find -L "$HOME/.config/waybar/$2" -maxdepth 1 -type f -samefile "$(readlink -f "$src")" -printf '%f' -quit 2>/dev/null)
  [ -n "$v" ] && ln -sfn "$2/$v" "$f"
}
if [ -d "$REPO/config/waybar" ]; then
  link_variant style.css style
  link_variant config configs
fi

# Lista de paquetes para reinstalar
if command -v pacman >/dev/null; then
  mkdir -p "$REPO/packages"
  pacman -Qqen > "$REPO/packages/pacman.txt"
  pacman -Qqem > "$REPO/packages/aur.txt"
fi

cd "$REPO"
git add -A
git status --short | head -20
if [ "$PUSH" -eq 1 ]; then
  if git diff --cached --quiet; then echo "Sin cambios."; else
    git commit -m "Sync $(date +%F)"
    git push
  fi
fi
