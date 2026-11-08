#!/usr/bin/env python3
"""
build.py - generates the "Matu" cursor theme from the matugen palette.

Draws every cursor as SVG, then builds:
  * Xcursor files   (~/.local/share/icons/Matu/cursors)  -> GTK/Qt/XWayland
  * hyprcursor      (~/.local/share/icons/Matu/hyprcursors) -> Hyprland (SVG, crisp)

Usage:  build.py [--apply] [--preview out.png]
  --apply    hyprctl setcursor Matu <size> after building
Runs automatically from matugen (templates.cursor post_hook).
"""
import json
import math
import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile

import cairo

HERE = os.path.dirname(os.path.abspath(__file__))
THEME = "Matu"
DEST = os.path.expanduser(f"~/.local/share/icons/{THEME}")
XC_SIZES = [24, 32, 48, 64]
CURSOR_SIZE = int(os.environ.get("XCURSOR_SIZE", "24"))

# ------------------------------------------------------------------ colors --
def load_colors():
    js = os.path.join(HERE, "colors.json")
    if os.path.exists(js):
        with open(js) as f:
            return json.load(f)
    # fallback: parse the Hyprland lua palette matugen already writes
    out = {}
    with open(os.path.expanduser("~/.config/hypr/colors.lua")) as f:
        for name, hexv in re.findall(r'(\w+)\s*=\s*"rgba\(([0-9a-fA-F]{6})', f.read()):
            out[name] = "#" + hexv
    return out


C = load_colors()
FILL = C.get("surface_container_high", "#322826")   # body
OUT = C.get("on_surface", "#f1dedc")                 # rim
ACC = C.get("primary", "#ffb4a9")                    # accents
ERR = C.get("error", "#ffb4ab")
B = 1.55        # rim width (viewBox units, canvas is 32x32)

# --------------------------------------------------------------- drawing ---
# An item is (kind, svg-element-without-paint, inner-color-or-None, width)
#   kind "f": filled shape          kind "l": stroked line/curve
def F(el, color=None):
    return ("f", el, color, 0)


def L(el, w, color=None):
    return ("l", el, color, w)


def layer(items, rim=True):
    """Rim pass (union outline) then body pass, so overlapping parts merge."""
    s = []
    if rim:
        s.append(f'<g fill="{OUT}" stroke="{OUT}" stroke-linejoin="round" stroke-linecap="round">')
        for k, el, _, w in items:
            if k == "f":
                s.append(el.replace("/>", f' stroke-width="{2*B}"/>'))
            else:
                s.append(el.replace("/>", f' fill="none" stroke-width="{w+2*B}"/>'))
        s.append("</g>")
    for k, el, col, w in items:
        if k == "f":
            c = col or FILL
            s.append(el.replace("/>", f' fill="{c}" stroke="{c}" stroke-width="0.5" stroke-linejoin="round"/>'))
        else:
            c = col or FILL
            s.append(el.replace("/>", f' fill="none" stroke="{c}" stroke-width="{w}" '
                                      f'stroke-linecap="round" stroke-linejoin="round"/>'))
    return "".join(s)


def svg(*groups, transform=None):
    body = "".join(groups)
    if transform:
        body = f'<g transform="{transform}">{body}</g>'
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 32 32">'
            '<defs><filter id="sh" x="-30%" y="-30%" width="160%" height="160%">'
            '<feDropShadow dx="0" dy="0.8" stdDeviation="0.9" flood-color="#000" flood-opacity="0.45"/>'
            f'</filter></defs><g filter="url(#sh)">{body}</g></svg>')


def poly(pts):
    return '<path d="M' + " L".join(f"{x:.2f} {y:.2f}" for x, y in pts) + ' Z"/>'


# --- arrow -----------------------------------------------------------------
AX, AY = 7.0, 4.0
ARROW_PTS = [(0, 0), (0, 18), (4.6, 13.9), (7.5, 20.4), (10.5, 19.1), (7.7, 12.8), (13.6, 12.8)]


def arrow_items(dx=0.0, dy=0.0, s=1.0):
    return [F(poly([(AX + dx + x * s, AY + dy + y * s) for x, y in ARROW_PTS]))]


def badge(cx, cy, r, icon):
    """Small accent circle with a dark glyph (icon = list of items)."""
    return layer([F(f'<circle cx="{cx}" cy="{cy}" r="{r}"/>', ACC)]) + layer(icon, rim=False)


def arrow_with(badge_svg):
    return svg(layer(arrow_items()), badge_svg)


# --- hands -----------------------------------------------------------------
def rr(x, y, w, h, r=None, rot=None):
    r = w / 2 if r is None else r
    t = f' transform="rotate({rot[0]} {rot[1]} {rot[2]})"' if rot else ""
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}"{t}/>'


def creases(lines):
    return layer([L(f'<path d="M{a} {b} L{c} {d}"/>', 0.9, OUT) for a, b, c, d in lines], rim=False)


def hand_pointer():
    items = [F(rr(11.0, 2.5, 4.8, 17)),                 # index
             F(rr(15.6, 10.2, 4.5, 11)),                # middle
             F(rr(19.9, 11.6, 4.3, 10)),                # ring
             F(rr(24.0, 13.2, 4.0, 9)),                 # pinky
             F(rr(11.0, 15.0, 17.0, 13.5, 5.2)),        # palm
             F(rr(6.4, 13.8, 4.8, 10.5, None, (-40, 8.8, 23.5)))]  # thumb
    return svg(layer(items), creases([(15.8, 13.2, 15.8, 17.6), (20.0, 14.6, 20.0, 18.2),
                                      (24.1, 16.2, 24.1, 18.8)]))


def hand_open():
    items = [F(rr(9.6, 4.6, 4.4, 13, None, (-8, 11.8, 17))),
             F(rr(14.0, 3.0, 4.5, 14)),
             F(rr(18.6, 4.4, 4.3, 13, None, (6, 20.7, 17))),
             F(rr(22.8, 7.6, 4.0, 11, None, (14, 24.8, 18))),
             F(rr(9.8, 13.5, 16.6, 14.5, 5.5)),
             F(rr(5.6, 13.2, 4.6, 10, None, (-42, 7.9, 22.5)))]
    return svg(layer(items))


def hand_closed():
    items = [F(rr(10.2, 9.6, 4.4, 8)), F(rr(14.5, 9.0, 4.5, 8)),
             F(rr(18.8, 9.6, 4.3, 8)), F(rr(22.9, 11.0, 4.0, 7)),
             F(rr(9.8, 13.0, 17.2, 14.5, 5.5)),
             F(rr(6.6, 14.6, 4.6, 9, None, (-55, 8.9, 22.5)))]
    return svg(layer(items), creases([(14.6, 11.8, 14.6, 15.0), (18.9, 11.8, 18.9, 15.0),
                                      (23.0, 13.0, 23.0, 15.4)]))


# --- simple glyphs ---------------------------------------------------------
def head(tx, ty, ang, ln=5.2, wd=4.6):
    """Arrow head polygon with its tip at (tx,ty) pointing toward angle ang (deg)."""
    a = math.radians(ang)
    ux, uy = math.cos(a), math.sin(a)
    bx, by = tx - ux * ln, ty - uy * ln
    px, py = -uy * wd, ux * wd
    return F(poly([(tx, ty), (bx + px, by + py), (bx - px, by - py)]))


def double_arrow(rot):
    items = [L('<path d="M8 16 L24 16"/>', 2.2), head(3.6, 16, 180), head(28.4, 16, 0)]
    return svg(layer(items), transform=f"rotate({rot} 16 16)")


def bar_resize(rot):
    items = [L('<path d="M16 7 L16 25"/>', 2.4),
             L('<path d="M7 16 L12 16"/>', 2.0), head(3.2, 16, 180, 4.6, 4.0),
             L('<path d="M20 16 L25 16"/>', 2.0), head(28.8, 16, 0, 4.6, 4.0)]
    return svg(layer(items), transform=f"rotate({rot} 16 16)")


def move():
    items = [L('<path d="M16 8 L16 24 M8 16 L24 16"/>', 2.2),
             head(16, 3.4, -90), head(16, 28.6, 90), head(3.4, 16, 180), head(28.6, 16, 0)]
    return svg(layer(items))


def all_scroll():
    items = [F('<circle cx="16" cy="16" r="2.6"/>', ACC),
             head(16, 4.0, -90), head(16, 28.0, 90), head(4.0, 16, 180), head(28.0, 16, 0)]
    return svg(layer(items))


def ibeam(rot=0):
    items = [L('<path d="M16 8 L16 24"/>', 2.0),
             L('<path d="M12.6 6.4 Q16 6.4 16 8.6 Q16 6.4 19.4 6.4"/>', 1.8),
             L('<path d="M12.6 25.6 Q16 25.6 16 23.4 Q16 25.6 19.4 25.6"/>', 1.8)]
    return svg(layer(items), transform=f"rotate({rot} 16 16)" if rot else None)


def crosshair():
    items = [L('<path d="M16 4.5 L16 12 M16 20 L16 27.5 M4.5 16 L12 16 M20 16 L27.5 16"/>', 2.0),
             F('<circle cx="16" cy="16" r="1.5"/>', ACC)]
    return svg(layer(items))


def cell():
    items = [L('<path d="M16 7 L16 25 M7 16 L25 16"/>', 4.4)]
    return svg(layer(items))


def not_allowed():
    items = [L('<circle cx="16" cy="16" r="8.6"/>', 3.0),
             L('<path d="M10 22 L22 10"/>', 3.0)]
    return svg(layer(items), layer([L('<circle cx="16" cy="16" r="8.6"/>', 1.2, ERR),
                                    L('<path d="M10 22 L22 10"/>', 1.2, ERR)], rim=False))


def zoom(plus):
    glyph = "M9.6 13 L16.4 13" + (" M13 9.6 L13 16.4" if plus else "")
    items = [L('<path d="M18.6 18.6 L25.6 25.6"/>', 3.6),
             F('<circle cx="13" cy="13" r="7.6"/>')]
    return svg(layer(items), layer([L(f'<path d="{glyph}"/>', 1.8, ACC)], rim=False))


def spinner(frame, n, cx=16.0, cy=16.0, r=8.0, w=3.4, standalone=True):
    a0 = frame / n * 2 * math.pi
    a1 = a0 + 2 * math.pi * 0.32
    p0 = (cx + r * math.cos(a0), cy + r * math.sin(a0))
    p1 = (cx + r * math.cos(a1), cy + r * math.sin(a1))
    arc = f'<path d="M{p0[0]:.2f} {p0[1]:.2f} A{r} {r} 0 0 1 {p1[0]:.2f} {p1[1]:.2f}"/>'
    g = layer([L(f'<circle cx="{cx}" cy="{cy}" r="{r}"/>', w)]) + \
        layer([L(arc, w * 0.62, ACC)], rim=False)
    return svg(g) if standalone else g


def progress(frame, n):
    return svg(layer(arrow_items()), spinner(frame, n, 22.6, 22.6, 4.6, 2.6, standalone=False))


def glyph_q():
    return [L('<path d="M20.4 20.4 Q20.4 18.4 22.4 18.4 Q24.4 18.4 24.4 20.2 '
              'Q24.4 21.5 22.4 22.3 L22.4 23.3"/>', 1.5, FILL),
            F('<circle cx="22.4" cy="25.6" r="0.9"/>', FILL)]


def glyph_plus():
    return [L('<path d="M22.4 19.2 L22.4 25.6 M19.2 22.4 L25.6 22.4"/>', 1.6, FILL)]


def glyph_link():
    return [L('<path d="M19.6 25 L19.6 22.6 Q19.6 20.4 22 20.4 L25 20.4"/>', 1.4, FILL),
            F(poly([(25.9, 20.4), (23.6, 18.5), (23.6, 22.3)]), FILL)]


def glyph_menu():
    return [L('<path d="M19.8 20 L25 20 M19.8 22.4 L25 22.4 M19.8 24.8 L25 24.8"/>', 1.2, FILL)]


def glyph_no():
    return [L('<circle cx="22.4" cy="22.4" r="3.1"/>', 1.3, FILL),
            L('<path d="M20.2 24.6 L24.6 20.2"/>', 1.3, FILL)]


# --------------------------------------------------------------- catalog ---
SPIN_N = 16
SPIN_MS = 45

def frames(fn):
    return [fn(i, SPIN_N) for i in range(SPIN_N)]


ARROW_HOT = (AX, AY)
CENTER = (16, 16)

# name: (svg or list-of-frame-svgs, hotspot, [aliases])
CURSORS = {
    "default":      (svg(layer(arrow_items())), ARROW_HOT,
                     ["left_ptr", "arrow", "top_left_arrow", "dnd-move", "dnd-none", "center_ptr",
                      "right_ptr", "draft", "pencil", "wayland-cursor", "x-cursor", "X_cursor"]),
    "pointer":      (hand_pointer(), (13.4, 2.6), ["hand2", "hand1", "pointing_hand", "hand",
                                                  "9d800788f1b08800ae810202380a0822",
                                                  "e29285e634086352946a0e7090d73106"]),
    "grab":         (hand_open(), CENTER, ["openhand", "fleur_open", "5aca4d189052212118709018842178c0"]),
    "grabbing":     (hand_closed(), CENTER, ["closedhand", "dnd_move", "208530c400c041818281048008011002"]),
    "text":         (ibeam(), CENTER, ["xterm", "ibeam"]),
    "vertical-text":(ibeam(90), CENTER, []),
    "crosshair":    (crosshair(), CENTER, ["cross", "tcross", "cross_reverse", "diamond_cross", "target"]),
    "cell":         (cell(), CENTER, ["plus"]),
    "move":         (move(), CENTER, ["fleur", "size_all", "pointer_move",
                                      "4498f0e0c1937ffe01fd06f973665830",
                                      "9081237383d90e509aa00f00170e968f"]),
    "all-scroll":   (all_scroll(), CENTER, []),
    "not-allowed":  (not_allowed(), CENTER, ["crossed_circle", "forbidden", "circle",
                                             "03b6e0fcb3499374a867c041f52298f0"]),
    "no-drop":      (arrow_with(badge(22.4, 22.4, 5.4, glyph_no())), ARROW_HOT, ["dnd_no_drop", "dnd-no-drop"]),
    "help":         (arrow_with(badge(22.4, 22.4, 5.6, glyph_q())), ARROW_HOT,
                     ["question_arrow", "whats_this", "left_ptr_help", "dnd-ask",
                      "5c6cd98b3f3ebcb1f9c7f1c204630408", "d9ce0ab605698f320427677b458ad60b"]),
    "copy":         (arrow_with(badge(22.4, 22.4, 5.4, glyph_plus())), ARROW_HOT,
                     ["dnd-copy", "1081e37283d90000800003c07f3ef6bf", "6407b0e94181790501fd1e167b474872"]),
    "alias":        (arrow_with(badge(22.4, 22.4, 5.4, glyph_link())), ARROW_HOT,
                     ["link", "dnd-link", "3085a0e285430894940527032f8b26df",
                      "640fb0e74195791501fd1ed57b41487f"]),
    "context-menu": (arrow_with(badge(22.4, 22.4, 5.4, glyph_menu())), ARROW_HOT, []),
    "zoom-in":      (zoom(True), (13, 13), []),
    "zoom-out":     (zoom(False), (13, 13), []),
    "ew-resize":    (double_arrow(0), CENTER,
                     ["e-resize", "w-resize", "sb_h_double_arrow", "h_double_arrow", "size_hor",
                      "size-hor", "left_side", "right_side", "028006030e0e7ebffc7f7070c0600140",
                      "14fef782d02440884392942c1120523"]),
    "ns-resize":    (double_arrow(90), CENTER,
                     ["n-resize", "s-resize", "sb_v_double_arrow", "v_double_arrow", "size_ver",
                      "size-ver", "top_side", "bottom_side", "double_arrow",
                      "00008160000006810000408080010102", "2870a09082c103050810ffdffffe0204"]),
    "nwse-resize":  (double_arrow(45), CENTER,
                     ["nw-resize", "se-resize", "size_fdiag", "fd_double_arrow", "top_left_corner",
                      "bottom_right_corner", "c7088f0f3e6c8088236ef8e1e3e70000"]),
    "nesw-resize":  (double_arrow(-45), CENTER,
                     ["ne-resize", "sw-resize", "size_bdiag", "bd_double_arrow", "top_right_corner",
                      "bottom_left_corner", "fcf1c3c7cd4491d801f1e1c78f100000"]),
    "col-resize":   (bar_resize(0), CENTER, ["split_h", "sb_h_double_arrow_bar",
                                             "14fef782d02440884392942c1120523"]),
    "row-resize":   (bar_resize(90), CENTER, ["split_v", "2870a09082c103050810ffdffffe0204"]),
    "wait":         (frames(lambda i, n: spinner(i, n)), CENTER, ["watch"]),
    "progress":     (frames(progress), ARROW_HOT,
                     ["left_ptr_watch", "half-busy", "08e8e1c95fe2fc01f976f1e063a24ccd",
                      "3ecb610c1bf2410f44200f48c40d3599"]),
}


# ---------------------------------------------------------------- output ---
def rasterize(svg_text, size, tmp):
    src = os.path.join(tmp, "in.svg")
    png = os.path.join(tmp, "out.png")
    with open(src, "w") as f:
        f.write(svg_text)
    subprocess.run(["rsvg-convert", "-w", str(size), "-h", str(size), src, "-o", png], check=True)
    surf = cairo.ImageSurface.create_from_png(png)   # premultiplied ARGB32 = Xcursor pixels
    w, h, stride = surf.get_width(), surf.get_height(), surf.get_stride()
    data = bytes(surf.get_data())
    rows = b"".join(data[y * stride: y * stride + w * 4] for y in range(h))
    return w, h, rows


def write_xcursor(path, images):
    """images: list of (nominal, w, h, xhot, yhot, delay, pixels)."""
    n = len(images)
    hdr = struct.pack("<4sIII", b"Xcur", 16, 0x10000, n)
    pos = 16 + n * 12
    toc, chunks = b"", b""
    for nom, w, h, xh, yh, delay, px in images:
        toc += struct.pack("<III", 0xFFFD0002, nom, pos)
        chunk = struct.pack("<IIIIIIIII", 36, 0xFFFD0002, nom, 1, w, h, xh, yh, delay) + px
        chunks += chunk
        pos += len(chunk)
    with open(path, "wb") as f:
        f.write(hdr + toc + chunks)


def build(dest):
    tmp = tempfile.mkdtemp(prefix="matu-cursor-")
    try:
        stage = os.path.join(tmp, "stage")
        xdir = os.path.join(stage, "cursors")
        hsrc = os.path.join(tmp, "hsrc")
        os.makedirs(xdir)
        os.makedirs(os.path.join(hsrc, "hyprcursors"))
        with open(os.path.join(hsrc, "manifest.hl"), "w") as f:
            f.write(f"name = {THEME}\ndescription = Rounded cursors from the matugen palette\n"
                    f"version = 1\ncursors_directory = hyprcursors\n")

        written = set()
        for name, (art, (hx, hy), aliases) in CURSORS.items():
            svgs = art if isinstance(art, list) else [art]
            delay = SPIN_MS if len(svgs) > 1 else 0
            # xcursor
            imgs = []
            for size in XC_SIZES:
                k = size / 32
                for s in svgs:
                    w, h, px = rasterize(s, size, tmp)
                    imgs.append((size, w, h, round(hx * k), round(hy * k), delay, px))
            write_xcursor(os.path.join(xdir, name), imgs)
            written.add(name)
            for a in aliases:
                if a not in written:
                    os.symlink(name, os.path.join(xdir, a))
                    written.add(a)
            # hyprcursor (svg)
            d = os.path.join(hsrc, "hyprcursors", name)
            os.makedirs(d)
            meta = [f"hotspot_x = {hx/32:.4f}", f"hotspot_y = {hy/32:.4f}", "nominal_size = 1.0"]
            meta += [f"define_override = {a}" for a in aliases]
            for i, s in enumerate(svgs):
                fn = f"{name}_{i:02d}.svg"
                with open(os.path.join(d, fn), "w") as f:
                    f.write(s)
                meta.append(f"define_size = 0, {fn}" + (f", {delay}" if delay else ""))
            with open(os.path.join(d, "meta.hl"), "w") as f:
                f.write("\n".join(meta) + "\n")

        hout = os.path.join(tmp, "hout")
        os.makedirs(hout)
        subprocess.run(["hyprcursor-util", "--create", hsrc, "--output", hout],
                       check=True, stdout=subprocess.DEVNULL)
        built = os.path.join(hout, f"theme_{THEME}")
        shutil.copy(os.path.join(built, "manifest.hl"), stage)
        shutil.copytree(os.path.join(built, "hyprcursors"), os.path.join(stage, "hyprcursors"))
        with open(os.path.join(stage, "index.theme"), "w") as f:
            f.write(f"[Icon Theme]\nName={THEME}\nComment=Rounded cursors from the matugen palette\n"
                    f"Inherits=Adwaita\n")
        # swap in atomically-ish
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        old = dest + ".old"
        shutil.rmtree(old, ignore_errors=True)
        if os.path.exists(dest):
            os.rename(dest, old)
        shutil.move(stage, dest)
        shutil.rmtree(old, ignore_errors=True)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def preview(path):
    """Contact sheet of every cursor at 48px on a light and a dark strip."""
    tmp = tempfile.mkdtemp()
    names = list(CURSORS)
    cell_, cols = 64, 9
    rows = math.ceil(len(names) / cols)
    W, H = cols * cell_, rows * cell_ * 2
    out = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    cr = cairo.Context(out)
    cr.set_source_rgb(0.95, 0.95, 0.95); cr.rectangle(0, 0, W, H / 2); cr.fill()
    cr.set_source_rgb(0.10, 0.07, 0.06); cr.rectangle(0, H / 2, W, H / 2); cr.fill()
    for i, n in enumerate(names):
        art = CURSORS[n][0]
        s = art[3] if isinstance(art, list) else art
        src = os.path.join(tmp, "p.svg"); png = os.path.join(tmp, "p.png")
        open(src, "w").write(s)
        subprocess.run(["rsvg-convert", "-w", "48", "-h", "48", src, "-o", png], check=True)
        img = cairo.ImageSurface.create_from_png(png)
        x, y = (i % cols) * cell_ + 8, (i // cols) * cell_ + 8
        for off in (0, H / 2):
            cr.set_source_surface(img, x, y + off); cr.paint()
    out.write_to_png(path)
    shutil.rmtree(tmp, ignore_errors=True)


def main():
    args = sys.argv[1:]
    if "--preview" in args:
        preview(args[args.index("--preview") + 1])
        return
    build(DEST)
    print(f"built {THEME} -> {DEST}")
    if "--apply" in args:
        subprocess.run(["hyprctl", "setcursor", THEME, str(CURSOR_SIZE)], stdout=subprocess.DEVNULL)


if __name__ == "__main__":
    main()
