import glob
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# All modules import cleanly.
import macshot
import macshot.capture
import macshot.clipboard
import macshot.effect
import macshot.picker  # noqa: F401  (imports tkinter lazily inside functions)

from PIL import Image

files = sorted(glob.glob(str(Path(__file__).resolve().parent / "out" / "*.png")),
               key=os.path.getmtime)
img = Image.open(files[-1]).convert("RGBA")
w, h = img.size
corners = [img.getpixel(p)[3] for p in [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)]]
print("file:", Path(files[-1]).name, "size:", img.size)
print("corner alphas (must be 0):", corners)
print("center alpha (must be 255):", img.getpixel((w // 2, h // 4))[3])
assert all(c == 0 for c in corners), "corners not transparent!"
print("OK - transparency + all imports verified")
