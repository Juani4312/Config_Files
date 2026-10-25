# Sync

Mi customización de Arch + Hyprland, lista para clonar en otra PC.

## Qué contiene
| Carpeta | Va a |
|---|---|
| `config/<x>` | `~/.config/<x>` (hypr, waybar, rofi, kitty, cava, fastfetch, gtk-3.0/4.0, swaync, wlogout, matugen, spicetify, vesktop, yay) |
| `home/` | dotfiles de la home (`.bashrc`, `.bash_profile`, `.gitconfig`, ...) y `Pictures/wallpapers` |
| `extra/` | temas de ZapZap y `userChrome/userContent.css` de LibreWolf |
| `packages/` | `pacman.txt` (explícitos) y `aur.txt` (foreign) |

Los `~/.config/<x>` originales eran symlinks a `~/dotfiles`; acá se guarda el **contenido real** (rsync `-L`).

## NO se sincroniza (a propósito)
`.ssh`, `.gnupg`, perfiles de Chrome/LibreWolf, sesiones de Vesktop/ZapZap, tokens de `gh`,
`.bash_history`, `.cache`, `.claude`. Esos se reconfiguran a mano en cada PC.

## Usar en la PC principal
```bash
git clone git@github.com:Juani4312/Sync.git ~/Sync
cd ~/Sync
./install.sh -n      # dry-run: mira qué va a cambiar
./install.sh -p      # instala todo (+ paquetes); sin -p no toca paquetes
```
Lo que se pisa se respalda en `~/.local/state/sync-backup/<fecha>/`.

## Actualizar desde esta PC
```bash
~/Sync/update.sh -p   # copia, commitea y pushea
```
Para agregar más carpetas, editá los arrays de `lib.sh`.
