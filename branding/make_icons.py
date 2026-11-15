"""Generate the app icon and logo set from two brand files. Run locally, then commit branding/assets.

    python branding/make_icons.py <square icon PNG, 1024 px or more> <wordmark logo PNG, transparent background>

The icon may have rounded corners and a transparent margin; the margin is trimmed.
PNGs are git-ignored in this repo, so add them with `git add -f branding/assets/*.png`.
"""
import sys
from pathlib import Path

from PIL import Image

icon_src, logo_src = Path(sys.argv[1]), Path(sys.argv[2])
out = Path(__file__).parent / "assets"
out.mkdir(exist_ok=True)


def square(img: Image.Image) -> Image.Image:
    """Trim the transparent margin and centre on a square transparent canvas."""
    box = img.getchannel("A").point(lambda a: 255 if a > 200 else 0).getbbox()
    img = img.crop(box)
    side = max(img.size)
    canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    canvas.paste(img, ((side - img.width) // 2, (side - img.height) // 2))
    return canvas


icon = square(Image.open(icon_src).convert("RGBA")).resize((1024, 1024), Image.LANCZOS)
icon.save(out / "app_icon.ico", sizes=[(s, s) for s in (16, 20, 24, 32, 40, 48, 64, 128, 256)])
icon.save(out / "icon.ico", sizes=[(s, s) for s in (16, 24, 32, 48, 64, 128, 256)])
icon.save(out / "tray-icon.ico", sizes=[(s, s) for s in (16, 20, 24, 32, 48)])
icon.resize((256, 256), Image.LANCZOS).save(out / "icon.png")

# macOS app icon: pad to the ~824/1024 macOS icon grid. Pillow writes the ICNS sizes; no iconutil needed.
canvas = Image.new("RGBA", (1024, 1024), (0, 0, 0, 0))
body = icon.resize((824, 824), Image.LANCZOS)
canvas.paste(body, (100, 100), body)
canvas.save(out / "AppIcon.icns")

# macOS menu bar: a template image (macOS uses only the alpha channel), so keep just the "C7" glyphs
# (white and red, both with a high red channel), not the blue square, which would render as a solid blob.
r, _, _, a = icon.split()
mask = Image.composite(r.point(lambda v: 255 if v > 200 else 0), Image.new("L", icon.size, 0), a)
glyph = Image.new("RGBA", icon.size, (0, 0, 0, 0))
glyph.putalpha(mask)
glyph = square(glyph)
glyph.resize((44, 44), Image.LANCZOS).save(out / "mac-tray.png")  # 22 pt @2x

# Wordmark. RustDesk shows logo_light.png in its light theme (logo for light backgrounds) and
# logo_dark.png in its dark theme; for dark, the blue lettering is turned white.
logo = Image.open(logo_src).convert("RGBA")
logo = logo.crop(logo.getchannel("A").getbbox())
w = min(600, logo.width * 2)
logo = logo.resize((w, round(logo.height * w / logo.width)), Image.LANCZOS)
logo.save(out / "logo_light.png")
px = logo.load()
for y in range(logo.height):
    for x in range(logo.width):
        rr, gg, bb, aa = px[x, y]
        if aa and bb > rr + 40:  # blue lettering
            px[x, y] = (255, 255, 255, aa)
logo.save(out / "logo_dark.png")
print("wrote", sorted(p.name for p in out.iterdir()))
