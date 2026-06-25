"""Small JSON-backed settings store for the desktop app."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

CONFIG_DIR = Path(os.environ.get("APPDATA") or Path.home()) / "Macshot"
CONFIG_PATH = CONFIG_DIR / "settings.json"

_KNOWN_KEYS = {
    "out",
    "open_after",
    "no_clipboard",
    "no_raise",
    "settle",
    "hotkey",
    "language",
    "radius",
    "padding",
    "no_shadow",
    "shadow_opacity",
    "shadow_blur",
    "shadow_offset",
}


def load_settings() -> dict[str, Any]:
    """Return persisted settings, ignoring unknown or malformed data."""
    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except Exception:
        return {}
    if not isinstance(data, dict):
        return {}
    return {key: value for key, value in data.items() if key in _KNOWN_KEYS}


def save_settings(values: dict[str, Any]) -> None:
    """Persist known settings with stable formatting."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    clean = {key: value for key, value in values.items() if key in _KNOWN_KEYS}
    CONFIG_PATH.write_text(
        json.dumps(clean, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
