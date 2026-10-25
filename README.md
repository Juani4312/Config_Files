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

## Aplicaciones que uso
Todo lo de esta tabla está instalado en esta PC; los paquetes exactos están en `packages/`.

| Rol | App | Config en el repo |
|---|---|---|
| Compositor / WM | [Hyprland](https://hypr.land) (config en Lua) | `config/hypr` |
| Barra | Waybar | `config/waybar` |
| Launcher | Rofi (`SUPER+R`, drun; menú de wifi propio) | `config/rofi` |
| Notificaciones | SwayNC | `config/swaync` |
| Menú de apagado | wlogout | `config/wlogout` |
| Lockscreen / idle | hyprlock, hypridle | `config/hypr` |
| Fondo de pantalla | awww (`awww-daemon`) | `config/hypr`, `home/Pictures/wallpapers` |
| Paleta de colores | matugen (genera colores desde el wallpaper) | `config/matugen` |
| Terminal | Kitty | `config/kitty` |
| File manager | Nemo (default) · Yazi en terminal (`kitty yazi`) · Nautilus instalado de respaldo | `config/gtk-3.0/gtk.css`, `config/mimeapps.list` |
| Navegadores | LibreWolf (con `userChrome`/`userContent` propios), Google Chrome | `extra/librewolf-chrome` |
| Mensajería | ZapZap (WhatsApp) con tema de matugen | `extra/zapzap` |
| Editor | Visual Studio Code, nano | — |
| Monitor / info | btop, fastfetch, cava (visualizador de audio) | `config/fastfetch`, `config/cava` |
| Audio | PipeWire + WirePlumber, pavucontrol, pamixer, playerctl | — |
| Brillo / energía | brightnessctl, power-profiles-daemon | — |
| Red / Bluetooth | NetworkManager (nm-applet, `nmcli`), BlueZ + Blueman | — |
| Capturas / portapapeles | grim, slurp, wl-clipboard, hyprpicker | — |
| Polkit / portal | hyprpolkitagent, xdg-desktop-portal-hyprland | — |
| Impresión | CUPS, system-config-printer | — |
| Fuentes | JetBrainsMono Nerd Font, Noto (+CJK, emoji), DejaVu, Liberation | — |
| Gestión de paquetes | pacman, yay, GNU Stow | `config/yay` |
| Git | git, GitHub CLI (`gh`) | `home/.gitconfig` |

**Con tema pero sin instalar en esta PC:** Vesktop (`config/vesktop`) y Spicetify (`config/spicetify`).
Matugen les genera el tema, pero las apps no figuran en `packages/`; instalalas aparte si las querés.

## NO se sincroniza (a propósito)
`.ssh`, `.gnupg`, perfiles de Chrome/LibreWolf, sesiones de Vesktop/ZapZap, tokens de `gh`,
`.bash_history`, `.cache`, `.claude`. Esos se reconfiguran a mano en cada PC.

## Usar en la PC principal
```bash
git clone https://github.com/Juani4312/Sync.git ~/Sync
cd ~/Sync
./install.sh -n      # solo revisión: nuevos/cambiados/iguales + diff de binds de hypr
./install.sh         # revisa, pide confirmación, respalda y recién ahí instala
./install.sh -p      # igual, y además instala los paquetes
```

### Backups y revert
Antes de pisar nada, `install.sh` guarda en `backups/<fecha>/`:
- `files/`: copia exacta de cada archivo que se iba a sobrescribir (misma ruta relativa a `~`)
- `manifest.txt`: symlinks que había (ej. `~/.config/hypr -> ~/dotfiles/...`); se reemplazan por una copia real y el original no se toca
- `created.txt`: archivos que no existían y creó la instalación
- `review.txt`: la revisión completa (incluye qué binds se pierden y cuáles se agregan)

```bash
./revert.sh -l          # lista backups
./revert.sh [fecha]     # restaura los archivos y borra los creados (sin fecha: el último)
```
`backups/` queda dentro del repo; commitealo si querés conservarlo en GitHub.

## Actualizar desde esta PC
```bash
~/Sync/update.sh -p   # copia, commitea y pushea
```
Para agregar más carpetas, editá los arrays de `lib.sh`.
