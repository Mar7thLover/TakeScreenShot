"""Quick visual + sanity test for the Mac effect (no screen capture needed)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PIL import Image, ImageDraw
from macshot.effect import ShotStyle, apply_mac_effect

w, h = 800, 520
img = Image.new("RGB", (w, h), (40, 44, 60))
d = ImageDraw.Draw(img)
d.rectangle([0, 0, w, 40], fill=(28, 30, 40))
d.ellipse([14, 13, 28, 27], fill=(255, 95, 86))
d.ellipse([34, 13, 48, 27], fill=(255, 189, 46))
d.ellipse([54, 13, 68, 27], fill=(39, 201, 63))
d.text((w // 2 - 40, 14), "Demo Window", fill=(220, 220, 230))
d.rectangle([40, 80, w - 40, h - 40], outline=(90, 140, 220), width=3)

out = apply_mac_effect(img, ShotStyle(), scale=1.0)
out_path = Path(__file__).resolve().parent / "demo_effect.png"
out.save(out_path)

trim = ShotStyle().trim                                  # 1px cropped per edge
assert out.mode == "RGBA"
assert out.size == (w - 2 * trim + 180, h - 2 * trim + 180), out.size   # padding 90/side
assert out.getpixel((0, 0))[3] == 0                      # outer corner transparent
cx, cy = out.size[0] // 2, out.size[1] // 2
assert out.getpixel((cx, cy))[3] == 255                  # window center opaque
# Shadow region below the window should be semi-transparent (not 0, not 255).
sa = out.getpixel((cx, cy + (h - 2 * trim) // 2 + 30))[3]
assert 0 < sa < 255, sa

print("OK  size:", out.size, " saved:", out_path)
print("    center alpha:", out.getpixel((cx, cy))[3], " shadow alpha:", sa)
