#!/bin/bash
# esperar a que wlogout cierre y suelte el teclado antes de bloquear
sleep 0.5
pidof hyprlock || hyprlock
