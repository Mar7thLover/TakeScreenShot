"""Application entry point for macshot.

Examples
--------
  python -m macshot                     run the Windows tray app
  python -m macshot --pick              pick a window (overlay), then capture
  python -m macshot --foreground -d 3   capture the foreground window after 3s
  python -m macshot --title "崩坏"       capture the first window matching a title
  python -m macshot --list              list capturable windows

Output goes to %USERPROFILE%\\Pictures\\Macshot by default and is copied to the
clipboard with transparency.
"""

from __future__ import annotations

import argparse
import sys
import time
from dataclasses import replace

from . import __version__
from .app import (
    capture_selected_window,
    config_from_args,
    load_config,
    process_hwnd,
    run_tray_app,
)
from .capture import (
    find_window_by_title,
    list_capturable_windows,
)


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
    config = config_from_args(args, load_config())
    print("[macshot] click the window you want to capture (Esc to cancel)...")
    path = capture_selected_window(config)
    if not path:
        print("[macshot] cancelled.")
        return 1
    print(f"[macshot] saved  {path}")
    return 0


def cmd_foreground(args) -> int:
    import win32gui

    config = config_from_args(args, load_config())
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
    path = process_hwnd(hwnd, replace(config, no_raise=True))
    print(f"[macshot] saved  {path}")
    return 0


def cmd_title(args) -> int:
    config = config_from_args(args, load_config())
    hwnd = find_window_by_title(args.title)
    if not hwnd:
        print(f"[macshot] no window matching: {args.title!r}")
        return 1
    path = process_hwnd(hwnd, config)
    print(f"[macshot] saved  {path}")
    return 0


def cmd_hotkey(args) -> int:
    return run_tray_app(config_from_args(args, load_config()))


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="macshot",
        description="Macshot tray app and developer CLI for Windows screenshots.",
    )
    p.add_argument("--version", action="version", version=f"macshot {__version__}")

    mode = p.add_mutually_exclusive_group()
    mode.add_argument("--tray", action="store_true",
                      help="run the Windows tray app (default)")
    mode.add_argument("--pick", action="store_true",
                      help="interactively click a window once")
    mode.add_argument("--foreground", action="store_true",
                      help="capture the current foreground window")
    mode.add_argument("--title", metavar="TEXT",
                      help="capture the first window whose title contains TEXT")
    mode.add_argument("--list", action="store_true",
                      help="list capturable windows and exit")
    mode.add_argument("--hotkey", action="store_true",
                      help="run the tray app with the configured hotkey")

    p.add_argument("-d", "--delay", type=int, default=0,
                   help="countdown seconds before --foreground capture")
    p.add_argument("--combo", default=None,
                   help="hotkey for --hotkey mode (default: ctrl+shift+s)")
    p.add_argument("--settle", type=float, default=None,
                   help="seconds to wait after raising a window before capture")
    p.add_argument("--no-raise", action="store_true", default=None,
                   help="do not bring the target window to the front")

    p.add_argument("-o", "--out", metavar="DIR",
                   help="output directory (default: ~/Pictures/Macshot)")
    p.add_argument("--open", action="store_true", default=None,
                   help="open the output folder afterwards")
    p.add_argument("--no-clipboard", action="store_true", default=None,
                   help="do not copy the result to the clipboard")

    # Style overrides.
    p.add_argument("--radius", type=int, help="corner radius (px @100%%, default 11)")
    p.add_argument("--padding", type=int, help="transparent margin (px, default 90)")
    p.add_argument("--no-shadow", action="store_true", default=None,
                   help="disable the drop shadow")
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
        if args.hotkey or args.tray:
            return cmd_hotkey(args)
        return run_tray_app(config_from_args(args, load_config()))
    except KeyboardInterrupt:
        print("\n[macshot] interrupted.")
        return 130


if __name__ == "__main__":
    sys.exit(main())
