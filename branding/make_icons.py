"""Generate the Bravetel icon and logo set from the brand exports. Run locally, commit branding/assets.

    python branding/make_icons.py <path to fusionpbx-automation/brand/exports>
"""
import sys
from pathlib import Path

from PIL import Image, ImageChops

src_dir = Path(sys.argv[1])
out = Path(__file__).parent / "assets"
out.mkdir(exist_ok=True)

icon = Image.open(src_dir / "bravetel-icon-1024.png").convert("RGBA")
icon.save(out / "app_icon.ico", sizes=[(s, s) for s in (16, 20, 24, 32, 40, 48, 64, 128, 256)])
icon.save(out / "icon.ico", sizes=[(s, s) for s in (16, 24, 32, 48, 64, 128, 256)])
icon.save(out / "tray-icon.ico", sizes=[(s, s) for s in (16, 20, 24, 32, 48)])
icon.resize((256, 256), Image.LANCZOS).save(out / "icon.png")


# macOS app icon: the brand icon is full bleed, so pad it to the ~824/1024 macOS icon grid.
# Pillow writes ic07..ic14 (16 to 1024 px, retina pairs); no iconutil needed.
canvas = Image.new("RGBA", (1024, 1024), (0, 0, 0, 0))
body = icon.resize((824, 824), Image.LANCZOS)
canvas.paste(body, (100, 100), body)
canvas.save(out / "AppIcon.icns")

# macOS menu bar: a template image (macOS uses only the alpha channel), so take the white "B" glyph,
# not the blue square, which would render as a solid blob.
r, g, b, a = icon.split()
mask = ImageChops.multiply(ImageChops.darker(ImageChops.darker(r, g), b).point(lambda v: 255 if v > 200 else 0), a)
glyph = Image.new("RGBA", icon.size, (0, 0, 0, 0))
glyph.putalpha(mask)
glyph = glyph.crop(mask.getbbox())
side = max(glyph.size)
square = Image.new("RGBA", (side, side), (0, 0, 0, 0))
square.paste(glyph, ((side - glyph.width) // 2, (side - glyph.height) // 2))
square.resize((44, 44), Image.LANCZOS).save(out / "mac-tray.png")  # 22 pt @2x


def logo(name: str, target: str) -> None:
    img = Image.open(src_dir / name).convert("RGBA")
    w = 600
    img.resize((w, round(img.height * w / img.width)), Image.LANCZOS).save(out / target)


# RustDesk shows logo_light.png in its light theme, so it needs the logo made for light backgrounds
# (Bravetel's "dark" logo), and the reverse for the dark theme.
logo("bravetel-logo-dark-1600.png", "logo_light.png")
logo("bravetel-logo-light-1600.png", "logo_dark.png")
print("wrote", sorted(p.name for p in out.iterdir()))
