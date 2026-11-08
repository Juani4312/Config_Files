-- Colores generados por matugen (ver ~/.config/matugen/config.toml)
local colors = require("colors")

hl.config({
    general = {
        gaps_in  = 5,
        gaps_out = 10,

        border_size = 2,

        col = {
            active_border   = colors.outline,
            inactive_border = colors.outline_variant,
        },

        -- Arrastrar bordes/esquinas para redimensionar (area de agarre extendida
        -- porque el borde es de solo 2px)
        resize_on_border        = true,
        extend_border_grab_area = 15,
        hover_icon_on_border    = true,
        allow_tearing    = false,

        layout = "dwindle",
    },

    decoration = {
        rounding       = 10,
        rounding_power = 2,

        active_opacity   = 1.0,
        inactive_opacity = 0.8,

        shadow = {
            enabled      = false,
            range        = 4,
            render_power = 3,
            color        = "rgba(1a1a1aee)",
        },

        blur = {
            enabled           = true,
            size              = 5,
            passes            = 3,
            ignore_opacity    = true,
            new_optimizations = true,
            special           = false,
            popups            = true,
            xray              = true,
            vibrancy          = 0.1696,
        },
    },
})
