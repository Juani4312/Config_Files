# REVIEW-REPORT — branch `review/ponytail`

> **BORRADOR (fase 3, antes de tocar código).** Los hallazgos marcados "plan" se aplican recién con tu OK.
> Base: `main` @ `facd049` (ya pusheado). Hyprland 0.57.2.

## 1. Resumen ejecutivo

El repo está sano: `bash -n` da 0 errores en 50 scripts y `shellcheck -S warning` da 10 avisos (8 son falsos
positivos de `lib.sh`). Los JSON son válidos, los `.lua` compilan y `Hyprland --verify-config` da `config ok`.
La simetría entre install y update es perfecta: no hay entradas de `lib.sh` sin archivo en el repo ni archivos huérfanos.
`install.sh -n` es read-only de verdad, verificado con un HOME falso.
No hay secretos en los archivos ni en el historial.

Lo más importante:
1. **Rutas `/home/juano` hardcodeadas** que install.sh no reescribe: los imports de GTK4, el bind `SUPER+B`,
   `librewolf.desktop` y ZapZap. Con otro usuario se rompen, y además dejan ver tu usuario en un repo público.
2. **`revert.sh` no desinstala del todo**: deja `autoscroll.service` habilitado (con el script ya borrado) y no recarga udev.
3. **`.gitconfig` con tu nombre y tu mail personal** en el repo público.
4. **Una PC nueva arranca sin waybar**: el `waybar/config` por defecto del repo trae `output: DP-3 / HDMI-A-1`.
5. **install.sh borra el historial de qalculate y del diálogo de archivos de Qt** en cada instalación (queda en el backup).

## 2. Mapa del sistema

```
install.sh [-n|-y|-p]
  lib.sh (arrays) ─► PAIRS repo→~ ─► review (+ diff de binds) ─► [-n: sale acá, no escribe nada]
  └► confirmación ─► backup(): backups/<fecha>/{files/, created.txt, manifest.txt (symlinks), dconf, review.txt}
     ─► -p: pacman + yay ─► monitors.lua si falta ─► aparta LOCAL_FILES ─► copia todo ─► repone LOCAL_FILES
     ─► dconf load ─► sed perfil LibreWolf en matugen/config.toml ─► sed /home/<x>/ (gtk3 + bookmarks)
     ─► nemo.desktop ─► current_wallpaper ─► SYSTEM_FILES con sudo (+ udev reload) ─► patch tidal-hifi
     ─► systemctl --user enable --now autoscroll ─► chmod +x
revert.sh [fecha] ─► restaura files/ ─► borra created.txt ─► dconf ─► sistema (sudo) ─► imprime cómo re-enlazar symlinks
update.sh [-n|-p] ─► copia ~→repo (dirs con delete, excluye *.bak* *cache* *token* ...) ─► dconf dump
  ─► limpia historial qalculate/Qt ─► LOCAL_FILES vuelven a HEAD ─► pacman -Qqen/-Qqem ─► git add -A ─► -p: commit+push

SUPER+W ─► wppicker.sh (rofi) ─► matugen image ─► templates (config.toml) + post_hooks:
  waybar(SIGUSR2) kitty(SIGUSR1) hypr colors.lua(hyprctl reload) cava(USR1) qalculate steam(build.sh)
  cursor(build.py --apply) ohmyposh(build.py)
  └► theme-reload.sh: GTK Matugen-a/b, btop(USR2), swaync -rs, wlogout tint, YouTube Enhancer,
     reinicia zapzap/qalculate; pregunta por tidal/librewolf/steam/prism (salvo que no se esté usando)
```

## 3. Hallazgos (del audit de la fase 1 + la review de la fase 2)

Severidad: C crítico · A alto · M medio · B bajo · N nit. Estado: **plan** = se aplica con tu OK,
**pend.** = queda propuesto, **duda** = ver §6.

| # | Sev | Dónde | Problema → escenario | Fix | Estado |
|---|-----|-------|----------------------|-----|--------|
| 1 | A | `install.sh:205-206` | El `sed` que cambia `/home/<x>/` por `$HOME` cubre solo GTK3 y los bookmarks. Con otro usuario fallan los `@import` de **GTK4** (`extra/gtk-themes/*/gtk-4.0/*.css`), `librewolf.desktop` (4 `Exec=`) y `ZapZap.conf` (download_path): las apps libadwaita quedan sin paleta y el lanzador de LibreWolf no abre. | Sumar esos archivos al mismo `sed`, que pasa a ser `s#/home/[^/]+/#$HOME/#g`. | plan |
| 2 | A | `keybinds.lua:29` | `SUPER+B` ejecuta `/home/juano/.local/bin/librewolf`: con otro usuario el bind no hace nada. | `os.getenv("HOME") .. "/.local/bin/librewolf"` | plan |
| 3 | A | `config/waybar/config` (LOCAL_FILES) | En una PC nueva, install.sh copia el `waybar/config` del repo, que solo define barras para `DP-3` y `HDMI-A-1`. En una laptop (`eDP-1`) **no aparece ninguna barra**. | Es un archivo por máquina (regla 6): no lo toco. Opción: que install.sh, si lo crea, saque las líneas `"output"`. | duda |
| 4 | M | `revert.sh` | No deshace `systemctl --user enable --now autoscroll`. Después del revert el unit queda habilitado, el `.service` y el script borrados, y el symlink en `default.target.wants` queda colgando (el servicio falla en cada login). | Si `created.txt` tiene el `.service`: `systemctl --user disable --now` antes de borrar. | plan |
| 5 | M | `revert.sh:129-132` | Al restaurar o borrar la regla udev no corre `udevadm control --reload && trigger` (install sí lo hace), así que los permisos viejos siguen hasta reiniciar. | Lo mismo que hace install.sh. | plan |
| 6 | M | `home/.gitconfig` | Tu nombre y tu mail personal en un repo público (pediste tratarlo como hallazgo). | Sacar `[user]` y agregar `[include] path = ~/.gitconfig.local`. install.sh crea ese archivo a partir de tu `~/.gitconfig` actual si falta, así tu identidad de git no cambia. | plan |
| 7 | M | `update.sh:39-44` ↔ `install.sh` | update saca el historial de `qalculate-gtk.cfg` y de `QtProject.conf`, así que install siempre los ve como "cambiados" y **pisa tu historial** (queda solo en el backup). Hoy `install.sh -n` en tu máquina da exactamente esos 2 cambios. | Opciones en §6. | duda |
| 8 | M | `home/.zshrc:71-76` | `alias grep='grep --color=always'` y los `eza --color=always`: en un pipe mandan códigos ANSI. `ls \| xargs rm`, `grep x \| grep y` o `> archivo` reciben basura y fallan sin error visible. | `--color=auto`: en la terminal se ve igual. | plan |
| 9 | M | `autoscroll.py` + udev | `/dev/uinput` es accesible solo por la regla `60-steam-input.rules` del paquete **steam**. Sin steam, `/dev/uinput` queda `root 0600`: `UInput()` falla, el servicio se reinicia cada 2 s hasta que systemd lo marca *failed*, y no hay autoscroll. | Agregar `KERNEL=="uinput", SUBSYSTEM=="misc", TAG+="uaccess"` a `70-mouse-uaccess.rules` (la misma línea que trae steam). | plan |
| 10 | B | `autoscroll.py:83` | `is_mouse` acepta un dispositivo que es teclado y mouse a la vez (combos con touchpad tipo K400): lo agarra en exclusiva, y como el uinput virtual no tiene teclas, **el teclado deja de andar**. Tus mouses actuales no tienen teclas (lo verifiqué). | `and e.KEY_A not in keys` | plan |
| 11 | B | `install.sh:60,143,170` | `"${dst/#$HOME/~}"`: bash expande el `~` del reemplazo, así que nunca acorta (la salida muestra `/home/juano/...`). | `\~` | plan |
| 12 | B | `install.sh:261` | `chmod +x ~/.config/hypr/UserScripts/*`: esa carpeta no existe en ningún lado. | Borrar ese glob. | plan |
| 13 | B | `matugen/templates/hyprland-colors.conf` | `$image = …` está dentro del `for`, así que sale 50 veces en `hypr/colors.conf`. | Moverlo afuera del loop (el resultado no cambia). | plan |
| 14 | B | `hyprlock.conf:89` | `curl -s 'wttr.in…'` sin timeout. | `curl -s -m 5` | plan |
| 15 | B | `packages/` | `imagemagick` (`magick` en `wlogout/tint-icons.sh`) es solo dependencia opcional: en una PC limpia los íconos de wlogout no se tiñen. Editar `pacman.txt` no sirve porque update.sh lo regenera con `pacman -Qqen`. | Correr `sudo pacman -D --asexplicit imagemagick` en tu máquina. | pend. |
| 16 | B | `packages/` | `dunst` y `swaync` están instalados y los dos registran activación D-Bus de `org.freedesktop.Notifications`. Si llega una notificación antes de que arranque swaync, dbus puede levantar dunst (a verificar). Otros a verificar: `hyprpaper` (se usa awww), `xdg-desktop-portal-wlr` junto a `-hyprland`, `librewolf-bin-debug`. | `pacman -Rns` lo que no uses. | duda |
| 17 | B | `config/tidal-hifi/userscripts/install/` | `patch-asar.py` y el `.hook` están duplicados (idénticos) con `extra/system/...`, y son dos copias que hay que cambiar juntas. install.sh usa la de `extra/system`. | Ver §6. | duda |
| 18 | B | `update.sh:72` | `git add -A` corre **siempre**, aunque no pases `-p`: deja staged todo lo que haya en el repo. | Moverlo adentro del `if -p` (`git status --short` alcanza para mostrar). | plan |
| 19 | N | `lib.sh` | 8× SC2034 (falsos positivos: lo sourcean otros scripts). `brightness.sh:6` y `music-ctl.sh:13` tienen variables sin usar. | `# shellcheck disable=SC2034` en lib.sh y borrar las 2 variables. | plan |
| 20 | N | `hyprland.lua:3` | El comentario apunta a `~/.config/hypr.bak-20261025-005229`, que ya no existe. | Borrar la línea. | plan |

Dejé afuera 4 nits que no cambian nada: el wrapper `bind()` de keybinds.lua que solo reenvía la llamada (tocarlo
ensucia el diff de binds de `install.sh -n`), `ZDG_DATA_HOME` (typo heredado, cae al default), `fastfetch` en cada
shell (es a propósito) y `kill $active_pid` sin comillas.

**Lo que está bien (verificado):** `-n` es read-only. Los backups cubren todo lo que se pisa, incluidos `extra/` y
los archivos de sistema. Los archivos que no existían van a `created.txt` y revert los borra. Los symlinks a
`~/dotfiles` se reemplazan sin escribir adentro. `backups/` y `monitors.lua` están en `.gitignore` y update.sh nunca
sube los LOCAL_FILES. theme-reload.sh usa `pkill -x` con nombres exactos (no mata nada de más). El clima tiene
timeout de 10 s, cache, marca "stale" y guarda la ubicación fuera del repo. No hay autostart duplicado con
systemd (hypridle, waybar y swaync no tienen unit habilitado). Los archivos generados por matugen que están
commiteados (colors.lua, etc.) **hacen falta**: sin `hypr/colors.lua` Hyprland no carga en el primer arranque.

## 4. Binds

Fuente: `config/hypr/configs/keybinds.lua`. Coincide 1:1 con la tabla del README. **No hay binds duplicados ni en
conflicto.** Todos los binarios que usan los binds están en `packages/` o son opcionales con fallback (`hyprshutdown`).

| Bind | Acción |
|------|--------|
| SUPER+T / SUPER+Return | kitty / kitty flotante 800×550 |
| SUPER+C | cerrar ventana |
| CTRL+ALT+Delete | hyprshutdown o salir |
| SUPER+E / SUPER+SHIFT+E | nemo / kitty yazi |
| SUPER+V / SUPER+SHIFT+V | cliphist en rofi / alternar flotante |
| SUPER+I | emoji-picker.sh |
| SUPER+Space | SwitchLayout.sh (us/latam) |
| SUPER+J | togglesplit |
| SUPER+R / SUPER+SHIFT+R | rofi drun / wbrestart.sh |
| SUPER+O | reload-all.sh |
| SUPER+K | pavucontrol |
| SUPER+M, XF86AudioMicMute | mic-mute.sh |
| SUPER+B / SUPER+N | LibreWolf (wrapper) / google-chrome-stable |
| SUPER+L | hyprlock |
| SUPER+F | fullscreen |
| SUPER+P | screenshot.sh |
| SUPER+W | wppicker.sh |
| SUPER+SHIFT+Q | KillActiveProcess.sh |
| SUPER+SHIFT+C | hyprpicker -a |
| SUPER+CTRL+B / SUPER+ALT+B | WaybarStyles.sh / WaybarLayout.sh |
| SUPER+H | ocultar waybar (SIGUSR1) |
| SUPER+←/→ · +SHIFT | workspace r∓1 · mover ventana |
| SUPER+↑/↓ | foco |
| SUPER+CTRL+flechas / SUPER+ALT+flechas | mover / redimensionar (repite) |
| SUPER+1..0 · +SHIFT | workspace 1..10 · mover ventana |
| SUPER+S / SUPER+SHIFT+S | especial "magic" / special-move.sh |
| SUPER+Z / SUPER+SHIFT+Z | especial "claude" / special-move.sh claude |
| SUPER+rueda | workspace e±1 |
| SUPER+clic izq/der | arrastrar / redimensionar |
| SUPER+clic medio | autoscroll (nc al socket) |
| XF86 volumen/brillo | volume.sh / brightness.sh (funcionan bloqueado, repiten) |
| XF86 Play/Pause/Next/Prev | playerctl (funcionan bloqueado) |

## 5. Cambios hechos

_(se completa después de tu OK)_

Plan de commits:
1. `fix(install)`: #1, #11, #12
2. `fix(revert)`: #4, #5
3. `fix(hypr)`: #2, #13, #14, #20
4. `fix(autoscroll)`: #9, #10
5. `fix(git)`: #6 (+ install.sh crea `~/.gitconfig.local`)
6. `fix(zsh)`: #8
7. `fix(update)`: #18
8. `chore`: #19 + backups viejos trackeados (§6.1) + `EXCLUDE_PATTERNS` con `*.orig *.pre-* *.save *(Copy)*`
   para que update.sh no los vuelva a subir + `config/rofi/power-menu.sh` en `.gitignore`
9. `docs`: README/instructions (`.gitconfig.local`, limpieza de backups)

## 6. Dudas (no borré ni cambié nada de esto)

### 6.1 Backups viejos (tu nota)
- **Trackeados en el repo** (propongo borrarlos en el commit `chore`, salvo que digas lo contrario):
  `config/hypr/old-conf/` (config hyprlang vieja: nada la carga y mete ruido en el diff de binds de `install.sh -n`),
  `config/matugen/templates/midnight-discord.css.pre-classfix`, `config/rofi/config (Copy).rasi`,
  `config/steam-theme/quick.css.orig`. **Ojo:** también existen en tu `~/.config`, y como update.sh copia las
  carpetas enteras, los volvería a subir. Por eso amplío `EXCLUDE_PATTERNS`; `old-conf/` lo tenés que borrar a mano
  de `~/.config/hypr`.
- **En tu home, fuera del repo:** 170 archivos `*.bak*`/`*.orig`/`*.pre-*` (1.7 MB), casi todos en
  `~/.config/{waybar,hypr,swaync,matugen}` y de sesiones anteriores de Claude. **No interfieren:** Hyprland no los
  carga y update.sh ya excluye `*.bak*`. No los borré porque están en tu `$HOME` real. Para verlos y borrarlos:
  `find ~/.config/{waybar,hypr,swaync,matugen,rofi,wlogout,kitty,steam-theme,tidal-hifi} \( -name '*.bak*' -o -name '*.pre-*' \) -print` (y después `-delete`).
  Los de `google-chrome`, `zen`, `ghidra` y `Code` los crean esas apps: no tocarlos.
- **`~/dotfiles` NO es un backup:** `nvim`, `ghostty`, `ohmyposh`, `colors`, `fontconfig`, `viegphunt`, `.zshrc`,
  `.tmux.conf` y `.tmux` son symlinks ahí y están en uso.
- **`backups/20261025-205927`** (180 KB): es lo único que tiene `revert.sh`. Dejalo.

### 6.2 Código posiblemente muerto
- `config/viegphunt/` (11 scripts): nada los referencia (ni binds, ni waybar, ni otros scripts).
- `config/hypr/scripts/AirplaneMode.sh`: sin bind ni módulo.
- Templates sin entrada en `matugen/config.toml`: `steam-adwaita.css`.
- `config/fastfetch/config1.jsonc`: ¿alternativa a mano (`fastfetch -c`) o sobra?
- `custom/weather` en `waybar/ModulesCustom` apunta a `hypr/UserScripts/Weather.py`, que no existe. Ningún layout
  lo usa (el tuyo es `custom/weather#ba`).
- `wbrestart.sh` (`SUPER+SHIFT+R`, `killall -9`) hace casi lo mismo que `reload-all.sh`. ¿Lo unifico?
- `config/tidal-hifi/userscripts/install/` (#17): ¿lo borro (install.sh ya hace todo) o lo dejo como instalador manual?

### 6.3 Decisiones
- #3 waybar en PC nueva: ¿que install.sh saque los `"output"` del default cuando lo crea?
- #7 historial de qalculate/Qt: (a) dejarlo así, (b) no instalarlos si ya existen (pasan a ser "locales"; perdés
  sincronizar sus opciones), (c) que install.sh conserve las líneas de historial al copiar.
- #16 paquetes duplicados o sin uso.

## 7. Qué no verifiqué

- No corrí `install.sh` (sin `-n`), `-p`, `update.sh` ni `revert.sh`. La instalación real llama a `dconf load`,
  `systemctl --user` y `sudo` **aunque uses un HOME falso**, así que no es segura de probar.
- No probé en una PC limpia. Lo recorrí leyendo el código: asume `yay` (si falta, avisa), y `monitors.lua` sale
  genérico si Hyprland no está corriendo.
- No chequeé con la red si los paquetes existen o cambiaron de nombre.
- Leí entero el ciclo de vida, Hyprland, theme-reload, wppicker, autoscroll, clima y los scripts chicos de hypr.
  **No leí línea por línea:** los popups Python de waybar (music/calendar/weather-popup, ~3000 líneas),
  `cursor/build.py`, `moz_ext_storage.py`, `steam-theme/generate.py`, CSS y templates grandes, nvim y tmux (TPM es vendor).
- README e instructions: revisé los flags, la tabla de binds y las rutas. No revisé cada frase.

## 8. Próximos pasos sugeridos

1. Decidir lo de §6.3 (sobre todo #3, que es lo que rompe una instalación nueva).
2. `sudo pacman -D --asexplicit imagemagick` y sacar `dunst` si no lo usás.
3. Borrar los `*.bak*` de tu `~/.config` (comando en §6.1).
4. Después de mergear: `./install.sh -n`, y recién ahí `./install.sh`.
