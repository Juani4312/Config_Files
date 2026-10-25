#!/usr/bin/env bash
# Instala la customización de este repo en la máquina actual.
# Lo que se sobrescribe se guarda en ~/.local/state/sync-backup/<fecha>/
#
# Uso: ./install.sh [-n] [-p]
#   -n   dry-run
#   -p   además instala los paquetes (pacman + yay) de packages/
set -euo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib.sh
source "$REPO/lib.sh"

BACKUP="${XDG_STATE_HOME:-$HOME/.local/state}/sync-backup/$(date +%Y%m%d-%H%M%S)"
PKG=0
while getopts "np" opt; do
  case $opt in n) DRY=1 ;; p) PKG=1 ;; *) exit 1 ;; esac
done

if [ "$PKG" -eq 1 ] && [ "$DRY" -eq 0 ]; then
  sudo pacman -S --needed - < "$REPO/packages/pacman.txt" || true
  if command -v yay >/dev/null; then yay -S --needed - < "$REPO/packages/aur.txt" || true
  else echo "yay no está instalado: instalalo y corré: yay -S --needed - < packages/aur.txt"; fi
fi

# Guarda lo que hay en el destino antes de pisarlo (y desarma symlinks, ej. a ~/dotfiles)
backup() {
  { [ -e "$1" ] || [ -L "$1" ]; } || return 0
  [ "$DRY" -eq 1 ] && return 0
  mkdir -p "$BACKUP/$(dirname "${1#"$HOME"/}")"
  cp -a "$1" "$BACKUP/${1#"$HOME"/}"
  [ -L "$1" ] && rm "$1"
  return 0
}
put_tree() { [ -d "$1" ] || return 0; backup "$2"; copy_tree "$1" "$2"; }
put_file() { [ -e "$1" ] || return 0; backup "$2"; copy_file "$1" "$2"; }

for d in "${CONFIG_DIRS[@]}"; do put_tree "$REPO/config/$d" "$HOME/.config/$d"; done
for f in "${CONFIG_FILES[@]}"; do put_file "$REPO/config/$f" "$HOME/.config/$f"; done
for f in "${HOME_FILES[@]}"; do put_file "$REPO/home/$f" "$HOME/$f"; done
for d in "${HOME_DIRS[@]}"; do put_tree "$REPO/home/$d" "$HOME/$d"; done
for e in "${EXTRA_FILES[@]}"; do put_file "$REPO/${e##*|}" "$HOME/${e%%|*}"; done

# LibreWolf: copia los .css a los perfiles *.default-release que ya existan
for prof in "$HOME"/.config/librewolf/librewolf/*.default-release; do
  [ -d "$prof" ] && [ -d "$REPO/extra/librewolf-chrome" ] && \
    copy_tree "$REPO/extra/librewolf-chrome" "$prof/chrome"
done

[ "$DRY" -eq 1 ] && { echo "(dry-run: nada instalado)"; exit 0; }

# Hyprland lee el wallpaper actual de ~/.config/hypr/current_wallpaper
wp="$HOME/Pictures/wallpapers/pacman-ghosts.png"
[ -e "$wp" ] || wp="$(find "$HOME/Pictures/wallpapers" -maxdepth 1 -type f 2>/dev/null | head -1)"
[ -n "$wp" ] && ln -sfn "$wp" "$HOME/.config/hypr/current_wallpaper"

chmod +x "$HOME"/.config/hypr/scripts/* "$HOME"/.config/hypr/UserScripts/* \
         "$HOME"/.config/rofi/*.sh 2>/dev/null || true

echo "Listo. Backup de lo reemplazado (si hubo): $BACKUP"
echo "Recargá: hyprctl reload; reiniciá waybar. Para instalar paquetes: ./install.sh -p"
