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
hl.window_rule({ match = { class = "^(discord|vesktop)$" }, opacity = "0.9" })
hl.window_rule({ match = { class = "^(com.rtosta.zapzap)$" }, opacity = "0.9" })
hl.window_rule({ match = { class = "^(org.telegram.desktop)$" }, opacity = "0.85 override 0.7 override 1 override" })
hl.window_rule({ match = { class = "^(Spotify)$" }, opacity = "0.8 override 0.6 override 1 override" })
hl.window_rule({ match = { class = "^(zen)$" }, opacity = "0.9 override 0.7 override 1 override" })


---------------------
---- LAYER RULES ----
---------------------

hl.layer_rule({ match = { namespace = "waybar" }, blur = true, ignore_alpha = 0.5 })
hl.layer_rule({ match = { namespace = "logout_dialog" }, blur = true })

-- ROFI (spotlight): pop-in rapido con rebote + blur del fondo translucido
hl.layer_rule({ match = { namespace = "^rofi$" }, animation = "popin 85%", blur = true, ignore_alpha = 0.3 })

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
hl.window_rule({ match = { class = "^(blueman-manager)$" }, float = true, size = "520 380", center = true })

-- Bitwarden (popup de la extension en LibreWolf): flota centrado.
-- La ventana abre con titulo "LibreWolf" y despues lo cambia, asi que la regla
-- estatica no alcanza: se re-aplica float/size/center cuando cambia el titulo.
local bitwarden_title = "^Extension: \\(Bitwarden Password Manager\\) - Bitwarden — LibreWolf$"
hl.window_rule({
    match  = { class = "^(librewolf)$", title = bitwarden_title },
    float  = true,
    size   = "700 1000",
    center = true,
})
hl.on("window.title", function(w)
    w = w or hl.get_active_window()
    if not w or w.class ~= "librewolf" or w.floating then return end
    if not string.find(w.title, "Extension: (Bitwarden Password Manager)", 1, true) then return end
    hl.dispatch(hl.dsp.window.float({ action = "enable" }))
    hl.dispatch(hl.dsp.window.resize({ x = 700, y = 1000 }))
    hl.dispatch(hl.dsp.window.center())
end)

-- Proton Authenticator: flota centrado, rectangulo vertical
hl.window_rule({ match = { class = "^(proton-authenticator)$" }, float = true, size = "450 750", center = true })

-- Bitwarden (app de escritorio): flota centrado, rectangulo vertical
hl.window_rule({ match = { class = "^(bitwarden)$" }, float = true, size = "550 750", center = true })

-- Steam: todo flota centrado menos la ventana principal (titulo exacto "Steam").
-- El regex matchea cualquier titulo distinto de "Steam" (RE2 no tiene lookahead).
hl.window_rule({
    match  = { class = "^(steam)$", initial_title = "^(.{0,4}|.{6,}|[^S].{4}|S[^t].{3}|St[^e].{2}|Ste[^a].|Stea[^m])$" },
    float  = true,
    size   = "1000 560",
    center = true,
})
-- Lista de amigos: finita y vertical
hl.window_rule({
    match  = { class = "^(steam)$", initial_title = "^(Friends List)$" },
    float  = true,
    size   = "340 760",
    center = true,
})

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

-- Qalculate!: flota centrado, rectangulo vertical
hl.window_rule({ match = { class = "^(qalculate-gtk)$" }, float = true, size = "480 780", center = true })
