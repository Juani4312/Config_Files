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
4. **No pises los archivos propios de cada máquina** (`LOCAL_FILES` en `lib.sh`): `~/.config/hypr/monitors.lua` y
   `~/.config/waybar/config` y `~/.config/rofi/power-menu.sh` (este último solo existe en la laptop). `install.sh`
   los crea solo si faltan y `update.sh` no los sube al repo.
5. **Editá templates, no archivos generados.** Todo lo que genera matugen (ver la tabla de templates en el README) se
   pisa en cada cambio de fondo. La fuente está en `~/.config/matugen/templates/`.
6. **Reiniciar apps interrumpe al usuario:** LibreWolf corta videos, tidal-hifi corta la música y Steam cierra juegos.
   Preguntá antes de reiniciarlas. Recargar waybar/swaync/Hyprland es inofensivo.
7. **`hyprctl dispatch` usa sintaxis Lua:** `hyprctl dispatch 'hl.dsp.focus({ workspace = "3" })'`,
   `hyprctl dispatch 'hl.dsp.exec_cmd("kitty")'`. La forma clásica (`dispatch workspace 3`) falla.
8. **`~/.config/waybar/style.css` puede ser un hardlink** a `style/<variante>.css`. Editalo en el lugar (con Edit);
   nunca `sed -i` ni reemplazar el archivo, porque rompe el enlace.
   Desde **waybar 0.16** los módulos `custom/*` son `eventbox > box > label#custom-x` y el hover queda en el `box`
   sin nombre: `#custom-x:hover` no matchea nunca, hay que escribir `box:hover > #custom-x`. Un error de CSS al
   recargar (SIGUSR2) cierra waybar (ej. `/*` dentro de un comentario): validalo antes con `Gtk.CssProvider`.
   Usá solo los colores de matugen (`@primary`, `@secondary`, ... de `colors.css`) para que siga a `SUPER+W`.
9. **Sincronizar después de cambiar configs:** `./update.sh` copia la máquina al repo. El push por SSH puede necesitar
   la passphrase de la clave del usuario: si `git push` falla con `Permission denied (publickey)`, avisale que corra
   `git -C ~/Laptop/Sync push` en su terminal.
10. **Logs útiles:** `$XDG_RUNTIME_DIR/theme-reload.log` (cambio de tema), `journalctl --user -u autoscroll`
    (autoscroll), `hyprctl configerrors` (config de Hyprland).
11. **tidal-hifi:** los `~/.config/tidal-hifi/userscripts/*.js` se recargan con `Ctrl+U` (sin reiniciar). Para
    inspeccionar el DOM, relanzalo con `--remote-debugging-port=9222 --remote-debugging-address=127.0.0.1` y usá CDP
    (`Runtime.evaluate`, `Input.dispatchKeyEvent` para probar teclas); el puerto 47836 es la API de tidal-hifi, no
    DevTools. Al terminar, relanzalo sin el puerto. Las ventanas relanzadas abren en el workspace actual (va en el 7).
12. **Autoscroll y modificadores:** el daemon no lee el teclado. `Super` + clic medio lo resuelve un bind
    `SUPER + mouse:274` de Hyprland, que avisa "mid" por `$XDG_RUNTIME_DIR/autoscroll-ctl.sock`. No vuelvas a
    seguir el estado de una tecla con binds de press/release (`Super_L` con `release = true`): Hyprland los
    *sombrea* después de cualquier combo `SUPER+tecla`, el release no llega y el daemon cree que la tecla sigue
    apretada. Para probarlo sin tocar nada, usá un teclado y un mouse virtuales (uinput) en un workspace vacío:
    un clic medio sobre kitty pega el portapapeles.

13. **Colores en waybar/popups:** `@error` de Material es siempre rosado/salmón sin importar el fondo (el usuario lo
    ve como "otro tema"): usalo solo para alertas críticas; estados "apagado" van en `@outline`. Para un tono más
    claro usá los `*_fixed` (ej. `@secondary_fixed`), nunca `white`/hex.
14. **Hyprland 0.57+:** los workspaces especiales no traen `"id"` en `hyprctl -j workspaces` ni en el `.workspace` de
    los clientes (usá `.get("id")`). `decoration.blur.special = true` dibuja el fondo difuminado ENCIMA de la waybar
    (layer `bottom`) con el especial abierto: dejalo en `false`. La API Lua (eventos, `hl.get_monitors()`, ...) está
    en `/usr/share/hypr/stubs/hl.meta.lua`.
15. **GTK3 en waybar:** las clases de un `custom/*` quedan en el label interno, así que `.clase ~ #grupo` no funciona;
    `:nth-child` cuenta solo hermanos *visibles* (un custom con texto vacío se oculta), eso se usa para el estado del
    especial. Un ícono simbólico (`-gtk-icontheme`) se multiplica por el alfa de `color`: no se puede ocultar el
    glifo con `color: transparent` y seguir viendo el ícono.

---

## 1. Requisitos previos
- Arch Linux (o derivada) con un usuario normal con `sudo` (install.sh no corre como root).
- `git` para clonar (`sudo pacman -S --needed git`). Todo lo demás (base-devel, `yay`, Hyprland, apps, fuentes,
  servicios) lo instala `./install.sh -p` (paso 2.4), aunque arranques desde una TTY sin entorno gráfico.

## 2. Instalación
### 2.1 Clonar
```bash
git clone https://github.com/Juani4312/Config_Files.git ~/Sync
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
2. Si falta `~/.config/hypr/monitors.lua`, lo genera con los monitores y el scale actuales (`hyprctl monitors`;
   desde una TTY sale uno genérico). Los `LOCAL_FILES` que ya existen (`monitors.lua`, `waybar/config`,
   `rofi/power-menu.sh`) no se tocan. En una PC nueva, `waybar/config` es una barra genérica (sin monitor fijo);
   el layout del desktop (una barra por monitor) es `configs/bintang default` y se elige con `SUPER+ALT+B`.
   Si falta `~/.gitconfig.local`, lo crea con el `user.name`/`user.email` del `~/.gitconfig` actual: el
   `.gitconfig` del repo no trae identidad (repo público) y la incluye desde ahí.
3. Copia `config/` → `~/.config`, `home/` → `~`, `extra/` → sus rutas (`~/.local/share/...`, `~/.vscode/...`,
   perfil de LibreWolf). Conserva el historial de qalculate y del diálogo de archivos de Qt (el repo no lo tiene).
4. Carga `extra/dconf-interface.ini` (tema GTK, íconos, cursor, fuentes).
5. Apunta las rutas de LibreWolf de `~/.config/matugen/config.toml` al perfil activo de esta máquina, y reescribe
   `/home/<usuario>/` a esta `$HOME` (tema GTK 3/4, marcadores, `librewolf.desktop`, ZapZap).
   Elige el tema de matugen en los archivos que no se sincronizan porque tienen tokens o son del perfil:
   `user.js` de LibreWolf (pref de `userChrome.css`), `theme` de tidal-hifi y `ApplicationTheme` de PrismLauncher.
6. Crea `~/.config/hypr/current_wallpaper` **solo si falta** (por defecto, `Pictures/Wallpapers/Set/pacman-ghosts.png`):
   si ya existe, respeta el fondo que eligió esta máquina.
7. Instala con `sudo` (pregunta) los archivos de sistema que cambiaron: `/etc/udev/rules.d/70-mouse-uaccess.rules`
   (mouse + `/dev/uinput` para el autoscroll), `/usr/local/lib/tidal-hifi-userscripts/patch-asar.py`,
   `/etc/pacman.d/hooks/tidal-hifi-userscripts.hook` y `/etc/sddm.conf` (tema del login). Las
   versiones anteriores quedan en `backups/<fecha>/system/<ruta>` (y los que no existían, en `system-created.txt`). Si
   tidal-hifi está instalado y su `app.asar` no tiene el cargador, pregunta y lo parchea (navegación con flechas).
8. Habilita `autoscroll.service` (systemd de usuario; si no estaba habilitado lo anota en `enabled.txt` para que
   `revert.sh` lo deshabilite) y da permisos de ejecución a los scripts.

### 2.4 Paquetes
```bash
./install.sh -p     # instalación + paquetes + servicios
```
Antes de copiar las configs:
1. `sudo pacman -Syu --needed git base-devel` e instala `yay` (desde `yay-bin` de AUR) si falta.
2. `yay -S --needed` de **`packages/deps.txt`**: los ~90 paquetes que usan las configs y scripts del repo
   (Hyprland, waybar, apps con tema, fuentes, dependencias de los scripts). La lista es **a mano**: si agregás algo
   que usa un programa nuevo, sumalo ahí. `update.sh` no la toca.
3. Pregunta si instalar también **todo** `packages/pacman.txt` + `aur.txt`. Es el volcado completo de la PC de
   origen (`pacman -Qqe`, lo regenera `update.sh`) e incluye kernel, microcódigo, drivers y apps personales:
   en otra PC normalmente respondé que no. Con `-y` no lo instala. Si un paquete ya no existe, se saltea y se avisa.
4. Habilita `NetworkManager`, `bluetooth` y `sddm` (este último solo si no hay otro display manager). Si tu
   instalación usa `iwd`/`systemd-networkd` en vez de NetworkManager, revisá que no choquen.

**LibreWolf:** el paquete es `librewolf` del repo oficial (`librewolf-bin` ya no existe en AUR). Si tenés
`librewolf-bin`, migrá antes de `-p` (mismas rutas, el perfil no cambia):
`sudo pacman -Rdd librewolf-bin librewolf-bin-debug && sudo pacman -S librewolf`.

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
| **LibreWolf** | Abrilo y cerralo una vez para que exista el perfil, y corré `./install.sh` de nuevo: recién ahí copia `chrome/*.css`, escribe el `user.js` con `toolkit.legacyUserProfileCustomizations.stylesheets` y apunta matugen al perfil. |
| **Enhancer for YouTube** | Instalalo desde addons.mozilla.org en LibreWolf y abrí sus opciones una vez (eso crea su base de storage). El script activa solo el tema "DeepDark custom" y el CSS custom. El tema de matugen se escribe solo al reiniciar LibreWolf o la próxima vez que lo abras con `SUPER+B` / el lanzador (wrapper `~/.local/bin/librewolf`); para forzarlo a mano: cerrá LibreWolf y corré `~/.config/matugen/scripts/youtube-enhancer-apply.sh`. |
| **Steam (Millennium)** | `millennium` (AUR) instalado; abrí Steam una vez. El tema `matugen` ya queda activo por `~/.config/millennium/config.json`. Si falta CSS: `~/.config/steam-theme/build.sh --regen`. |
| **VS Code** | La extensión `local.matugen-theme` se copia sola; si no aparece el tema, elegí "Matugen" en *Preferences: Color Theme*. |
| **tidal-hifi** | `install.sh` elige `matugen.css` (si tidal-hifi ya estaba instalado). Para las flechas: si tidal-hifi se instaló *después* de `install.sh`, corré `install.sh` de nuevo (o `sudo python3 /usr/local/lib/tidal-hifi-userscripts/patch-asar.py`) y reiniciá tidal-hifi. |
| **Vesktop** | Viene en `deps.txt`; el tema `matugen.css` ya queda activo por `~/.config/vesktop/settings/settings.json`. |
| **PrismLauncher** | `install.sh` elige el tema `matugen` (si Prism ya estaba instalado; si no, corré `install.sh` de nuevo). |
| **Autoscroll** | La regla udev se aplica al reconectar el mouse o reiniciar. Comprobá con `systemctl --user status autoscroll`. |
| **Shell** | `chsh -s /usr/bin/zsh`; zinit y los plugins se instalan solos en el primer zsh. tmux: `prefix + I` instala los plugins de tpm. |
| **Git / SSH** | `~/.ssh` no viaja: generá una clave, agregala a GitHub y configurá el host que use el remoto. Tu nombre y mail van en `~/.gitconfig.local` (`git config -f ~/.gitconfig.local user.email tu@mail`), no en el `.gitconfig` del repo. |
| **Primer fondo** | `SUPER+W` y elegí un fondo: el repo trae colores pre-generados, pero recién ahí matugen genera todo para esta PC (cursor, Steam, YouTube, etc.). |

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
  se actualiza la próxima vez que abras LibreWolf (el wrapper `~/.local/bin/librewolf` aplica el tema pendiente).
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
- `HISTORY_KEYS`: claves de historial que `update.sh` borra antes de subir y `install.sh` conserva.

Si lo nuevo usa un programa que no está en `packages/deps.txt`, sumalo ahí.

Nunca se copian `*.key`, `*.pem`, `*token*`, `*secret*`, `.env`, `*cache*`, `*.log`, `*.bak*`, `*.orig`, `*.save`,
`*(Copy)*`, `*.pre-classfix` ni carpetas `old-conf` (backups viejos). Las configs de apps que guardan tokens
(tidal-hifi, PrismLauncher, perfil de LibreWolf) no se sincronizan: `install.sh` solo elige su tema.

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
| El autoscroll arranca con clic medio sin `Super` | Config vieja que seguía `Super_L` con binds de release (Hyprland los sombrea). Actualizá `keybinds.lua` y `autoscroll.py` desde el repo y `systemctl --user restart autoscroll`. `journalctl --user -u autoscroll` muestra cada `start`/`stop`. |
| Nemo: `Supr` no manda nada a la papelera | Nemo se abrió desde el portal (ej. "abrir carpeta" de otra app) y heredó `GIO_USE_VFS=local`. `~/.local/share/applications/nemo.desktop` lo evita (`Exec=env -u GIO_USE_VFS nemo`); `install.sh` lo rehace desde el `.desktop` del sistema. Para salir del paso: `nemo --quit` y abrirlo de nuevo. |
| Waybar no aparece | `waybar` en una terminal muestra el error; `SUPER+O` la reinicia. |
| Waybar: no aparece el ícono de música | Solo se ve con tidal-hifi o DeaDBeeF abiertos (DeaDBeeF necesita su plugin MPRIS, viene con el paquete). `playerctl -l` debe listar `tidal-hifi` / `DeaDBeeF`. En la laptop, `"custom/music"` tiene que estar en `modules-right` de `~/.config/waybar/config` (es local). Para ver errores: `~/.config/waybar/scripts/music.py` en una terminal. |
| Waybar: no aparece la temperatura | `"custom/weather#ba"` tiene que estar en `modules-left` de `~/.config/waybar/config` (es local). `~/.config/waybar/scripts/weather.py` en una terminal muestra el JSON o el error; sin red usa `~/.cache/waybar-weather.json`. |
| Waybar: el click en la temperatura no abre el pronóstico | `~/.config/waybar/scripts/weather-popup.py` en una terminal: si no hay `gtk-layer-shell` cae a la página HTML (lo avisa en stderr). Para probarlo sin que tome el teclado: `WEATHER_POPUP_TEST=3 …/weather-popup.py`. |
| Waybar: el clima muestra otra ciudad / volver a Buenos Aires | Click derecho en la temperatura para buscar otra. Para volver al valor por defecto: `rm ~/.local/state/waybar-weather/location.json` (también borra las recientes) y click en la temperatura → `R`. El buscador se prueba sin tomar el teclado con `WEATHER_POPUP_TEST=3 WEATHER_SEARCH_QUERY=cordoba …/weather-search.py`. |
| `hyprctl dispatch ...` da error | Usá la sintaxis Lua (`hl.dsp.*`). |
| Steam tarda minutos en abrir | No pongas el CSS en quick.css de Millennium; el tema `matugen` lo inyecta por ventana. |
| tidal-hifi: las flechas no hacen nada | `grep -c tidal-hifi-userscripts-loader /opt/tidal-hifi/resources/app.asar` debe dar ≥1; si da 0, corré el patcher con sudo y reiniciá tidal-hifi. El hook solo actúa en actualizaciones por pacman. |
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

Los archivos del sistema (regla udev, patcher y hook de tidal-hifi) también se revierten: `revert.sh` pregunta y,
con `sudo`, repone la versión anterior desde `backups/<fecha>/system/` o borra los que la instalación creó.

También deshabilita `autoscroll.service` si la instalación lo habilitó (`enabled.txt`), recarga udev si tocó la
regla y borra `~/.gitconfig.local` / los archivos de tema que creó.

`revert.sh` **no** deshace:
- **Los servicios del sistema** que habilitó `-p` (`NetworkManager`, `bluetooth`, `sddm`): `sudo systemctl disable <servicio>`.
- **El `app.asar` parcheado de tidal-hifi:** reinstalá el paquete para recuperar el original (`yay -S tidal-hifi-bin`).
  Para desactivar solo las flechas: borrá `~/.config/tidal-hifi/userscripts/arrow-nav.js`.
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
