#!/usr/bin/env python3
"""Genera los cuadros del parlante (glifos FA de JetBrainsMono Nerd Font) como
íconos simbólicos SVG, para animarlos desde el CSS de waybar con
-gtk-icontheme(): GTK los pinta con el `color` del widget (= color del tema).
Todos comparten el mismo viewBox, así el parlante no se mueve entre cuadros."""
import os
import gi
gi.require_version("Pango", "1.0"); gi.require_version("PangoCairo", "1.0")
from gi.repository import Pango, PangoCairo
import cairo

OUT = os.path.expanduser("~/.local/share/icons/hicolor/scalable/status")
FRAMES = {"waybar-spk-0-symbolic": "", "waybar-spk-1-symbolic": "",
          "waybar-spk-2-symbolic": ""}
SIZE = 100  # px de fuente para generar (el SVG escala)

surf = cairo.RecordingSurface(cairo.CONTENT_COLOR_ALPHA, None)
cr = cairo.Context(surf)
fd = Pango.FontDescription(f"JetBrainsMono Nerd Font Bold {SIZE}px")
paths, box = {}, None
for name, ch in FRAMES.items():
    cr.new_path()
    l = PangoCairo.create_layout(cr); l.set_font_description(fd); l.set_text(ch, -1)
    cr.move_to(0, 0); PangoCairo.layout_path(cr, l)
    x1, y1, x2, y2 = cr.fill_extents()
    box = (x1, y1, x2, y2) if box is None else (min(box[0], x1), min(box[1], y1),
                                               max(box[2], x2), max(box[3], y2))
    d = []
    for t, pts in cr.copy_path():
        if t == cairo.PATH_MOVE_TO: d.append("M%.2f %.2f" % pts)
        elif t == cairo.PATH_LINE_TO: d.append("L%.2f %.2f" % pts)
        elif t == cairo.PATH_CURVE_TO: d.append("C%.2f %.2f %.2f %.2f %.2f %.2f" % pts)
        elif t == cairo.PATH_CLOSE_PATH: d.append("Z")
    paths[name] = " ".join(d)
x1, y1, x2, y2 = box
w, h = x2 - x1, y2 - y1
for name, d in paths.items():
    with open(os.path.join(OUT, name + ".svg"), "w") as f:
        f.write(f'<svg xmlns="http://www.w3.org/2000/svg" width="{w:.2f}" height="{h:.2f}" '
                f'viewBox="{x1:.2f} {y1:.2f} {w:.2f} {h:.2f}">'
                f'<path fill="#bebebe" d="{d}"/></svg>\n')
print(f"ok {w:.2f}x{h:.2f} (ratio {w/h:.3f}) -> {OUT}")
