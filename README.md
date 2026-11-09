# PC Config File

Mi customización de Arch Linux + Hyprland, lista para clonar en otra PC.

**Idea central:** todo el sistema toma su paleta del fondo de pantalla. `SUPER+W` elige un wallpaper,
[matugen](https://github.com/InioX/matugen) genera una paleta Material You a partir de él y la escribe en
los temas de ~25 apps; después `theme-reload.sh` recarga en vivo lo que puede y reinicia (en su mismo
workspace) lo que no.

> **Instalar, aplicar, usar y desinstalar:** ver [`instructions.md`](instructions.md). Está escrito para
> leerse aparte, y para que un agente (Claude Code) lo pueda seguir paso a paso.

---

## Índice
1. [Qué contiene el repo](#qué-contiene-el-repo)
2. [Aplicaciones](#aplicaciones)
3. [Tema dinámico (matugen)](#tema-dinámico-matugen)
4. [Hyprland](#hyprland)
5. [Barra, launcher, notificaciones y menús](#barra-launcher-notificaciones-y-menús)
6. [Apps con tema propio](#apps-con-tema-propio)
7. [Cursor, GTK, fuentes y shell](#cursor-gtk-fuentes-y-shell)
8. [Autoscroll con el mouse](#autoscroll-con-el-mouse)
9. [Atajos de teclado](#atajos-de-teclado)
10. [Scripts del repo](#scripts-del-repo)
11. [Qué NO se sincroniza](#qué-no-se-sincroniza)

---

## Qué contiene el repo
| Carpeta | Va a |
|---|---|
| `config/<x>` | `~/.config/<x>`: hypr, waybar, rofi, kitty, cava, fastfetch, gtk-3.0/4.0, swaync, wlogout, matugen, spicetify, btop, bonsai, neofetch, autostart, nvim, ghostty, ohmyposh, colors, fontconfig, viegphunt, steam-theme, millennium, ZapZap, `vesktop/{themes,settings}`, `tidal-hifi/themes`, `nvim-kickstart` + archivos sueltos (`mimeapps.list`, `xdg-terminals.list`, `starship.toml`, `qalculate/qalculate-gtk.cfg`, `Code/User/settings.json`, `systemd/user/autoscroll.service`, ...) |
| `home/` | dotfiles de la home (`.bashrc`, `.bash_profile`, `.zshrc`, `.zshenv`, `.nanorc`, `.tmux.conf`, `.gitconfig`, ...), `.tmux/`, `.fonts/`, `.icons/` y `Pictures/Wallpapers` (sueltos + `Set/`) |
| `extra/` | temas que viven fuera de `~/.config`: ZapZap, `userChrome/userContent.css` de LibreWolf, extensión de VS Code `local.matugen-theme`, tema `matugen` de Millennium (Steam), tema de PrismLauncher, temas GTK `Matugen-a/b`, cursor `Matu` (`~/.local/share/icons`), `bin/wivrn-dashboard-avahi` (`~/.local/bin`), `dconf-interface.ini` (tema GTK, íconos, cursor, fuentes) y `system/` (archivos de `/etc`: regla udev del autoscroll) |
| `packages/` | `pacman.txt` (paquetes explícitos) y `aur.txt` (AUR / foreign) |
| `install.sh` · `update.sh` · `revert.sh` · `lib.sh` | instalar en una máquina · copiar esta máquina al repo · deshacer una instalación · listas compartidas (qué se sincroniza) |

Varios `~/.config/<x>` (nvim, ghostty, ohmyposh, colors, fontconfig, viegphunt) y `.zshrc`, `.tmux.conf`, `.tmux`
son symlinks a `~/dotfiles` en esta PC; acá se guarda el **contenido real** (`tar -h` / `cp -L`).

Archivos propios de cada máquina que **no** viajan: `~/.config/hypr/monitors.lua` (resolución, posición,
scale) y el symlink `~/.config/hypr/current_wallpaper` (lo crean `install.sh` y el selector de fondos).

---

## Aplicaciones
Todo lo de esta tabla está instalado en esta PC; los paquetes exactos están en `packages/`.

| Rol | App | Config en el repo |
|---|---|---|
| Compositor / WM | [Hyprland](https://hypr.land) (config en **Lua**) | `config/hypr` |
| Barra | Waybar (estilo "bintang") | `config/waybar` |
| Launcher | Rofi estilo Spotlight (`SUPER+R`) + menú de wifi propio | `config/rofi` |
| Notificaciones | SwayNC | `config/swaync` |
| Menú de apagado | wlogout (íconos teñidos con la paleta) | `config/wlogout` |
| Lockscreen / idle | hyprlock, hypridle | `config/hypr` |
| Fondo de pantalla | awww (`awww-daemon`); `SUPER+W` abre un selector en rofi con carpetas | `config/hypr`, `home/Pictures/Wallpapers` |
| Paleta de colores | matugen | `config/matugen` |
| Terminal | Kitty (Ghostty configurado) | `config/kitty`, `config/ghostty` |
| Shell | zsh (zinit, fzf, zoxide, oh-my-posh), bash | `home/.zshrc`, `home/.zshenv`, `config/ohmyposh`, `home/.bashrc` |
| Multiplexor | tmux + tpm | `home/.tmux.conf`, `home/.tmux` |
| File manager | Nemo (default) · Yazi en terminal (`SUPER+SHIFT+E`) · Nautilus de respaldo | `config/gtk-3.0/gtk.css`, `config/mimeapps.list` |
| Navegadores | LibreWolf (con `userChrome`/`userContent` propios), Google Chrome | `extra/librewolf-chrome` |
| YouTube | Enhancer for YouTube (extensión de LibreWolf) con CSS y paleta de matugen | `config/matugen/templates/youtube-enhancer*` |
| Mensajería | ZapZap (WhatsApp) | `extra/zapzap` |
| Música | tidal-hifi | `config/tidal-hifi/themes` |
| Editor | VS Code (tema matugen), Neovim (+ kickstart con `vk`), nano | `extra/vscode-matugen-theme`, `config/Code/User/settings.json`, `config/nvim`, `config/nvim-kickstart`, `home/.nanorc` |
| Steam | Millennium con tema `matugen` | `config/steam-theme`, `config/millennium`, `extra/steam-millennium-theme` |
| Minecraft | PrismLauncher (tema matugen) | `extra/prismlauncher-theme` |
| Calculadora | Qalculate (colores de matugen) | `config/qalculate/qalculate-gtk.cfg` |
| Monitor / info | btop, fastfetch, cava | `config/btop`, `config/fastfetch`, `config/cava` |
| Audio | PipeWire + WirePlumber, pavucontrol (`SUPER+K`), pamixer, playerctl | `config/pavucontrol.ini` |
| Brillo / energía | brightnessctl, power-profiles-daemon | — |
| Red / Bluetooth | NetworkManager (nm-applet, `nmcli`), BlueZ + Blueman | — |
| Capturas / portapapeles | grim + slurp (`SUPER+P`), wl-clipboard + cliphist (`SUPER+V`), hyprpicker (`SUPER+SHIFT+C`) | `config/hypr/scripts` |
| Polkit / portal | hyprpolkitagent, xdg-desktop-portal-hyprland | — |
| Impresión | CUPS, system-config-printer | — |
| Fuentes | JetBrainsMono Nerd Font, Noto (+CJK, emoji), DejaVu, Liberation | `home/.fonts`, `config/fontconfig` |
| Paquetes | pacman, yay, GNU Stow | `config/yay` |
| Git | git, GitHub CLI (`gh`) | `home/.gitconfig` |

**Con tema pero sin instalar en esta PC:** Vesktop (`config/vesktop`) y Spicetify (`config/spicetify`).
Matugen les genera el tema, pero no figuran en `packages/`; instalalas aparte si las querés.

---

## Tema dinámico (matugen)

### Flujo al cambiar el fondo (`SUPER+W`)
1. `hypr/scripts/wppicker.sh` abre rofi sobre `~/Pictures/Wallpapers`: primero las subcarpetas (`Set/`), después
   las imágenes sueltas (las más nuevas primero); `..` vuelve atrás.
2. `matugen image --source-color-index 0 <imagen>` pone el fondo (vía awww, con transición) y renderiza todos los
   templates de `config/matugen/templates/` según `config/matugen/config.toml`.
3. Los `post_hook` de matugen recargan lo instantáneo: waybar (SIGUSR2), kitty (SIGUSR1), cava, cursor `Matu`
   (`build.py --apply`), prompt de oh-my-posh, colores de Qalculate y tema de Steam (`steam-theme/build.sh`).
4. `matugen/scripts/theme-reload.sh` (en segundo plano) hace el resto (log en `$XDG_RUNTIME_DIR/theme-reload.log`):
   - **En vivo:** GTK3 (alterna el tema `Matugen-a` ↔ `Matugen-b` para que nemo/waybar relean los colores), btop
     (SIGUSR2), swaync (`swaync-client -rs`), íconos de wlogout (`tint-icons.sh`). VS Code y Vesktop vigilan sus
     archivos solos.
   - **Reinicio automático**, vuelven a su workspace: ZapZap y Qalculate.
   - **Reinicio "inteligente":** tidal-hifi se reinicia solo si no está reproduciendo; Steam solo si no hay un juego
     abierto. Si no, se pregunta.
   - **Preguntan:** LibreWolf y PrismLauncher, con un popup único "Reiniciar todo / Ignorar" y una notificación por app
     que queda en el panel de swaync.
   - **Steam:** la ventana la crea `steamwebhelper` (otro PID) y, después del login, Steam la vuelve a mapear en el
     workspace con foco. El script la vigila hasta 2 min y la devuelve a su workspace.
   - **YouTube (Enhancer):** su CSS vive en la base IndexedDB de la extensión, así que se escribe con LibreWolf cerrado
     (justo antes de relanzarlo, o en el momento si ya estaba cerrado).
5. Se actualiza `~/.config/hypr/current_wallpaper`, que es el fondo que se carga al iniciar sesión.

### Templates (`config/matugen/templates` → destino)
| Template | Genera | Recarga |
|---|---|---|
| `colors.css` | `~/.config/waybar/colors.css` (también lo importan swaync y wlogout) | SIGUSR2 a waybar |
| `kitty-colors.conf` | `~/.config/kitty/colors.conf` | SIGUSR1 a kitty |
| `hyprland-colors.conf` / `.lua` | `~/.config/hypr/colors.conf` (hyprlock) / `colors.lua` (bordes, etc.) | hyprctl reload |
| `gtk-colors.css` | `~/.config/gtk-3.0/colors.css`, `~/.config/gtk-4.0/colors.css` | toggle Matugen-a/b (GTK3); GTK4 al reiniciar la app |
| `rofi-colors.rasi` | `~/.config/rofi/colors.rasi` (incluye el gradiente y colores "glass") | próxima apertura |
| `matugen-cava` | `~/.config/cava/config` | SIGUSR1 |
| `spotify-colors.ini` | `~/.config/spicetify/Themes/text/color.ini` | — |
| `midnight-discord.css` | `~/.config/vesktop/themes/matugen.css` | Vesktop vigila el archivo |
| `firefox-userChrome.css` / `firefox-userContent.css` | `<perfil LibreWolf>/chrome/` | reinicio de LibreWolf |
| `youtube-enhancer.css` / `youtube-enhancer-colors.json` | `~/.config/youtube-enhancer/` → storage de Enhancer for YouTube | reinicio de LibreWolf |
| `zapzap.css` | `~/.local/share/ZapZap/customizations/global/css/matugen.css` | reinicio automático |
| `tidal-hifi.css` | `~/.config/tidal-hifi/themes/matugen.css` | reinicio (si no suena música) |
| `btop.theme` | `~/.config/btop/themes/matugen.theme` | SIGUSR2 |
| `vscode-theme.json` | extensión `local.matugen-theme` | en vivo (`_watch`) |
| `qalculate-colors.sh` | script que reescribe `qalculate-gtk.cfg` | reinicio automático |
| `steam-millennium.css` | `~/.config/steam-theme/colors.css` → `build.sh` arma el tema Millennium | reinicio (si no hay juego) |
| `prismlauncher-theme.json` / `-style.css` | `~/.local/share/PrismLauncher/themes/matugen/` | reinicio |
| `cursor-colors.json` | `~/.config/hypr/scripts/cursor/colors.json` → cursor `Matu` | `hyprctl setcursor` |
| `ohmyposh-palette.json` | `~/.config/ohmyposh/matugen-palette.json` → `matugen.omp.json` | próximo prompt |

---

## Hyprland
- Config en **Lua**: `config/hypr/hyprland.lua` carga `configs/{tags,looknfeel,animations,opacity,windowrules,input,keybinds}.lua`
  y `monitors.lua` (propio de cada máquina, opcional).
- `hyprctl dispatch` usa sintaxis Lua: `hyprctl dispatch 'hl.dsp.focus({ workspace = "3" })'`.
- Autostart (`hl.on("hyprland.start")`): waybar, awww-daemon + fondo actual, swaync, hyprpolkitagent, hypridle,
  indicador de autoscroll, cliphist (texto e imágenes). El servicio `autoscroll.service` arranca por systemd.
- **Window rules:** el diálogo de Bitwarden de LibreWolf y la app Bitwarden flotan centrados en vertical; Proton
  Authenticator flota; en Steam flota todo menos la ventana principal ("Steam"), y la lista de amigos es angosta.
  Se ignoran los pedidos de maximizar de las apps.
- **Workspace especial "magic"** (scratchpad): `SUPER+S` lo muestra; `SUPER+SHIFT+S` manda la ventana ahí recordando
  su workspace de origen, y si ya está ahí la devuelve (`scripts/special-move.sh`).
- **Animaciones:** popin para rofi, fades de capas (`configs/animations.lua`); opacidad por app en `configs/opacity.lua`.
- **hypridle:** baja el brillo a los 2,5 min (el bloqueo, el apagado de pantalla y la suspensión están comentados).
- `SUPER+O` (`reload-all.sh`) recarga Hyprland y reinicia swaync y waybar.

## Barra, launcher, notificaciones y menús
- **Waybar** (`config/waybar`): `config` y `style.css` apuntan a la variante elegida en `configs/` y `style/`
  (actual: "bintang default"; `SUPER+CTRL+B` / `SUPER+ALT+B` cambian estilo y layout).
  - Isla de workspaces por monitor con animaciones (el foco crece a una píldora con glow; urgente parpadea en
    `@tertiary`), burbuja 特 a la izquierda cuando hay ventanas en el workspace especial.
  - Volumen propio (`scripts/volume.py`, con `pactl subscribe`): las ondas del parlante se animan al pasar el mouse.
  - Campana de swaync que suena una vez con cada notificación nueva; batería que "respira" cargando y titila crítica;
    botón de apagado con glow en `@primary`.
  - En esta PC `style.css` es un **hardlink** a `style/bintang default.css`: editalo en el lugar, no lo reemplaces.
- **Rofi** (`config/rofi/config.rasi`): estilo Spotlight compartido por todos los menús. Solo el launcher agrega
  `require-input` (la lista aparece al escribir). `wifi-menu.sh` es un menú de redes propio.
- **SwayNC** (`config/swaync`): colores de waybar, popups de 390 px; el panel se agranda o achica con las flechas
  ◂▸▴▾ (`scripts/resize.sh`). Reglas: las notificaciones `theme.summary` solo se ven como popup, las `theme.app`
  van directo al panel.
- **wlogout**: íconos PNG re-teñidos con el primary en cada cambio de fondo (`tint-icons.sh` → `icons/matugen/`).
- **hyprlock**: colores de `hypr/colors.conf`.

## Apps con tema propio
- **LibreWolf:** `userChrome.css` (barra, pestañas, paneles) y `userContent.css` (about:home, about:newtab, páginas
  internas, scrollbars finas). `install.sh` los copia al perfil activo y reescribe las rutas en `matugen/config.toml`.
- **YouTube (Enhancer for YouTube):** tema base "DeepDark custom" con la paleta del fondo + CSS propio: barra superior
  translúcida con blur, buscador y chips como píldoras, miniaturas redondeadas que se levantan con glow, menú lateral
  con el activo en `secondary_container`, botones y barra de progreso en `primary`, menús del reproductor translúcidos.
  `youtube-enhancer-apply.sh` lo escribe en el `storage.local` de la extensión con `moz_ext_storage.py` (codec de
  IndexedDB de Firefox en Python puro). No edites el CSS desde la página de la extensión: se pisa en cada cambio de fondo.
- **Steam (Millennium):** `steam-theme/generate.py` extrae las reglas de color del CSS de Steam y las re-emite como
  `var(--m-*)`; `build.sh` arma `client.css`/`webkit.css` del tema `matugen`. Se inyecta solo en las ventanas
  principales (no en el login) para que Steam arranque rápido. Tras una actualización de Steam: `build.sh --regen`.
- **Vesktop:** paleta de matugen sobre el layout de midnight-discord (`themes/lib/midnight-fixed.css` tiene los nombres
  de clase nuevos de Discord).
- **tidal-hifi, ZapZap, PrismLauncher, VS Code, btop, cava, Qalculate, kitty, Spicetify:** ver la tabla de templates.

## Cursor, GTK, fuentes y shell
- **Cursor `Matu`:** generado por `hypr/scripts/cursor/build.py` (formas redondeadas, cuerpo oscuro, acentos en
  primary) en `~/.local/share/icons/Matu`, en XCursor y hyprcursor. Se rehace en cada cambio de fondo.
  `build.py --preview out.png` muestra una hoja de contactos.
- **GTK:** temas `Matugen-a`/`Matugen-b` = adw-gtk3-dark + `colors.css`. GTK4/libadwaita importa
  `gtk-4.0/colors.css`. Tema, íconos, cursor y fuentes en dconf (`extra/dconf-interface.ini`).
- **Fuentes:** JetBrainsMono Nerd Font (terminal y barra), Noto, `home/.fonts`.
- **zsh + oh-my-posh:** el diseño del prompt (segmentos tipo píldora) está en `config/ohmyposh/viet.omp.json`;
  `ohmyposh-build.py` le inyecta la paleta → `matugen.omp.json`, que carga `.zshrc`.

## Autoscroll con el mouse
`hypr/scripts/autoscroll.py` (python-evdev, servicio `autoscroll.service`) toma los mouse y los re-emite por un
dispositivo virtual. **Clic medio normal = clic medio; `Shift` + clic medio = autoscroll** (un toque lo fija y
mover el mouse desplaza; mantener y arrastrar desplaza mientras se mantiene; cualquier clic sale). Un indicador
GTK4 layer-shell muestra la burbuja. Los mouse se acceden con la regla udev `70-mouse-uaccess.rules`
(sin meter al usuario en el grupo `input`). El estado de Shift llega desde binds de Hyprland, no leyendo el teclado.
Si el mouse se porta raro, este daemon es el primer sospechoso: `journalctl --user -u autoscroll`.

---

## Atajos de teclado
`SUPER` = tecla Windows. Definidos en `config/hypr/configs/keybinds.lua`.

| Atajo | Acción |
|---|---|
| `SUPER+T` / `SUPER+SHIFT+Enter` | terminal (kitty) / terminal flotante |
| `SUPER+R` | launcher (rofi) |
| `SUPER+E` / `SUPER+SHIFT+E` | Nemo / Yazi |
| `SUPER+B` / `SUPER+N` | LibreWolf / Google Chrome |
| `SUPER+W` | **elegir wallpaper → retematiza todo el sistema** |
| `SUPER+C` | cerrar ventana |
| `SUPER+SHIFT+Q` | matar el proceso de la ventana activa |
| `SUPER+F` / `SUPER+SHIFT+V` | pantalla completa / alternar flotante |
| `SUPER+J` | cambiar orientación del split (dwindle) |
| `SUPER+1..0` / `SUPER+SHIFT+1..0` | ir a workspace / mover ventana a workspace |
| `SUPER+←/→` / `SUPER+SHIFT+←/→` | workspace anterior/siguiente / mover ventana ahí |
| `SUPER+↑/↓` | foco arriba/abajo |
| `SUPER+CTRL+flechas` / `SUPER+ALT+flechas` | mover ventana / redimensionar |
| `SUPER+rueda` | recorrer workspaces |
| `SUPER+clic izq.` / `SUPER+clic der.` | arrastrar / redimensionar ventana |
| `SUPER+S` / `SUPER+SHIFT+S` | mostrar workspace especial / mandar o devolver ventana |
| `SUPER+V` | historial del portapapeles |
| `SUPER+P` | captura de región (se guarda en `~/Pictures/Screenshots` y se copia) |
| `SUPER+SHIFT+C` | selector de color (hyprpicker) |
| `SUPER+Espacio` | alternar teclado us / latam |
| `SUPER+K` | pavucontrol |
| `SUPER+M` | mutear micrófono |
| `SUPER+L` | bloquear pantalla |
| `SUPER+H` | ocultar/mostrar waybar |
| `SUPER+O` | recargar Hyprland + swaync + waybar |
| `SUPER+SHIFT+R` | reiniciar waybar (script viejo) |
| `SUPER+CTRL+B` / `SUPER+ALT+B` | menú de estilos / layouts de waybar |
| `CTRL+ALT+Supr` | salir de Hyprland |
| Teclas multimedia | volumen, mic, brillo y reproducción (funcionan con la pantalla bloqueada) |
| `Shift` + clic medio | autoscroll |

---

## Scripts del repo
```bash
./install.sh -n     # solo revisión: qué es nuevo / cambia / igual + diff de binds de hypr
./install.sh        # revisa, pide confirmación, respalda en backups/<fecha>/ e instala
./install.sh -p     # igual + instala paquetes (pacman + yay)
./update.sh [-n] [-p]   # copia esta máquina al repo (-p: commit "Sync <fecha>" + push)
./revert.sh -l | [fecha] # lista backups / deshace una instalación
```
Qué se sincroniza se define en los arrays de `lib.sh` (`CONFIG_DIRS`, `CONFIG_FILES`, `HOME_FILES`, `HOME_DIRS`,
`EXTRA_FILES`, `EXTRA_DIRS`, `SYSTEM_FILES`). Detalle completo en [`instructions.md`](instructions.md).

## Qué NO se sincroniza
`.ssh`, `.gnupg`, perfiles de Chrome/LibreWolf/Zen (salvo `chrome/*.css`), sesiones de Vesktop/ZapZap/TIDAL, tokens
de `gh` y `tidal_dl_ng`, Bitwarden, Proton Authenticator, nicotine, OrpheusDL, REAPER, `.bash_history`, `.cache`,
`.claude`, `monitors.lua`, `backups/`, y los scripts sueltos de la home (`mountWin.sh`, `reset-alien.sh`, ...) que
dependen de discos/juegos de esta PC. Tampoco las extensiones de LibreWolf (Enhancer for YouTube se instala a mano).
Esos se reconfiguran a mano en cada PC.
