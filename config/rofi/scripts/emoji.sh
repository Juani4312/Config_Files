#!/usr/bin/env bash
# rofi script mode for the Super+I emoji picker (see ../emoji.rasi).
# Usage: emoji.sh <category-key>   (one rofi mode per category tab)
# The prompt doubles as the tab label in rofi's mode-switcher.
# Data: rofi-emoji's list (emoji \t group \t subgroup \t name \t keywords).
DATA=/usr/share/rofi-emoji/all_emojis.txt

if [ -n "$1" ] && [ "${ROFI_RETV:-0}" -ne 0 ]; then
    # entry selected: $2 holds the chosen line (rofi passes it after our arg)
    printf '%s' "$2" | wl-copy
    exit 0
fi

case "$1" in
    all)        group="";                  label=$'\U000F0570' ;;
    smileys)    group="Smileys & Emotion"; label="😀" ;;
    people)     group="People & Body";     label="👋" ;;
    animals)    group="Animals & Nature";  label="🌿" ;;
    food)       group="Food & Drink";      label="🍔" ;;
    activities) group="Activities";        label="⚽" ;;
    travel)     group="Travel & Places";   label="✈️" ;;
    objects)    group="Objects";           label="💡" ;;
    symbols)    group="Symbols";           label="💟" ;;
    flags)      group="Flags";             label="🏳️" ;;
esac

printf '\0prompt\x1f%s\n' "$label"
printf '\0no-custom\x1ftrue\n'
awk -F'\t' -v g="$group" '$2 != "Component" && (g == "" || $2 == g) {
    printf "%s\0meta\x1f%s %s %s\n", $1, $4, $5, $3
}' "$DATA"
