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
#   ASK      -> apps donde reiniciar molesta: notificacion con boton "Reiniciar"
#   Tidal    -> se reinicia solo si NO esta sonando; si suena, pregunta
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

wait_exit() {  # espera hasta ~15s a que el proceso termine
  local i
  for ((i = 0; i < 75; i++)); do pgrep -x "$1" >/dev/null || return 0; sleep 0.2; done
  return 1
}

restart_app() {
  local app=$1 proc=${PROC[$1]} ws
  running "$app" || return 0
  ws=$(ws_of "${CLASS[$app]}")
  echo "reiniciando $app (workspace: ${ws:-ninguno})"
  if [[ $app == steam ]]; then
    steam -shutdown >/dev/null 2>&1
  else
    kill -TERM "$(pgrep -o -x "$proc")"   # proceso principal: cierre limpio
  fi
  wait_exit "$proc" || { echo "$app no cerro, SIGKILL"; pkill -KILL -x "$proc"; sleep 0.5; }
  # qalculate pisa su cfg al cerrar: re-aplicar los colores despues de que cierre
  [[ $app == qalculate ]] && sh ~/.config/matugen/scripts/qalculate-colors.sh
  launch_on "$ws" "${CMD[$app]}"
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

pending=()
for app in "${ASK_RESTART[@]}"; do
  running "$app" || continue
  if [[ $app == tidal ]] && ! tidal_playing; then
    restart_app tidal          # pausado: reiniciar no corta nada
  else
    pending+=("$app")
  fi
done

[[ ${#pending[@]} -eq 0 ]] && exit 0

# Notificacion con botones; corre en segundo plano y espera la respuesta.
(
  names=$(for a in "${pending[@]}"; do printf '%s, ' "${NAME[$a]}"; done); names=${names%, }
  actions=()
  if [[ ${#pending[@]} -eq 1 ]]; then
    actions+=(-A "${pending[0]}=Reiniciar ${NAME[${pending[0]}]}")
  else
    for a in "${pending[@]}"; do actions+=(-A "$a=${NAME[$a]}"); done
    actions+=(-A "all=Reiniciar todas")
  fi
  if [[ ${#pending[@]} -eq 1 ]]; then
    body="Para que $names tome los colores nuevos hay que reiniciarla."
  else
    body="Para que $names tomen los colores nuevos hay que reiniciarlas."
  fi
  choice=$(notify-send -a "Tema" -i preferences-desktop-theme \
    "Colores nuevos aplicados" "$body" "${actions[@]}")
  echo "eleccion: ${choice:-ninguna}"
  case $choice in
    all) for a in "${pending[@]}"; do restart_app "$a"; done ;;
    "")  ;;
    *)   restart_app "$choice" ;;
  esac
) &
disown
