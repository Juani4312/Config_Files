-- Transparencia global: ventana en foco 0.95, sin foco 0.8
-- Se carga antes de windowrules para que las reglas especificas (video, kitty, etc.) la pisen.
hl.window_rule({ match = { class = ".*" }, opacity = "0.95 0.8" })
