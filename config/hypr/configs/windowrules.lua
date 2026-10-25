-----------------------------
---- APPLICATIONS BLUR ----
-----------------------------

hl.window_rule({ match = { tag = "multimedia_video" }, no_blur = true, opacity = "1.0" })
hl.window_rule({ match = { tag = "settings" }, opacity = "0.8" })
hl.window_rule({ match = { class = "^(org.gnome.Nautilus)$" }, opacity = "0.8" })
hl.window_rule({ match = { class = "^(nemo)$" }, opacity = "0.8" })
hl.window_rule({ match = { class = "^(gedit|org.gnome.TextEditor|mousepad)$" }, opacity = "0.9" })
hl.window_rule({ match = { class = "^(org.pulseaudio.pavucontrol)$" }, opacity = "0.9" })
hl.window_rule({ match = { class = "^(kitty)$" }, opacity = "0.9" })
hl.window_rule({ match = { class = "^(discord|vesktop|org.telegram.desktop)$" }, opacity = "0.85 override 0.7 override 1 override" })
hl.window_rule({ match = { class = "^(Spotify)$" }, opacity = "0.8 override 0.6 override 1 override" })
hl.window_rule({ match = { class = "^(zen)$" }, opacity = "0.9 override 0.7 override 1 override" })


---------------------
---- LAYER RULES ----
---------------------

hl.layer_rule({ match = { namespace = "waybar" }, blur = true, ignore_alpha = 0.5 })
hl.layer_rule({ match = { namespace = "logout_dialog" }, blur = true })

-- ROFI: sin animacion de fade/slide para que abra al instante
hl.layer_rule({ match = { namespace = "^rofi$" }, no_anim = true })

-- SWAYNC BLUR & XRAY
hl.layer_rule({
    match = { namespace = "^(swaync-control-center|swaync-notification-window)$" },
    blur = true,
    ignore_alpha = 0.5,
    xray = false,
})


---------------
---- FLOAT ----
---------------

hl.window_rule({ match = { tag = "settings" }, float = true })
hl.window_rule({ match = { tag = "viewer" }, float = true })
hl.window_rule({ match = { tag = "multimedia_video" }, float = true, size = "900 506" })
hl.window_rule({ match = { class = "^(org.pulseaudio.pavucontrol)$" }, float = true, size = "monitor_w*0.5 monitor_h*0.6" })

-- Ignore maximize requests from apps
hl.window_rule({
    name  = "suppress-maximize-events",
    match = { class = ".*" },
    suppress_event = "maximize",
})

-- Fix some dragging issues with XWayland
hl.window_rule({
    name  = "fix-xwayland-drags",
    match = {
        class      = "^$",
        title      = "^$",
        xwayland   = true,
        float      = true,
        fullscreen = false,
        pin        = false,
    },
    no_focus = true,
})


------------------------------
---- POP UPS AND DIALOGUES ----
------------------------------

hl.window_rule({
    match  = { title = "^(Save As|Save a File|Pick Files)$" },
    float  = true,
    size   = "monitor_w*0.5 monitor_h*0.6",
    center = true,
})

hl.window_rule({
    match = { initial_title = "(Open Files)" },
    float = true,
    size  = "monitor_w*0.7 monitor_h*0.6",
})
