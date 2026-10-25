#!/bin/bash
# Alterna el layout del teclado (us <-> latam) y avisa con una notificación
hyprctl switchxkblayout all next >/dev/null
layout=$(hyprctl devices -j | python3 -I -c "
import sys, json
kbs = json.load(sys.stdin)['keyboards']
print(next((k['active_keymap'] for k in kbs if k.get('main')), kbs[0]['active_keymap']))")
notify-send -u low -t 1500 -h string:x-canonical-private-synchronous:kb-layout \
    "Switching keyboard layout" "$layout"
