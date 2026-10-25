#!/usr/bin/env bash
# Instala la customización de este repo en la máquina actual.
#
# Antes de tocar nada:
#   1. Revisa qué archivos son nuevos / cambiados / iguales (y compara los binds de hypr).
#   2. Pide confirmación.
#   3. Guarda en <repo>/backups/<fecha>/ una copia de todo lo que va a pisar
#      (más manifest.txt con symlinks y created.txt con lo que no existía).
# Para deshacer: ./revert.sh [fecha]
#
# Uso: ./install.sh [-n] [-y] [-p]
#   -n   solo revisión (no copia ni respalda nada)
#   -y   no pedir confirmación
#   -p   además instala los paquetes (pacman + yay) de packages/
set -euo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib.sh
source "$REPO/lib.sh"

BACKUP="$REPO/backups/$(date +%Y%m%d-%H%M%S)"
PKG=0 YES=0
while getopts "nyp" opt; do
  case $opt in n) DRY=1 ;; y) YES=1 ;; p) PKG=1 ;; *) exit 1 ;; esac
done

# Lista de pares "tipo|origen en el repo|destino en la máquina" (d = carpeta, f = archivo)
PAIRS=()
for d in "${CONFIG_DIRS[@]}"; do PAIRS+=("d|$REPO/config/$d|$HOME/.config/$d"); done
for f in "${CONFIG_FILES[@]}"; do PAIRS+=("f|$REPO/config/$f|$HOME/.config/$f"); done
for f in "${HOME_FILES[@]}"; do PAIRS+=("f|$REPO/home/$f|$HOME/$f"); done
for d in "${HOME_DIRS[@]}"; do PAIRS+=("d|$REPO/home/$d|$HOME/$d"); done
for e in "${EXTRA_FILES[@]}"; do PAIRS+=("f|$REPO/${e##*|}|$HOME/${e%%|*}"); done
for prof in "$HOME"/.config/librewolf/librewolf/*.default-release; do
  [ -d "$prof" ] && [ -d "$REPO/extra/librewolf-chrome" ] && PAIRS+=("d|$REPO/extra/librewolf-chrome|$prof/chrome")
done

# Archivos (rutas relativas) de una carpeta origen, separados por NUL
list_rel() { (cd "$1" && find . \( -type f -o -type l \) -printf '%P\0'); }
# estado de un archivo respecto al destino: new | same | changed
state() { if [ ! -e "$2" ] && [ ! -L "$2" ]; then echo new; elif cmp -s "$1" "$2"; then echo same; else echo changed; fi; }

# ---------- 1. REVISIÓN ----------
review() {
  echo "== Revisión: repo vs. esta máquina =="
  local t_new=0 t_chg=0 t_same=0 pair kind src dst rel n c s st
  for pair in "${PAIRS[@]}"; do
    IFS='|' read -r kind src dst <<<"$pair"
    [ -e "$src" ] || continue
    n=0 c=0 s=0; local changed=()
    if [ "$kind" = d ]; then
      while IFS= read -r -d '' rel; do
        st=$(state "$src/$rel" "$dst/$rel")
        case $st in new) n=$((n+1));; same) s=$((s+1));; changed) c=$((c+1)); changed+=("$rel");; esac
      done < <(list_rel "$src")
    else
      st=$(state "$src" "$dst")
      case $st in new) n=1;; same) s=1;; changed) c=1; changed+=("$(basename "$dst")");; esac
    fi
    t_new=$((t_new+n)); t_chg=$((t_chg+c)); t_same=$((t_same+s))
    printf '  %-48s %3d nuevos  %3d cambiados  %3d iguales\n' "${dst/#$HOME/~}" "$n" "$c" "$s"
    [ -L "$dst" ] && echo "      (es un symlink a $(readlink -f "$dst"): se reemplaza por una copia real, el original queda intacto)"
    local shown=0 f
    for f in "${changed[@]}"; do
      [ $shown -ge 12 ] && { echo "      ... y $((${#changed[@]}-12)) más"; break; }
      echo "      ~ $f"; shown=$((shown+1))
    done
  done
  echo "  TOTAL: $t_new nuevos, $t_chg cambiados (se respaldan), $t_same iguales"
  review_binds
}

# Compara las líneas de bind de hypr (cualquier .lua/.conf que contenga "bind")
review_binds() {
  echo; echo "== Binds de hypr =="
  local src="$REPO/config/hypr" rel dst any=0 old new
  [ -d "$src" ] || { echo "  (el repo no tiene config/hypr)"; return; }
  while IFS= read -r -d '' rel; do
    grep -qiE 'bind' "$src/$rel" || continue
    any=1; dst="$HOME/.config/hypr/$rel"
    if [ ! -e "$dst" ]; then echo "  + $rel: archivo de binds nuevo (no existe en esta máquina)"; continue; fi
    norm() { grep -iE 'bind' "$1" | sed -E 's/^[[:space:]]+//; s/[[:space:]]+/ /g' | sort -u; }
    old=$(comm -23 <(norm "$dst") <(norm "$src/$rel"))   # solo en tu config actual
    new=$(comm -13 <(norm "$dst") <(norm "$src/$rel"))   # solo en el repo
    if [ -z "$old$new" ]; then echo "  = $rel: binds idénticos"; continue; fi
    echo "  ~ $rel"
    [ -n "$old" ] && { echo "      Actuales que se PIERDEN (quedan en el backup):"; echo "$old" | head -40 | sed 's/^/        - /'; }
    [ -n "$new" ] && { echo "      Nuevos que se AGREGAN:"; echo "$new" | head -40 | sed 's/^/        + /'; }
  done < <(cd "$src" && find . \( -name '*.lua' -o -name '*.conf' \) -type f -printf '%P\0')
  [ $any -eq 0 ] && echo "  (no se encontraron archivos de binds en el repo)"
  return 0
}

# ---------- 2. BACKUP ----------
save() { # <ruta absoluta en ~> -> BACKUP/files/<ruta relativa a ~>
  local rel="${1#"$HOME"/}"
  mkdir -p "$BACKUP/files/$(dirname "$rel")"
  cp -a "$1" "$BACKUP/files/$rel"
}
backup() {
  mkdir -p "$BACKUP/files"; : > "$BACKUP/manifest.txt"; : > "$BACKUP/created.txt"
  local pair kind src dst rel
  for pair in "${PAIRS[@]}"; do
    IFS='|' read -r kind src dst <<<"$pair"
    [ -e "$src" ] || continue
    # Si el destino es un symlink (ej. ~/.config/hypr -> ~/dotfiles/...), se anota y se
    # reemplaza por una copia real, así la instalación nunca escribe dentro de ~/dotfiles.
    if [ -L "$dst" ]; then
      echo "symlink $dst -> $(readlink "$dst")" >> "$BACKUP/manifest.txt"
      local tgt; tgt="$(readlink -f "$dst")"; rm "$dst"; cp -a "$tgt" "$dst"
    fi
    if [ "$kind" = d ]; then
      while IFS= read -r -d '' rel; do
        case $(state "$src/$rel" "$dst/$rel") in
          changed) save "$dst/$rel" ;;
          new) echo "${dst#"$HOME"/}/$rel" >> "$BACKUP/created.txt" ;;
        esac
      done < <(list_rel "$src")
    else
      case $(state "$src" "$dst") in
        changed) save "$dst" ;;
        new) echo "${dst#"$HOME"/}" >> "$BACKUP/created.txt" ;;
      esac
    fi
  done
  # Copia de la revisión junto al backup
  review > "$BACKUP/review.txt" 2>&1
}

# ---------- flujo ----------
review
if [ "$DRY" -eq 1 ]; then echo; echo "(dry-run: no se respaldó ni instaló nada)"; exit 0; fi

if [ "$YES" -ne 1 ]; then
  [ -t 0 ] || { echo "Sin terminal interactiva: usá -y para continuar sin confirmar."; exit 1; }
  read -rp $'\n¿Respaldar y aplicar estos cambios? [s/N] ' ans
  [[ "$ans" =~ ^[sSyY]$ ]] || { echo "Cancelado, no se tocó nada."; exit 1; }
fi

backup
echo; echo "Backup guardado en: ${BACKUP/#$HOME/~}"

if [ "$PKG" -eq 1 ]; then
  sudo pacman -S --needed - < "$REPO/packages/pacman.txt" || true
  if command -v yay >/dev/null; then yay -S --needed - < "$REPO/packages/aur.txt" || true
  else echo "yay no está instalado: instalalo y corré: yay -S --needed - < packages/aur.txt"; fi
fi

for pair in "${PAIRS[@]}"; do
  IFS='|' read -r kind src dst <<<"$pair"
  if [ "$kind" = d ]; then copy_tree "$src" "$dst"; else copy_file "$src" "$dst"; fi
done

# Hyprland lee el wallpaper actual de ~/.config/hypr/current_wallpaper
wp="$HOME/Pictures/wallpapers/pacman-ghosts.png"
[ -e "$wp" ] || wp="$(find "$HOME/Pictures/wallpapers" -maxdepth 1 -type f 2>/dev/null | head -1)"
[ -n "$wp" ] && ln -sfn "$wp" "$HOME/.config/hypr/current_wallpaper"

chmod +x "$HOME"/.config/hypr/scripts/* "$HOME"/.config/hypr/UserScripts/* \
         "$HOME"/.config/rofi/*.sh 2>/dev/null || true

echo "Listo. Para deshacer: $REPO/revert.sh $(basename "$BACKUP")"
echo "Recargá: hyprctl reload; reiniciá waybar. Para instalar paquetes: ./install.sh -p"
