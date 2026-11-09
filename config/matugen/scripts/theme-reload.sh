#!/usr/bin/env bash
# theme-reload.sh — hace que las apps abiertas tomen la paleta nueva de matugen.
# Lo llama wppicker.sh (Super+W) despues de `matugen image`.
#
# Ya cubierto sin este script (post_hook de matugen o la app vigila su archivo):
#   waybar, kitty, hyprland, cava, cursor, rofi (lee al abrir), vesktop (vigila
#   themes/), VS Code (manifest con "_watch": true).
#
# Este script se encarga de:
#   swaync   -> swaync-client -rs ; wlogout -> re-tiñe los iconos PNG
#   GTK3     -> alterna el tema Matugen-a/Matugen-b: GTK relee colors.css en vivo
#   btop     -> SIGUSR2 (relee config + tema)
#   AUTO     -> apps que se reinician solas si estan abiertas (vuelven a su workspace)
#   ASK      -> apps donde reiniciar molesta: un popup "Reiniciar todo / Ignorar"
#               + una notificacion por app en el panel de swaync (boton "Reiniciar")
#   Tidal    -> se reinicia solo si NO esta sonando; si suena, pregunta
#   Steam    -> se reinicia solo si NO hay un juego abierto; si hay, pregunta
#
# Log: $XDG_RUNTIME_DIR/theme-reload.log

AUTO_RESTART=(zapzap qalculate)          # se reinician sin preguntar
ASK_RESTART=(tidal librewolf steam prism) # notificacion con boton

LOG="${XDG_RUNTIME_DIR:-/tmp}/theme-reload.log"
exec >>"$LOG" 2>&1
echo "== $(date '+%F %T')"

# ---------- datos de cada app: proceso | clase de ventana | comando ----------
declare -A PROC=(  [zapzap]=zapzap [qalculate]=qalculate-gtk [tidal]=tidal-hifi
                   [librewolf]=librewolf [steam]=steam [prism]=prismlauncher )
declare -A CLASS=( [zapzap]=com.rtosta.zapzap [qalculate]=qalculate-gtk [tidal]=tidal-hifi
                   [librewolf]=librewolf [steam]=steam [prism]=org.prismlauncher.PrismLauncher )
declare -A CMD=(   [zapzap]=zapzap [qalculate]=qalculate-gtk
                   [tidal]="tidal-hifi --enable-features=UseOzonePlatform --ozone-platform-hint=auto --enable-features=WaylandWindowDecorations"
                   [librewolf]=/usr/lib/librewolf/librewolf [steam]=steam [prism]=prismlauncher )
declare -A NAME=(  [zapzap]=ZapZap [qalculate]=Qalculate [tidal]=Tidal
                   [librewolf]=Librewolf [steam]=Steam [prism]=PrismLauncher )

running() { pgrep -x "${PROC[$1]}" >/dev/null; }

ws_of() {  # workspace de la primera ventana de esa clase (vacio si no tiene ventana)
  hyprctl clients -j | jq -r --arg c "$1" '[.[] | select(.class==$c)][0].workspace.name // empty'
}

launch_on() {  # launch_on <workspace|""> <comando...>
  local ws=$1; shift
  if [[ -n $ws ]]; then
    hyprctl dispatch "hl.dsp.exec_cmd(\"$*\", { workspace = \"$ws silent\" })"
  else
    hyprctl dispatch "hl.dsp.exec_cmd(\"$*\")"
  fi
}

wait_exit() {  # wait_exit <proceso> [segundos=15]: espera a que el proceso termine
  local i
  for ((i = 0; i < ${2:-15} * 5; i++)); do pgrep -x "$1" >/dev/null || return 0; sleep 0.2; done
  return 1
}

restart_app() {
  local app=$1 proc=${PROC[$1]} ws
  running "$app" || return 0
  ws=$(ws_of "${CLASS[$app]}")
  echo "reiniciando $app (workspace: ${ws:-ninguno})"
  local cmd=${CMD[$app]} secs=15
  if [[ $app == steam ]]; then
    steam -shutdown >/dev/null 2>&1
    secs=40                              # Steam tarda en cerrar (sync de nube, etc.)
    [[ -z $ws ]] && cmd="steam -silent"  # estaba en la bandeja: que vuelva ahi
  else
    kill -TERM "$(pgrep -o -x "$proc")"   # proceso principal: cierre limpio
  fi
  wait_exit "$proc" "$secs" || { echo "$app no cerro, SIGKILL"; pkill -KILL -x "$proc"; sleep 0.5; }
  # qalculate pisa su cfg al cerrar: re-aplicar los colores despues de que cierre
  [[ $app == qalculate ]] && sh ~/.config/matugen/scripts/qalculate-colors.sh
  launch_on "$ws" "$cmd"
  # La ventana de Steam la crea steamwebhelper (otro PID), asi que la regla de
  # workspace de exec_cmd no le llega: esperarla y moverla sin cambiar el foco.
  if [[ $app == steam && -n $ws ]]; then
    (
      for ((i = 0; i < 120; i++)); do
        sleep 0.5
        hyprctl clients -j | jq -e '.[] | select(.class=="steam" and .title=="Steam")' >/dev/null || continue
        hyprctl dispatch "hl.dsp.window.move({ workspace = \"$ws\", window = \"class:steam\", follow = false })" >/dev/null
        echo "steam movido al workspace $ws"; break
      done
    ) &
  fi
}

tidal_playing() {
  [[ $(curl -s -m 2 http://localhost:47836/current | jq -r '.status // empty' 2>/dev/null) == playing ]]
}

# ---------- recargas en vivo ----------
cur=$(gsettings get org.gnome.desktop.interface gtk-theme | tr -d "'")
[[ $cur == Matugen-a ]] && next=Matugen-b || next=Matugen-a
gsettings set org.gnome.desktop.interface gtk-theme "$next" && echo "gtk: $cur -> $next"

pkill -USR2 -x btop && echo "btop recargado"

# swaync (panel + notificaciones) lee waybar/colors.css solo al arrancar o con -rs
swaync-client -rs >/dev/null && echo "swaync recargado"

# wlogout: sus íconos son PNG, se re-tiñen con el primary nuevo
~/.config/wlogout/tint-icons.sh && echo "iconos de wlogout tenidos"

# ---------- reinicios ----------
for app in "${AUTO_RESTART[@]}"; do restart_app "$app"; done

steam_ingame() {  # los juegos (nativos y Proton) corren bajo "reaper SteamLaunch AppId=N"
  pgrep -f 'SteamLaunch AppId=' >/dev/null
}

# ---------- notificaciones de reinicio ----------
# Un popup resumen (Reiniciar todo / Ignorar) + una notificacion por app que va
# directo al panel sin popup. Las reglas estan en ~/.config/swaync/config.json
# (notification-visibility): category theme.summary -> transient (solo popup),
# theme.app -> muted (solo panel).
STATE="${XDG_RUNTIME_DIR:-/tmp}/theme-reload"
mkdir -p "$STATE"

close_notif() {
  gdbus call --session --dest org.freedesktop.Notifications \
    --object-path /org/freedesktop/Notifications \
    --method org.freedesktop.Notifications.CloseNotification "$1" >/dev/null 2>&1
}

# Las de un cambio de fondo anterior ya no sirven: cerrarlas (sus procesos
# notify-send reciben "cerrada" y terminan sin hacer nada).
if [[ -f $STATE/ids ]]; then
  while read -r id; do [[ -n $id ]] && close_notif "$id"; done <"$STATE/ids"
fi
rm -f "$STATE"/ids "$STATE"/*.id "$STATE"/*.done

ask_app() {  # notificacion individual de una app (queda en el panel)
  local app=$1 id action
  notify-send -p -a "Tema · ${NAME[$app]}" -c theme.app -i "${ICON[$app]}" \
    "${NAME[$app]}" "Reiniciar para tomar los colores nuevos." \
    -A "restart=Reiniciar" | {
    read -r id
    echo "$id" >>"$STATE/ids"; echo "$id" >"$STATE/$app.id"
    read -r action
    if [[ $action == restart && ! -e $STATE/$app.done ]]; then
      touch "$STATE/$app.done"
      echo "eleccion: $app (panel)"
      restart_app "$app"
    fi
  }
}

ask_summary() {  # popup unico: Reiniciar todo / Ignorar
  local names body id action a
  names=$(for a in "$@"; do printf '%s, ' "${NAME[$a]}"; done); names=${names%, }
  if [[ $# -eq 1 ]]; then
    body="$names necesita reiniciarse para tomar los colores nuevos."
  else
    body="$names necesitan reiniciarse para tomar los colores nuevos."
  fi
  notify-send -p -a "Tema" -c theme.summary -t 15000 -i preferences-desktop-theme \
    "Colores nuevos" "$body" \
    -A "all=Reiniciar todo" -A "ignore=Ignorar" 2>/dev/null | {
    read -r id
    echo "$id" >>"$STATE/ids"
    read -r action
    echo "eleccion: ${action:-ninguna} (resumen)"
    [[ $action == all ]] || return 0   # Ignorar / vencida: quedan las del panel
    for a in "$@"; do
      [[ -e $STATE/$a.done ]] && continue
      touch "$STATE/$a.done"
      [[ -f $STATE/$a.id ]] && close_notif "$(<"$STATE/$a.id")"
      restart_app "$a"
    done
  }
}

declare -A ICON=( [tidal]=tidal-hifi [librewolf]=librewolf [steam]=steam
                  [prism]=org.prismlauncher.PrismLauncher )

pending=()
for app in "${ASK_RESTART[@]}"; do
  running "$app" || continue
  if [[ $app == tidal ]] && ! tidal_playing; then
    restart_app tidal          # pausado: reiniciar no corta nada
  elif [[ $app == steam ]] && ! steam_ingame; then
    restart_app steam          # sin juego abierto: reiniciar no corta nada
  else
    pending+=("$app")
  fi
done

[[ ${#pending[@]} -eq 0 ]] && exit 0

# Las individuales primero (asi el resumen puede cerrarlas), despues el popup.
# Todo en segundo plano: cada notify-send espera la respuesta.
for app in "${pending[@]}"; do ask_app "$app" & done
sleep 0.3
ask_summary "${pending[@]}" &
disown -a
