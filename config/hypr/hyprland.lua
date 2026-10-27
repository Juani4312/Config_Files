-- Hyprland config basada en https://github.com/binnewbs/arch-hyprland
-- (traducida de hyprlang a Lua para Hyprland 0.55+)
-- Backup de la config original: ~/.config/hypr.bak-20261025-005229


------------------
---- MONITORS ----
------------------

-- See https://wiki.hypr.land/Configuring/Basics/Monitors/
-- El repo original usa: output = "eDP-1", mode = "1920x1080@60", position = "0x0", scale = 1
-- PC: Samsung (HDMI-A-1) a la izquierda, LG UltraGear (DP-3) a la derecha
hl.monitor({
    output   = "HDMI-A-1",
    mode     = "1920x1080@75",
    position = "0x0",
    scale    = 1,
})

hl.monitor({
    output   = "DP-3",
    mode     = "1920x1080@144",
    position = "1920x0",
    scale    = 1,
})

-- Cualquier otro monitor
hl.monitor({
    output   = "",
    mode     = "preferred",
    position = "auto",
    scale    = "auto",
})

-- Workspaces por monitor (PC): DP-3 = 1-5, HDMI-A-1 = 6-10
for i = 1, 10 do
    hl.workspace_rule({
        workspace = tostring(i),
        monitor   = i <= 5 and "DP-3" or "HDMI-A-1",
        default   = (i == 1 or i == 6),
    })
end


---------------------
---- MY PROGRAMS ----
---------------------

terminal    = "kitty"
fileManager = "nemo"
menu        = "rofi -show drun"


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
    hl.exec_cmd("wl-paste --type text --watch cliphist store")
    hl.exec_cmd("wl-paste --type image --watch cliphist store")
end)


-------------------------------
---- ENVIRONMENT VARIABLES ----
-------------------------------

hl.env("XCURSOR_SIZE", "24")
hl.env("HYPRCURSOR_SIZE", "24")
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
