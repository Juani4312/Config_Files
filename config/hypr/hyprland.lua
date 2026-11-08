-- Hyprland config basada en https://github.com/binnewbs/arch-hyprland
-- (traducida de hyprlang a Lua para Hyprland 0.55+)
-- Backup de la config original: ~/.config/hypr.bak-20261025-005229


------------------
---- MONITORS ----
------------------

-- Los monitores (resolución, posición y scale/zoom) son distintos en cada máquina,
-- así que viven en ~/.config/hypr/monitors.lua, que NO se sincroniza con el repo.
-- Si no existe, se usa la config genérica de abajo.
if not pcall(require, "monitors") then
    hl.monitor({
        output   = "",
        mode     = "preferred",
        position = "auto",
        scale    = "auto",
    })
end


---------------------
---- MY PROGRAMS ----
---------------------

terminal    = "kitty"
fileManager = "nemo"
menu        = "rofi -show drun -theme-str 'listview { require-input: true; }'"  -- spotlight: lista aparece al escribir


-------------------
---- AUTOSTART ----
-------------------

hl.on("hyprland.start", function ()
    hl.exec_cmd("waybar")
    hl.exec_cmd("awww-daemon")
    hl.exec_cmd("sleep 1 && awww img ~/.config/hypr/current_wallpaper")
    hl.exec_cmd("swaync")
    hl.exec_cmd("systemctl --user start hyprpolkitagent")
    hl.exec_cmd("hypridle")
    hl.exec_cmd("~/.config/hypr/scripts/autoscroll-indicator.py")
    hl.exec_cmd("wl-paste --type text --watch cliphist store")
    hl.exec_cmd("wl-paste --type image --watch cliphist store")
end)


-------------------------------
---- ENVIRONMENT VARIABLES ----
-------------------------------

hl.env("XCURSOR_SIZE", "24")
hl.env("HYPRCURSOR_SIZE", "24")
hl.env("XCURSOR_THEME", "Matu")
hl.env("HYPRCURSOR_THEME", "Matu")
hl.env("TERMINAL", "kitty")


-----------------
---- MODULES ----
-----------------

require("configs.tags")
require("configs.looknfeel")
require("configs.animations")
require("configs.opacity")
require("configs.windowrules")
require("configs.input")
require("configs.keybinds")


-----------------
---- LAYOUTS ----
-----------------

hl.config({
    dwindle = {
        preserve_split = true,
    },
    master = {
        new_status = "master",
    },
})


----------------
----  MISC  ----
----------------

hl.config({
    misc = {
        force_default_wallpaper = 0,
        disable_hyprland_logo   = true,
    },
    render = {
        new_render_scheduling = true,
    },
})
