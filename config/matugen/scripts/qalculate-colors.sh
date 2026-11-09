#!/bin/sh
# Generado por matugen: aplica la paleta a qalculate-gtk.cfg
# (qalculate reescribe el cfg al cerrar; los cambios se ven al reabrirlo)
cfg="$HOME/.config/qalculate/qalculate-gtk.cfg"
[ -f "$cfg" ] || exit 0
set_key() {
  if grep -q "^$1=" "$cfg"; then sed -i "s|^$1=.*|$1=$2|" "$cfg"
  else sed -i "/^\[General\]/a $1=$2" "$cfg"; fi
}
set_key status_error_color '#ffb4ab'
set_key status_warning_color '#d2bfe7'
