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


def pick_window(_auto_close_ms: int | None = None) -> int | None:
    """Show the overlay and return the clicked window's HWND (None if cancelled).

    ``_auto_close_ms`` is a test hook: when set, the overlay cancels itself after
    that many milliseconds (used by the smoke test, no real interaction needed).
    """
    import tkinter as tk

    vx = win32api.GetSystemMetrics(76)  # SM_XVIRTUALSCREEN
    vy = win32api.GetSystemMetrics(77)  # SM_YVIRTUALSCREEN
    vw = win32api.GetSystemMetrics(78)  # SM_CXVIRTUALSCREEN
    vh = win32api.GetSystemMetrics(79)  # SM_CYVIRTUALSCREEN

    root = tk.Tk()
    root.overrideredirect(True)
    root.geometry(f"{vw}x{vh}+{vx}+{vy}")
    root.attributes("-topmost", True)
    root.attributes("-alpha", 0.22)
    root.config(bg="#101216", cursor="crosshair")

    canvas = tk.Canvas(root, bg="#101216", highlightthickness=0)
    canvas.pack(fill="both", expand=True)

    overlay_hwnd = top_level_hwnd(root.winfo_id())
    state = {"hwnd": None, "selected": None}

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
            cl, ct, cr, cb = l - vx, t - vy, r - vx, b - vy
            canvas.create_rectangle(cl, ct, cr - 1, cb - 1,
                                    outline=_ACCENT, width=3, tag="hl")
            title = win32gui.GetWindowText(hwnd) or "(untitled)"
            label = f"  {title}   {r - l}x{b - t}  "
            ty = ct - 26 if ct - 26 > (vy - vy) else cb + 4
            canvas.create_rectangle(cl, ty, cl + 9 * len(label), ty + 24,
                                    fill=_ACCENT, outline="", tag="hl")
            canvas.create_text(cl + 6, ty + 12, text=label.strip(), fill="white",
                               anchor="w", font=("Segoe UI", 10, "bold"), tag="hl")
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
    root.mainloop()
    return state["selected"]
