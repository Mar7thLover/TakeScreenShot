"""Interactive screen overlays for picking a window, region, or freehand shape.

Each overlay is a faint, fullscreen, top-most window spanning the whole virtual
desktop. The overlays are built as ``Toplevel`` widgets on a shared Tk root when
one is provided (the tray app runs a single UI thread), and fall back to a
temporary standalone root for the developer CLI. This avoids creating multiple
``tk.Tk()`` interpreters across threads, which is unstable in Tkinter.
"""

from __future__ import annotations

import ctypes

import win32api
import win32gui

from .capture import get_frame_bounds, top_level_hwnd, window_at_point
from .i18n import LANG_AUTO, translate

_ACCENT = "#3b9dff"
_BG = "#101216"


def _virtual_screen() -> tuple[int, int, int, int]:
    vx = win32api.GetSystemMetrics(76)  # SM_XVIRTUALSCREEN
    vy = win32api.GetSystemMetrics(77)  # SM_YVIRTUALSCREEN
    vw = win32api.GetSystemMetrics(78)  # SM_CXVIRTUALSCREEN
    vh = win32api.GetSystemMetrics(79)  # SM_CYVIRTUALSCREEN
    return vx, vy, vw, vh


def _fade_in(win, target: float) -> None:
    current = {"alpha": 0.02}

    def step():
        current["alpha"] = min(target, current["alpha"] + 0.035)
        try:
            win.attributes("-alpha", current["alpha"])
        except Exception:
            return
        if current["alpha"] < target:
            win.after(16, step)

    step()


def _make_overlay(parent):
    """Return (owner, window, standalone) for a fullscreen overlay.

    When ``parent`` is given the overlay is a ``Toplevel`` of that root and the
    caller is expected to already be on the root's UI thread. When ``parent`` is
    ``None`` a temporary hidden root is created (developer CLI use).
    """
    import tkinter as tk

    standalone = parent is None
    if standalone:
        owner = tk.Tk()
        owner.withdraw()
    else:
        owner = parent
    window = tk.Toplevel(owner)
    vx, vy, vw, vh = _virtual_screen()
    window.overrideredirect(True)
    window.geometry(f"{vw}x{vh}+{vx}+{vy}")
    window.attributes("-topmost", True)
    window.attributes("-alpha", 0.02)
    window.config(bg=_BG, cursor="crosshair")
    return owner, window, standalone


def _wait_overlay(owner, window, standalone) -> None:
    try:
        owner.wait_window(window)
    finally:
        if standalone:
            try:
                owner.destroy()
            except Exception:
                pass


def pick_window(
    parent=None,
    language: str = LANG_AUTO,
    _auto_close_ms: int | None = None,
) -> int | None:
    """Show the overlay and return the clicked window's HWND (None if cancelled)."""
    import tkinter as tk

    vx, vy, vw, vh = _virtual_screen()
    owner, window, standalone = _make_overlay(parent)

    canvas = tk.Canvas(window, bg=_BG, highlightthickness=0)
    canvas.pack(fill="both", expand=True)

    overlay_hwnd = top_level_hwnd(window.winfo_id())
    state = {"hwnd": None, "selected": None, "rect": None}

    def lerp_rect(source, target, amount: float = 0.28):
        if source is None:
            return target
        return tuple(round(source[i] + (target[i] - source[i]) * amount) for i in range(4))

    def refresh():
        try:
            x, y = win32api.GetCursorPos()
        except Exception:
            window.after(33, refresh)
            return
        hwnd = window_at_point(x, y, skip=overlay_hwnd)
        state["hwnd"] = hwnd
        canvas.delete("hl")
        if hwnd:
            l, t, r, b = get_frame_bounds(hwnd)
            target = (l - vx, t - vy, r - vx, b - vy)
            state["rect"] = lerp_rect(state["rect"], target)
            cl, ct, cr, cb = state["rect"]
            canvas.create_rectangle(cl, ct, cr - 1, cb - 1,
                                    outline=_ACCENT, width=3, tag="hl")
            canvas.create_rectangle(cl + 3, ct + 3, cr - 4, cb - 4,
                                    outline="white", width=1, tag="hl")
            title = win32gui.GetWindowText(hwnd) or "(untitled)"
            label = f"  {title}   {r - l}x{b - t}  "
            ty = ct - 26 if ct - 26 > 0 else cb + 4
            canvas.create_rectangle(cl, ty, cl + 9 * len(label), ty + 24,
                                    fill=_ACCENT, outline="", tag="hl")
            canvas.create_text(cl + 6, ty + 12, text=label.strip(), fill="white",
                               anchor="w", font=("Segoe UI", 10, "bold"), tag="hl")
        else:
            state["rect"] = None
        window.after(33, refresh)

    def on_click(_event):
        state["selected"] = state["hwnd"]
        window.destroy()

    def on_cancel(_event=None):
        state["selected"] = None
        window.destroy()

    canvas.bind("<Button-1>", on_click)
    canvas.bind("<Button-3>", on_cancel)
    window.bind("<Escape>", on_cancel)

    canvas.create_text(vw // 2, 40,
                       text=translate("picker.window_hint", language),
                       fill="white", font=("Segoe UI", 13, "bold"))

    window.after(33, refresh)
    window.focus_force()
    try:
        ctypes.windll.user32.SetForegroundWindow(overlay_hwnd)
    except Exception:
        pass
    if _auto_close_ms is not None:
        window.after(_auto_close_ms, on_cancel)
    _fade_in(window, 0.24)
    _wait_overlay(owner, window, standalone)
    return state["selected"]


def pick_region(
    mode: str = "free",
    parent=None,
    language: str = LANG_AUTO,
    _auto_close_ms: int | None = None,
) -> tuple[int, int, int, int] | None:
    """Show a drag-to-select overlay and return a physical screen rectangle."""
    import tkinter as tk

    if mode not in {"free", "circle"}:
        raise ValueError(f"unsupported region picker mode: {mode}")

    vx, vy, vw, vh = _virtual_screen()
    owner, window, standalone = _make_overlay(parent)

    canvas = tk.Canvas(window, bg=_BG, highlightthickness=0)
    canvas.pack(fill="both", expand=True)

    hint_key = "picker.circle_hint" if mode == "circle" else "picker.region_hint"
    canvas.create_text(
        vw // 2,
        40,
        text=translate(hint_key, language),
        fill="white",
        font=("Segoe UI", 13, "bold"),
        tag="hint",
    )

    state = {"start": None, "current": None, "selected": None}

    def normalized_rect():
        if not state["start"] or not state["current"]:
            return None
        x0, y0 = state["start"]
        x1, y1 = state["current"]
        l, r = sorted((x0, x1))
        t, b = sorted((y0, y1))
        return l, t, r, b

    def redraw():
        canvas.delete("sel")
        rect = normalized_rect()
        if not rect:
            return
        l, t, r, b = rect
        width = r - l
        height = b - t
        if width < 1 or height < 1:
            return
        shape = canvas.create_oval if mode == "circle" else canvas.create_rectangle
        shape(l, t, r, b, outline=_ACCENT, width=3, tag="sel")
        shape(l + 3, t + 3, r - 3, b - 3, outline="white", width=1, tag="sel")
        label = f"{width}x{height}"
        ty = t - 26 if t > 32 else b + 6
        canvas.create_rectangle(l, ty, l + 9 * len(label) + 12, ty + 24,
                                fill=_ACCENT, outline="", tag="sel")
        canvas.create_text(l + 6, ty + 12, text=label, fill="white",
                           anchor="w", font=("Segoe UI", 10, "bold"), tag="sel")

    def on_press(event):
        state["start"] = (event.x, event.y)
        state["current"] = (event.x, event.y)
        redraw()

    def on_drag(event):
        x = max(0, min(vw, event.x))
        y = max(0, min(vh, event.y))
        if mode == "circle" and state["start"]:
            sx, sy = state["start"]
            dx = x - sx
            dy = y - sy
            sign_x = 1 if dx >= 0 else -1
            sign_y = 1 if dy >= 0 else -1
            max_x = vw - sx if sign_x > 0 else sx
            max_y = vh - sy if sign_y > 0 else sy
            side = min(max(abs(dx), abs(dy)), max_x, max_y)
            x = sx + sign_x * side
            y = sy + sign_y * side
        state["current"] = (x, y)
        redraw()

    def on_release(event):
        on_drag(event)
        rect = normalized_rect()
        if not rect:
            window.destroy()
            return
        l, t, r, b = rect
        if (r - l) < 4 or (b - t) < 4:
            state["selected"] = None
        else:
            state["selected"] = (l + vx, t + vy, r + vx, b + vy)
        window.destroy()

    def on_cancel(_event=None):
        state["selected"] = None
        window.destroy()

    canvas.bind("<Button-1>", on_press)
    canvas.bind("<B1-Motion>", on_drag)
    canvas.bind("<ButtonRelease-1>", on_release)
    canvas.bind("<Button-3>", on_cancel)
    window.bind("<Escape>", on_cancel)

    window.focus_force()
    try:
        ctypes.windll.user32.SetForegroundWindow(top_level_hwnd(window.winfo_id()))
    except Exception:
        pass
    if _auto_close_ms is not None:
        window.after(_auto_close_ms, on_cancel)
    _fade_in(window, 0.26)
    _wait_overlay(owner, window, standalone)
    return state["selected"]


def pick_freeform_region(
    parent=None,
    language: str = LANG_AUTO,
    _auto_close_ms: int | None = None,
) -> tuple[tuple[int, int, int, int], list[tuple[int, int]]] | None:
    """Draw a freehand region and return its physical bbox plus local points."""
    import tkinter as tk

    vx, vy, vw, vh = _virtual_screen()
    owner, window, standalone = _make_overlay(parent)

    canvas = tk.Canvas(window, bg=_BG, highlightthickness=0)
    canvas.pack(fill="both", expand=True)
    canvas.create_text(
        vw // 2,
        40,
        text=translate("picker.freeform_hint", language),
        fill="white",
        font=("Segoe UI", 13, "bold"),
        tag="hint",
    )

    state = {"points": [], "selected": None}

    def clamp_point(x: int, y: int) -> tuple[int, int]:
        return max(0, min(vw, x)), max(0, min(vh, y))

    def bounds(points: list[tuple[int, int]]) -> tuple[int, int, int, int]:
        xs = [point[0] for point in points]
        ys = [point[1] for point in points]
        return min(xs), min(ys), max(xs), max(ys)

    def redraw() -> None:
        canvas.delete("sel")
        points = state["points"]
        if len(points) < 2:
            return
        flat = [coord for point in points for coord in point]
        canvas.create_line(
            *flat,
            fill=_ACCENT,
            width=4,
            smooth=True,
            capstyle="round",
            joinstyle="round",
            tag="sel",
        )
        if len(points) >= 3:
            canvas.create_polygon(
                *flat,
                outline="white",
                fill="",
                width=1,
                smooth=True,
                tag="sel",
            )
            l, t, r, b = bounds(points)
            label = f"{r - l}x{b - t}"
            ty = t - 26 if t > 32 else b + 6
            canvas.create_rectangle(
                l,
                ty,
                l + 9 * len(label) + 12,
                ty + 24,
                fill=_ACCENT,
                outline="",
                tag="sel",
            )
            canvas.create_text(
                l + 6,
                ty + 12,
                text=label,
                fill="white",
                anchor="w",
                font=("Segoe UI", 10, "bold"),
                tag="sel",
            )

    def on_press(event):
        state["points"] = [clamp_point(event.x, event.y)]
        redraw()

    def on_drag(event):
        point = clamp_point(event.x, event.y)
        points = state["points"]
        if points and abs(point[0] - points[-1][0]) < 2 and abs(point[1] - points[-1][1]) < 2:
            return
        points.append(point)
        redraw()

    def on_release(event):
        on_drag(event)
        points = state["points"]
        if len(points) < 3:
            state["selected"] = None
            window.destroy()
            return
        l, t, r, b = bounds(points)
        if (r - l) < 4 or (b - t) < 4:
            state["selected"] = None
        else:
            local_points = [(x - l, y - t) for x, y in points]
            state["selected"] = ((l + vx, t + vy, r + vx, b + vy), local_points)
        window.destroy()

    def on_cancel(_event=None):
        state["selected"] = None
        window.destroy()

    canvas.bind("<Button-1>", on_press)
    canvas.bind("<B1-Motion>", on_drag)
    canvas.bind("<ButtonRelease-1>", on_release)
    canvas.bind("<Button-3>", on_cancel)
    window.bind("<Escape>", on_cancel)

    window.focus_force()
    try:
        ctypes.windll.user32.SetForegroundWindow(top_level_hwnd(window.winfo_id()))
    except Exception:
        pass
    if _auto_close_ms is not None:
        window.after(_auto_close_ms, on_cancel)
    _fade_in(window, 0.26)
    _wait_overlay(owner, window, standalone)
    return state["selected"]
