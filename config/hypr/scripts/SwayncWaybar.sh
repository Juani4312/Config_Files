#!/bin/bash
# Wrapper de swaync-client -swb: oculta el contador cuando no hay notificaciones
swaync-client -swb | while IFS= read -r line; do
    echo "$line" | sed -E 's/"text": "0"/"text": ""/'
done
