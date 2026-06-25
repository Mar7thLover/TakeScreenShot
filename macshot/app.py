"""Windows desktop application entry point for Macshot."""

from __future__ import annotations

import ctypes
import os
import threading
import time
from dataclasses import dataclass, fields, replace
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageDraw

from .capture import bring_to_front, capture_full_screen, capture_region, capture_window
from .clipboard import copy_image
from .effect import (
    ShotStyle,
    apply_circle_effect,
    apply_freeform_effect,
    apply_mac_effect,
    apply_region_effect,
)
from .i18n import LANG_AUTO, translate
from .settings import load_settings, save_settings

WM_HOTKEY = 0x0312
WM_APP_CAPTURE = 0x8001
WM_APP_OPEN_DIR = 0x8002
WM_APP_EXIT = 0x8003
WM_APP_HOME = 0x8004
WM_APP_SETTINGS = 0x8005
WM_APP_CAPTURE_FULL = 0x8006
WM_APP_CAPTURE_CIRCLE = 0x8007
WM_APP_CAPTURE_FREE = 0x8008
WM_APP_CAPTURE_REGION = 0x8009
WM_APP_APPLY_SETTINGS = 0x800A
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
    language: str = LANG_AUTO
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


def load_config() -> AppConfig:
    """Load persisted desktop settings into an AppConfig instance."""
    config = AppConfig()
    data = load_settings()
    valid_fields = {field.name for field in fields(AppConfig)}
    updates = {}
    for key, value in data.items():
        if key not in valid_fields:
            continue
        if key == "out":
            updates[key] = Path(value) if value else None
        else:
            updates[key] = value
    return replace(config, **updates)


def save_config(config: AppConfig) -> None:
    """Persist settings edited from the desktop UI."""
    values = {
        "out": str(config.out) if config.out else None,
        "open_after": config.open_after,
        "no_clipboard": config.no_clipboard,
        "no_raise": config.no_raise,
        "settle": config.settle,
        "hotkey": config.hotkey,
        "language": config.language,
        "radius": config.radius,
        "padding": config.padding,
        "no_shadow": config.no_shadow,
        "shadow_opacity": config.shadow_opacity,
        "shadow_blur": config.shadow_blur,
        "shadow_offset": config.shadow_offset,
    }
    save_settings(values)


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


def config_from_args(args, base: AppConfig | None = None) -> AppConfig:
    config = base or AppConfig()
    return AppConfig(
        out=Path(args.out) if args.out else config.out,
        open_after=args.open if args.open is not None else config.open_after,
        no_clipboard=(
            args.no_clipboard if args.no_clipboard is not None else config.no_clipboard
        ),
        no_raise=args.no_raise if args.no_raise is not None else config.no_raise,
        settle=args.settle if args.settle is not None else config.settle,
        hotkey=args.combo or config.hotkey,
        language=config.language,
        radius=args.radius if args.radius is not None else config.radius,
        padding=args.padding if args.padding is not None else config.padding,
        no_shadow=args.no_shadow if args.no_shadow is not None else config.no_shadow,
        shadow_opacity=(
            args.shadow_opacity
            if args.shadow_opacity is not None
            else config.shadow_opacity
        ),
        shadow_blur=(
            args.shadow_blur if args.shadow_blur is not None else config.shadow_blur
        ),
        shadow_offset=(
            args.shadow_offset
            if args.shadow_offset is not None
            else config.shadow_offset
        ),
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

    hwnd = pick_window(language=config.language)
    if not hwnd:
        return None
    return process_hwnd(hwnd, config)


def capture_full_screen_once(config: AppConfig) -> Path:
    img, _scale = capture_full_screen()
    return save_and_finish(img.convert("RGBA"), config, "full-screen")


def capture_region_once(config: AppConfig) -> Path | None:
    from .picker import pick_region

    region = pick_region("free", language=config.language)
    if not region:
        return None
    img, scale = capture_region(region)
    result = apply_region_effect(img, style_from_config(config), scale=scale)
    return save_and_finish(result, config, "region")


def capture_free_region_once(config: AppConfig) -> Path | None:
    from .picker import pick_freeform_region

    selection = pick_freeform_region(language=config.language)
    if not selection:
        return None
    region, points = selection
    img, scale = capture_region(region)
    result = apply_freeform_effect(img, points, style_from_config(config), scale=scale)
    return save_and_finish(result, config, "free-region")


def capture_circle_region_once(config: AppConfig) -> Path | None:
    from .picker import pick_region

    region = pick_region("circle", language=config.language)
    if not region:
        return None
    img, scale = capture_region(region)
    result = apply_circle_effect(img, style_from_config(config), scale=scale)
    return save_and_finish(result, config, "circle-region")


def process_region(region: tuple[int, int, int, int], config: AppConfig) -> Path:
    """Grab + style an already-selected rectangular region."""
    img, scale = capture_region(region)
    result = apply_region_effect(img, style_from_config(config), scale=scale)
    return save_and_finish(result, config, "region")


def process_circle(region: tuple[int, int, int, int], config: AppConfig) -> Path:
    """Grab + style an already-selected circular region."""
    img, scale = capture_region(region)
    result = apply_circle_effect(img, style_from_config(config), scale=scale)
    return save_and_finish(result, config, "circle-region")


def process_freeform(selection, config: AppConfig) -> Path:
    """Grab + style an already-drawn freehand selection."""
    region, points = selection
    img, scale = capture_region(region)
    result = apply_freeform_effect(img, points, style_from_config(config), scale=scale)
    return save_and_finish(result, config, "free-region")


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
        from .ui import UiController

        self.config = config or load_config()
        self._thread_id = 0
        self._icon = None
        self._capture_lock = threading.Lock()
        self._hotkey_registered = False
        self._mutex_handle = None
        self._last_path: Path | None = None
        self._pending_config: AppConfig | None = None
        self._ui = UiController()

    def run(self) -> int:
        self._thread_id = ctypes.windll.kernel32.GetCurrentThreadId()
        try:
            if not self._acquire_single_instance():
                _show_message(
                    "Macshot",
                    translate("app.already_running", self.config.language),
                )
                return 0
            self._ui.start()
            self._start_tray()
            self._hotkey_registered = self._register_hotkey()
            self.open_home()
            self._message_loop()
        except Exception as exc:
            _show_message("Macshot", str(exc), error=True)
            return 1
        finally:
            self._unregister_hotkey()
            self._stop_tray()
            self._ui.stop()
            self._release_single_instance()
        return 0

    def _run_daemon(self, target, name: str) -> None:
        thread = threading.Thread(target=target, name=name, daemon=True)
        thread.start()

    # -- Home / Settings ------------------------------------------------------

    def _home_callbacks(self):
        from .ui import HomeCallbacks

        return HomeCallbacks(
            on_capture_window=lambda: self._post(WM_APP_CAPTURE),
            on_capture_full=lambda: self._post(WM_APP_CAPTURE_FULL),
            on_capture_region=lambda: self._post(WM_APP_CAPTURE_REGION),
            on_capture_circle=lambda: self._post(WM_APP_CAPTURE_CIRCLE),
            on_capture_free=lambda: self._post(WM_APP_CAPTURE_FREE),
            on_settings=lambda: self._post(WM_APP_SETTINGS),
            on_open_folder=lambda: self._post(WM_APP_OPEN_DIR),
        )

    def open_home(self) -> None:
        self._ui.show_home(self.config, self._home_callbacks(), self._last_path)

    def open_settings(self) -> None:
        self._ui.show_settings(
            self.config, default_out_dir(), self._on_settings_saved
        )

    def _on_settings_saved(self, new_config: AppConfig) -> None:
        # Called on the UI thread; apply on the message-loop thread so the hotkey
        # is (re)registered on the thread that owns the Win32 message queue.
        self._pending_config = new_config
        self._post(WM_APP_APPLY_SETTINGS)

    def _apply_settings(self) -> None:
        new_config = self._pending_config
        self._pending_config = None
        if new_config is None:
            return
        old_hotkey = self.config.hotkey
        old_language = self.config.language
        self.config = new_config
        save_config(self.config)
        if self._icon:
            self._icon.title = translate(
                "app.tray_title", self.config.language, hotkey=self.config.hotkey
            )
        if old_language != self.config.language:
            self._stop_tray()
            self._start_tray()
        if old_hotkey != self.config.hotkey:
            self._unregister_hotkey()
            self._hotkey_registered = self._register_hotkey()
        self._ui.rebuild_home_if_open(
            self.config, self._home_callbacks(), self._last_path
        )

    # -- Capture --------------------------------------------------------------

    def _spawn_capture(self, do_capture) -> None:
        if not self._capture_lock.acquire(blocking=False):
            return

        def worker() -> None:
            home_was_visible = False
            try:
                home_was_visible = self._ui.hide_home_for_capture()
                if home_was_visible:
                    time.sleep(0.12)  # let the window vanish before grabbing
                do_capture()
            except Exception as exc:  # noqa: BLE001
                _show_message(
                    translate("app.capture_failed", self.config.language),
                    str(exc),
                    error=True,
                )
            finally:
                if home_was_visible:
                    self._ui.reshow_home(self._last_path)
                self._capture_lock.release()

        self._run_daemon(worker, "MacshotCapture")

    def _finish(self, path: Path | None) -> None:
        if not path:
            return
        self._last_path = path
        config = self.config
        self._ui.show_notification(
            config, path, lambda: open_output_dir(config)
        )

    def _capture_window(self) -> None:
        hwnd = self._ui.pick_window(self.config.language)
        if hwnd:
            self._finish(process_hwnd(hwnd, self.config))

    def _capture_full(self) -> None:
        self._finish(capture_full_screen_once(self.config))

    def _capture_region(self) -> None:
        region = self._ui.pick_region("free", self.config.language)
        if region:
            self._finish(process_region(region, self.config))

    def _capture_circle(self) -> None:
        region = self._ui.pick_region("circle", self.config.language)
        if region:
            self._finish(process_circle(region, self.config))

    def _capture_free(self) -> None:
        selection = self._ui.pick_freeform(self.config.language)
        if selection:
            self._finish(process_freeform(selection, self.config))

    def _start_tray(self) -> None:
        try:
            import pystray
        except ImportError as exc:
            raise RuntimeError(
                translate("app.tray_required", self.config.language)
            ) from exc

        menu = pystray.Menu(
            pystray.MenuItem(
                translate("tray.home", self.config.language),
                lambda _icon, _item: self._post(WM_APP_HOME),
            ),
            pystray.MenuItem(
                translate("tray.capture_window", self.config.language),
                lambda _icon, _item: self._post(WM_APP_CAPTURE),
            ),
            pystray.MenuItem(
                translate("tray.capture_full", self.config.language),
                lambda _icon, _item: self._post(WM_APP_CAPTURE_FULL),
            ),
            pystray.MenuItem(
                translate("tray.capture_region", self.config.language),
                lambda _icon, _item: self._post(WM_APP_CAPTURE_REGION),
            ),
            pystray.MenuItem(
                translate("tray.capture_circle", self.config.language),
                lambda _icon, _item: self._post(WM_APP_CAPTURE_CIRCLE),
            ),
            pystray.MenuItem(
                translate("tray.capture_freeform", self.config.language),
                lambda _icon, _item: self._post(WM_APP_CAPTURE_FREE),
            ),
            pystray.MenuItem(
                translate("tray.settings", self.config.language),
                lambda _icon, _item: self._post(WM_APP_SETTINGS),
            ),
            pystray.MenuItem(
                translate("tray.open_folder", self.config.language),
                lambda _icon, _item: self._post(WM_APP_OPEN_DIR),
            ),
            pystray.MenuItem(
                translate("tray.exit", self.config.language),
                lambda _icon, _item: self._post(WM_APP_EXIT),
            ),
        )
        self._icon = pystray.Icon(
            "Macshot",
            _make_icon_image(),
            translate("app.tray_title", self.config.language, hotkey=self.config.hotkey),
            menu,
        )
        self._icon.run_detached()

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
        try:
            modifiers, key = _parse_hotkey(self.config.hotkey)
        except ValueError as exc:
            _show_message(
                translate("app.hotkey_unavailable", self.config.language),
                translate(
                    "app.hotkey_register_error",
                    self.config.language,
                    hotkey=self.config.hotkey,
                    error=exc,
                ),
            )
            return False
        ctypes.windll.kernel32.SetLastError(0)
        ok = ctypes.windll.user32.RegisterHotKey(None, HOTKEY_ID, modifiers, key)
        if not ok:
            error_code = ctypes.windll.kernel32.GetLastError()
            reason = translate("app.hotkey_registered_elsewhere", self.config.language)
            if error_code and error_code != ERROR_HOTKEY_ALREADY_REGISTERED:
                reason = translate(
                    "app.hotkey_windows_error",
                    self.config.language,
                    code=error_code,
                )
            _show_message(
                translate("app.hotkey_unavailable", self.config.language),
                (
                    f"{translate('app.hotkey_register_error', self.config.language, hotkey=self.config.hotkey, error=reason)}\n\n"
                    f"{translate('app.hotkey_tray_fallback', self.config.language)}"
                ),
            )
            return False
        return True

    def _unregister_hotkey(self) -> None:
        if self._hotkey_registered:
            ctypes.windll.user32.UnregisterHotKey(None, HOTKEY_ID)
            self._hotkey_registered = False

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
                self._spawn_capture(self._capture_window)
            elif msg.message == WM_APP_CAPTURE:
                self._spawn_capture(self._capture_window)
            elif msg.message == WM_APP_CAPTURE_FULL:
                self._spawn_capture(self._capture_full)
            elif msg.message == WM_APP_CAPTURE_REGION:
                self._spawn_capture(self._capture_region)
            elif msg.message == WM_APP_CAPTURE_CIRCLE:
                self._spawn_capture(self._capture_circle)
            elif msg.message == WM_APP_CAPTURE_FREE:
                self._spawn_capture(self._capture_free)
            elif msg.message == WM_APP_HOME:
                try:
                    self.open_home()
                except Exception as exc:
                    _show_message("Macshot", str(exc), error=True)
            elif msg.message == WM_APP_SETTINGS:
                try:
                    self.open_settings()
                except Exception as exc:
                    _show_message("Macshot", str(exc), error=True)
            elif msg.message == WM_APP_APPLY_SETTINGS:
                try:
                    self._apply_settings()
                except Exception as exc:
                    _show_message("Macshot", str(exc), error=True)
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
