#!/bin/sh
# Run once with sudo: installs the asar patcher + pacman hook and patches tidal-hifi now.
set -e
cd "$(dirname "$0")"
install -Dm755 patch-asar.py /usr/local/lib/tidal-hifi-userscripts/patch-asar.py
install -Dm644 tidal-hifi-userscripts.hook /etc/pacman.d/hooks/tidal-hifi-userscripts.hook
/usr/bin/python3 /usr/local/lib/tidal-hifi-userscripts/patch-asar.py /opt/tidal-hifi/resources/app.asar
