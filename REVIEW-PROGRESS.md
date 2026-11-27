# REVIEW-PROGRESS — bitácora para retomar

Branch: `review/ponytail` (sale de `main` @ `facd049`, ya pusheado). Nada se pushea ni se mergea desde acá.
Instrucciones originales: `~/Laptop/CONFIG-FILES-REVISION.md`. Reporte: `REVIEW-REPORT.md`.

## Cómo retomar (si se cortó)
1. `cd ~/Laptop/Sync && git switch review/ponytail && git log --oneline main..` → muestra qué commits ya están.
2. Leer "Estado" y "Próximo paso" abajo.
3. **No correr** `update.sh` (pisaría la branch con el estado de la máquina) ni `install.sh` sin `-n`.
4. Archivos temporales de la review: `~/Laptop/.review-tmp/` (fuera del repo, se puede borrar al final).

## Pedido (2026-11-27)
1. Corregir lo encontrado en el borrador del reporte.
2. Leer todo el código.
3. Que una persona cualquiera con Arch pueda instalar **todo**: paquetes, configs, scripts. Si falta algo, buscarlo en la PC.
4. Documentar todo para poder pausar.

## Decisiones tomadas
- Datos personales: se tratan como hallazgos. `[user]` de `.gitconfig` pasa a `~/.gitconfig.local` (con include).
  El historial de git no se reescribe.
- Backups trackeados en el repo (`hypr/old-conf/`, `*.pre-classfix`, `(Copy).rasi`, `quick.css.orig`): se borran
  del repo y `EXCLUDE_PATTERNS` los ignora de ahora en más. Los `*.bak*` del `$HOME` real no se tocan: hay un comando en el reporte.
- Código posiblemente muerto (`viegphunt/`, `AirplaneMode.sh`, `steam-adwaita.css`, etc.) **no se borra**: queda en Dudas.
- `packages/pacman.txt` y `aur.txt` los regenera `update.sh` (`pacman -Qqe`). Las dependencias reales del repo van
  en una lista aparte, mantenida a mano, que `update.sh` no toca.

## Estado
(lo actualizo después de cada paso)

- [x] Fase 0–2: inventario, audit, review → borrador del reporte.
- [x] Fixes del plan: commits 4708d9a…b39ebd6 (install, revert, hypr, autoscroll, git, zsh, update, chore).
  #14 (curl en hyprlock) no aplicaba: el label estaba deshabilitado, pero comentado a medias → arreglado.
  El commit de docs (#9) queda para el final, junto con lo de instalación desde cero.
- [x] Leer todo el código restante (popups grandes de waybar leídos por estructura + interacciones externas;
  arte SVG de cursor/build.py y CSS minificado de steam no línea por línea).
- [x] Instalación desde cero: commits 999debe (waybar genérico), fd6c17d (deps.txt + yay + servicios + temas
  de apps + sddm.conf), 8cf516e (historial qalculate/Qt), e85947f (state() con /home/<usuario>).
  Probado de punta a punta en HOME falso con stubs (~/Laptop/.review-tmp/e2e): instala, es idempotente
  y revert deja el HOME vacío.
- [x] Verificación final + /ponytail-review (fixes en c6837c0) + tests/install-e2e.sh + docs + REVIEW-REPORT.md final.

## Próximo paso
La review terminó. Lo que queda depende del usuario:
1. Que revise el diff y mergee.
2. Que haga los pendientes con sudo (abajo).
3. La prueba con un usuario nuevo (REVIEW-REPORT §8) y las dudas de §6. Si pide aplicar alguna duda, va en commits nuevos en esta branch.

## Pendientes para el usuario (necesitan sudo, no los hago yo)
- ~~Migrar LibreWolf~~ HECHO 2026-11-27: librewolf 160 (extra), mismo perfil ~/.librewolf/l1vipx6v.default-default.
  (antes: `sudo pacman -Rdd librewolf-bin librewolf-bin-debug && sudo pacman -S librewolf`)
  (librewolf-bin ya no existe en AUR; mismas rutas, el perfil sigue igual). Hacerlo ANTES de `install.sh -p`.
- `./install.sh` después de mergear: instala la regla udev nueva (uinput) y /etc/sddm.conf con sudo.

## Log
- 2026-11-27: LibreWolf migrado. Próximo: prueba de instalación desde cero con un usuario nuevo (la hace el usuario).
- 2026-11-27: review cerrada; reporte final. Test: `tests/install-e2e.sh` → OK.
- 2026-11-27: fixes del plan + instalación desde cero + prueba e2e en HOME falso.
- 2026-11-27: review inicial terminada; borrador de `REVIEW-REPORT.md`. Pusheaste los 5 commits de main.
