"""``modules.i18n.translator`` — Core translator implementation.

Translation source: ``modules/i18n/locales/<lang>.json``, JSON object ``{key: text}``.

* Supports ``str.format`` placeholders: ``{name}`` in translations is replaced
  by keyword arguments at call time, e.g. ``t("greeting", name="Alice")``.
* Missing translation fallback: current language key → English (when zh_CN is missing) → key as-is.
  UI never shows blank text due to missing translations.
* Language changes triggered via :meth:`Translator.set_language`; registered
  :data:`I18nListener` callbacks are invoked synchronously.
"""

from __future__ import annotations

import contextlib
import json
import os
import threading
from collections.abc import Callable
from typing import Any

from modules.data import i18n_path

_LOCALE_DIR = i18n_path("locales")

AVAILABLE_LANGUAGES: tuple = ("zh_CN", "en_US")

I18nListener = Callable[[str], None]


def _load_locale(lang: str) -> dict[str, str]:
    """Load translation JSON for a given language. Returns empty dict if file is missing or corrupt.

    Handles BOM but tolerates any parse errors: missing translations are normal
    (fallback handles them), raising exceptions would lock the UI.
    """

    path = os.path.join(_LOCALE_DIR, f"{lang}.json")
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(data, dict):
        return {}
    return {str(k): str(v) for k, v in data.items()}


class Translator:
    """Global translator instance.

    Singleton: obtain via :func:`get_translator`; one instance is shared across
    the entire process to avoid ``t()`` pointing to different languages in
    different modules.
    """

    _FALLBACK_LANG = "en_US"

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._current: str = self._FALLBACK_LANG
        self._tables: dict[str, dict[str, str]] = {}
        self._listeners: list[I18nListener] = []
        self._changing: bool = False
        for lang in AVAILABLE_LANGUAGES:
            self._tables[lang] = _load_locale(lang)

    @property
    def current_language(self) -> str:
        with self._lock:
            return self._current

    @property
    def available_languages(self) -> tuple:
        return AVAILABLE_LANGUAGES

    def set_language(self, lang: str) -> bool:
        """Switch the current language. Returns whether the change actually occurred."""

        if lang not in AVAILABLE_LANGUAGES:
            return False
        with self._lock:
            if self._changing:
                return False
            if lang == self._current:
                return False
            self._changing = True
            self._current = lang
            listeners = list(self._listeners)
        try:
            for cb in listeners:
                with contextlib.suppress(Exception):
                    cb(lang)
            return True
        finally:
            with self._lock:
                self._changing = False

    def add_listener(self, callback: I18nListener) -> None:
        with self._lock:
            if callback in self._listeners:
                return
            self._listeners.append(callback)

    def remove_listener(self, callback: I18nListener) -> None:
        with self._lock:
            with contextlib.suppress(ValueError):
                self._listeners.remove(callback)

    def reload(self) -> None:
        """Re-read all language packs from disk. Useful for tests and immediate effect after edits during development."""

        with self._lock:
            for lang in AVAILABLE_LANGUAGES:
                self._tables[lang] = _load_locale(lang)

    def has(self, key: str, locale: str | None = None) -> bool:
        """Check if a key has a translation in the specified (or current) language."""

        target = locale if locale is not None else self._current
        return key in self._tables.get(target, {})

    def translate(
        self, key: str, default: str | None = None, locale: str | None = None, **kwargs: Any
    ) -> str:
        """Look up the translation for a key.

        Args:
            key — Translation key, e.g. ``"menu.file.new"``.
            default — Fallback text when not found; defaults to the key itself.
            locale — Force a specific language (defaults to current language), useful for plugins rendering across languages.
            **kwargs — Placeholders passed to ``str.format``.

        Returns: The translated string. Never ``None``; missing translations return the key at minimum.
        """

        with self._lock:
            target = locale if locale is not None else self._current
            text = self._tables.get(target, {}).get(key)
            if text is None and target != self._FALLBACK_LANG:
                text = self._tables.get(self._FALLBACK_LANG, {}).get(key)
            if text is None:
                text = default if default is not None else key
        if kwargs:
            try:
                return text.format(**kwargs)
            except (KeyError, IndexError, ValueError):
                # Placeholder mismatch: return original string instead of raising, to prevent UI crash
                return text
        return text


_TRANSLATOR = Translator()


def get_translator() -> Translator:
    """Return the global translator instance."""

    return _TRANSLATOR


def t(key: str, default: str | None = None, **kwargs: Any) -> str:
    """Module-level convenience translation function: equivalent to ``get_translator().translate(...)``."""

    return _TRANSLATOR.translate(key, default=default, **kwargs)


__all__ = [
    "AVAILABLE_LANGUAGES",
    "I18nListener",
    "Translator",
    "get_translator",
    "t",
]
