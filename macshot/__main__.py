"""Command-line entry point for macshot.

Examples
--------
  python -m macshot                     pick a window (overlay), then capture
  python -m macshot --foreground -d 3   capture the foreground window after 3s
  python -m macshot --title "崩坏"       capture the first window matching a title
  python -m macshot --list              list capturable windows
  python -m macshot --hotkey            run in the background; Ctrl+Shift+S to grab

Output goes to %USERPROFILE%\\Pictures\\Macshot by default and is copied to the
clipboard with transparency.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from datetime import datetime
from pathlib import Path

from . import __version__
from .capture import (
    bring_to_front,
    capture_window,
    find_window_by_title,
    list_capturable_windows,
)
from .clipboard import copy_image
from .effect import ShotStyle, apply_mac_effect


def default_out_dir() -> Path:
    base = Path(os.path.expanduser("~")) / "Pictures" / "Macshot"
    return base


def style_from_args(args) -> ShotStyle:
    st = ShotStyle()
    if args.radius is not None:
        st.radius = args.radius
    if args.padding is not None:
        st.padding = args.padding
    if args.shadow_opacity is not None:
        st.shadow_opacity = args.shadow_opacity
    if args.shadow_blur is not None:
        st.shadow_blur = args.shadow_blur
    if args.shadow_offset is not None:
        st.shadow_dy = args.shadow_offset
    if args.no_shadow:
        st.shadow = False
    return st


def save_and_finish(image, args, hwnd_title: str = "") -> Path:
    out_dir = Path(args.out) if args.out else default_out_dir()
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    safe = "".join(c for c in hwnd_title if c.isalnum() or c in " -_")[:40].strip()
    name = f"macshot-{stamp}{('-' + safe) if safe else ''}.png"
    path = out_dir / name
    image.save(path, format="PNG")

    copied = False
    if not args.no_clipboard:
        copied = copy_image(image)

    print(f"[macshot] saved  {path}  ({image.width}x{image.height})")
    if copied:
        print("[macshot] copied to clipboard (transparent PNG)")
    if args.open:
        try:
            os.startfile(out_dir)  # noqa: S606 (intentional, opens explorer)
        except Exception:
            pass
    return path


def process_hwnd(hwnd: int, args) -> Path | None:
    import win32gui

    title = win32gui.GetWindowText(hwnd)
    if not args.no_raise:
        bring_to_front(hwnd)
        time.sleep(args.settle)
    img, scale = capture_window(hwnd)
    style = style_from_args(args)
    result = apply_mac_effect(img, style, scale=scale)
    return save_and_finish(result, args, title)


def cmd_list(_args) -> int:
    rows = list_capturable_windows()
    if not rows:
        print("No capturable windows found.")
        return 1
    print(f"{'HWND':>10}  {'SIZE':>11}  TITLE")
    for hwnd, title, (l, t, r, b) in rows:
        print(f"{hwnd:>10}  {r - l:>4}x{b - t:<5}  {title}")
    return 0


def cmd_pick(args) -> int:
    from .picker import pick_window

    print("[macshot] click the window you want to capture (Esc to cancel)...")
    hwnd = pick_window()
    if not hwnd:
        print("[macshot] cancelled.")
        return 1
    process_hwnd(hwnd, args)
    return 0


def cmd_foreground(args) -> int:
    import win32gui

    for remaining in range(args.delay, 0, -1):
        print(f"[macshot] capturing foreground window in {remaining}s...", end="\r")
        time.sleep(1)
    if args.delay:
        print()
    hwnd = win32gui.GetForegroundWindow()
    if not hwnd:
        print("[macshot] no foreground window.")
        return 1
    # Don't steal focus from the window we're about to capture.
    args.no_raise = True
    process_hwnd(hwnd, args)
    return 0


def cmd_title(args) -> int:
    hwnd = find_window_by_title(args.title)
    if not hwnd:
        print(f"[macshot] no window matching: {args.title!r}")
        return 1
    process_hwnd(hwnd, args)
    return 0


def cmd_hotkey(args) -> int:
    try:
        import keyboard
    except ImportError:
        print("[macshot] the 'keyboard' package is required for --hotkey.")
        print("          install it with:  python -m pip install keyboard")
        return 1

    from .picker import pick_window

    combo = args.combo
    print(f"[macshot] running. press {combo} to capture a window, Ctrl+C to quit.")

    def trigger():
        # Run the picker on the main thread shortly after the hotkey fires.
        hwnd = pick_window()
        if hwnd:
            try:
                process_hwnd(hwnd, args)
            except Exception as exc:  # keep the daemon alive on errors
                print(f"[macshot] error: {exc}")
        else:
            print("[macshot] cancelled.")

    keyboard.add_hotkey(combo, trigger)
    try:
        keyboard.wait("ctrl+c")
    except KeyboardInterrupt:
        pass
    print("\n[macshot] bye.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="macshot",
        description="macOS-style window screenshots for Windows "
                    "(transparent background, rounded corners, soft shadow).",
    )
    p.add_argument("--version", action="version", version=f"macshot {__version__}")

    mode = p.add_mutually_exclusive_group()
    mode.add_argument("--pick", action="store_true",
                      help="interactively click a window (default)")
    mode.add_argument("--foreground", action="store_true",
                      help="capture the current foreground window")
    mode.add_argument("--title", metavar="TEXT",
                      help="capture the first window whose title contains TEXT")
    mode.add_argument("--list", action="store_true",
                      help="list capturable windows and exit")
    mode.add_argument("--hotkey", action="store_true",
                      help="run as a background hotkey daemon")

    p.add_argument("-d", "--delay", type=int, default=0,
                   help="countdown seconds before --foreground capture")
    p.add_argument("--combo", default="ctrl+shift+s",
                   help="hotkey for --hotkey mode (default: ctrl+shift+s)")
    p.add_argument("--settle", type=float, default=0.35,
                   help="seconds to wait after raising a window before capture")
    p.add_argument("--no-raise", action="store_true",
                   help="do not bring the target window to the front")

    p.add_argument("-o", "--out", metavar="DIR",
                   help="output directory (default: ~/Pictures/Macshot)")
    p.add_argument("--open", action="store_true",
                   help="open the output folder afterwards")
    p.add_argument("--no-clipboard", action="store_true",
                   help="do not copy the result to the clipboard")

    # Style overrides.
    p.add_argument("--radius", type=int, help="corner radius (px @100%%, default 11)")
    p.add_argument("--padding", type=int, help="transparent margin (px, default 90)")
    p.add_argument("--no-shadow", action="store_true", help="disable the drop shadow")
    p.add_argument("--shadow-opacity", type=float, help="shadow opacity 0..1 (default 0.45)")
    p.add_argument("--shadow-blur", type=int, help="shadow blur radius (default 34)")
    p.add_argument("--shadow-offset", type=int, help="shadow vertical offset (default 22)")
    return p


def main(argv=None) -> int:
    # Console may be a legacy codepage (e.g. GBK) that can't encode some window
    # titles; never let a print crash the tool.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="replace")  # type: ignore[union-attr]
        except Exception:
            pass

    args = build_parser().parse_args(argv)
    try:
        if args.list:
            return cmd_list(args)
        if args.foreground:
            return cmd_foreground(args)
        if args.title:
            return cmd_title(args)
        if args.hotkey:
            return cmd_hotkey(args)
        return cmd_pick(args)
    except KeyboardInterrupt:
        print("\n[macshot] interrupted.")
        return 130


if __name__ == "__main__":
    sys.exit(main())
