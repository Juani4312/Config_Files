#!/usr/bin/env bash
# Definiciones compartidas por update.sh e install.sh (solo usa tar y cp, sin rsync).

# Carpetas de ~/.config que se sincronizan (cada una es ~/.config/<nombre>)
CONFIG_DIRS=(hypr waybar rofi kitty cava fastfetch gtk-3.0 gtk-4.0 swaync wlogout
             matugen spicetify vesktop yay)
# Archivos sueltos de ~/.config
CONFIG_FILES=(pavucontrol.ini QtProject.conf mimeapps.list)
# Dotfiles de la home
HOME_FILES=(.bashrc .bash_profile .bash_logout .gitconfig)
# Carpetas de la home (relativas a ~)
HOME_DIRS=(Pictures/wallpapers)
# Temas de apps que viven en perfiles/datos propios: <origen relativo a ~>|<destino en el repo>
EXTRA_FILES=(
  ".local/share/ZapZap/customizations/global/css/matugen.css|extra/zapzap/matugen.css"
)

# Nunca copiar esto, aunque aparezca dentro de una carpeta de arriba
EXCLUDE_PATTERNS=('.git' '*cache*' 'Cache*' '*.log' '*.key' '*.pem' '*token*' '*secret*' '.env' '*.bak*')
TAR_EX=(); for p in "${EXCLUDE_PATTERNS[@]}"; do TAR_EX+=(--exclude="$p"); done

DRY=0

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
