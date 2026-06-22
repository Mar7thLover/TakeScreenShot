"""macshot - macOS-style window screenshots for Windows.

Capture a window at its original size with rounded corners, a soft drop shadow,
and a fully transparent background, saved as a PNG (and copied to the clipboard).
"""

__version__ = "1.0.0"

from .effect import ShotStyle, apply_mac_effect

__all__ = ["ShotStyle", "apply_mac_effect", "__version__"]
