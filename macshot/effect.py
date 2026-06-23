"""Mac-style image effects: rounded corners + soft drop shadow on a transparent canvas.

The pipeline turns a plain rectangular window capture into the look macOS produces
with Cmd+Shift+4+Space: the window keeps its original pixel size, gets rounded
corners, sits on a fully transparent background, and casts a soft downward shadow.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from PIL import Image, ImageDraw, ImageFilter


@dataclass
class ShotStyle:
    """Visual parameters for the Mac effect. Pixel values are at 100% scaling and
    are multiplied by ``scale`` (DPI factor) when the effect is applied."""

    radius: int = 11           # corner radius of the window
    padding: int = 90          # transparent margin around the window (room for shadow)
    shadow: bool = True
    shadow_opacity: float = 0.45
    shadow_blur: int = 34      # gaussian blur radius of the shadow
    shadow_dx: int = 0         # horizontal shadow offset
    shadow_dy: int = 22        # vertical shadow offset (macOS shadow falls downward)
    shadow_grow: int = 0       # expand/shrink the shadow shape vs. the window
    trim: int = 1              # crop N px off each capture edge (kills 1px desktop seams)

    def scaled(self, scale: float) -> "ShotStyle":
        s = scale if scale and scale > 0 else 1.0
        return ShotStyle(
            radius=max(0, round(self.radius * s)),
            padding=max(0, round(self.padding * s)),
            shadow=self.shadow,
            shadow_opacity=self.shadow_opacity,
            shadow_blur=max(0, round(self.shadow_blur * s)),
            shadow_dx=round(self.shadow_dx * s),
            shadow_dy=round(self.shadow_dy * s),
            shadow_grow=round(self.shadow_grow * s),
            trim=self.trim,
        )


def _rounded_mask(size: tuple[int, int], radius: int, supersample: int = 4) -> Image.Image:
    """Anti-aliased rounded-rectangle alpha mask (L mode)."""
    w, h = size
    if radius <= 0:
        return Image.new("L", size, 255)
    big = Image.new("L", (w * supersample, h * supersample), 0)
    draw = ImageDraw.Draw(big)
    draw.rounded_rectangle(
        [0, 0, w * supersample - 1, h * supersample - 1],
        radius=radius * supersample,
        fill=255,
    )
    return big.resize(size, Image.LANCZOS)


def _ellipse_mask(size: tuple[int, int], supersample: int = 4) -> Image.Image:
    """Anti-aliased ellipse alpha mask (L mode)."""
    w, h = size
    big = Image.new("L", (w * supersample, h * supersample), 0)
    draw = ImageDraw.Draw(big)
    draw.ellipse(
        [0, 0, w * supersample - 1, h * supersample - 1],
        fill=255,
    )
    return big.resize(size, Image.LANCZOS)


def apply_mac_effect(img: Image.Image, style: ShotStyle, scale: float = 1.0) -> Image.Image:
    """Return an RGBA image of the window with rounded corners, drop shadow and a
    transparent background. The window pixels keep their original resolution."""
    st = style.scaled(scale)
    img = img.convert("RGBA")

    # Trim a hair off each edge so a stray 1px desktop seam at the rounded corners
    # of the source window never bleeds into the result.
    if st.trim > 0 and img.width > 2 * st.trim and img.height > 2 * st.trim:
        img = img.crop((st.trim, st.trim, img.width - st.trim, img.height - st.trim))

    w, h = img.size

    # 1) Round the window's own corners.
    mask = _rounded_mask((w, h), st.radius)
    rounded = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    rounded.paste(img, (0, 0), mask)

    # 2) Build the transparent canvas with room for the shadow.
    cw, ch = w + st.padding * 2, h + st.padding * 2
    canvas = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))

    # 3) Soft drop shadow, shaped like the rounded window and blurred.
    if st.shadow and st.shadow_opacity > 0:
        shadow = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
        sdraw = ImageDraw.Draw(shadow)
        g = st.shadow_grow
        sx0 = st.padding + st.shadow_dx - g
        sy0 = st.padding + st.shadow_dy - g
        sx1 = st.padding + st.shadow_dx + w + g
        sy1 = st.padding + st.shadow_dy + h + g
        alpha = max(0, min(255, round(255 * st.shadow_opacity)))
        sdraw.rounded_rectangle(
            [sx0, sy0, sx1, sy1],
            radius=st.radius + max(0, g),
            fill=(0, 0, 0, alpha),
        )
        shadow = shadow.filter(ImageFilter.GaussianBlur(st.shadow_blur))
        canvas = Image.alpha_composite(canvas, shadow)

    # 4) Drop the window on top of the shadow.
    canvas.alpha_composite(rounded, (st.padding, st.padding))
    return canvas


def apply_region_effect(img: Image.Image, style: ShotStyle, scale: float = 1.0) -> Image.Image:
    """Apply the shared Macshot look to a freeform rectangular screen region.

    Region captures must keep every selected source pixel, so the window-specific
    1px edge trim is disabled here.
    """
    return apply_mac_effect(img, replace(style, trim=0), scale=scale)


def apply_circle_effect(img: Image.Image, style: ShotStyle, scale: float = 1.0) -> Image.Image:
    """Return an RGBA circular crop with the same transparent shadow style."""
    st = replace(style, trim=0).scaled(scale)
    img = img.convert("RGBA")
    w, h = img.size

    mask = _ellipse_mask((w, h))
    clipped = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    clipped.paste(img, (0, 0), mask)

    cw, ch = w + st.padding * 2, h + st.padding * 2
    canvas = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))

    if st.shadow and st.shadow_opacity > 0:
        shadow = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
        sdraw = ImageDraw.Draw(shadow)
        g = st.shadow_grow
        sx0 = st.padding + st.shadow_dx - g
        sy0 = st.padding + st.shadow_dy - g
        sx1 = st.padding + st.shadow_dx + w + g
        sy1 = st.padding + st.shadow_dy + h + g
        alpha = max(0, min(255, round(255 * st.shadow_opacity)))
        sdraw.ellipse([sx0, sy0, sx1, sy1], fill=(0, 0, 0, alpha))
        shadow = shadow.filter(ImageFilter.GaussianBlur(st.shadow_blur))
        canvas = Image.alpha_composite(canvas, shadow)

    canvas.alpha_composite(clipped, (st.padding, st.padding))
    return canvas
