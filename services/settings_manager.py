"""
Persistent LLM settings manager.

Reads / writes  DATA_DIR/settings.json  and keeps Config.LLM_* in sync.
"""

import json
import os
import threading
from config import Config

_SETTINGS_FILE = os.path.join(Config.DATA_DIR, "settings.json")
_lock = threading.Lock()

# Keys we manage (mapped to Config class-attribute names)
_KEYS = {
    "api_key":     "LLM_API_KEY",
    "base_url":    "LLM_BASE_URL",
    "model":       "LLM_MODEL",
    "max_tokens":  "LLM_MAX_TOKENS",
    "temperature": "LLM_TEMPERATURE",
}


def _read_file() -> dict:
    if not os.path.isfile(_SETTINGS_FILE):
        return {}
    with open(_SETTINGS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _write_file(data: dict):
    os.makedirs(os.path.dirname(_SETTINGS_FILE), exist_ok=True)
    with open(_SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _apply_to_config(data: dict):
    """Push persisted values into Config class attributes."""
    for json_key, attr in _KEYS.items():
        if json_key not in data:
            continue
        val = data[json_key]
        if isinstance(val, str):
            val = val.strip()
        if attr == "LLM_MAX_TOKENS":
            val = int(val)
        elif attr == "LLM_TEMPERATURE":
            val = float(val)
        elif attr == "LLM_BASE_URL" and isinstance(val, str):
            val = val.rstrip("/")
        setattr(Config, attr, val)


def load():
    """Load settings.json (if any) and override Config.LLM_* values."""
    with _lock:
        data = _read_file()
        if data:
            _apply_to_config(data)


def get_settings() -> dict:
    """Return current settings with the API key masked."""
    with _lock:
        return {
            "api_key":     _mask_key(Config.LLM_API_KEY),
            "base_url":    Config.LLM_BASE_URL,
            "model":       Config.LLM_MODEL,
            "max_tokens":  Config.LLM_MAX_TOKENS,
            "temperature": Config.LLM_TEMPERATURE,
        }


def update_settings(data: dict) -> dict:
    """
    Merge *data* into saved settings and update Config.

    - Empty string for api_key means "keep existing".
    - Returns the (masked) settings after update.
    """
    with _lock:
        current = _read_file()

        for json_key in _KEYS:
            if json_key not in data:
                continue
            value = data[json_key]
            # Trim whitespace from all string values
            if isinstance(value, str):
                value = value.strip()
            # Empty api_key → preserve current
            if json_key == "api_key" and (value is None or value == ""):
                continue
            if json_key == "max_tokens":
                value = int(value)
            elif json_key == "temperature":
                value = float(value)
            elif json_key == "base_url" and isinstance(value, str):
                value = value.rstrip("/")
            current[json_key] = value

        _write_file(current)
        _apply_to_config(current)

    return get_settings()


def _mask_key(key: str) -> str:
    if not key:
        return ""
    if len(key) <= 4:
        return "****"
    return "*" * (len(key) - 4) + key[-4:]
