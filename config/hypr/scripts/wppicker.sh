#!/bin/bash

# === CONFIG ===
WALLPAPER_DIR="$HOME/Pictures/Wallpapers"
SYMLINK_PATH="$HOME/.config/hypr/current_wallpaper"
ICON_FOLDER="/usr/share/icons/WhiteSur/places/scalable/folder-pictures.svg"
ICON_BACK="/usr/share/icons/WhiteSur/places/scalable/folder-open.svg"
BACK=".."

cd "$WALLPAPER_DIR" || exit 1

# === MENU: subfolders first, then images (newest first) of the current folder ===
# $1 = folder relative to WALLPAPER_DIR ("" = root)
menu() {
    local rel="$1" dir="$WALLPAPER_DIR${1:+/$1}"
    [ -n "$rel" ] && echo -en "$BACK\0icon\x1f$ICON_BACK\n"
    find "$dir" -mindepth 1 -maxdepth 1 -type d ! -name '.*' -printf '%f\n' | sort -f \
        | while read -r d; do echo -en "$d/\0icon\x1f$ICON_FOLDER\n"; done
    find "$dir" -mindepth 1 -maxdepth 1 -type f \( -iname '*.jpg' -o -iname '*.jpeg' -o -iname '*.png' -o -iname '*.gif' -o -iname '*.webp' \) \
        -printf '%T@\t%f\n' | sort -rn | cut -f2- \
        | while read -r f; do echo -en "$f\0icon\x1f$dir/$f\n"; done
}

REL=""
while true; do
    CHOICE=$(menu "$REL" | rofi -dmenu -i -p "Wallpapers${REL:+/$REL}" -theme-str 'entry { placeholder: "Search wallpapers"; }')
    [ -z "$CHOICE" ] && exit 1
    if [ "$CHOICE" = "$BACK" ]; then
        REL=$(dirname "$REL"); [ "$REL" = "." ] && REL=""
    elif [[ "$CHOICE" == */ ]]; then
        REL="${REL:+$REL/}${CHOICE%/}"
    else
        SELECTED_PATH="$WALLPAPER_DIR/${REL:+$REL/}$CHOICE"
        [ -f "$SELECTED_PATH" ] && break
    fi
done

# === SET WALLPAPER ===
matugen image --source-color-index 0 "$SELECTED_PATH"

# === RELOAD APP THEMES (gtk, btop, zapzap, tidal, librewolf...) ===
"$HOME/.config/matugen/scripts/theme-reload.sh" &

# === CREATE SYMLINK ===
mkdir -p "$(dirname "$SYMLINK_PATH")"
ln -sf "$SELECTED_PATH" "$SYMLINK_PATH"
