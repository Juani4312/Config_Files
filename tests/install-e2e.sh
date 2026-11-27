#!/usr/bin/env bash
# Prueba de punta a punta de install.sh + revert.sh SIN tocar el sistema:
# copia el repo a un directorio temporal (así los backups de la prueba no quedan en backups/), usa un HOME
# vacío y stubs de sudo/systemctl/dconf/udevadm/hyprctl. No necesita red ni sudo.
# Verifica: install -y anda; conserva el historial de qalculate; deja waybar/style.css como symlink;
# borra los OBSOLETE_FILES; una segunda corrida no cambia nada más; revert de las dos deja el HOME como estaba.
# Uso: tests/install-e2e.sh
set -euo pipefail
SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
W=$(mktemp -d); trap 'rm -rf "$W"' EXIT
fail() { echo "FALLA: $*"; exit 1; }

mkdir -p "$W/stubs" "$W/repo" "$W/home/.config/qalculate"
for c in sudo dconf udevadm; do printf '#!/bin/sh\nexit 0\n' > "$W/stubs/$c"; done
printf '#!/bin/sh\ncase "$*" in *is-enabled*) exit 1;; esac\nexit 0\n' > "$W/stubs/systemctl"
printf '#!/bin/sh\nexit 1\n' > "$W/stubs/hyprctl"   # como en una TTY sin Hyprland
chmod +x "$W"/stubs/*
tar -C "$SRC" --exclude=./backups --exclude=./.git -cf - . | tar -C "$W/repo" -xf -

seed='[General]
history_expression=1+1
precision=10'
printf '%s\n' "$seed" > "$W/home/.config/qalculate/qalculate-gtk.cfg"
obs="$W/home/.config/tidal-hifi/userscripts/volume-sync.js"     # uno de OBSOLETE_FILES
mkdir -p "$(dirname "$obs")"; echo 'viejo' > "$obs"

run() { HOME="$W/home" PATH="$W/stubs:$PATH" "$W/repo/install.sh" -y > "$W/install$1.log" 2>&1 || fail "install $1 (ver log)"; }

run 1
[ ! -e "$obs" ] || fail "no borró el obsoleto volume-sync.js"
grep -qx 'history_expression=1+1' "$W/home/.config/qalculate/qalculate-gtk.cfg" || fail "se perdió el historial de qalculate"
[ -L "$W/home/.config/waybar/style.css" ] || fail "waybar/style.css no quedó como symlink"
[ -f "$W/home/.config/waybar/config" ] || fail "falta waybar/config"
grep -q "$W/home/.config/gtk-4.0/colors.css" "$W/home/.local/share/themes/Matugen-a/gtk-4.0/gtk.css" \
  || fail "no se reescribió /home/<usuario> en el tema GTK4"

run 2
grep -q 'TOTAL: 0 nuevos' "$W/install2.log" || fail "la 2da corrida crea archivos: $(grep TOTAL "$W/install2.log")"
b2=$(find "$W/repo/backups" -mindepth 1 -maxdepth 1 | sort | tail -1)
pisados=$(cd "$b2/files" && find . -type f | sort | tr '\n' ' ')
[ "$pisados" = "./.config/qalculate/qalculate-gtk.cfg " ] || fail "la 2da corrida pisa más de lo esperado: $pisados"

for b in $(ls -1 "$W/repo/backups" | sort -r); do
  HOME="$W/home" PATH="$W/stubs:$PATH" "$W/repo/revert.sh" "$b" < <(yes s) > "$W/revert-$b.log" 2>&1 || fail "revert $b"
done
quedan=$(cd "$W/home" && find . \( -type f -o -type l \) | sort | tr '\n' ' ')
[ "$quedan" = "./.config/qalculate/qalculate-gtk.cfg ./.config/tidal-hifi/userscripts/volume-sync.js " ] \
  || fail "revert dejó archivos (o no repuso el obsoleto): $quedan"
[ "$(cat "$obs")" = viejo ] || fail "revert no repuso volume-sync.js"
[ "$(cat "$W/home/.config/qalculate/qalculate-gtk.cfg")" = "$seed" ] || fail "revert no repuso qalculate-gtk.cfg"

echo "OK: install (2 corridas) + revert en HOME falso"
