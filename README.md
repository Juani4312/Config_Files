# Sync

Mi customización de Arch + Hyprland, lista para clonar en otra PC.

## Qué contiene
| Carpeta | Va a |
|---|---|
| `config/<x>` | `~/.config/<x>`: hypr, waybar, rofi, kitty, cava, fastfetch, gtk-3.0/4.0, swaync, wlogout, matugen, spicetify, btop, bonsai, neofetch, autostart, nvim, ghostty, ohmyposh, colors, fontconfig, viegphunt, steam-theme, millennium, ZapZap, `vesktop/{themes,settings}`, `tidal-hifi/themes`, `nvim-kickstart` + archivos sueltos (`mimeapps.list`, `xdg-terminals.list`, `starship.toml`, `qalculate/qalculate-gtk.cfg`, `Code/User/settings.json`, `systemd/user/autoscroll.service`, ...) |
| `home/` | dotfiles de la home (`.bashrc`, `.bash_profile`, `.zshrc`, `.zshenv`, `.nanorc`, `.tmux.conf`, `.gitconfig`, ...), `.tmux/`, `.fonts/`, `.icons/` y `Pictures/Wallpapers` (sueltos + `Set/`) |
| `extra/` | temas que viven fuera de `~/.config`: ZapZap, `userChrome/userContent.css` de LibreWolf, extensión de VS Code `local.matugen-theme`, tema `matugen` de Millennium (Steam), tema de PrismLauncher, temas GTK `Matugen-a/b`, cursor `Matu` (`~/.local/share/icons`), `bin/wivrn-dashboard-avahi` (`~/.local/bin`), `dconf-interface.ini` (tema GTK, íconos, cursor, fuentes) y `system/` (archivos de `/etc`: regla udev del autoscroll; `install.sh` los instala con sudo si cambiaron) |
| `packages/` | `pacman.txt` (explícitos) y `aur.txt` (foreign) |

Varios `~/.config/<x>` (nvim, ghostty, ohmyposh, colors, fontconfig, viegphunt) y `.zshrc`, `.tmux.conf`, `.tmux`
son symlinks a `~/dotfiles`; acá se guarda el **contenido real** (`tar -h` / `cp -L`).

LibreWolf: se usa el perfil activo (`Default=` de `installs.ini`, en `~/.librewolf` o `~/.config/librewolf/librewolf`).
Al instalar, `install.sh` copia ahí los `chrome/*.css` y reescribe las rutas de LibreWolf en `~/.config/matugen/config.toml`
para que apunten al perfil de esa máquina.

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
| Fondo de pantalla | awww (`awww-daemon`); `SUPER+W` abre un selector en rofi con carpetas (`Set/` primero, `..` vuelve) | `config/hypr`, `home/Pictures/Wallpapers` |
| Paleta de colores | matugen (genera colores desde el wallpaper) | `config/matugen` |
| Terminal | Kitty (Ghostty configurado) | `config/kitty`, `config/ghostty` |
| Shell | zsh (zinit, fzf, zoxide, oh-my-posh), bash | `home/.zshrc`, `home/.zshenv`, `config/ohmyposh`, `home/.bashrc` |
| Multiplexor | tmux + tpm | `home/.tmux.conf`, `home/.tmux` |
| File manager | Nemo (default) · Yazi en terminal (`kitty yazi`) · Nautilus instalado de respaldo | `config/gtk-3.0/gtk.css`, `config/mimeapps.list` |
| Navegadores | LibreWolf (con `userChrome`/`userContent` propios), Google Chrome | `extra/librewolf-chrome` |
| YouTube | Enhancer for YouTube (extensión de LibreWolf) con CSS + paleta de matugen; `theme-reload.sh` los escribe en el storage de la extensión al reiniciar LibreWolf (`youtube-enhancer-apply.sh` + `moz_ext_storage.py`, solo con LibreWolf cerrado) | `config/matugen/templates/youtube-enhancer*`, `config/matugen/scripts` |
| Mensajería | ZapZap (WhatsApp) con tema de matugen | `extra/zapzap` |
| Editor | Visual Studio Code (tema matugen), Neovim (+ kickstart con `vk`), nano | `extra/vscode-matugen-theme`, `config/Code/User/settings.json`, `config/nvim`, `config/nvim-kickstart`, `home/.nanorc` |
| Steam | Millennium con tema `matugen` (generado por `steam-theme/build.sh`) | `config/steam-theme`, `config/millennium`, `extra/steam-millennium-theme` |
| Monitor / info | btop, fastfetch, cava (visualizador de audio) | `config/btop`, `config/fastfetch`, `config/cava` |
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
`.ssh`, `.gnupg`, perfiles de Chrome/LibreWolf/Zen, sesiones de Vesktop/ZapZap/TIDAL, tokens de `gh` y `tidal_dl_ng`,
Bitwarden, Proton Authenticator, nicotine, OrpheusDL, REAPER, `.bash_history`, `.cache`, `.claude`,
y los scripts sueltos de la home (`mountWin.sh`, `reset-alien.sh`, ...) que dependen de discos/juegos de esta PC.
Esos se reconfiguran a mano en cada PC.

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
