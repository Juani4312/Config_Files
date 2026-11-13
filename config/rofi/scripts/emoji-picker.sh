#!/usr/bin/env bash
# Super+I: emoji picker with category tabs (rofi mode-switcher).
pkill -x rofi && exit 0
s="$HOME/.config/rofi/scripts/emoji.sh"
modi=""
for c in all smileys people animals food activities travel objects symbols flags; do
    modi+="${modi:+,}$c:$s $c"
done
exec rofi -modi "$modi" -show all -theme "$HOME/.config/rofi/emoji.rasi"
