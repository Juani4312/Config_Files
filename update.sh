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

# Temas de LibreWolf (solo chrome/*.css, nunca el perfil)
for css in "$HOME"/.config/librewolf/librewolf/*.default-release/chrome/*.css; do
  [ -e "$css" ] && copy_file "$css" "$REPO/extra/librewolf-chrome/$(basename "$css")"
done

[ "$DRY" -eq 1 ] && { echo "(dry-run: nada copiado)"; exit 0; }

# Los symlinks absolutos se reemplazan: current_wallpaper lo crea install.sh,
# y los de waybar pasan a ser relativos.
rm -f "$REPO/config/hypr/current_wallpaper"
if [ -d "$REPO/config/waybar" ]; then
  ln -sfn "style/bintang default.css" "$REPO/config/waybar/style.css"
  ln -sfn "configs/bintang default"   "$REPO/config/waybar/config"
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
