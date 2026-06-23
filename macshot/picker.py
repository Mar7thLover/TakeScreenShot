"""Interactive 'click a window to capture' overlay, like macOS Cmd+Shift+4+Space.

A faint fullscreen, top-most window spans the whole virtual desktop. It highlights
the window under the cursor and returns that window's HWND when clicked. Because the
overlay sits on top, it absorbs the click so the underlying app never receives it.
"""

from __future__ import annotations

import ctypes

import win32api
import win32gui

from .capture import get_frame_bounds, top_level_hwnd, window_at_point

_ACCENT = "#3b9dff"
_BG = "#101216"


def _virtual_screen() -> tuple[int, int, int, int]:
    vx = win32api.GetSystemMetrics(76)  # SM_XVIRTUALSCREEN
    vy = win32api.GetSystemMetrics(77)  # SM_YVIRTUALSCREEN
    vw = win32api.GetSystemMetrics(78)  # SM_CXVIRTUALSCREEN
    vh = win32api.GetSystemMetrics(79)  # SM_CYVIRTUALSCREEN
    return vx, vy, vw, vh


def _fade_in(root, target: float) -> None:
    current = {"alpha": 0.02}

    def step():
        current["alpha"] = min(target, current["alpha"] + 0.035)
        try:
            root.attributes("-alpha", current["alpha"])
        except Exception:
            return
        if current["alpha"] < target:
            root.after(16, step)

    step()


def pick_window(_auto_close_ms: int | None = None) -> int | None:
    """Show the overlay and return the clicked window's HWND (None if cancelled).

    ``_auto_close_ms`` is a test hook: when set, the overlay cancels itself after
    that many milliseconds (used by the smoke test, no real interaction needed).
    """
    import tkinter as tk

    vx, vy, vw, vh = _virtual_screen()

    root = tk.Tk()
    root.overrideredirect(True)
    root.geometry(f"{vw}x{vh}+{vx}+{vy}")
    root.attributes("-topmost", True)
    root.attributes("-alpha", 0.02)
    root.config(bg=_BG, cursor="crosshair")

    canvas = tk.Canvas(root, bg=_BG, highlightthickness=0)
    canvas.pack(fill="both", expand=True)

    overlay_hwnd = top_level_hwnd(root.winfo_id())
    state = {"hwnd": None, "selected": None, "rect": None}

    def lerp_rect(source, target, amount: float = 0.28):
        if source is None:
            return target
        return tuple(round(source[i] + (target[i] - source[i]) * amount) for i in range(4))

    def refresh():
        try:
            x, y = win32api.GetCursorPos()
        except Exception:
            root.after(33, refresh)
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
            ty = ct - 26 if ct - 26 > (vy - vy) else cb + 4
            canvas.create_rectangle(cl, ty, cl + 9 * len(label), ty + 24,
                                    fill=_ACCENT, outline="", tag="hl")
            canvas.create_text(cl + 6, ty + 12, text=label.strip(), fill="white",
                               anchor="w", font=("Segoe UI", 10, "bold"), tag="hl")
        else:
            state["rect"] = None
        root.after(33, refresh)

    def on_click(_event):
        state["selected"] = state["hwnd"]
        root.destroy()

    def on_cancel(_event=None):
        state["selected"] = None
        root.destroy()

    canvas.bind("<Button-1>", on_click)
    canvas.bind("<Button-3>", on_cancel)
    root.bind("<Escape>", on_cancel)

    # Center hint text.
    canvas.create_text(vw // 2, 40,
                       text="Click a window to capture    ·    Esc / right-click to cancel",
                       fill="white", font=("Segoe UI", 13, "bold"))

    root.after(33, refresh)
    root.focus_force()
    try:
        ctypes.windll.user32.SetForegroundWindow(overlay_hwnd)
    except Exception:
        pass
    if _auto_close_ms is not None:
        root.after(_auto_close_ms, on_cancel)
    _fade_in(root, 0.24)
    root.mainloop()
    return state["selected"]


def pick_region(mode: str = "free", _auto_close_ms: int | None = None) -> tuple[int, int, int, int] | None:
    """Show a drag-to-select overlay and return a physical screen rectangle."""
    import tkinter as tk

    if mode not in {"free", "circle"}:
        raise ValueError(f"unsupported region picker mode: {mode}")

    vx, vy, vw, vh = _virtual_screen()
    root = tk.Tk()
    root.overrideredirect(True)
    root.geometry(f"{vw}x{vh}+{vx}+{vy}")
    root.attributes("-topmost", True)
    root.attributes("-alpha", 0.02)
    root.config(bg=_BG, cursor="crosshair")

    canvas = tk.Canvas(root, bg=_BG, highlightthickness=0)
    canvas.pack(fill="both", expand=True)

    verb = "Drag a circle region" if mode == "circle" else "Drag a free screenshot region"
    canvas.create_text(
        vw // 2,
        40,
        text=f"{verb}    ·    Esc / right-click to cancel",
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
            root.destroy()
            return
        l, t, r, b = rect
        if (r - l) < 4 or (b - t) < 4:
            state["selected"] = None
        else:
            state["selected"] = (l + vx, t + vy, r + vx, b + vy)
        root.destroy()

    def on_cancel(_event=None):
        state["selected"] = None
        root.destroy()

    canvas.bind("<Button-1>", on_press)
    canvas.bind("<B1-Motion>", on_drag)
    canvas.bind("<ButtonRelease-1>", on_release)
    canvas.bind("<Button-3>", on_cancel)
    root.bind("<Escape>", on_cancel)

    root.focus_force()
    try:
        ctypes.windll.user32.SetForegroundWindow(top_level_hwnd(root.winfo_id()))
    except Exception:
        pass
    if _auto_close_ms is not None:
        root.after(_auto_close_ms, on_cancel)
    _fade_in(root, 0.26)
    root.mainloop()
    return state["selected"]
