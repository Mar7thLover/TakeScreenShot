"""Copy an RGBA image to the Windows clipboard preserving transparency.

We publish two formats:
  * CF_DIBV5  - a 32-bit DIB with an explicit alpha channel (apps that understand
                it, e.g. modern Office, keep the transparency on paste).
  * "PNG"     - raw PNG bytes for apps that prefer it (Chrome, GIMP, etc.).
"""

from __future__ import annotations

import io
import struct

import win32clipboard
from PIL import Image

_CF_DIBV5 = 17
_BI_BITFIELDS = 3
_LCS_sRGB = 0x73524742  # 'sRGB'


def _to_dibv5(image: Image.Image) -> bytes:
    image = image.convert("RGBA")
    w, h = image.size
    pixels = image.tobytes("raw", "BGRA")  # bottom rows first when height > 0

    header = struct.pack(
        "<IiiHHIIiiII"   # core BITMAPINFOHEADER fields
        "IIII"           # R, G, B, A masks
        "I"              # CSType
        "9i"             # CIEXYZTRIPLE endpoints (unused)
        "III"            # gamma R, G, B
        "I"              # intent
        "III",           # profile data, profile size, reserved
        124,             # bV5Size
        w,               # bV5Width
        h,               # bV5Height (positive -> bottom-up rows, matching BGRA above)
        1,               # bV5Planes
        32,              # bV5BitCount
        _BI_BITFIELDS,   # bV5Compression
        len(pixels),     # bV5SizeImage
        2835, 2835,      # ~72 dpi pels-per-meter
        0, 0,            # ClrUsed, ClrImportant
        0x00FF0000,      # red mask
        0x0000FF00,      # green mask
        0x000000FF,      # blue mask
        0xFF000000,      # alpha mask
        _LCS_sRGB,       # CSType
        0, 0, 0, 0, 0, 0, 0, 0, 0,  # endpoints
        0, 0, 0,         # gamma
        0,               # intent
        0, 0, 0,         # profile data, size, reserved
    )

    # tobytes gives top-down rows; DIB with positive height is bottom-up, so flip.
    row = w * 4
    rows = [pixels[i:i + row] for i in range(0, len(pixels), row)]
    pixels_bottom_up = b"".join(reversed(rows))
    return header + pixels_bottom_up


def copy_image(image: Image.Image) -> bool:
    try:
        png_buf = io.BytesIO()
        image.convert("RGBA").save(png_buf, format="PNG")
        png_bytes = png_buf.getvalue()
        dibv5 = _to_dibv5(image)
        png_fmt = win32clipboard.RegisterClipboardFormat("PNG")

        win32clipboard.OpenClipboard()
        try:
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardData(_CF_DIBV5, dibv5)
            win32clipboard.SetClipboardData(png_fmt, png_bytes)
        finally:
            win32clipboard.CloseClipboard()
        return True
    except Exception:
        return False
