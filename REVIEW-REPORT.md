# REVIEW-REPORT — branch `review/ponytail`

Base: `main` @ `facd049`. 19 commits, 44 archivos (+657 / −1021). Hyprland 0.57.2. Nada pusheado ni mergeado.
Bitácora para retomar: [`REVIEW-PROGRESS.md`](REVIEW-PROGRESS.md).

## 1. Resumen ejecutivo

El repo ya estaba sano y ahora también se puede instalar desde cero en un Arch limpio.
- **Validaciones:** `bash -n` da 0 errores en 50 scripts y `shellcheck -S warning` pasa de 10 a **0** warnings.
  Python compila, Lua compila, los JSON son válidos y `Hyprland --verify-config` da `config ok`.
  Los dos configs de waybar tienen todos sus módulos definidos.
- **Test nuevo:** `tests/install-e2e.sh` prueba install ×2 + revert en un HOME falso, sin red ni sudo, y pasa.
- **Secretos:** no hay ninguno, ni en los archivos ni en el historial de git.

Lo más importante que se arregló:
1. **Una PC nueva no tenía barra:** el `waybar/config` por defecto solo definía `DP-3`/`HDMI-A-1`. Ahora es genérico.
2. **No había forma de instalar "todo" en otra PC:** faltaban dependencias reales, `yay`, servicios y la selección
   de temas. Ahora está `packages/deps.txt` (90 paquetes verificados) y `install.sh -p` hace el resto.
3. **install.sh borraba datos:** el historial de qalculate y Qt, y archivos con rutas de home se pisaban sin backup.
   Además rompía el hardlink de `waybar/style.css`.
4. **revert.sh no desinstalaba del todo:** quedaba `autoscroll.service` habilitado y no recargaba udev.
5. **Datos personales en el repo público:** el mail en `.gitconfig` y `/home/juano` en binds y lanzadores.

**Para vos, con sudo:** `librewolf-bin` ya no existe en AUR, así que tu LibreWolf está congelado en la 152.
Migrá al paquete oficial (ver §8).

## 2. Mapa del sistema

```
install.sh [-n|-y|-p]   (no corre como root)
  lib.sh (arrays) ─► PAIRS repo→~ ─► review: nuevo/cambiado/igual + diff de binds ─► [-n: termina acá, no escribe]
  └► confirmación ─► backup(): backups/<fecha>/{files/, created.txt, manifest.txt, enabled.txt, history/, system/, dconf}
     ─► -p: pacman -Syu git base-devel ─► yay-bin si falta ─► yay deps.txt ─► [pregunta] pacman.txt + aur.txt
           ─► enable NetworkManager, bluetooth, sddm
     ─► monitors.lua si falta ─► aparta LOCAL_FILES ─► ~/.gitconfig.local si falta ─► aparta historial (HISTORY_KEYS)
     ─► copia todo (tar -h) ─► style.css → symlink a su variante ─► repone LOCAL_FILES ─► dconf load
     ─► matugen → perfil de LibreWolf ─► sed /home/<x>/ en HOMEPATH_FILES ─► repone historial ─► nemo.desktop
     ─► temas en archivos no sincronizados (user.js de LibreWolf, tidal-hifi, PrismLauncher)
     ─► current_wallpaper ─► SYSTEM_FILES con sudo (+ udev reload) ─► patch tidal-hifi ─► autoscroll.service ─► chmod
revert.sh [fecha] ─► restaura files/ ─► disable enabled.txt ─► borra created.txt ─► dconf ─► sistema (sudo + udev reload)
update.sh [-n|-p] ─► ~→repo (dirs con delete, EXCLUDE_PATTERNS) ─► dconf dump ─► borra HISTORY_KEYS ─► saca [user] de .gitconfig
  ─► LOCAL_FILES vuelven a HEAD ─► pacman -Qqen/-Qqem ─► -p: git add -A + commit + push

SUPER+W ─► wppicker.sh (rofi) ─► matugen image ─► templates (config.toml) + post_hooks
  └► theme-reload.sh: GTK a/b, btop, swaync, wlogout, YouTube Enhancer, reinicia zapzap/qalculate, pregunta tidal/librewolf/steam/prism
```

## 3. Hallazgos

Severidad: A alto · M medio · B bajo · N nit. ✅ = arreglado (commit) · ⏳ = queda para vos · ❓ = duda (§6).

| # | Sev | Dónde | Problema | Estado |
|---|-----|-------|----------|--------|
| 1 | A | `config/waybar/config` | En una PC nueva no aparecía ninguna barra: el default solo tenía `DP-3`/`HDMI-A-1`. Ahora es una barra genérica con módulos `#any` + `group/ws-all`. El layout del desktop sigue en `configs/bintang default` (`SUPER+ALT+B`). | ✅ 999debe |
| 2 | A | `packages/` + `install.sh -p` | No se podía instalar todo en otra PC: varias dependencias reales (jq, playerctl, gtk4-layer-shell, python-cairo, imagemagick, ripgrep…) solo estaban como dependencias de otros paquetes. `yay` no se instalaba. `pacman -S - < pacman.txt` y `yay - < aur.txt` abortan **todo** si falta un paquete (hoy faltan `librewolf-bin`, `librewolf-bin-debug` y `spotiflac-bin`). No se habilitaban servicios. | ✅ fd6c17d |
| 3 | A | LibreWolf | `librewolf-bin` ya no está en AUR. Tu 152 no se actualiza más y la oficial `extra/librewolf` va por la 160, con las mismas rutas. | ✅ deps.txt / ⏳ migración en tu máquina |
| 4 | A | `install.sh` `sed` | `/home/juano` en los imports de GTK4, `librewolf.desktop` y ZapZap no se reescribía: con otro usuario se rompían. | ✅ 4708d9a, c6837c0 |
| 5 | A | `keybinds.lua:29` | `SUPER+B` tenía `/home/juano/…` hardcodeado. Ahora es `~/.local/bin/librewolf`. | ✅ f48a156 |
| 6 | M | `install.sh` | Borraba el historial de qalculate y del diálogo de Qt en cada instalación. Ahora lo aparta y lo repone, con `HISTORY_KEYS` compartido con update.sh. Probado ida y vuelta con tus archivos reales. | ✅ 8cf516e |
| 7 | M | `install.sh` | `tar -h` convertía `waybar/style.css` (hardlink en tu máquina) en una copia suelta: editar la variante dejaba de cambiar la barra. Ahora queda como symlink. | ✅ 2863289 |
| 8 | M | `install.sh` `state()` | Con otro usuario, los archivos con rutas de home se respaldaban y recopiaban en cada corrida. Después, el review encontró que `colors.conf`/`QtProject.conf` se pisaban sin backup. Se resolvió con una lista única `HOMEPATH_FILES`. | ✅ e85947f, c6837c0 |
| 9 | M | `revert.sh` | No deshabilitaba `autoscroll.service` y quedaba un symlink colgando en `default.target.wants`. Ahora install anota lo que habilita en `enabled.txt`. | ✅ c324d8f |
| 10 | M | `revert.sh` | No recargaba udev al revertir la regla. Ahora sí, y avisa que tidal-hifi sigue parcheado. | ✅ c324d8f |
| 11 | M | `home/.gitconfig` | Tu nombre y mail personal en el repo público. Pasaron a `~/.gitconfig.local`: install lo crea con tu identidad actual y el include va antes del `includeIf` de ITBA (probado). update.sh saca `[user]` si vuelve a aparecer. | ✅ afb103e |
| 12 | M | `hyprlock.conf` | Los labels "Degrees"/"USER" estaban comentados a medias y dejaban 2 `}` sueltas. Además el typo `dots_rouding`. | ✅ f48a156 |
| 13 | M | `.zshrc` | `--color=always` en `ls`/`grep` mandaba códigos ANSI a pipes y archivos: `ls \| xargs rm` fallaba. | ✅ c975d35 |
| 14 | M | autoscroll | `/dev/uinput` solo era accesible por la regla del paquete **steam**: sin steam, no había autoscroll. Ahora tiene regla propia. | ✅ 589224b |
| 15 | M | LibreWolf / tidal / Prism | En una PC nueva el tema no cargaba. Faltaba la pref de `userChrome.css`, que tenías puesta a mano en `about:config`, y el tema elegido en tidal y Prism. Esas configs tienen tokens (ListenBrainz, Modrinth), así que no se sincronizan: install escribe solo esa clave, con backup. | ✅ fd6c17d |
| 16 | M | login | `/etc/sddm.conf` (tema `sddm-astronaut-theme`) no estaba en el repo. Ahora está en `SYSTEM_FILES`. | ✅ fd6c17d |
| 17 | B | `update.sh:72` | `git add -A` corría aunque no pasaras `-p`. | ✅ 397ea43 |
| 18 | B | `autoscroll.py:83` | Un combo teclado+touchpad se agarraba en exclusiva y el teclado dejaba de andar. Verifiqué que tus 3 mouses siguen detectados. | ✅ 589224b |
| 19 | B | `ws-listener.py` | Con varias barras, los listeners se pisaban el `.tmp` del estado. | ✅ c6837c0 |
| 20 | B | `install.sh` | Los mensajes nunca acortaban la ruta a `~` (bash expande el `~` del reemplazo). Había un glob a `UserScripts/` que no existe. | ✅ 4708d9a |
| 21 | B | `hyprland-colors.conf` | `$image` dentro del `for`: salía 50 veces. Mismos colores, probado con una config aislada de matugen. | ✅ f48a156 |
| 22 | B | repo | Backups viejos trackeados (`hypr/old-conf/`, `*.pre-classfix`, `(Copy).rasi`, `quick.css.orig`). Además ahora `EXCLUDE_PATTERNS` los ignora, porque siguen en tu `~/.config` y update.sh los volvía a subir. | ✅ b39ebd6 |
| 23 | N | varios | 8 SC2034 en lib.sh (falsos positivos), variables sin usar en brightness/music-ctl, comentario a un backup que no existe. | ✅ b39ebd6, f48a156 |
| 24 | B | `config/autostart/bitwarden.desktop` | No hace nada: la sesión arranca con SDDM → `start-hyprland` (sin uwsm) y nadie procesa el autostart XDG. Bitwarden no está corriendo. | ❓ |
| 25 | B | packages | `dunst` y `swaync` instalados, los dos con activación D-Bus de notificaciones. `hyprpaper` sin uso (se usa awww). `xdg-desktop-portal-wlr` junto al de Hyprland. | ❓ |
| 26 | B | `music-popup.py` | La cache de carátulas (`~/.cache/…`) crece sin límite (un archivo por tema). | ⏳ |
| 27 | B | `rofi/wifi-menu.sh` | La clave wifi viaja por la línea de comandos de `nmcli`: otro usuario local la ve un instante en `/proc`. | ⏳ |

**Quedan 9 notas de shellcheck nivel *info*, todas justificadas:**
- SC2016 en `special-move.sh`: son expresiones de jq a propósito.
- SC2012 (`ls`): nombres controlados.
- SC2086, SC2181 y SC2295: casos inofensivos en scripts chicos o en `viegphunt/`, que no se usa.

**Shortcut documentado:** `install.sh:267`. Con una HOME más profunda que `/home/<usuario>`, repetir el `sed` anida la ruta.

## 4. Binds

Fuente: `config/hypr/configs/keybinds.lua`. Coincide 1:1 con la tabla del README. **No hay duplicados ni conflictos.**
El único cambio de la branch es `SUPER+B`: misma acción, ruta con `~`.

| Bind | Acción |
|------|--------|
| SUPER+T / SUPER+Return | kitty / kitty flotante 800×550 |
| SUPER+C · CTRL+ALT+Delete | cerrar ventana · hyprshutdown o salir |
| SUPER+E / SUPER+SHIFT+E | nemo / kitty yazi |
| SUPER+V / SUPER+SHIFT+V | cliphist en rofi / alternar flotante |
| SUPER+I · SUPER+Space · SUPER+J | emojis · us/latam · togglesplit |
| SUPER+R / SUPER+SHIFT+R · SUPER+O | rofi / wbrestart.sh · reload-all.sh |
| SUPER+K · SUPER+M (y XF86AudioMicMute) | pavucontrol · mic-mute.sh |
| SUPER+B / SUPER+N | LibreWolf (wrapper) / google-chrome-stable |
| SUPER+L · SUPER+F · SUPER+P · SUPER+W | hyprlock · fullscreen · screenshot · wppicker |
| SUPER+SHIFT+Q · SUPER+SHIFT+C | matar proceso activo · hyprpicker |
| SUPER+CTRL+B / SUPER+ALT+B · SUPER+H | estilos / layouts de waybar · ocultar waybar |
| SUPER+←/→ (+SHIFT) · SUPER+↑/↓ | workspace r∓1 (mover ventana) · foco |
| SUPER+CTRL/ALT+flechas | mover / redimensionar |
| SUPER+1..0 (+SHIFT) | workspace 1..10 (mover ventana) |
| SUPER+S / +SHIFT · SUPER+Z / +SHIFT | especial "magic" / "claude" (mostrar / mandar o devolver) |
| SUPER+rueda · SUPER+clic izq/der · SUPER+clic medio | workspaces e±1 · arrastrar/redimensionar · autoscroll |
| XF86 volumen/brillo/multimedia | volume.sh / brightness.sh / playerctl (funcionan bloqueado) |

## 5. Cambios, por commit

| Commit | Qué |
|--------|-----|
| 4708d9a | fix(install): `/home/<usuario>` en GTK4/LibreWolf/ZapZap, `~` en mensajes, sin glob de UserScripts |
| c324d8f | fix(revert): deshabilita los servicios que habilitó install, recarga udev, avisa del patch de tidal |
| f48a156 | fix(hypr): SUPER+B, hyprlock (llaves sueltas, typo), `$image` una vez |
| 589224b | fix(autoscroll): regla udev de uinput, sin combos teclado+mouse |
| afb103e | fix(git): identidad → `~/.gitconfig.local` |
| c975d35 | fix(zsh): `--color=auto` |
| 397ea43 | fix(update): `git add -A` solo con `-p` |
| b39ebd6 | chore: backups viejos fuera + EXCLUDE_PATTERNS + shellcheck limpio + `.gitignore` power-menu |
| 999debe | fix(waybar): config genérico para PC nueva |
| fd6c17d | feat(install): deps.txt, yay, servicios, temas de apps, sddm.conf, no root |
| 8cf516e | fix(install): conservar el historial de qalculate/Qt |
| e85947f | fix(install): rutas de home no cuentan como cambio |
| 2863289 | fix(install): style.css como symlink |
| c6837c0 | fix: hallazgos de /ponytail-review + `tests/install-e2e.sh` |
| 64e9030, d6ca6c4 | docs: README + instructions |
| 3b03d84, d6459cc, 7ef00dd | bitácora/reporte |

## 6. Dudas (no borré ni cambié nada de esto)

- **`config/viegphunt/`** (11 scripts): nada los referencia. Sus dependencias están instaladas. ¿Los borro?
- **`hypr/scripts/AirplaneMode.sh`:** sin bind ni módulo.
- **`matugen/templates/steam-adwaita.css`:** sin entrada en `config.toml`.
- **`fastfetch/config1.jsonc`:** ¿alternativa a mano o sobra?
- **`custom/weather` en `waybar/ModulesCustom`:** apunta a `hypr/UserScripts/Weather.py`, que no existe. Ningún
  layout tuyo lo usa; los layouts JaKooLit de `configs/` quizás sí.
- **`wbrestart.sh` (`SUPER+SHIFT+R`, `killall -9`):** hace casi lo mismo que `reload-all.sh`. ¿Lo unifico?
- **`config/tidal-hifi/userscripts/install/`:** el patcher y el hook están duplicados, idénticos, con
  `extra/system/`. install.sh usa los de `extra/system/`. ¿Borro esta copia?
- **`autostart/bitwarden.desktop` (#24):** ¿agrego `hl.exec_cmd("/opt/Bitwarden/bitwarden-app --autostart")` al
  autostart de Hyprland, o lo borro?
- **`starship.toml`:** no lo usa nada (el prompt es oh-my-posh) y starship no está instalado.
- **`spicetify/`:** hay tema de matugen para Spotify, pero `spicetify-cli` no está instalado, así que no se aplica.
- **`ghostty/`:** está configurado pero no instalado. Lo dejé fuera de `deps.txt`.
- **Paquetes (#25):** `dunst`, `hyprpaper`, `xdg-desktop-portal-wlr`. ¿Los sacás con `sudo pacman -Rns`?
- **En tu `~/.config` hay 170 `*.bak*` (1.7 MB)** de sesiones anteriores de Claude. No interfieren: update.sh los
  excluye y Hyprland no los carga. Para verlos:
  `find ~/.config/{waybar,hypr,swaync,matugen,rofi,wlogout,kitty,steam-theme,tidal-hifi} \( -name '*.bak*' -o -name '*.pre-*' \) -print`
  (y después `-delete`). Los de `google-chrome`, `zen`, `ghidra` y `Code` los crean esas apps.
  `~/.config/hypr/old-conf/` también se puede borrar.
- **`~/dotfiles` NO es un backup:** varias carpetas de `~/.config` y `.zshrc`/`.tmux` son symlinks ahí. La primera
  instalación los convierte en copias reales y revert te dice cómo re-enlazarlos.

## 7. Qué no verifiqué y riesgos

- **Instalación real de paquetes:** no corrí `-p` (necesita sudo). Verifiqué los 90 nombres de `deps.txt` contra los
  repos oficiales (base local de pacman) y contra la API de AUR. Lo que hace `yay` (prompts, builds) no está probado.
  Se puede probar en un contenedor `archlinux` con docker (§8).
- **install.sh real sobre tu HOME:** no lo corrí. Lo probé de punta a punta en un HOME falso con stubs de `sudo`,
  `systemctl`, `dconf` y `hyprctl` (`tests/install-e2e.sh`). `install.sh -n` contra tu HOME da: 0 nuevos,
  16 cambiados (los de esta branch más el historial), y solo cambia el bind `SUPER+B`.
- **hyprlock:** no tiene modo de validar sin bloquear la pantalla. Verifiqué el balance de llaves y la sintaxis a ojo.
- **waybar:** no la levanté; hubiera aparecido una barra extra en tu pantalla. Validé el JSONC con los includes y
  el CSS con `Gtk.CssProvider`.
- **No leí línea por línea:** el arte SVG de `cursor/build.py`, el CSS minificado de steam/tidal/vesktop, ni nvim
  más allá de bootstrap y dependencias. Los popups grandes de waybar los leí por estructura y por todo lo que tocan
  afuera (procesos, red, archivos, escapes).
- **Riesgo en tu máquina:** `install.sh -p` va a fallar al instalar `deps.txt` mientras tengas `librewolf-bin`
  (choca con `librewolf`). Migrá primero (§8).
- **NetworkManager:** si una PC nueva usa `iwd`/`systemd-networkd`, habilitar NetworkManager puede chocar. Está
  avisado en instructions.md.

## 8. Próximos pasos

1. **Revisar y mergear:** `git log main..review/ponytail` · `git diff main...review/ponytail`. No corras
   `update.sh` antes de mergear.
2. **Migrar LibreWolf (sudo):** `sudo pacman -Rdd librewolf-bin librewolf-bin-debug && sudo pacman -S librewolf`.
3. **Aplicar en tu PC:** `./install.sh -n` y después `./install.sh`. Te va a pedir sudo para la regla udev nueva y
   para `/etc/sddm.conf`, y va a crear `~/.gitconfig.local` con tu identidad. Después `SUPER+O`.
4. **Prueba con un usuario nuevo** (lo corrés vos, necesita sudo):
   ```bash
   sudo useradd -m -G wheel -s /bin/bash prueba && sudo passwd prueba
   # entrar como "prueba" (TTY o SDDM → Hyprland) y:
   git clone https://github.com/Juani4312/Config_Files.git ~/Sync && cd ~/Sync && ./install.sh
   # al terminar: sudo userdel -r prueba
   ```
   Opcional, para probar los paquetes desde cero sin tocar tu sistema:
   `docker run --rm -it archlinux bash`, y adentro instalar `git sudo`, crear un usuario, y correr `./install.sh -p`.
5. **Decidir las dudas de §6.**
