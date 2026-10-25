local tags = {
    { tag = "+multimedia_video", class = "^([Mm]pv|vlc)$" },
    { tag = "+settings",         class = "^(nm-applet|nm-connection-editor|blueman-manager|org.gnome.FileRoller)$" },
    { tag = "+settings",         class = "^(org.gnome.DiskUtility|wihotspot(-gui)?)$" },
    { tag = "+viewer",           class = "^(org.gnome.SystemMonitor)$" }, -- system monitor
    { tag = "+viewer",           class = "^(org.gnome.Evince)$" },        -- document viewer
    { tag = "+viewer",           class = "^(eog|org.gnome.Loupe)$" },     -- image viewer
}

for _, t in ipairs(tags) do
    hl.window_rule({ match = { class = t.class }, tag = t.tag })
end
