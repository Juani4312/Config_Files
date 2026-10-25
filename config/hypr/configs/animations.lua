hl.config({
    animations = {
        enabled = true,
    },
})

local function bezier(name, x1, y1, x2, y2)
    hl.curve(name, { type = "bezier", points = { {x1, y1}, {x2, y2} } })
end

bezier("myBezier",   0.05, 0.9,  0.1,  1.05)
bezier("been",       0.24, 0.9,  0.25, 0.91)
bezier("been2",      0,    0.94, 0.5,  0.99)
bezier("menu_decel", 0.1,  1,    0,    1)
bezier("linear",     0.0,  0.0,  1.0,  1.0)
bezier("wind",       0.05, 0.9,  0.1,  1.05)
bezier("winIn",      0.1,  1.1,  0.1,  1.1)
bezier("winOut",     0.3,  -0.3, 0,    1)
bezier("slow",       0,    0.85, 0.3,  1)
bezier("overshot",   0.7,  0.6,  0.1,  1.1)
bezier("bounce",     1.1,  1.6,  0.1,  0.85)
bezier("sligshot",   1,    -1,   0.15, 1.25)

hl.animation({ leaf = "windowsIn",   enabled = true, speed = 5, bezier = "slow",     style = "popin" })
hl.animation({ leaf = "windowsOut",  enabled = true, speed = 7, bezier = "been",     style = "popin 70%" })
hl.animation({ leaf = "windowsMove", enabled = true, speed = 5, bezier = "wind",     style = "slide" })
hl.animation({ leaf = "border",      enabled = true, speed = 1, bezier = "linear" })
hl.animation({ leaf = "fade",        enabled = true, speed = 5, bezier = "overshot" })
hl.animation({ leaf = "workspaces",  enabled = true, speed = 5, bezier = "wind" })
hl.animation({ leaf = "windows",     enabled = true, speed = 5, bezier = "bounce",   style = "popin" })
