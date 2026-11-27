-- Niveles de opacidad para ventanas SIN foco (globales: los usa windowrules.lua).
-- Se aplican con "override", así que son el valor final exacto y no se
-- multiplican por decoration.inactive_opacity.
transparency_dif_low  = 0.65  -- bien transparente
transparency_dif_mid  = 0.75  -- intermedio (default)
transparency_dif_high = 0.85  -- apenas transparente

-- "<activa> <sin foco> override" (la activa se sigue multiplicando por active_opacity)
function inactive_opacity_rule(active, inactive)
    return active .. " " .. inactive .. " override"
end

-- Transparencia global: ventana en foco 0.95, sin foco nivel medio.
-- Se carga antes de windowrules para que las reglas especificas (video, kitty, etc.) la pisen.
hl.window_rule({ match = { class = ".*" }, opacity = inactive_opacity_rule(0.95, transparency_dif_mid) })
