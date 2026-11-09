---------------------
---- KEYBINDINGS ----
---------------------

local mainMod = "SUPER"
local scripts = "~/.config/hypr/scripts/"

local function bind(keys, dsp, opts)
    hl.bind(keys, dsp, opts)
end

local function mod(keys) return mainMod .. " + " .. keys end

bind(mod("T"),              hl.dsp.exec_cmd(terminal))
bind(mod("SHIFT + Return"), hl.dsp.exec_cmd(terminal, { float = true, size = "800 550" }))
bind(mod("C"),              hl.dsp.window.close())
bind("CTRL + ALT + Delete", hl.dsp.exec_cmd("command -v hyprshutdown >/dev/null 2>&1 && hyprshutdown || hyprctl dispatch 'hl.dsp.exit()'"))
bind(mod("E"),              hl.dsp.exec_cmd(fileManager))
bind(mod("V"),              hl.dsp.exec_cmd("cliphist list | rofi -dmenu -p clipboard -display-columns 2 | cliphist decode | wl-copy")) -- historial del portapapeles
bind(mod("SHIFT + V"),      hl.dsp.window.float({ action = "toggle" }))
bind(mod("Space"),          hl.dsp.exec_cmd(scripts .. "SwitchLayout.sh")) -- alternar us / latam + notificación
bind(mod("J"),              hl.dsp.layout("togglesplit")) -- dwindle
bind(mod("R"),              hl.dsp.exec_cmd(menu))
bind(mod("SHIFT + R"),      hl.dsp.exec_cmd(scripts .. "wbrestart.sh"))
bind(mod("O"),              hl.dsp.exec_cmd(scripts .. "reload-all.sh")) -- recargar Hyprland + swaync + waybar
bind(mod("K"),              hl.dsp.exec_cmd("pavucontrol"))  -- control de sonido
bind(mod("M"),              hl.dsp.exec_cmd(scripts .. "mic-mute.sh")) -- mute micrófono + notificación
bind(mod("B"),              hl.dsp.exec_cmd("librewolf")) -- browser
bind(mod("N"),              hl.dsp.exec_cmd("google-chrome-stable")) -- Google Chrome
bind(mod("L"),              hl.dsp.exec_cmd("pidof hyprlock || hyprlock")) -- bloquear pantalla
bind(mod("F"),              hl.dsp.window.fullscreen())
bind(mod("P"),              hl.dsp.exec_cmd(scripts .. "screenshot.sh"))
bind(mod("W"),              hl.dsp.exec_cmd(scripts .. "wppicker.sh"))
bind(mod("SHIFT + Q"),      hl.dsp.exec_cmd(scripts .. "KillActiveProcess.sh"))
bind(mod("SHIFT + C"),      hl.dsp.exec_cmd("hyprpicker -a"))
bind(mod("CTRL + B"),       hl.dsp.exec_cmd(scripts .. "WaybarStyles.sh")) -- Waybar Styles Menu
bind(mod("ALT + B"),        hl.dsp.exec_cmd(scripts .. "WaybarLayout.sh")) -- Waybar Layout Menu
bind(mod("H"),              hl.dsp.exec_cmd("pkill -SIGUSR1 waybar"))      -- Hide Waybar
bind(mod("SHIFT + E"),      hl.dsp.exec_cmd("kitty yazi"))                 -- Yazi File Manager

-- mainMod + left/right: workspace anterior/siguiente
-- mainMod + SHIFT + left/right: mover ventana al workspace anterior/siguiente
bind(mod("left"),          hl.dsp.focus({ workspace = "r-1" }))
bind(mod("right"),         hl.dsp.focus({ workspace = "r+1" }))
bind(mod("SHIFT + left"),  hl.dsp.window.move({ workspace = "r-1" }))
bind(mod("SHIFT + right"), hl.dsp.window.move({ workspace = "r+1" }))

-- mainMod + up/down: mover foco
bind(mod("up"),   hl.dsp.focus({ direction = "up" }))
bind(mod("down"), hl.dsp.focus({ direction = "down" }))

-- mainMod + CTRL + arrows: mover ventana; mainMod + ALT + arrows: redimensionar
local resizeStep = {
    left  = { x = -50, y = 0 },
    right = { x = 50,  y = 0 },
    up    = { x = 0,   y = -50 },
    down  = { x = 0,   y = 50 },
}

for dir, step in pairs(resizeStep) do
    bind(mod("CTRL + " .. dir), hl.dsp.window.move({ direction = dir }))
    bind(mod("ALT + " .. dir),  hl.dsp.window.resize({ x = step.x, y = step.y, relative = true }), { repeating = true })
end

-- Switch workspaces with mainMod + [0-9]
-- Move active window to a workspace with mainMod + SHIFT + [0-9]
for i = 1, 10 do
    local key = i % 10 -- 10 maps to key 0
    bind(mod(key),              hl.dsp.focus({ workspace = i }))
    bind(mod("SHIFT + " .. key), hl.dsp.window.move({ workspace = i }))
end

-- Workspace especial (scratchpad): SUPER+S lo muestra/oculta.
-- SUPER+SHIFT+S manda la ventana activa al especial (recordando de dónde vino);
-- si la ventana ya está en el especial, la devuelve a ese workspace.
bind(mod("S"),         hl.dsp.workspace.toggle_special("magic"))
bind(mod("SHIFT + S"), hl.dsp.exec_cmd(scripts .. "special-move.sh"))

-- Scroll through existing workspaces with mainMod + scroll
bind(mod("mouse_down"), hl.dsp.focus({ workspace = "e+1" }))
bind(mod("mouse_up"),   hl.dsp.focus({ workspace = "e-1" }))

-- Move/resize windows with mainMod + LMB/RMB and dragging
bind(mod("mouse:272"), hl.dsp.window.drag(),   { mouse = true })
bind(mod("mouse:273"), hl.dsp.window.resize(), { mouse = true })

-- Laptop multimedia keys for volume and LCD brightness
local el = { locked = true, repeating = true }
bind("XF86AudioRaiseVolume",  hl.dsp.exec_cmd(scripts .. "volume.sh --inc"), el)
bind("XF86AudioLowerVolume",  hl.dsp.exec_cmd(scripts .. "volume.sh --dec"), el)
bind("XF86AudioMute",         hl.dsp.exec_cmd(scripts .. "volume.sh --toggle"), el)
bind("XF86AudioMicMute",      hl.dsp.exec_cmd(scripts .. "mic-mute.sh"), el)
bind("XF86MonBrightnessUp",   hl.dsp.exec_cmd(scripts .. "brightness.sh --inc"), el)
bind("XF86MonBrightnessDown", hl.dsp.exec_cmd(scripts .. "brightness.sh --dec"), el)

-- Requires playerctl
bind("XF86AudioNext",  hl.dsp.exec_cmd("playerctl next"),       { locked = true })
bind("XF86AudioPause", hl.dsp.exec_cmd("playerctl play-pause"), { locked = true })
bind("XF86AudioPlay",  hl.dsp.exec_cmd("playerctl play-pause"), { locked = true })
bind("XF86AudioPrev",  hl.dsp.exec_cmd("playerctl previous"),   { locked = true })

-- autoscroll.py: tell the daemon when Shift is held, so Shift + middle-click
-- passes through as a normal middle click (close tab, paste...)
local ctl = 'nc -UuN -w1 "$XDG_RUNTIME_DIR/autoscroll-ctl.sock"'
for _, key in ipairs({ "Shift_L", "Shift_R" }) do
    bind(key, hl.dsp.exec_cmd("printf shift1 | " .. ctl),
         { non_consuming = true, ignore_mods = true, locked = true })
    bind(key, hl.dsp.exec_cmd("printf shift0 | " .. ctl),
         { non_consuming = true, ignore_mods = true, locked = true, release = true })
end
