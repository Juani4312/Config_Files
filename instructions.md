# Instrucciones: instalar, aplicar, usar y desinstalar

Guía operativa del repo `Config_Files` (Arch Linux + Hyprland con tema dinámico de matugen). Para *qué* contiene cada
parte de la customización, ver [`README.md`](README.md). Este archivo dice *cómo* hacer cada cosa.

Está escrito para que lo siga una persona o un agente (Claude Code). Los comandos asumen que el repo está en
`~/Sync` (en la laptop original está en `~/Laptop/Sync`): reemplazá la ruta si es otra.

---

## 0. Reglas para un agente (Claude Code)
Leé esto antes de ejecutar nada.

1. **Primero revisión, después cambios.** Corré siempre `./install.sh -n` y mostrale al usuario el resumen (archivos
   nuevos/cambiados y binds de hypr que se pierden o se agregan) antes de instalar.
2. **Confirmación.** `install.sh` pide `[s/N]` por terminal. En una shell no interactiva hace falta `-y`: usalo solo
   después de que el usuario apruebe la revisión. `-p` instala paquetes con `sudo`: pedí permiso explícito.
3. **Nunca escribas dentro de `~/dotfiles`.** Varios `~/.config/<x>` pueden ser symlinks ahí; `install.sh` ya los
   reemplaza por copias reales y anota el symlink en el backup.
4. **No pises `~/.config/hypr/monitors.lua`.** Es propio de cada máquina; `install.sh` lo crea solo si falta.
5. **Editá templates, no archivos generados.** Todo lo que genera matugen (ver la tabla de templates en el README) se
   pisa en cada cambio de fondo. La fuente está en `~/.config/matugen/templates/`.
6. **Reiniciar apps interrumpe al usuario:** LibreWolf corta videos, tidal-hifi corta la música y Steam cierra juegos.
   Preguntá antes de reiniciarlas. Recargar waybar/swaync/Hyprland es inofensivo.
7. **`hyprctl dispatch` usa sintaxis Lua:** `hyprctl dispatch 'hl.dsp.focus({ workspace = "3" })'`,
   `hyprctl dispatch 'hl.dsp.exec_cmd("kitty")'`. La forma clásica (`dispatch workspace 3`) falla.
8. **`~/.config/waybar/style.css` puede ser un hardlink** a `style/<variante>.css`. Editalo en el lugar (con Edit);
   nunca `sed -i` ni reemplazar el archivo, porque rompe el enlace.
9. **Sincronizar después de cambiar configs:** `./update.sh` copia la máquina al repo. El push por SSH puede necesitar
   la passphrase de la clave del usuario: si `git push` falla con `Permission denied (publickey)`, avisale que corra
   `git -C ~/Sync push` en su terminal.
10. **Logs útiles:** `$XDG_RUNTIME_DIR/theme-reload.log` (cambio de tema), `journalctl --user -u autoscroll`
    (autoscroll), `hyprctl configerrors` (config de Hyprland).

---

## 1. Requisitos previos
- Arch Linux (o derivada) con usuario normal y `sudo`.
- `git` y `base-devel`. Para los paquetes AUR, `yay`:
  ```bash
  sudo pacman -S --needed git base-devel
  git clone https://aur.archlinux.org/yay-bin.git /tmp/yay-bin && (cd /tmp/yay-bin && makepkg -si)
  ```
- Una sesión de Hyprland. Si todavía no está instalado, se instala con `./install.sh -p` (paso 2.4) y después se elige
  "Hyprland" en el display manager, o se ejecuta `Hyprland` desde una TTY.

## 2. Instalación
### 2.1 Clonar
```bash
git clone https://github.com/Juani4312/Sync.git ~/Sync
cd ~/Sync
```

### 2.2 Revisar (no toca nada)
```bash
./install.sh -n
```
Muestra, por cada destino, cuántos archivos son nuevos, cuántos cambian y cuántos son iguales; los cambiados se
listan. Al final compara los binds de Hyprland: cuáles **se pierden** (quedan en el backup) y cuáles se agregan.

### 2.3 Instalar
```bash
./install.sh        # pide confirmación
./install.sh -y     # sin confirmación (shell no interactiva)
```
Qué hace, en orden:
1. Guarda en `backups/<fecha>/`: `files/` (copia de cada archivo que pisa), `manifest.txt` (symlinks reemplazados),
   `created.txt` (archivos que no existían), `review.txt` y `dconf-interface.ini` (dconf anterior).
2. Si falta `~/.config/hypr/monitors.lua`, lo genera con los monitores y el scale actuales (`hyprctl monitors`).
3. Copia `config/` → `~/.config`, `home/` → `~`, `extra/` → sus rutas (`~/.local/share/...`, `~/.vscode/...`,
   perfil de LibreWolf).
4. Carga `extra/dconf-interface.ini` (tema GTK, íconos, cursor, fuentes).
5. Apunta las rutas de LibreWolf de `~/.config/matugen/config.toml` al perfil activo de esta máquina.
6. Crea `~/.config/hypr/current_wallpaper` (por defecto, `Pictures/Wallpapers/Set/pacman-ghosts.png`).
7. Instala con `sudo` (pregunta) los archivos de sistema que cambiaron: `/etc/udev/rules.d/70-mouse-uaccess.rules`.
8. Habilita `autoscroll.service` (systemd de usuario) y da permisos de ejecución a los scripts.

### 2.4 Paquetes
```bash
./install.sh -p     # instalación + pacman -S --needed packages/pacman.txt + yay -S --needed packages/aur.txt
```
Algunas dependencias que usan los scripts están instaladas como dependencias de otros paquetes, así que no
figuran en `packages/`. En una máquina limpia, asegurate de tenerlas:
```bash
sudo pacman -S --needed jq gtk4-layer-shell libnotify python-gobject python-cairo python-evdev \
  imagemagick librsvg playerctl curl openbsd-netcat wl-clipboard cliphist grim slurp adw-gtk-theme matugen awww
```

### 2.5 Aplicar
```bash
hyprctl reload
~/.config/hypr/scripts/reload-all.sh     # o SUPER+O: recarga Hyprland + reinicia swaync y waybar
```
Después, elegí un fondo con **`SUPER+W`** para que matugen genere todos los temas con la paleta de esa imagen.
Si querés hacerlo sin rofi:
```bash
matugen image --source-color-index 0 ~/Pictures/Wallpapers/<imagen>
~/.config/matugen/scripts/theme-reload.sh
```
Para que tome el cursor, el tema GTK y las variables de entorno nuevas, cerrá sesión y volvé a entrar una vez.

## 3. Pasos manuales después de instalar
Estas cosas no se pueden copiar como archivos.

| Qué | Cómo |
|---|---|
| **Scale / monitores** | Editá `~/.config/hypr/monitors.lua` (resolución, posición, scale) y corré `hyprctl reload`. |
| **LibreWolf** | Abrilo una vez *antes* de `install.sh` para que exista el perfil (si no, no se copian `chrome/*.css`; corré `install.sh` de nuevo después). En `about:config`, `toolkit.legacyUserProfileCustomizations.stylesheets = true`. |
| **Enhancer for YouTube** | Instalalo desde addons.mozilla.org en LibreWolf y abrí sus opciones una vez (eso crea su base de storage). El script activa solo el tema "DeepDark custom" y el CSS custom. El tema de matugen se escribe solo en el próximo cambio de fondo que reinicie LibreWolf; para forzarlo ahora: cerrá LibreWolf y corré `~/.config/matugen/scripts/youtube-enhancer-apply.sh`. |
| **Steam (Millennium)** | `millennium` (AUR) instalado; abrí Steam una vez. El tema `matugen` ya queda activo por `~/.config/millennium/config.json`. Si falta CSS: `~/.config/steam-theme/build.sh --regen`. |
| **VS Code** | La extensión `local.matugen-theme` se copia sola; si no aparece el tema, elegí "Matugen" en *Preferences: Color Theme*. |
| **tidal-hifi** | En Settings → Theming elegí `matugen.css`. |
| **Vesktop** (opcional) | Instalalo aparte; en Settings → Themes activá `matugen.css`. |
| **Autoscroll** | La regla udev se aplica al reconectar el mouse o reiniciar. Comprobá con `systemctl --user status autoscroll`. |
| **Shell** | `chsh -s /usr/bin/zsh`; zinit y los plugins se instalan solos en el primer zsh. tmux: `prefix + I` instala los plugins de tpm. |
| **Git / SSH** | `~/.ssh` no viaja: generá una clave, agregala a GitHub y configurá el host que use el remoto. |

## 4. Verificar
```bash
hyprctl configerrors                         # vacío = OK
pgrep -x waybar && pgrep -x swaync && pgrep -x awww-daemon
systemctl --user is-active autoscroll        # active
tail -20 "$XDG_RUNTIME_DIR/theme-reload.log" # después de un SUPER+W
gsettings get org.gnome.desktop.interface gtk-theme   # 'Matugen-a' o 'Matugen-b'
gsettings get org.gnome.desktop.interface cursor-theme # 'Matu'
```
A la vista: barra con la isla de workspaces, rofi Spotlight con `SUPER+R` y, después de `SUPER+W`, todo
(bordes, barra, terminal, notificaciones, GTK) con el color del fondo.

---

## 5. Uso diario
### Cambiar el tema
- `SUPER+W` → elegir imagen (`Set/` es una carpeta; `..` vuelve). Se recolorea todo.
- Aparece **un popup "Reiniciar todo / Ignorar"** si hay apps que conviene reiniciar (LibreWolf, PrismLauncher, y
  tidal-hifi o Steam si estaban en uso). También queda una notificación por app en el panel de swaync (campana) con
  su propio botón "Reiniciar".
- "Ignorar" no pierde nada: esas apps toman los colores nuevos la próxima vez que se reinicien. YouTube (Enhancer)
  se actualiza en el próximo cambio de fondo en que LibreWolf se reinicie o esté cerrado.
- Agregar fondos: copiá imágenes a `~/Pictures/Wallpapers` (o a una subcarpeta). Los `.webp` aparecen sin miniatura.

### Mantener el repo al día (desde la máquina que cambiaste)
```bash
cd ~/Sync
./update.sh -n      # qué copiaría
./update.sh         # copia y hace git add (sin commit)
git commit -m "..." && git push
./update.sh -p      # o todo junto, con mensaje "Sync <fecha>"
```
`update.sh` también regenera `packages/*.txt`, `extra/dconf-interface.ini` y los temas de LibreWolf del perfil activo.
Los colores generados por matugen cambian con cada fondo, así que casi siempre aparecen en el diff: es normal.

### Traer cambios a otra máquina
```bash
cd ~/Sync && git pull && ./install.sh -n && ./install.sh
```

---

## 6. Personalizar y extender
### Cambiar un atajo
Editá `~/.config/hypr/configs/keybinds.lua` (`bind(mod("X"), hl.dsp....)`). Hyprland recarga solo al guardar; si no,
`hyprctl reload`.

### Darle tema de matugen a una app nueva
1. Creá el template en `~/.config/matugen/templates/<app>.<ext>` con variables como `{{colors.primary.default.hex}}`
   (los roles disponibles: `surface`, `surface_container[_low|_high|_highest]`, `on_surface`, `on_surface_variant`,
   `primary`, `on_primary`, `primary_container`, `secondary_container`, `tertiary`, `outline`, `outline_variant`, ...).
2. Agregalo a `~/.config/matugen/config.toml`:
   ```toml
   [templates.miapp]
   input_path = '~/.config/matugen/templates/miapp.css'
   output_path = '~/.config/miapp/colors.css'
   post_hook = 'pkill -USR1 miapp'   # opcional: solo si la app recarga con una señal
   ```
3. Si la app necesita reiniciarse, sumala en `~/.config/matugen/scripts/theme-reload.sh`: en `AUTO_RESTART` (sin
   preguntar) o en `ASK_RESTART` (con notificación), y completá `PROC`, `CLASS`, `CMD`, `NAME` (e `ICON` si pregunta).
4. Para probar solo ese template sin re-tematizar todo, usá una config temporal:
   ```bash
   printf '[config]\n[templates.miapp]\ninput_path = %s\noutput_path = %s\n' \
     "'~/.config/matugen/templates/miapp.css'" "'~/.config/miapp/colors.css'" > /tmp/m.toml
   matugen -c /tmp/m.toml image --source-color-index 0 "$(readlink -f ~/.config/hypr/current_wallpaper)"
   ```
5. Si los archivos viven fuera de las carpetas sincronizadas, agregalos a `lib.sh` (paso siguiente).

### Sincronizar algo nuevo
Editá los arrays de `lib.sh`:
- `CONFIG_DIRS` / `CONFIG_FILES`: carpetas o archivos dentro de `~/.config`.
- `HOME_FILES` / `HOME_DIRS`: relativos a `~`.
- `EXTRA_FILES` / `EXTRA_DIRS`: `"<origen relativo a ~>|<destino en el repo>"`.
- `SYSTEM_FILES`: rutas absolutas fuera de `~` (se instalan con sudo).

Nunca se copian `*.key`, `*.pem`, `*token*`, `*secret*`, `.env`, `*cache*`, `*.log` ni `*.bak*`.

### Cambiar el diseño de YouTube
Editá `~/.config/matugen/templates/youtube-enhancer.css`, regeneralo (`SUPER+W`, o la config temporal del paso 4 con
`youtube-enhancer.css` → `~/.config/youtube-enhancer/custom.css`), cerrá LibreWolf y corré
`~/.config/matugen/scripts/youtube-enhancer-apply.sh`. El tema base de Enhancer (DeepDark material) usa reglas
`!important` muy específicas: para pisarlas, igualá su selector.

### Steam después de una actualización
Si Steam cambia sus clases CSS, el tema queda incompleto: `~/.config/steam-theme/build.sh --regen` y reiniciá Steam.

---

## 7. Problemas comunes
| Síntoma | Causa / solución |
|---|---|
| El fondo cambia pero una app no | Mirá `$XDG_RUNTIME_DIR/theme-reload.log`. Las apps de la lista "preguntan" esperan que aceptes el reinicio. |
| GTK4 (nautilus, apps libadwaita) con colores viejos | GTK4 solo lee el CSS al iniciar: reiniciá la app. |
| YouTube sin tema | `youtube-enhancer-apply.sh` necesita LibreWolf **cerrado**. Si dice "no hay base de storage", abrí las opciones de Enhancer una vez. Si se reinstaló la extensión, el script encuentra el UUID nuevo solo. |
| Steam abre en otro workspace | El script lo devuelve en unos segundos (vigila hasta 2 min). Si no, revisá el log. |
| El mouse no responde bien / binds de mouse por dispositivo no aplican | Hyprland solo ve el mouse virtual del autoscroll: `systemctl --user stop autoscroll` para descartarlo. |
| Waybar no aparece | `waybar` en una terminal muestra el error; `SUPER+O` la reinicia. |
| `hyprctl dispatch ...` da error | Usá la sintaxis Lua (`hl.dsp.*`). |
| Steam tarda minutos en abrir | No pongas el CSS en quick.css de Millennium; el tema `matugen` lo inyecta por ventana. |
| `git push` → `Permission denied (publickey)` | La clave SSH tiene passphrase: corré el push desde tu terminal (o con `ssh-agent`). |

---

## 8. Desinstalar / revertir
### Deshacer una instalación (recomendado)
```bash
cd ~/Sync
./revert.sh -l          # lista backups
./revert.sh             # revierte el más reciente (pide confirmación)
./revert.sh 20261109-120000
```
Restaura cada archivo pisado, borra los que creó la instalación y vuelve a cargar el dconf anterior. Si había
symlinks (por ejemplo `~/.config/hypr -> ~/dotfiles/...`), imprime los comandos `rm` + `ln -s` para recrearlos;
correlos si querés volver a ese estado.

`revert.sh` **no** deshace:
- **El servicio de autoscroll:**
  `systemctl --user disable --now autoscroll.service && rm ~/.config/systemd/user/autoscroll.service`
- **La regla udev:** `sudo rm /etc/udev/rules.d/70-mouse-uaccess.rules && sudo udevadm control --reload`.
  Si había una versión anterior, está en `backups/<fecha>/files/system_etc_udev_rules.d_70-mouse-uaccess.rules`;
  reponela con `sudo install -Dm644 <ese archivo> /etc/udev/rules.d/70-mouse-uaccess.rules`. Como `revert.sh` copia
  todo `files/` a `~`, ese archivo también aparece como `~/system_etc_udev_...`: borralo.
- **Los paquetes** instalados con `-p`: desinstalalos a mano (`sudo pacman -Rns <paquete>`).
- **El tema de Enhancer for YouTube:** en las opciones de la extensión, Theme → desactivá "Custom theme" o elegí otro
  tema. La base original quedó en `<perfil>/storage/default/moz-extension+++<uuid>*/idb/*.sqlite.bak-matugen`; se puede
  reponer con LibreWolf cerrado.

### Quitar solo el tema dinámico
- **Que `SUPER+W` solo cambie el fondo:** en `~/.config/hypr/scripts/wppicker.sh`, reemplazá la línea `matugen image ...`
  por `awww img "$SELECTED_PATH"` y borrá la llamada a `theme-reload.sh`.
- **Que una app deje de recibir colores:** borrá su bloque `[templates.<app>]` en `~/.config/matugen/config.toml` (y su
  entrada en `theme-reload.sh` si se reinicia).
- **Volver al tema GTK por defecto:**
  `gsettings set org.gnome.desktop.interface gtk-theme adw-gtk3-dark` y borrá el `@import` de
  `~/.config/gtk-4.0/gtk.css`.
- **Cursor por defecto:** `gsettings set org.gnome.desktop.interface cursor-theme Adwaita`, y quitá
  `XCURSOR_THEME`/`HYPRCURSOR_THEME` de `hyprland.lua`.

### Borrar todo
1. `./revert.sh` con el backup de la **primera** instalación (deja la máquina como estaba antes de instalar este repo).
   Si hubo varias instalaciones, revertí de la más nueva a la más vieja.
2. Hacé los pasos manuales de "`revert.sh` no deshace".
3. Borrá el repo: `rm -rf ~/Sync`. Ojo: los backups están en `~/Sync/backups/`; borralos solo cuando ya no los necesites.
