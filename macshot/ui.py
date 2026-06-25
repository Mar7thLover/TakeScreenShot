"""Tkinter desktop UI for Macshot.

All windows live on a single dedicated UI thread that owns one hidden Tk root.
Home, Settings, the saved-notification and every capture overlay are created as
``Toplevel`` widgets of that root. Running a single root on one thread avoids the
multi-interpreter / cross-thread problems that previously made the tray menu and
captures unreliable.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, replace
from pathlib import Path
from typing import TYPE_CHECKING, Callable

from .i18n import SUPPORTED_LANGUAGES, language_label, translate

if TYPE_CHECKING:
    from .app import AppConfig

_BG = "#f4f5f8"
_CARD = "#ffffff"
_BORDER = "#e3e6eb"
_TEXT = "#1f2328"
_MUTED = "#6b7280"
_ACCENT = "#2f6fed"
_ACCENT_ACTIVE = "#2056c7"
_NOTIFY_BG = "#1f2330"


@dataclass
class HomeCallbacks:
    on_capture_window: Callable[[], None]
    on_capture_full: Callable[[], None]
    on_capture_region: Callable[[], None]
    on_capture_circle: Callable[[], None]
    on_capture_free: Callable[[], None]
    on_settings: Callable[[], None]
    on_open_folder: Callable[[], None]


def _center(win, width: int, height: int) -> None:
    win.update_idletasks()
    sw = win.winfo_screenwidth()
    sh = win.winfo_screenheight()
    x = max(0, (sw - width) // 2)
    y = max(0, (sh - height) // 3)
    win.geometry(f"{width}x{height}+{x}+{y}")


def _button(parent, text: str, command, primary: bool = False, width: int | None = None):
    import tkinter as tk

    return tk.Button(
        parent,
        text=text,
        command=command,
        bg=_ACCENT if primary else "#eef1f6",
        fg="white" if primary else _TEXT,
        activebackground=_ACCENT_ACTIVE if primary else "#e1e6ee",
        activeforeground="white" if primary else _TEXT,
        relief="flat",
        bd=0,
        padx=14,
        pady=9,
        width=width,
        font=("Segoe UI", 10, "bold"),
        cursor="hand2",
    )


def _link_button(parent, text: str, command):
    import tkinter as tk

    return tk.Button(
        parent,
        text=text,
        command=command,
        bg=_BG,
        fg=_ACCENT,
        activebackground=_BG,
        activeforeground=_ACCENT_ACTIVE,
        relief="flat",
        bd=0,
        padx=4,
        pady=6,
        font=("Segoe UI", 10, "bold"),
        cursor="hand2",
    )


def _card(parent):
    import tkinter as tk

    return tk.Frame(
        parent,
        bg=_CARD,
        highlightbackground=_BORDER,
        highlightthickness=1,
        bd=0,
    )


def _section_title(parent, text: str):
    import tkinter as tk

    return tk.Label(
        parent,
        text=text,
        bg=_BG,
        fg=_MUTED,
        font=("Segoe UI", 9, "bold"),
    )


# ---------------------------------------------------------------------------
# Home window
# ---------------------------------------------------------------------------


def build_home(root, config, callbacks: HomeCallbacks, last_path, on_destroy):
    import tkinter as tk

    def t(key: str, **values) -> str:
        return translate(key, config.language, **values)

    top = tk.Toplevel(root)
    top.title("Macshot")
    top.configure(bg=_BG)
    top.resizable(False, False)

    def handle_close():
        try:
            top.destroy()
        finally:
            on_destroy()

    top.protocol("WM_DELETE_WINDOW", handle_close)

    shell = tk.Frame(top, bg=_BG, padx=24, pady=22)
    shell.pack(fill="both", expand=True)

    tk.Label(
        shell, text="Macshot", bg=_BG, fg=_TEXT, font=("Segoe UI", 21, "bold")
    ).pack(anchor="w")
    tk.Label(
        shell, text=t("home.subtitle"), bg=_BG, fg=_MUTED, font=("Segoe UI", 10)
    ).pack(anchor="w", pady=(2, 0))

    info = _card(shell)
    info.pack(fill="x", pady=(18, 16))
    info_inner = tk.Frame(info, bg=_CARD, padx=16, pady=14)
    info_inner.pack(fill="x")

    hotkey_label = tk.Label(
        info_inner,
        text=t("home.hotkey", hotkey=config.hotkey),
        bg=_CARD,
        fg=_TEXT,
        font=("Segoe UI", 10, "bold"),
        anchor="w",
        justify="left",
    )
    hotkey_label.pack(anchor="w")

    out_dir = config.out or Path.home() / "Pictures" / "Macshot"
    tk.Label(
        info_inner,
        text=t("home.output", path=out_dir),
        bg=_CARD,
        fg=_MUTED,
        font=("Segoe UI", 9),
        wraplength=420,
        justify="left",
        anchor="w",
    ).pack(anchor="w", pady=(6, 0))

    last_var = tk.StringVar(
        value=t("home.last_saved", path=last_path) if last_path else t("home.last_saved_none")
    )
    tk.Label(
        info_inner,
        textvariable=last_var,
        bg=_CARD,
        fg=_MUTED,
        font=("Segoe UI", 9),
        wraplength=420,
        justify="left",
        anchor="w",
    ).pack(anchor="w", pady=(4, 0))

    _section_title(shell, t("home.capture_section")).pack(anchor="w")

    grid = tk.Frame(shell, bg=_BG)
    grid.pack(fill="x", pady=(8, 4))
    grid.columnconfigure(0, weight=1, uniform="cap")
    grid.columnconfigure(1, weight=1, uniform="cap")

    actions = [
        (t("home.capture_window"), callbacks.on_capture_window, True),
        (t("home.capture_full"), callbacks.on_capture_full, False),
        (t("home.capture_region"), callbacks.on_capture_region, False),
        (t("home.capture_circle"), callbacks.on_capture_circle, False),
        (t("home.capture_freeform"), callbacks.on_capture_free, False),
    ]
    for index, (label, callback, primary) in enumerate(actions):
        btn = _button(grid, label, callback, primary=primary)
        btn.grid(row=index // 2, column=index % 2, sticky="ew", padx=4, pady=4)

    tk.Frame(shell, bg=_BORDER, height=1).pack(fill="x", pady=(16, 10))

    footer = tk.Frame(shell, bg=_BG)
    footer.pack(fill="x")
    _link_button(footer, t("home.settings"), callbacks.on_settings).pack(side="left")
    _link_button(footer, t("home.open_folder"), callbacks.on_open_folder).pack(
        side="left", padx=(6, 0)
    )
    _button(footer, t("home.close"), handle_close).pack(side="right")

    _center(top, 460, 470)
    top.lift()
    top.attributes("-topmost", True)
    top.after(300, lambda: top.attributes("-topmost", False))

    def refresh(new_last_path):
        if new_last_path:
            last_var.set(t("home.last_saved", path=new_last_path))

    return top, refresh


# ---------------------------------------------------------------------------
# Settings window
# ---------------------------------------------------------------------------


def build_settings(root, config, default_out_dir: Path, on_save, on_destroy):
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk

    def t(key: str, **values) -> str:
        return translate(key, config.language, **values)

    top = tk.Toplevel(root)
    top.title(t("settings.window_title"))
    top.configure(bg=_BG)
    top.resizable(False, False)

    def handle_close():
        try:
            top.destroy()
        finally:
            on_destroy()

    top.protocol("WM_DELETE_WINDOW", handle_close)

    shell = tk.Frame(top, bg=_BG, padx=24, pady=22)
    shell.pack(fill="both", expand=True)

    tk.Label(
        shell, text=t("settings.title"), bg=_BG, fg=_TEXT, font=("Segoe UI", 19, "bold")
    ).pack(anchor="w", pady=(0, 4))

    out_var = tk.StringVar(value=str(config.out or default_out_dir))
    hotkey_var = tk.StringVar(value=config.hotkey)
    language_codes = list(SUPPORTED_LANGUAGES)
    language_labels = [language_label(code) for code in language_codes]
    language_by_label = dict(zip(language_labels, language_codes))
    language_var = tk.StringVar(
        value=language_label(config.language if config.language in language_codes else "auto")
    )
    settle_var = tk.StringVar(value=str(config.settle))
    radius_var = tk.StringVar(value="" if config.radius is None else str(config.radius))
    padding_var = tk.StringVar(value="" if config.padding is None else str(config.padding))
    shadow_opacity_var = tk.StringVar(
        value="" if config.shadow_opacity is None else str(config.shadow_opacity)
    )
    shadow_blur_var = tk.StringVar(
        value="" if config.shadow_blur is None else str(config.shadow_blur)
    )
    shadow_offset_var = tk.StringVar(
        value="" if config.shadow_offset is None else str(config.shadow_offset)
    )
    open_var = tk.BooleanVar(value=config.open_after)
    clipboard_var = tk.BooleanVar(value=not config.no_clipboard)
    raise_var = tk.BooleanVar(value=not config.no_raise)
    shadow_var = tk.BooleanVar(value=not config.no_shadow)

    def make_section(title: str):
        _section_title(shell, title).pack(anchor="w", pady=(14, 6))
        card = _card(shell)
        card.pack(fill="x")
        inner = tk.Frame(card, bg=_CARD, padx=16, pady=12)
        inner.pack(fill="x")
        inner.columnconfigure(1, weight=1)
        inner._row = 0
        return inner

    def add_field(card, label: str, build_widget, browse=None):
        row = card._row
        tk.Label(
            card, text=label, bg=_CARD, fg=_TEXT, font=("Segoe UI", 10), anchor="w"
        ).grid(row=row, column=0, sticky="w", padx=(0, 12), pady=6)
        widget = build_widget(card)
        widget.grid(row=row, column=1, sticky="ew", pady=6)
        if browse:
            _button(card, t("settings.browse"), browse).grid(
                row=row, column=2, sticky="e", padx=(8, 0), pady=6
            )
        card._row = row + 1

    def add_check(card, label: str, var):
        row = card._row
        tk.Checkbutton(
            card,
            text=label,
            variable=var,
            bg=_CARD,
            fg=_TEXT,
            activebackground=_CARD,
            selectcolor=_CARD,
            anchor="w",
            font=("Segoe UI", 10),
        ).grid(row=row, column=0, columnspan=3, sticky="w", pady=3)
        card._row = row + 1

    def entry(var):
        return lambda parent: tk.Entry(
            parent, textvariable=var, relief="solid", bd=1, font=("Segoe UI", 10)
        )

    def language_combo(parent):
        return ttk.Combobox(
            parent,
            textvariable=language_var,
            values=language_labels,
            state="readonly",
            font=("Segoe UI", 10),
        )

    def browse_out() -> None:
        selected = filedialog.askdirectory(
            initialdir=out_var.get() or str(default_out_dir), parent=top
        )
        if selected:
            out_var.set(selected)

    general = make_section(t("settings.section_general"))
    add_field(general, t("settings.output_folder"), entry(out_var), browse_out)
    add_field(general, t("settings.hotkey"), entry(hotkey_var))
    add_field(general, t("settings.language"), language_combo)
    add_field(general, t("settings.settle_seconds"), entry(settle_var))
    add_check(general, t("settings.open_after"), open_var)
    add_check(general, t("settings.copy_clipboard"), clipboard_var)
    add_check(general, t("settings.raise_window"), raise_var)

    style = make_section(t("settings.section_style"))
    add_field(style, t("settings.corner_radius"), entry(radius_var))
    add_field(style, t("settings.padding"), entry(padding_var))
    add_field(style, t("settings.shadow_opacity"), entry(shadow_opacity_var))
    add_field(style, t("settings.shadow_blur"), entry(shadow_blur_var))
    add_field(style, t("settings.shadow_offset"), entry(shadow_offset_var))
    add_check(style, t("settings.enable_shadow"), shadow_var)

    def optional_int(var, name):
        value = var.get().strip()
        if not value:
            return None
        try:
            parsed = int(value)
        except ValueError as exc:
            raise ValueError(t("error.must_int", name=name)) from exc
        if parsed < 0:
            raise ValueError(t("error.non_negative", name=name))
        return parsed

    def optional_float(var, name):
        value = var.get().strip()
        if not value:
            return None
        try:
            parsed = float(value)
        except ValueError as exc:
            raise ValueError(t("error.must_number", name=name)) from exc
        if parsed < 0:
            raise ValueError(t("error.non_negative", name=name))
        return parsed

    def save() -> None:
        try:
            settle = float(settle_var.get().strip())
            if settle < 0:
                raise ValueError(t("error.non_negative", name=t("settings.settle_seconds")))
            hotkey = hotkey_var.get().strip() or "ctrl+shift+s"
            from .app import _parse_hotkey

            _parse_hotkey(hotkey)
            output = out_var.get().strip()
            new_config = replace(
                config,
                out=Path(output) if output else None,
                open_after=open_var.get(),
                no_clipboard=not clipboard_var.get(),
                no_raise=not raise_var.get(),
                settle=settle,
                hotkey=hotkey,
                language=language_by_label.get(language_var.get(), "auto"),
                radius=optional_int(radius_var, t("settings.corner_radius")),
                padding=optional_int(padding_var, t("settings.padding")),
                no_shadow=not shadow_var.get(),
                shadow_opacity=optional_float(shadow_opacity_var, t("settings.shadow_opacity")),
                shadow_blur=optional_int(shadow_blur_var, t("settings.shadow_blur")),
                shadow_offset=optional_int(shadow_offset_var, t("settings.shadow_offset")),
            )
        except ValueError as exc:
            messagebox.showerror(t("settings.window_title"), str(exc), parent=top)
            return
        handle_close()
        on_save(new_config)

    footer = tk.Frame(shell, bg=_BG)
    footer.pack(fill="x", pady=(18, 0))
    _button(footer, t("settings.save"), save, primary=True).pack(side="right")
    _button(footer, t("settings.cancel"), handle_close).pack(side="right", padx=(0, 10))

    top.update_idletasks()
    width = 540
    height = min(top.winfo_reqheight(), top.winfo_screenheight() - 80)
    sw = top.winfo_screenwidth()
    sh = top.winfo_screenheight()
    x = max(0, (sw - width) // 2)
    y = max(0, (sh - height) // 3)
    top.geometry(f"{width}x{height}+{x}+{y}")
    top.lift()
    top.attributes("-topmost", True)
    top.after(300, lambda: top.attributes("-topmost", False))
    return top


# ---------------------------------------------------------------------------
# Saved notification
# ---------------------------------------------------------------------------


def build_notification(root, config, path, on_click, duration_ms: int = 6000):
    import tkinter as tk

    def t(key: str, **values) -> str:
        return translate(key, config.language, **values)

    win = tk.Toplevel(root)
    win.overrideredirect(True)
    win.attributes("-topmost", True)
    win.configure(bg=_NOTIFY_BG)
    try:
        win.wm_attributes("-alpha", 0.97)
    except Exception:
        pass

    frame = tk.Frame(win, bg=_NOTIFY_BG, padx=16, pady=12, cursor="hand2")
    frame.pack(fill="both", expand=True)

    title_label = tk.Label(
        frame, text="Macshot", bg=_NOTIFY_BG, fg="white",
        font=("Segoe UI", 10, "bold"), anchor="w", cursor="hand2",
    )
    title_label.pack(anchor="w")
    message_label = tk.Label(
        frame,
        text=t("notify.saved_click", path=path),
        bg=_NOTIFY_BG,
        fg="#e8eaed",
        font=("Segoe UI", 9),
        justify="left",
        wraplength=320,
        anchor="w",
        cursor="hand2",
    )
    message_label.pack(anchor="w", pady=(4, 8))

    def close():
        try:
            win.destroy()
        except Exception:
            pass

    def activate(_event=None):
        try:
            on_click()
        finally:
            close()

    open_btn = tk.Button(
        frame,
        text=t("notify.open_folder"),
        command=activate,
        bg=_ACCENT,
        fg="white",
        activebackground=_ACCENT_ACTIVE,
        activeforeground="white",
        relief="flat",
        bd=0,
        padx=12,
        pady=5,
        font=("Segoe UI", 9, "bold"),
        cursor="hand2",
    )
    open_btn.pack(anchor="e")

    for widget in (win, frame, title_label, message_label):
        widget.bind("<Button-1>", activate)
    win.bind("<Escape>", lambda _event: close())

    win.update_idletasks()
    width = max(320, win.winfo_width())
    height = win.winfo_height()
    screen_w = win.winfo_screenwidth()
    screen_h = win.winfo_screenheight()
    x = screen_w - width - 24
    y = screen_h - height - 60
    win.geometry(f"{width}x{height}+{x}+{y}")
    win.after(duration_ms, close)


# ---------------------------------------------------------------------------
# Controller (single UI thread)
# ---------------------------------------------------------------------------


class UiController:
    """Owns one hidden Tk root on a dedicated thread and dispatches UI work."""

    def __init__(self):
        self.root = None
        self._thread = None
        self._ready = threading.Event()
        self._home = None
        self._home_refresh = None
        self._home_visible = False
        self._settings = None

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, name="MacshotUI", daemon=True)
        self._thread.start()
        if not self._ready.wait(10):
            raise RuntimeError("Macshot UI thread failed to start.")

    def _run(self) -> None:
        import tkinter as tk

        root = tk.Tk()
        root.withdraw()
        self.root = root
        self._ready.set()
        root.mainloop()

    @property
    def _ident(self):
        return self._thread.ident if self._thread else None

    def submit(self, fn) -> None:
        root = self.root
        if root is None:
            return
        try:
            root.after(0, fn)
        except Exception:
            pass

    def call(self, fn, timeout: float | None = None):
        if threading.get_ident() == self._ident:
            return fn()
        box: dict = {}
        done = threading.Event()

        def wrapper():
            try:
                box["value"] = fn()
            except Exception as exc:  # noqa: BLE001
                box["error"] = exc
            finally:
                done.set()

        self.submit(wrapper)
        if not done.wait(timeout):
            return None
        if "error" in box:
            raise box["error"]
        return box.get("value")

    def stop(self) -> None:
        def _quit():
            try:
                self.root.quit()
            except Exception:
                pass

        self.submit(_quit)

    # -- Home -----------------------------------------------------------------

    def show_home(self, config, callbacks: HomeCallbacks, last_path) -> None:
        def _do():
            if self._home is not None and self._home.winfo_exists():
                if self._home_refresh:
                    self._home_refresh(last_path)
                self._home.deiconify()
                self._home.lift()
                self._home_visible = True
                return
            top, refresh = build_home(
                self.root, config, callbacks, last_path, on_destroy=self._on_home_destroy
            )
            self._home = top
            self._home_refresh = refresh
            self._home_visible = True

        self.submit(_do)

    def _on_home_destroy(self) -> None:
        self._home = None
        self._home_refresh = None
        self._home_visible = False

    def rebuild_home_if_open(self, config, callbacks: HomeCallbacks, last_path) -> None:
        """Recreate the Home window in place (e.g. after a language change)."""

        def _do():
            if self._home is None or not self._home.winfo_exists():
                return
            try:
                self._home.destroy()
            except Exception:
                pass
            top, refresh = build_home(
                self.root, config, callbacks, last_path, on_destroy=self._on_home_destroy
            )
            self._home = top
            self._home_refresh = refresh
            self._home_visible = True

        self.submit(_do)

    def hide_home_for_capture(self) -> bool:
        def _hide():
            if self._home is not None and self._home.winfo_exists() and self._home_visible:
                self._home.withdraw()
                self._home_visible = False
                return True
            return False

        return bool(self.call(_hide))

    def reshow_home(self, last_path=None) -> None:
        def _do():
            if self._home is not None and self._home.winfo_exists():
                if last_path is not None and self._home_refresh:
                    self._home_refresh(last_path)
                self._home.deiconify()
                self._home.lift()
                self._home_visible = True

        self.submit(_do)

    # -- Settings -------------------------------------------------------------

    def show_settings(self, config, default_out_dir, on_save) -> None:
        def _do():
            if self._settings is not None and self._settings.winfo_exists():
                self._settings.deiconify()
                self._settings.lift()
                self._settings.focus_force()
                return
            self._settings = build_settings(
                self.root, config, default_out_dir, on_save=on_save,
                on_destroy=self._on_settings_destroy,
            )

        self.submit(_do)

    def _on_settings_destroy(self) -> None:
        self._settings = None

    # -- Notification ---------------------------------------------------------

    def show_notification(self, config, path, on_click) -> None:
        self.submit(lambda: build_notification(self.root, config, path, on_click))

    # -- Pickers (run on the UI thread, block the caller) ---------------------

    def pick_window(self, language):
        from .picker import pick_window

        return self.call(lambda: pick_window(self.root, language))

    def pick_region(self, mode, language):
        from .picker import pick_region

        return self.call(lambda: pick_region(mode, self.root, language))

    def pick_freeform(self, language):
        from .picker import pick_freeform_region

        return self.call(lambda: pick_freeform_region(self.root, language))
