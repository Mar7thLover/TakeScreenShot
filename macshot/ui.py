"""Tkinter desktop windows for Macshot home and settings."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from .app import AppConfig

_BG = "#f6f7fb"
_CARD = "#ffffff"
_TEXT = "#1f2328"
_MUTED = "#6b7280"
_ACCENT = "#2f80ed"


def _center(root, width: int, height: int) -> None:
    root.update_idletasks()
    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()
    x = max(0, (sw - width) // 2)
    y = max(0, (sh - height) // 2)
    root.geometry(f"{width}x{height}+{x}+{y}")


def _button(parent, text: str, command: Callable[[], None], primary: bool = False):
    import tkinter as tk

    return tk.Button(
        parent,
        text=text,
        command=command,
        bg=_ACCENT if primary else "#eef2f7",
        fg="white" if primary else _TEXT,
        activebackground="#1f6fd1" if primary else "#e2e8f0",
        activeforeground="white" if primary else _TEXT,
        relief="flat",
        bd=0,
        padx=14,
        pady=10,
        font=("Segoe UI", 10, "bold"),
        cursor="hand2",
    )


def show_home(
    config: AppConfig,
    *,
    on_capture_window: Callable[[], None],
    on_capture_full: Callable[[], None],
    on_capture_circle: Callable[[], None],
    on_capture_free: Callable[[], None],
    on_settings: Callable[[], None],
    on_open_folder: Callable[[], None],
    last_path: Path | None = None,
) -> None:
    """Show the desktop home window."""
    import tkinter as tk
    from tkinter import messagebox

    root = tk.Tk()
    root.title("Macshot")
    root.configure(bg=_BG)
    root.resizable(False, False)
    _center(root, 560, 430)

    shell = tk.Frame(root, bg=_BG, padx=22, pady=22)
    shell.pack(fill="both", expand=True)

    header = tk.Frame(shell, bg=_BG)
    header.pack(fill="x")
    tk.Label(
        header,
        text="Macshot",
        bg=_BG,
        fg=_TEXT,
        font=("Segoe UI", 22, "bold"),
    ).pack(anchor="w")
    tk.Label(
        header,
        text="macOS-style screenshots for Windows",
        bg=_BG,
        fg=_MUTED,
        font=("Segoe UI", 10),
    ).pack(anchor="w", pady=(2, 0))

    card = tk.Frame(shell, bg=_CARD, padx=18, pady=18)
    card.pack(fill="x", pady=(20, 14))

    tk.Label(
        card,
        text=f"Hotkey: {config.hotkey}",
        bg=_CARD,
        fg=_TEXT,
        font=("Segoe UI", 11, "bold"),
    ).pack(anchor="w")
    out_dir = config.out or Path.home() / "Pictures" / "Macshot"
    tk.Label(
        card,
        text=f"Output: {out_dir}",
        bg=_CARD,
        fg=_MUTED,
        font=("Segoe UI", 9),
        wraplength=480,
        justify="left",
    ).pack(anchor="w", pady=(5, 0))
    last_text = f"Last saved: {last_path}" if last_path else "Last saved: none this session"
    tk.Label(
        card,
        text=last_text,
        bg=_CARD,
        fg=_MUTED,
        font=("Segoe UI", 9),
        wraplength=480,
        justify="left",
    ).pack(anchor="w", pady=(4, 0))

    grid = tk.Frame(shell, bg=_BG)
    grid.pack(fill="x")

    def run_action(callback: Callable[[], None]) -> None:
        root.withdraw()

        def invoke():
            try:
                callback()
            except Exception as exc:
                messagebox.showerror("Macshot", str(exc))
            finally:
                try:
                    root.deiconify()
                    root.lift()
                except Exception:
                    pass

        root.after(120, invoke)

    actions = [
        ("Capture Window", on_capture_window, True),
        ("Capture Full Screen", on_capture_full, False),
        ("Capture Circle", on_capture_circle, False),
        ("Free Screenshot", on_capture_free, False),
    ]
    for index, (label, callback, primary) in enumerate(actions):
        btn = _button(grid, label, lambda cb=callback: run_action(cb), primary=primary)
        btn.grid(row=index // 2, column=index % 2, sticky="ew", padx=6, pady=6)
    grid.columnconfigure(0, weight=1)
    grid.columnconfigure(1, weight=1)

    footer = tk.Frame(shell, bg=_BG)
    footer.pack(fill="x", pady=(14, 0))
    _button(footer, "Settings", lambda: run_action(on_settings)).pack(side="left")
    _button(footer, "Open Output Folder", lambda: run_action(on_open_folder)).pack(
        side="left", padx=(10, 0)
    )
    _button(footer, "Close", root.destroy).pack(side="right")

    root.mainloop()


def show_settings(config: AppConfig, default_out_dir: Path) -> AppConfig | None:
    """Show settings window and return an updated config when saved."""
    import tkinter as tk
    from tkinter import filedialog, messagebox

    root = tk.Tk()
    root.title("Macshot Settings")
    root.configure(bg=_BG)
    root.resizable(False, False)
    _center(root, 560, 560)

    result = {"config": None}
    shell = tk.Frame(root, bg=_BG, padx=22, pady=22)
    shell.pack(fill="both", expand=True)

    tk.Label(
        shell,
        text="Settings",
        bg=_BG,
        fg=_TEXT,
        font=("Segoe UI", 20, "bold"),
    ).pack(anchor="w")

    form = tk.Frame(shell, bg=_CARD, padx=18, pady=16)
    form.pack(fill="x", pady=(16, 0))

    out_var = tk.StringVar(value=str(config.out or default_out_dir))
    hotkey_var = tk.StringVar(value=config.hotkey)
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

    def row(label: str, widget, browse=None) -> None:
        frame = tk.Frame(form, bg=_CARD)
        frame.pack(fill="x", pady=5)
        tk.Label(frame, text=label, bg=_CARD, fg=_TEXT, width=16, anchor="w").pack(
            side="left"
        )
        widget.pack(side="left", fill="x", expand=True)
        if browse:
            _button(frame, "Browse", browse).pack(side="left", padx=(8, 0))

    def entry(var):
        return tk.Entry(form, textvariable=var, relief="solid", bd=1, font=("Segoe UI", 10))

    def browse_out() -> None:
        selected = filedialog.askdirectory(initialdir=out_var.get() or str(default_out_dir))
        if selected:
            out_var.set(selected)

    row("Output folder", entry(out_var), browse_out)
    row("Hotkey", entry(hotkey_var))
    row("Settle seconds", entry(settle_var))
    row("Corner radius", entry(radius_var))
    row("Padding", entry(padding_var))
    row("Shadow opacity", entry(shadow_opacity_var))
    row("Shadow blur", entry(shadow_blur_var))
    row("Shadow offset", entry(shadow_offset_var))

    checks = tk.Frame(form, bg=_CARD)
    checks.pack(fill="x", pady=(10, 0))
    for text, var in [
        ("Open folder after capture", open_var),
        ("Copy result to clipboard", clipboard_var),
        ("Bring window to front before capture", raise_var),
        ("Enable shadow", shadow_var),
    ]:
        tk.Checkbutton(
            checks,
            text=text,
            variable=var,
            bg=_CARD,
            fg=_TEXT,
            activebackground=_CARD,
            anchor="w",
        ).pack(fill="x")

    def optional_int(var: tk.StringVar, name: str) -> int | None:
        value = var.get().strip()
        if not value:
            return None
        try:
            parsed = int(value)
        except ValueError as exc:
            raise ValueError(f"{name} must be an integer.") from exc
        if parsed < 0:
            raise ValueError(f"{name} must be zero or greater.")
        return parsed

    def optional_float(var: tk.StringVar, name: str) -> float | None:
        value = var.get().strip()
        if not value:
            return None
        try:
            parsed = float(value)
        except ValueError as exc:
            raise ValueError(f"{name} must be a number.") from exc
        if parsed < 0:
            raise ValueError(f"{name} must be zero or greater.")
        return parsed

    def save() -> None:
        try:
            settle = float(settle_var.get().strip())
            if settle < 0:
                raise ValueError("Settle seconds must be zero or greater.")
            hotkey = hotkey_var.get().strip() or "ctrl+shift+s"
            from .app import _parse_hotkey

            _parse_hotkey(hotkey)
            output = out_var.get().strip()
            result["config"] = replace(
                config,
                out=Path(output) if output else None,
                open_after=open_var.get(),
                no_clipboard=not clipboard_var.get(),
                no_raise=not raise_var.get(),
                settle=settle,
                hotkey=hotkey,
                radius=optional_int(radius_var, "Corner radius"),
                padding=optional_int(padding_var, "Padding"),
                no_shadow=not shadow_var.get(),
                shadow_opacity=optional_float(shadow_opacity_var, "Shadow opacity"),
                shadow_blur=optional_int(shadow_blur_var, "Shadow blur"),
                shadow_offset=optional_int(shadow_offset_var, "Shadow offset"),
            )
        except ValueError as exc:
            messagebox.showerror("Macshot Settings", str(exc))
            return
        root.destroy()

    footer = tk.Frame(shell, bg=_BG)
    footer.pack(fill="x", pady=(14, 0))
    _button(footer, "Save", save, primary=True).pack(side="right")
    _button(footer, "Cancel", root.destroy).pack(side="right", padx=(0, 10))

    root.mainloop()
    return result["config"]
