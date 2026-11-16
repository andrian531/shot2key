"""User settings (API keys, default engines) stored in ``data/settings.json``."""

from __future__ import annotations

import json
import threading
from typing import Any

import config

_LOCK = threading.RLock()

SECRET_KEYS = ("gemini_api_key", "openai_api_key")


def load() -> dict[str, Any]:
    path = config.get_settings_path()
    data: dict[str, Any] = dict(config.DEFAULT_SETTINGS)
    if path.is_file():
        try:
            stored = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(stored, dict):
                data.update({k: v for k, v in stored.items() if k in config.DEFAULT_SETTINGS})
        except (OSError, json.JSONDecodeError):
            pass
    return data


def save(values: dict[str, Any]) -> dict[str, Any]:
    """Merge ``values`` into the stored settings; empty secrets are ignored."""
    with _LOCK:
        current = load()
        for key, value in values.items():
            if key not in config.DEFAULT_SETTINGS:
                continue
            if key in SECRET_KEYS and value in (None, ""):
                continue
            current[key] = value
        path = config.get_settings_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(current, ensure_ascii=False, indent=2), encoding="utf-8")
        return current


def masked() -> dict[str, Any]:
    """Settings safe to send to the browser: secrets become ``set``/``unset``."""
    data = load()
    for key in SECRET_KEYS:
        value = str(data.get(key) or "")
        data[key] = ""
        data[f"{key}_set"] = bool(value)
    return data
