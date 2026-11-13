"""Generate the Bravetel icon and logo set from the brand exports. Run locally, commit branding/assets.

    python branding/make_icons.py <path to fusionpbx-automation/brand/exports>
"""
import sys
from pathlib import Path

from PIL import Image

src_dir = Path(sys.argv[1])
out = Path(__file__).parent / "assets"
out.mkdir(exist_ok=True)

icon = Image.open(src_dir / "bravetel-icon-1024.png").convert("RGBA")
icon.save(out / "app_icon.ico", sizes=[(s, s) for s in (16, 20, 24, 32, 40, 48, 64, 128, 256)])
icon.save(out / "icon.ico", sizes=[(s, s) for s in (16, 24, 32, 48, 64, 128, 256)])
icon.save(out / "tray-icon.ico", sizes=[(s, s) for s in (16, 20, 24, 32, 48)])
icon.resize((256, 256), Image.LANCZOS).save(out / "icon.png")


def logo(name: str, target: str) -> None:
    img = Image.open(src_dir / name).convert("RGBA")
    w = 600
    img.resize((w, round(img.height * w / img.width)), Image.LANCZOS).save(out / target)


# RustDesk shows logo_light.png in its light theme, so it needs the logo made for light backgrounds
# (Bravetel's "dark" logo), and the reverse for the dark theme.
logo("bravetel-logo-dark-1600.png", "logo_light.png")
logo("bravetel-logo-light-1600.png", "logo_dark.png")
print("wrote", sorted(p.name for p in out.iterdir()))
