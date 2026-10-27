#!/usr/bin/env python3
"""
Genera rules-client.css (CSS del cliente) y rules-web.css (tienda/comunidad):
recorre el CSS de Steam y, por cada declaracion
que use un color de la paleta de Steam, emite la misma regla con el color
reemplazado por una variable de matugen (--m-*). Los valores de las variables
los define colors.css (template de matugen); build.sh arma el tema de Millennium.

Volver a correrlo si una actualizacion de Steam cambia los nombres de clases.
"""
import colorsys
import os
import re
import sys
import urllib.request

STEAMUI = os.path.expanduser("~/.local/share/Steam/steamui/css")
HERE = os.path.dirname(os.path.abspath(__file__))
OUT_CLIENT = os.path.join(HERE, "rules-client.css")
OUT_WEB = os.path.join(HERE, "rules-web.css")
# paginas web que Steam muestra dentro del cliente: se baja el CSS que enlazan
WEB_PAGES = [
    "https://store.steampowered.com/",
    "https://store.steampowered.com/app/620/",
    "https://steamcommunity.com/",
]
UA = {"User-Agent": "Mozilla/5.0 Valve Steam Client", "Cookie": "birthtime=0; lastagecheckage=1-0-1990"}

# selectores de Big Picture / teclado virtual / tienda de puntos: no aplican al escritorio
SKIP_SELECTOR = re.compile(r"KeyTheme_|Layout_|\.Spectrum|\.GamepadMode|\.TestChamber|\.DEX\b|\.Candy\b")
COLOR_PROPS = re.compile(
    r"^(color|background(-color|-image)?|border(-top|-right|-bottom|-left)?(-color)?|"
    r"outline(-color)?|box-shadow|fill|stroke|caret-color|text-decoration-color|"
    r"scrollbar-color|--[\w-]+)$"
)
COLOR_RE = re.compile(
    r"#[0-9a-fA-F]{8}\b|#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3}\b|"
    r"rgba?\(\s*[\d.]+%?\s*[, ]\s*[\d.]+%?\s*[, ]\s*[\d.]+%?\s*(?:[,/]\s*[\d.]+%?\s*)?\)"
)


def parse_color(tok):
    tok = tok.strip()
    if tok.startswith("#"):
        h = tok[1:]
        if len(h) == 3:
            h = "".join(c * 2 for c in h)
        r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
        a = int(h[6:8], 16) / 255 if len(h) == 8 else 1.0
        return r, g, b, a
    nums = re.findall(r"[\d.]+%?", tok)
    vals = []
    for n in nums[:3]:
        vals.append(float(n[:-1]) * 2.55 if n.endswith("%") else float(n))
    a = 1.0
    if len(nums) > 3:
        n = nums[3]
        a = float(n[:-1]) / 100 if n.endswith("%") else float(n)
    return (*vals, a)


def role_for(r, g, b, prop):
    h, l, s = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
    hue = h * 360
    if l < 0.025:
        return None  # negro: sombras y overlays, se deja igual
    if l > 0.97:
        return "on-surface"
    neutral = s < 0.2 or (s < 0.45 and l < 0.3)
    if neutral:
        for limit, role in (
            (0.07, "surface-lowest"), (0.11, "surface-dim"), (0.15, "surface-low"),
            (0.20, "surface-container"), (0.25, "surface-high"), (0.33, "surface-highest"),
            (0.45, "outline-variant"), (0.60, "outline"), (0.80, "on-surface-variant"),
        ):
            if l <= limit:
                return role
        return "on-surface"
    if l >= 0.8 and prop == "color":
        return "on-surface"
    if l >= 0.8 and prop in ("fill", "stroke"):
        # tintes palidos: Steam los usa para iconos sobre botones de acento
        if 170 <= hue <= 250:
            return "on-primary"
        if 60 <= hue < 170:
            return "on-tertiary"
    if s >= 0.25 and 170 <= hue <= 250:
        return "primary-container" if l < 0.3 else "primary"
    if s >= 0.25 and 60 <= hue < 170:
        return "tertiary-container" if l < 0.3 else "tertiary"
    if s >= 0.5 and (hue < 15 or hue > 345):
        return "error"
    return None


def recolor(value, prop):
    changed = False
    roles = {}

    def sub(m):
        nonlocal changed
        r, g, b, a = parse_color(m.group(0))
        role = role_for(r, g, b, prop)
        if role is None and max(r, g, b) < 8 and a >= 0.999 and prop in ("background", "background-color"):
            # fondos negros opacos (p.ej. la raiz de la ventana): tono mas oscuro del sistema
            role = "surface-lowest"
        if role is None:
            return m.group(0)
        changed = True
        roles.setdefault(role)
        if a >= 0.999:
            return f"var(--m-{role})"
        return f"color-mix(in srgb, var(--m-{role}) {a * 100:.0f}%, transparent)"

    out = COLOR_RE.sub(sub, value)
    if changed and "gradient" in value and COLOR_RE.search(out):
        first = next(iter(roles))

        def fill(m):
            r, g, b, a = parse_color(m.group(0))
            if max(r, g, b) < 8:
                return m.group(0)
            return f"color-mix(in srgb, var(--m-{first}) {a * 100:.0f}%, transparent)"

        out = COLOR_RE.sub(fill, out)
    return (out if changed else None), roles


PLAIN_COLOR = re.compile(rf"transparent|none|{COLOR_RE.pattern}", re.I)
MIXED = re.compile(r"var\(--m-[\w-]+\)|color-mix\(in srgb, var\(--m-[\w-]+\) \d+%, transparent\)")


def narrow(prop, value):
    """Pasa shorthands a su longhand de color, para que el !important no pise
    background-image, anchos de borde, etc. definidos en otras reglas."""
    if prop == "background":
        if MIXED.fullmatch(value):
            return "background-color", value
        if "url(" not in value and value.startswith(("linear-gradient", "radial-gradient")):
            return "background-image", value
        return prop, value
    if re.fullmatch(r"(border(-top|-right|-bottom|-left)?|outline)", prop):
        found = MIXED.findall(value)
        if len(found) != 1:
            return None, None
        return f"{prop}-color", found[0]
    return prop, value


def split_top(s, sep):
    parts, depth, cur, esc = [], 0, [], False
    for ch in s:
        if esc or ch == "\\":
            # caracter escapado (p.ej. "\\," dentro de un nombre de clase): no es separador
            esc = not esc
            cur.append(ch)
            continue
        if ch in "([":
            depth += 1
        elif ch in ")]":
            depth -= 1
        if ch == sep and depth == 0:
            parts.append("".join(cur))
            cur = []
        else:
            cur.append(ch)
    parts.append("".join(cur))
    return parts


def skip_string(css, k):
    """Devuelve el indice de la comilla que cierra el string que empieza en k."""
    q, k = css[k], k + 1
    while k < len(css) and css[k] != q:
        k += 2 if css[k] == "\\" else 1
    return k


def blocks(css):
    """Itera (prelude, body) de nivel superior respetando llaves anidadas,
    strings, url() y caracteres escapados (Steam usa selectores como .KeyTheme_\\{)."""
    i, n = 0, len(css)
    start, depth, open_at = 0, 0, 0
    while i < n:
        c = css[i]
        if c == "\\":
            i += 2
            continue
        if c in "\"'":
            i = skip_string(css, i)
        elif css.startswith("url(", i):
            i = css.find(")", i)
        elif c == "{":
            if depth == 0:
                open_at = i
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                yield css[start:open_at].strip(), css[open_at + 1:i]
                start = i + 1
        i += 1


def process(css):
    out = []
    for prelude, body in blocks(css):
        # declaraciones sueltas antes de un bloque (p.ej. @charset;) quedan en el prelude
        if ";" in prelude and not prelude.startswith("@"):
            prelude = prelude.rsplit(";", 1)[-1].strip()
        if prelude.startswith("@"):
            if prelude.startswith(("@media", "@supports", "@container", "@layer")):
                if "prefers-contrast" in prelude or "prefers-color-scheme: light" in prelude:
                    continue
                inner = process(body)
                if inner:
                    out.append(f"{prelude}{{{''.join(inner)}}}")
            continue
        sels = [x.strip() for x in split_top(prelude, ",") if x.strip() and not SKIP_SELECTOR.search(x)
                and not (x.strip().startswith(":") and not x.strip().startswith(":root"))]
        if not sels:
            continue
        decls, bg_primary, has_color = [], False, False
        for d in split_top(body, ";"):
            if ":" not in d:
                continue
            prop, val = d.split(":", 1)
            prop = prop.strip()
            if not COLOR_PROPS.match(prop.lower()):
                continue
            val = val.replace("!important", "").strip()
            new, roles = recolor(val, prop)
            if new is None:
                if prop in ("background", "background-color") and PLAIN_COLOR.fullmatch(val):
                    # fondo que Steam deja sin pintar (p.ej. ".X.X{background-color:transparent}"
                    # para resetear ".X{background-color:#141414}"): se re-emite tal cual para que
                    # la cascada entre reglas !important siga igual que en Steam
                    decls.append(["background-color", "transparent" if val.lower() == "none" else val])
                continue
            if prop.startswith("background") and "primary" in roles:
                bg_primary = True
            if prop == "color":
                has_color = True
            prop, new = narrow(prop, new)
            if prop is None:
                continue
            decls.append([prop, new])
        if bg_primary:
            # texto sobre fondo de acento: usar on-primary para mantener contraste
            for d in decls:
                if d[0] == "color" and "primary)" not in d[1]:
                    d[1] = "var(--m-on-primary)"
            if not has_color:
                decls.append(["color", "var(--m-on-primary)"])
        if decls:
            body_out = ";".join(f"{p}:{v} !important" for p, v in decls)
            out.append(f"{','.join(sels)}{{{body_out}}}")
    return out


def fetch(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read().decode("utf-8", "replace")


def web_sources():
    seen = []
    for page in WEB_PAGES:
        try:
            html = fetch(page)
        except OSError as e:
            print(f"no se pudo bajar {page}: {e}", file=sys.stderr)
            continue
        for href in re.findall(r'<link[^>]+href="([^"]+\.css[^"]*)"', html):
            href = href.replace("&amp;", "&")
            name = href.split("?")[0].split("/public/", 1)[-1]
            if "steamstatic.com" in href and "jquery-ui" not in name and name not in [n for n, _ in seen]:
                seen.append((name, href))
    for name, href in seen:
        try:
            yield name, fetch(href)
        except OSError as e:
            print(f"no se pudo bajar {href}: {e}", file=sys.stderr)


def write(path, sources):
    rules = []
    for name, css in sources:
        css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
        rules.append(f"/* {name} */")
        rules.extend(process(css))
    with open(path, "w") as fh:
        fh.write("/* generado por generate.py, no editar a mano */\n")
        fh.write("\n".join(rules) + "\n")
    print(f"{path}: {os.path.getsize(path) // 1024} KiB, {len(rules)} reglas", file=sys.stderr)


def main():
    files = sorted(f for f in os.listdir(STEAMUI) if f.endswith(".css"))
    write(OUT_CLIENT, [(f, open(os.path.join(STEAMUI, f), encoding="utf-8", errors="replace").read()) for f in files])
    if "--no-web" not in sys.argv:
        write(OUT_WEB, list(web_sources()))


if __name__ == "__main__":
    main()
