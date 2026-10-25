#!/usr/bin/env bash
# Menu de wifi en rofi (nmcli). Click en la red para conectar; ya guardadas conectan sin pedir clave.
THEME="$HOME/.config/rofi/wifi.rasi"
rofi_cmd() { rofi -no-config -dmenu -i -theme "$THEME" "$@"; }

# toggle: abrir de nuevo cierra el menu
pkill -x rofi && exit 0

radio=$(nmcli radio wifi)
if [ "$radio" != "enabled" ]; then
	choice=$(printf '󰖩  Activar wifi\n' | rofi_cmd -p "󰤭 ")
	[ -n "$choice" ] && nmcli radio wifi on && sleep 2
	exec "$0"
fi

(nmcli device wifi rescan >/dev/null 2>&1 &)
current=$(nmcli -t -f active,ssid device wifi | awk -F: '$1=="yes"{print $2; exit}')

menu=$(nmcli -t -f ssid,signal,security device wifi list --rescan no | awk -F: -v cur="$current" '
	$1 != "" && !seen[$1]++ { n++; ssid[n]=$1; sig[n]=$2; sec[n]=$3 }
	END {
		for (i = 1; i <= n; i++) { # orden por señal (burbuja estable, pocas redes)
			idx[i] = i
		}
		for (i = 1; i <= n; i++) for (j = i + 1; j <= n; j++)
			if (sig[idx[j]] + 0 > sig[idx[i]] + 0) { t = idx[i]; idx[i] = idx[j]; idx[j] = t }
		for (k = 1; k <= n; k++) {
			i = idx[k]; s = sig[i] + 0
			ic = s >= 80 ? "󰤨" : s >= 60 ? "󰤥" : s >= 40 ? "󰤢" : s >= 20 ? "󰤟" : "󰤯"
			lock = sec[i] != "" ? " 󰌾" : ""
			mark = ssid[i] == cur ? "  (conectada)" : ""
			printf "%s  %s%s%s\n", ic, ssid[i], lock, mark
		}
		printf "󰖪  Desactivar wifi"
	}')
active_row=$(grep -n -m1 '(conectada)$' <<<"$menu" | cut -d: -f1)
[ -n "$active_row" ] && active_row=$((active_row-1)) || active_row=-1

args=(-p "󰤨 ")
[ "$active_row" -ge 0 ] && args+=(-a "$active_row")
choice=$(printf '%s' "$menu" | rofi_cmd "${args[@]}") || exit 0
[ -z "$choice" ] && exit 0

if [[ "$choice" == *"Desactivar wifi" ]]; then
	nmcli radio wifi off; exit 0
fi

ssid=$(sed -E 's/^[^ ]+  //; s/ 󰌾//; s/  \(conectada\)$//' <<<"$choice")

if [ "$ssid" = "$current" ]; then
	nmcli connection down id "$ssid" >/dev/null 2>&1
	exit 0
fi

if nmcli -t -f name connection show | grep -qxF "$ssid"; then
	out=$(nmcli connection up id "$ssid" 2>&1)
else
	pass=$(rofi_cmd -password -p "󰌾 " -mesg "Clave de $ssid" </dev/null) || exit 0
	out=$(nmcli device wifi connect "$ssid" password "$pass" 2>&1)
fi

if [ $? -eq 0 ]; then
	notify-send -i network-wireless "Wifi" "Conectado a $ssid"
else
	notify-send -u critical -i network-error "Wifi" "No se pudo conectar a $ssid\n$out"
fi
