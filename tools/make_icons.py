#!/usr/bin/env python3
"""Draw the QTask icons: a ball-and-stick molecule in the shape of a check mark, in an electron
cloud, on deep blue. Writes src/static/icons/:

  qtask.svg                      master drawing (also used as the SVG favicon)
  apple-touch-icon.png           180 px, full bleed (iOS and Safari on the Mac round the corners)
  control-center-192/512.png     rounded tile with a margin, for browsers that do not round icons
  control-center-512-maskable    full bleed with the molecule inside the safe zone
  <suite>-192/512(-maskable).png the suite icons, recoloured to the blue gradient

Needs Playwright with Chromium (for the SVG) and Pillow.   python3 tools/make_icons.py
"""
import io, os
from PIL import Image
from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "src", "static", "icons")

DEFS = '''<defs>
<linearGradient id="bond" x1="0" y1="1" x2="1" y2="0"><stop offset="0" stop-color="#5EF2D6"/><stop offset=".5" stop-color="#4DB4FF"/><stop offset="1" stop-color="#6A7DFF"/></linearGradient>
<radialGradient id="bg" cx=".32" cy=".2" r="1.05"><stop offset="0" stop-color="#1D4A82"/><stop offset=".5" stop-color="#0C2243"/><stop offset="1" stop-color="#050C1A"/></radialGradient>
<radialGradient id="atom" cx=".36" cy=".3" r=".75"><stop offset="0" stop-color="#FFFFFF"/><stop offset=".3" stop-color="#D2F8FF"/><stop offset=".75" stop-color="#6CC4FF"/><stop offset="1" stop-color="#3C8DF0"/></radialGradient>
<radialGradient id="cloud" cx=".5" cy=".5" r=".5"><stop offset="0" stop-color="#4DB4FF" stop-opacity=".36"/><stop offset=".65" stop-color="#4DB4FF" stop-opacity=".09"/><stop offset="1" stop-color="#4DB4FF" stop-opacity="0"/></radialGradient>
<filter id="soft" x="-30%" y="-30%" width="160%" height="160%"><feDropShadow dx="0" dy="10" stdDeviation="14" flood-color="#020814" flood-opacity=".55"/></filter>
</defs>'''


def molecule(scale=0.92):
    """the check-shaped molecule, centred on the 1024 canvas"""
    return f'''<g transform="translate(512 512) scale({scale}) translate(-571 -512)">
<ellipse cx="560" cy="560" rx="390" ry="300" fill="url(#cloud)" transform="rotate(-25 560 560)"/>
<g filter="url(#soft)">
<path d="M300 540 L470 710 L800 330" fill="none" stroke="url(#bond)" stroke-width="64" stroke-linecap="round" stroke-linejoin="round"/>
<path d="M300 540 L470 710 L800 330" fill="none" stroke="#FFFFFF" stroke-opacity=".28" stroke-width="16" stroke-linecap="round" stroke-linejoin="round" transform="translate(-6 -10)"/>
<circle cx="300" cy="540" r="70" fill="url(#atom)"/>
<circle cx="470" cy="710" r="92" fill="url(#atom)"/>
<circle cx="800" cy="330" r="112" fill="url(#atom)"/>
</g></g>'''


def svg(body, size=1024):
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1024 1024" width="{size}" height="{size}">{DEFS}{body}</svg>'


FULL = svg('<rect width="1024" height="1024" fill="url(#bg)"/>' + molecule(0.92))
MASKABLE = svg('<rect width="1024" height="1024" fill="url(#bg)"/>' + molecule(0.74))
# a rounded tile on a transparent square, sized like a macOS app icon (824 of 1024)
TILE = svg('''<defs><clipPath id="r"><rect x="100" y="100" width="824" height="824" rx="185"/></clipPath>
<filter id="tsh" x="-20%" y="-20%" width="140%" height="140%"><feDropShadow dx="0" dy="12" stdDeviation="16" flood-color="#000" flood-opacity=".35"/></filter></defs>
<rect x="100" y="100" width="824" height="824" rx="185" fill="#0C2243" filter="url(#tsh)"/>
<g clip-path="url(#r)"><g transform="translate(100 100) scale(.8047)"><rect width="1024" height="1024" fill="url(#bg)"/>''' + molecule(0.92) + '</g></g>')


def render(page, svg_text, size):
    page.set_viewport_size({"width": 1024, "height": 1024})
    page.set_content(f'<html><body style="margin:0;background:transparent">{svg_text}</body></html>')
    png = page.locator("svg").screenshot(omit_background=True)
    return Image.open(io.BytesIO(png)).convert("RGBA").resize((size, size), Image.LANCZOS)


def recolour(path_in, path_out, size, dark_bg=False):
    """keep the shape of a suite icon (its alpha), paint it with the blue gradient"""
    src = Image.open(path_in).convert("RGBA")
    if dark_bg:
        src = Image.open(path_in.replace("-512-maskable", "-512")).convert("RGBA")
    a = src.split()[3].resize((size, size), Image.LANCZOS)
    grad = Image.new("RGBA", (size, size))
    stops = [(0, (0x5E, 0xF2, 0xD6)), (0.5, (0x4D, 0xB4, 0xFF)), (1, (0x6A, 0x7D, 0xFF))]
    px = grad.load()
    for y in range(size):
        for x in range(size):
            t = (x + (size - 1 - y)) / (2 * (size - 1))
            for (t0, c0), (t1, c1) in zip(stops, stops[1:]):
                if t <= t1:
                    f = (t - t0) / (t1 - t0)
                    px[x, y] = tuple(int(c0[i] + (c1[i] - c0[i]) * f) for i in range(3)) + (255,)
                    break
    shape = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    shape.paste(grad, (0, 0), a)
    if dark_bg:
        bg = Image.new("RGBA", (size, size), (0x0C, 0x1A, 0x2E, 255))
        inner = shape.resize((int(size * 0.8), int(size * 0.8)), Image.LANCZOS)
        bg.alpha_composite(inner, ((size - inner.width) // 2, (size - inner.height) // 2))
        shape = bg
    shape.save(path_out)


def main():
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "qtask.svg"), "w") as fh:
        fh.write(FULL.replace(' width="1024" height="1024"', "", 1))
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page()
        full = render(pg, FULL, 1024)
        os.makedirs(os.path.join(ROOT, "design"), exist_ok=True)
        full.save(os.path.join(ROOT, "design", "qtask-1024.png"))
        full.convert("RGB").resize((180, 180), Image.LANCZOS).save(os.path.join(OUT, "apple-touch-icon.png"))
        tile = render(pg, TILE, 1024)
        for s in (192, 512):
            tile.resize((s, s), Image.LANCZOS).save(os.path.join(OUT, f"control-center-{s}.png"))
        render(pg, MASKABLE, 512).convert("RGB").save(os.path.join(OUT, "control-center-512-maskable.png"))
        b.close()
    for suite in ("lab-notebook", "literature-hub", "structure-studio", "paper-kit"):
        orig = os.path.join(OUT, f"{suite}-512.png")
        recolour(orig, os.path.join(OUT, f"{suite}-512-maskable.png"), 512, dark_bg=True)
        recolour(orig, os.path.join(OUT, f"{suite}-192.png"), 192)
        recolour(orig, orig, 512)
    print("icons written to", OUT)


if __name__ == "__main__":
    main()
