-- Colores generados por matugen (ver ~/.config/matugen/config.toml)
local colors = require("colors")

-- Blur normal y blur "fuerte" mientras hay un workspace especial abierto
-- (ver update_special_blur al final del archivo)
local BLUR_SIZE,         BLUR_PASSES         = 5, 3
local BLUR_SIZE_SPECIAL, BLUR_PASSES_SPECIAL = 10, 4

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
        inactive_opacity = 0.9,

        shadow = {
            enabled      = false,
            range        = 4,
            render_power = 3,
            color        = "rgba(1a1a1aee)",
        },

        blur = {
            enabled           = true,
            size              = BLUR_SIZE,
            passes            = BLUR_PASSES,
            ignore_opacity    = true,
            new_optimizations = true,
            special           = false,  -- true tapa la waybar (layer "bottom") con el especial abierto
            popups            = true,
            xray              = true,
            vibrancy          = 0.1696,
        },
    },
})


-- Con el workspace especial abierto (SUPER+S) se sube el blur global, así lo que
-- queda detrás (el resto de los workspaces) se ve más difuminado. Con blur.xray
-- las ventanas del especial difuminan el wallpaper. NO usar blur.special = true: con el
-- especial abierto dibuja el fondo difuminado ENCIMA de la waybar (layer "bottom").
local function special_open()
    for _, m in ipairs(hl.get_monitors()) do
        if m.active_special_workspace then return true end
    end
    return false
end

local function update_special_blur()
    local on = special_open()
    hl.config({ decoration = { blur = {
        size   = on and BLUR_SIZE_SPECIAL   or BLUR_SIZE,
        passes = on and BLUR_PASSES_SPECIAL or BLUR_PASSES,
    } } })
end

hl.on("workspace.special_active", function() pcall(update_special_blur) end)
pcall(update_special_blur)  -- al recargar la config con el especial abierto
