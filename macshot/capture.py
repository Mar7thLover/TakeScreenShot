"""Win32 window capture helpers.

We capture the on-screen pixels of a window region with BitBlt from the screen DC.
This is deliberately chosen over PrintWindow because it reliably captures
hardware-accelerated / GPU content (games, browsers, video) exactly as displayed.
The window's true visible rectangle comes from DWM extended frame bounds, which
excludes the invisible resize border that GetWindowRect would include.
"""

from __future__ import annotations

import ctypes
from ctypes import wintypes

import win32api
import win32con
import win32gui
import win32ui
from PIL import Image

# --- DPI awareness: capture in real physical pixels ------------------------------
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)  # PROCESS_PER_MONITOR_DPI_AWARE
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

_DWMWA_EXTENDED_FRAME_BOUNDS = 9
_DWMWA_CLOAKED = 14
_GA_ROOT = 2


def get_dpi_scale(hwnd: int) -> float:
    """Return the DPI scale factor (1.0 == 96 dpi == 100%) for a window's monitor."""
    try:
        dpi = ctypes.windll.user32.GetDpiForWindow(wintypes.HWND(hwnd))
        if dpi:
            return dpi / 96.0
    except Exception:
        pass
    return 1.0


def get_frame_bounds(hwnd: int) -> tuple[int, int, int, int]:
    """Visible bounds (left, top, right, bottom) in physical screen pixels."""
    rect = wintypes.RECT()
    res = ctypes.windll.dwmapi.DwmGetWindowAttribute(
        wintypes.HWND(hwnd),
        _DWMWA_EXTENDED_FRAME_BOUNDS,
        ctypes.byref(rect),
        ctypes.sizeof(rect),
    )
    if res == 0:
        return rect.left, rect.top, rect.right, rect.bottom
    return win32gui.GetWindowRect(hwnd)


def is_cloaked(hwnd: int) -> bool:
    val = ctypes.c_int(0)
    res = ctypes.windll.dwmapi.DwmGetWindowAttribute(
        wintypes.HWND(hwnd),
        _DWMWA_CLOAKED,
        ctypes.byref(val),
        ctypes.sizeof(val),
    )
    return res == 0 and val.value != 0


def top_level_hwnd(hwnd: int) -> int:
    return ctypes.windll.user32.GetAncestor(wintypes.HWND(hwnd), _GA_ROOT)


def is_capturable(hwnd: int) -> bool:
    """A real, visible, non-cloaked top-level window with some area."""
    if not win32gui.IsWindow(hwnd) or not win32gui.IsWindowVisible(hwnd):
        return False
    if win32gui.IsIconic(hwnd):  # minimized
        return False
    if is_cloaked(hwnd):
        return False
    ex_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
    if ex_style & win32con.WS_EX_TOOLWINDOW:
        return False
    l, t, r, b = get_frame_bounds(hwnd)
    if (r - l) < 8 or (b - t) < 8:
        return False
    return True


def enum_top_windows() -> list[int]:
    """All top-level windows in Z-order (topmost first)."""
    result: list[int] = []

    def _cb(hwnd, _):
        result.append(hwnd)
        return True

    win32gui.EnumWindows(_cb, None)
    return result


def list_capturable_windows() -> list[tuple[int, str, tuple[int, int, int, int]]]:
    out = []
    for hwnd in enum_top_windows():
        if not is_capturable(hwnd):
            continue
        title = win32gui.GetWindowText(hwnd)
        if not title:
            continue
        out.append((hwnd, title, get_frame_bounds(hwnd)))
    return out


def window_at_point(x: int, y: int, skip: int | None = None) -> int | None:
    """Topmost capturable window containing the physical point (x, y)."""
    for hwnd in enum_top_windows():
        if skip is not None and hwnd == skip:
            continue
        if not is_capturable(hwnd):
            continue
        l, t, r, b = get_frame_bounds(hwnd)
        if l <= x < r and t <= y < b:
            return hwnd
    return None


def find_window_by_title(substring: str) -> int | None:
    sub = substring.lower()
    for hwnd, title, _ in list_capturable_windows():
        if sub in title.lower():
            return hwnd
    return None


def bring_to_front(hwnd: int) -> None:
    """Best-effort raise of a window above others before capture."""
    try:
        if win32gui.IsIconic(hwnd):
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        # AttachThreadInput dance to satisfy SetForegroundWindow restrictions.
        fg = win32gui.GetForegroundWindow()
        cur_thread = win32api.GetCurrentThreadId()
        fg_thread = ctypes.windll.user32.GetWindowThreadProcessId(fg, None) if fg else 0
        target_thread = ctypes.windll.user32.GetWindowThreadProcessId(hwnd, None)
        for th in {fg_thread, target_thread}:
            if th and th != cur_thread:
                ctypes.windll.user32.AttachThreadInput(cur_thread, th, True)
        win32gui.SetWindowPos(
            hwnd, win32con.HWND_TOP, 0, 0, 0, 0,
            win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_NOACTIVATE,
        )
        try:
            win32gui.SetForegroundWindow(hwnd)
        except Exception:
            pass
        for th in {fg_thread, target_thread}:
            if th and th != cur_thread:
                ctypes.windll.user32.AttachThreadInput(cur_thread, th, False)
    except Exception:
        pass


def grab_region(left: int, top: int, right: int, bottom: int) -> Image.Image:
    """Capture a physical screen rectangle as a PIL RGB image (works for GPU content)."""
    width, height = right - left, bottom - top
    if width <= 0 or height <= 0:
        raise ValueError("invalid capture region")

    hwnd_desktop = win32gui.GetDesktopWindow()
    screen_dc = win32gui.GetWindowDC(hwnd_desktop)
    src_dc = win32ui.CreateDCFromHandle(screen_dc)
    mem_dc = src_dc.CreateCompatibleDC()
    bmp = win32ui.CreateBitmap()
    bmp.CreateCompatibleBitmap(src_dc, width, height)
    mem_dc.SelectObject(bmp)
    try:
        mem_dc.BitBlt((0, 0), (width, height), src_dc, (left, top), win32con.SRCCOPY)
        info = bmp.GetInfo()
        bits = bmp.GetBitmapBits(True)
        img = Image.frombuffer(
            "RGB", (info["bmWidth"], info["bmHeight"]), bits, "raw", "BGRX", 0, 1
        )
    finally:
        win32gui.DeleteObject(bmp.GetHandle())
        mem_dc.DeleteDC()
        src_dc.DeleteDC()
        win32gui.ReleaseDC(hwnd_desktop, screen_dc)
    return img


def capture_window(hwnd: int) -> tuple[Image.Image, float]:
    """Capture a window's visible region. Returns (image, dpi_scale)."""
    l, t, r, b = get_frame_bounds(hwnd)
    return grab_region(l, t, r, b), get_dpi_scale(hwnd)
