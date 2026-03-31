from __future__ import annotations

from functools import lru_cache
import json
from pathlib import Path
from typing import Any

from homeassistant.core import HomeAssistant

from .const import DOMAIN


_TRANSLATIONS_DIR = Path(__file__).resolve().parent / "translations"


def _normalize_language(language: str | None) -> str:
    if not language:
        return "en"
    lowered = language.replace("_", "-").lower()
    if lowered.startswith("zh"):
        return "zh-Hans"
    if lowered.startswith("ja"):
        return "ja"
    if lowered.startswith("ko"):
        return "ko"
    if lowered.startswith("fr"):
        return "fr"
    if lowered.startswith("ru"):
        return "ru"
    if lowered.startswith("es"):
        return "es"
    if lowered.startswith("en"):
        return "en"
    return language


@lru_cache(maxsize=32)
def _load_language(language: str) -> dict[str, Any]:
    path = _TRANSLATIONS_DIR / f"{language}.json"
    if not path.exists():
        path = _TRANSLATIONS_DIR / "en.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except OSError:
        return {}


def _deep_get(data: dict[str, Any], dotted_key: str) -> str | None:
    cur: Any = data
    for part in dotted_key.split("."):
        if not isinstance(cur, dict):
            return None
        cur = cur.get(part)
    return cur if isinstance(cur, str) else None


def t(
    hass: HomeAssistant,
    dotted_key: str,
    default: str | None = None,
    **placeholders: Any,
) -> str:
    language = _normalize_language(getattr(hass.config, "language", None))
    data = _load_language(language)
    value = _deep_get(data, dotted_key)
    if value is None and language != "en":
        value = _deep_get(_load_language("en"), dotted_key)
    if value is None:
        value = default if default is not None else dotted_key
    try:
        return value.format(**placeholders)
    except Exception:
        return value


def err(hass: HomeAssistant, key: str, default: str) -> str:
    return t(hass, f"localize.errors.{key}", default=default)


def cal(hass: HomeAssistant, key: str, default: str) -> str:
    return t(hass, f"localize.calendar.{key}", default=default)


def integration_name(hass: HomeAssistant) -> str:
    return t(hass, "localize.integration.name", default=DOMAIN)

