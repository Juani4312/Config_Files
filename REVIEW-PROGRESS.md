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
- [ ] Fixes del plan (commits 1–9).
- [ ] Leer todo el código restante.
- [ ] Instalación desde cero (paquetes, yay, servicios, archivos que faltan).
- [ ] Verificación final + docs + reporte final.

## Próximo paso
Aplicar los fixes del plan, empezando por `fix(install)`.

## Log
- 2026-11-27: review inicial terminada; borrador de `REVIEW-REPORT.md`. Pusheaste los 5 commits de main.
