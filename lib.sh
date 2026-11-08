#!/usr/bin/env bash
# Definiciones compartidas por update.sh e install.sh (solo usa tar y cp, sin rsync).

# Carpetas de ~/.config que se sincronizan (cada una es ~/.config/<nombre>)
# (los que en esta PC son symlinks a ~/dotfiles se copian con su contenido real)
CONFIG_DIRS=(hypr waybar rofi kitty cava fastfetch gtk-3.0 gtk-4.0 swaync wlogout
             matugen spicetify yay btop bonsai neofetch autostart
             nvim ghostty ohmyposh colors fontconfig viegphunt
             steam-theme millennium ZapZap
             vesktop/themes vesktop/settings tidal-hifi/themes)
# Archivos sueltos de ~/.config
CONFIG_FILES=(pavucontrol.ini QtProject.conf mimeapps.list xdg-terminals.list starship.toml)
# Dotfiles de la home
HOME_FILES=(.bashrc .bash_profile .bash_logout .gitconfig .zshrc .zshenv .nanorc .tmux.conf)
# Carpetas de la home (relativas a ~)
HOME_DIRS=(Pictures/Wallpapers .tmux .fonts .icons)
# Temas de apps que viven en perfiles/datos propios: <origen relativo a ~>|<destino en el repo>
EXTRA_FILES=(
  ".local/share/ZapZap/customizations/global/css/matugen.css|extra/zapzap/matugen.css"
)
EXTRA_DIRS=(
  ".vscode/extensions/local.matugen-theme-1.0.0|extra/vscode-matugen-theme"
  ".local/share/Steam/millennium/themes/matugen|extra/steam-millennium-theme"
  ".local/share/PrismLauncher/themes/matugen|extra/prismlauncher-theme"
  # tema GTK = adw-gtk3-dark + colores de matugen; theme-reload.sh alterna a/b para recargar en vivo
  ".local/share/themes/Matugen-a|extra/gtk-themes/Matugen-a"
  ".local/share/themes/Matugen-b|extra/gtk-themes/Matugen-b"
)
# Claves de dconf (tema GTK, íconos, cursor, fuentes) que se guardan en extra/dconf-interface.ini
DCONF_PATH=/org/gnome/desktop/interface/

# Nunca copiar esto, aunque aparezca dentro de una carpeta de arriba
EXCLUDE_PATTERNS=('.git' '*cache*' 'Cache*' '*.log' '*.key' '*.pem' '*token*' '*secret*' '.env' '*.bak*')
TAR_EX=(); for p in "${EXCLUDE_PATTERNS[@]}"; do TAR_EX+=(--exclude="$p"); done

DRY=0

# Perfil activo de LibreWolf (el "Default=" de installs.ini), sea ~/.librewolf o ~/.config/librewolf/librewolf
librewolf_profile() {
  local base def
  for base in "$HOME/.librewolf" "$HOME/.config/librewolf/librewolf"; do
    [ -f "$base/installs.ini" ] || continue
    def=$(grep -m1 '^Default=' "$base/installs.ini" | cut -d= -f2-)
    [ -n "$def" ] && [ -d "$base/$def" ] && { echo "$base/$def"; return 0; }
  done
  return 1
}

# copy_tree <dir origen> <dir destino> [delete]
# Sigue symlinks (tar -h) y guarda el contenido real. Con "delete" deja el destino idéntico al origen.
copy_tree() {
  [ -d "$1" ] || { echo "skip  $1 (no existe)"; return 0; }
  if [ "$DRY" -eq 1 ]; then echo "dry   $1 -> $2"; return 0; fi
  [ "${3:-}" = delete ] && rm -rf "$2"
  mkdir -p "$2"
  tar -C "$1" -h "${TAR_EX[@]}" -cf - . | tar -C "$2" -xpf -
  echo "ok    $1"
}

# copy_file <archivo origen> <archivo destino>
copy_file() {
  [ -e "$1" ] || { echo "skip  $1 (no existe)"; return 0; }
  if [ "$DRY" -eq 1 ]; then echo "dry   $1 -> $2"; return 0; fi
  mkdir -p "$(dirname "$2")"
  cp -L --preserve=mode,timestamps "$1" "$2"
  echo "ok    $1"
}
