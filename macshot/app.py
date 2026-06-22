"""Windows desktop application entry point for Macshot."""

from __future__ import annotations

import ctypes
import os
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageDraw

from .capture import bring_to_front, capture_window
from .clipboard import copy_image
from .effect import ShotStyle, apply_mac_effect

WM_HOTKEY = 0x0312
WM_APP_CAPTURE = 0x8001
WM_APP_OPEN_DIR = 0x8002
WM_APP_EXIT = 0x8003
HOTKEY_ID = 1
ERROR_ALREADY_EXISTS = 183
ERROR_HOTKEY_ALREADY_REGISTERED = 1409
SINGLE_INSTANCE_MUTEX = "Local\\MacshotTrayApp"

MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008

ctypes.windll.kernel32.CreateMutexW.restype = ctypes.c_void_p


@dataclass
class AppConfig:
    """Runtime options shared by the CLI compatibility path and tray app."""

    out: Path | None = None
    open_after: bool = False
    no_clipboard: bool = False
    no_raise: bool = False
    settle: float = 0.35
    hotkey: str = "ctrl+shift+s"
    radius: int | None = None
    padding: int | None = None
    no_shadow: bool = False
    shadow_opacity: float | None = None
    shadow_blur: int | None = None
    shadow_offset: int | None = None


class MSG(ctypes.Structure):
    _fields_ = [
        ("hwnd", ctypes.c_void_p),
        ("message", ctypes.c_uint),
        ("wParam", ctypes.c_size_t),
        ("lParam", ctypes.c_size_t),
        ("time", ctypes.c_ulong),
        ("pt", ctypes.c_long * 2),
    ]


def default_out_dir() -> Path:
    return Path(os.path.expanduser("~")) / "Pictures" / "Macshot"


def style_from_config(config: AppConfig) -> ShotStyle:
    st = ShotStyle()
    if config.radius is not None:
        st.radius = config.radius
    if config.padding is not None:
        st.padding = config.padding
    if config.shadow_opacity is not None:
        st.shadow_opacity = config.shadow_opacity
    if config.shadow_blur is not None:
        st.shadow_blur = config.shadow_blur
    if config.shadow_offset is not None:
        st.shadow_dy = config.shadow_offset
    if config.no_shadow:
        st.shadow = False
    return st


def config_from_args(args) -> AppConfig:
    return AppConfig(
        out=Path(args.out) if args.out else None,
        open_after=args.open,
        no_clipboard=args.no_clipboard,
        no_raise=args.no_raise,
        settle=args.settle,
        hotkey=args.combo,
        radius=args.radius,
        padding=args.padding,
        no_shadow=args.no_shadow,
        shadow_opacity=args.shadow_opacity,
        shadow_blur=args.shadow_blur,
        shadow_offset=args.shadow_offset,
    )


def save_and_finish(image, config: AppConfig, hwnd_title: str = "") -> Path:
    out_dir = config.out or default_out_dir()
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    safe = "".join(c for c in hwnd_title if c.isalnum() or c in " -_")[:40].strip()
    name = f"macshot-{stamp}{('-' + safe) if safe else ''}.png"
    path = out_dir / name
    image.save(path, format="PNG")

    if not config.no_clipboard:
        copy_image(image)

    if config.open_after:
        open_output_dir(config)
    return path


def process_hwnd(hwnd: int, config: AppConfig) -> Path | None:
    import win32gui

    title = win32gui.GetWindowText(hwnd)
    if not config.no_raise:
        bring_to_front(hwnd)
        time.sleep(config.settle)
    img, scale = capture_window(hwnd)
    result = apply_mac_effect(img, style_from_config(config), scale=scale)
    return save_and_finish(result, config, title)


def capture_selected_window(config: AppConfig) -> Path | None:
    from .picker import pick_window

    hwnd = pick_window()
    if not hwnd:
        return None
    return process_hwnd(hwnd, config)


def open_output_dir(config: AppConfig) -> None:
    out_dir = config.out or default_out_dir()
    out_dir.mkdir(parents=True, exist_ok=True)
    os.startfile(out_dir)  # noqa: S606 (intentional, opens explorer)


def _make_icon_image() -> Image.Image:
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle((10, 16, 54, 48), radius=9, fill=(47, 128, 237, 255))
    draw.rounded_rectangle((16, 22, 48, 42), radius=5, fill=(255, 255, 255, 255))
    draw.ellipse((28, 27, 38, 37), fill=(47, 128, 237, 255))
    return img


def _show_message(title: str, message: str, error: bool = False) -> None:
    flags = 0x10 if error else 0x40
    ctypes.windll.user32.MessageBoxW(None, message, title, flags)


def _notify(icon, message: str, title: str = "Macshot") -> None:
    try:
        icon.notify(message, title)
    except Exception:
        pass


def _show_startup_feedback(config: AppConfig, hotkey_registered: bool) -> None:
    try:
        import tkinter as tk
    except Exception:
        _show_message("Macshot", "Macshot is running.")
        return

    root = tk.Tk()
    root.overrideredirect(True)
    root.attributes("-topmost", True)
    root.configure(bg="#202124")

    hotkey_text = f"Press {config.hotkey} to capture a window."
    if not hotkey_registered:
        hotkey_text = "Use the tray menu to capture windows."
    message = f"Macshot is running\n{hotkey_text}"

    label = tk.Label(
        root,
        text=message,
        bg="#202124",
        fg="white",
        font=("Segoe UI", 11),
        padx=18,
        pady=14,
        justify="left",
    )
    label.pack()

    root.update_idletasks()
    width = root.winfo_width()
    height = root.winfo_height()
    screen_w = root.winfo_screenwidth()
    screen_h = root.winfo_screenheight()
    root.geometry(f"{width}x{height}+{screen_w - width - 24}+{screen_h - height - 64}")
    root.after(2600, root.destroy)
    root.mainloop()


def _parse_hotkey(combo: str) -> tuple[int, int]:
    modifiers = 0
    key = None
    for part in combo.lower().replace("+", " ").split():
        if part in {"ctrl", "control"}:
            modifiers |= MOD_CONTROL
        elif part == "shift":
            modifiers |= MOD_SHIFT
        elif part == "alt":
            modifiers |= MOD_ALT
        elif part in {"win", "windows"}:
            modifiers |= MOD_WIN
        elif len(part) == 1:
            key = ord(part.upper())
        else:
            raise ValueError(f"unsupported hotkey key: {part}")
    if key is None:
        raise ValueError(f"unsupported hotkey: {combo}")
    return modifiers, key


class MacshotTrayApp:
    def __init__(self, config: AppConfig | None = None):
        self.config = config or AppConfig()
        self._thread_id = 0
        self._icon = None
        self._capturing = False
        self._hotkey_registered = False
        self._mutex_handle = None

    def run(self) -> int:
        self._thread_id = ctypes.windll.kernel32.GetCurrentThreadId()
        try:
            if not self._acquire_single_instance():
                _show_message(
                    "Macshot",
                    "Macshot is already running. Use the existing tray icon.",
                )
                return 0
            self._start_tray()
            self._hotkey_registered = self._register_hotkey()
            _show_startup_feedback(self.config, self._hotkey_registered)
            self._message_loop()
        except Exception as exc:
            _show_message("Macshot", str(exc), error=True)
            return 1
        finally:
            self._unregister_hotkey()
            self._stop_tray()
            self._release_single_instance()
        return 0

    def capture_once(self) -> None:
        if self._capturing:
            return
        self._capturing = True
        try:
            path = capture_selected_window(self.config)
            if path and self._icon:
                _notify(self._icon, f"Saved to {path}")
        except Exception as exc:
            _show_message("Macshot capture failed", str(exc), error=True)
        finally:
            self._capturing = False

    def _start_tray(self) -> None:
        try:
            import pystray
        except ImportError as exc:
            raise RuntimeError(
                "The 'pystray' package is required for the Macshot tray app."
            ) from exc

        menu = pystray.Menu(
            pystray.MenuItem(
                "Capture Window",
                lambda _icon, _item: self._post(WM_APP_CAPTURE),
            ),
            pystray.MenuItem(
                "Open Output Folder",
                lambda _icon, _item: self._post(WM_APP_OPEN_DIR),
            ),
            pystray.MenuItem("Exit", lambda _icon, _item: self._post(WM_APP_EXIT)),
        )
        self._icon = pystray.Icon(
            "Macshot",
            _make_icon_image(),
            f"Macshot - {self.config.hotkey} to capture",
            menu,
        )
        self._icon.run_detached()
        _notify(
            self._icon,
            f"Press {self.config.hotkey} to capture a window.",
            "Macshot is running",
        )

    def _stop_tray(self) -> None:
        if self._icon:
            self._icon.stop()
            self._icon = None

    def _post(self, message: int) -> None:
        if self._thread_id:
            ctypes.windll.user32.PostThreadMessageW(self._thread_id, message, 0, 0)

    def _acquire_single_instance(self) -> bool:
        ctypes.windll.kernel32.SetLastError(0)
        handle = ctypes.windll.kernel32.CreateMutexW(None, False, SINGLE_INSTANCE_MUTEX)
        if not handle:
            raise RuntimeError("Could not create Macshot single-instance lock.")
        self._mutex_handle = handle
        return ctypes.windll.kernel32.GetLastError() != ERROR_ALREADY_EXISTS

    def _release_single_instance(self) -> None:
        if self._mutex_handle:
            ctypes.windll.kernel32.CloseHandle(self._mutex_handle)
            self._mutex_handle = None

    def _register_hotkey(self) -> bool:
        modifiers, key = _parse_hotkey(self.config.hotkey)
        ctypes.windll.kernel32.SetLastError(0)
        ok = ctypes.windll.user32.RegisterHotKey(None, HOTKEY_ID, modifiers, key)
        if not ok:
            error_code = ctypes.windll.kernel32.GetLastError()
            reason = "The hotkey is already registered by another app."
            if error_code and error_code != ERROR_HOTKEY_ALREADY_REGISTERED:
                reason = f"Windows error {error_code}."
            _show_message(
                "Macshot hotkey unavailable",
                (
                    f"Could not register hotkey: {self.config.hotkey}\n\n"
                    f"{reason}\n\n"
                    "Macshot will keep running. Use the tray menu to capture windows."
                ),
            )
            return False
        return True

    def _unregister_hotkey(self) -> None:
        if self._hotkey_registered:
            ctypes.windll.user32.UnregisterHotKey(None, HOTKEY_ID)

    def _message_loop(self) -> None:
        msg = MSG()
        user32 = ctypes.windll.user32
        while True:
            result = user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
            if result == 0:
                break
            if result == -1:
                raise RuntimeError("Windows message loop failed")
            if msg.message == WM_HOTKEY and msg.wParam == HOTKEY_ID:
                self.capture_once()
            elif msg.message == WM_APP_CAPTURE:
                self.capture_once()
            elif msg.message == WM_APP_OPEN_DIR:
                try:
                    open_output_dir(self.config)
                except Exception as exc:
                    _show_message("Macshot", str(exc), error=True)
            elif msg.message == WM_APP_EXIT:
                break
            else:
                user32.TranslateMessage(ctypes.byref(msg))
                user32.DispatchMessageW(ctypes.byref(msg))


def run_tray_app(config: AppConfig | None = None) -> int:
    return MacshotTrayApp(config).run()
