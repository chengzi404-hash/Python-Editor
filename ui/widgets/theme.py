"""UI theme registry.

Themes are defined as JSON files under ``data/theme/`` and loaded at runtime.
Each JSON file describes the full set of attributes consumed by widgets and
the code-area highlighter (``CODE_HIGHLIGHTS``). See
``data/theme/dark.json`` for the schema.
"""

from __future__ import annotations

import contextlib
import json
import os
import sys
from collections.abc import Callable
from typing import Any, ClassVar


class Theme:
    """A single UI theme. Attributes are populated from a JSON dict."""

    name: str = "Base"

    CODE_HIGHLIGHTS: ClassVar[dict[str, dict[str, str]]] = {}

    def __init__(self, **attrs: Any) -> None:
        for key, value in attrs.items():
            setattr(self, key, value)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Theme:
        payload = dict(data)
        payload.pop("default", None)
        return cls(**payload)


def _load_themes_from_disk() -> list[Theme]:
    """Load every ``*.json`` theme file from ``data/theme/``.

    Files are sorted by name for deterministic ordering. The theme marked with
    ``"default": true`` is placed first; if none is marked, the first sorted
    entry is used as the initial active theme.
    """
    from core.data import theme_path

    directory = theme_path()
    if not os.path.isdir(directory):
        return []

    themes: list[Theme] = []
    default_theme: Theme | None = None
    for filename in sorted(os.listdir(directory)):
        if not filename.endswith(".json"):
            continue
        full_path = os.path.join(directory, filename)
        try:
            with open(full_path, encoding="utf-8") as fh:
                raw = json.load(fh)
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(raw, dict):
            continue
        theme_obj = Theme.from_dict(raw)
        if raw.get("default") and default_theme is None:
            default_theme = theme_obj
        themes.append(theme_obj)

    if default_theme is not None and themes and themes[0] is not default_theme:
        themes.remove(default_theme)
        themes.insert(0, default_theme)
    return themes


_themes: list[Theme] = _load_themes_from_disk()
_current: Theme = _themes[0] if _themes else Theme(name="Default")
_listeners: list[Callable[[Theme], None]] = []


def available() -> list[Theme]:
    return list(_themes)


def by_name(name: str) -> Theme | None:
    for t in _themes:
        if t.name == name:
            return t
    return None


def current() -> Theme:
    return _current


def on_change(callback: Callable[[Theme], None]) -> None:
    _listeners.append(callback)


def off_change(callback: Callable[[Theme], None]) -> None:
    with contextlib.suppress(ValueError):
        _listeners.remove(callback)


def reload() -> None:
    """Re-read themes from disk. The current theme is preserved by name."""
    global _themes, _current
    current_name = _current.name if _themes else None
    _themes = _load_themes_from_disk()
    if _themes:
        restored = by_name(current_name) if current_name else None
        _current = restored or _themes[0]


def set_theme(theme_obj: Theme, *, refresh_root=None) -> None:
    global _current
    if _current is theme_obj:
        return
    _current = theme_obj
    _sync_code_highlights(theme_obj)
    if refresh_root is not None:
        apply_theme_recursive(refresh_root)
    for cb in list(_listeners):
        with contextlib.suppress(Exception):
            cb(theme_obj)


def _sync_code_highlights(theme_obj: Theme) -> None:
    """Push this theme's CODE_HIGHLIGHTS into the highlighter."""
    highlights = getattr(theme_obj, "CODE_HIGHLIGHTS", None)
    if not highlights:
        return
    try:
        from core.language.highlighter import themes as _highlight_themes
    except Exception:
        return
    with contextlib.suppress(Exception):
        _highlight_themes.set_tokens(highlights)


def apply_theme_recursive(widget) -> None:
    """Walk the widget tree and call _apply_theme() on every themed widget."""
    apply_fn = getattr(widget, "_apply_theme", None)
    if apply_fn is not None:
        with contextlib.suppress(Exception):
            apply_fn()
    try:
        children = widget.winfo_children()
    except Exception:
        children = []
    for child in children:
        apply_theme_recursive(child)


def __getattr__(name: str):
    if name.startswith("_"):
        raise AttributeError(name)
    try:
        return getattr(_current, name)
    except AttributeError:
        raise AttributeError(f"theme has no attribute {name!r}") from None


FOLLOW_SYSTEM_THEME: dict = {
    "dark": "Dark",
    "light": "Light",
    "default": "Dark",
}

_DEFAULT_FOLLOW_SYSTEM_THEME: dict = dict(FOLLOW_SYSTEM_THEME)

_follow_root = None
_follow_after_id = None
_follow_enabled = False
_follow_mapping: dict | None = None


def _read_os_theme() -> str | None:
    """Return 'dark', 'light', or None if not detectable."""
    if not sys.platform.startswith("win"):
        try:
            from subprocess import run

            r = run(
                ["defaults", "read", "-g", "AppleInterfaceStyle"],
                capture_output=True,
                text=True,
                timeout=2,
            )
            if r.returncode == 0 and r.stdout.strip().lower() == "dark":
                return "dark"
            if r.returncode == 0:
                return "light"
        except Exception:
            pass
        return None
    try:
        import winreg

        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
        ) as key:
            value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
            return "light" if value == 1 else "dark"
    except Exception:
        return None


def _resolve_target_name(os_theme: str) -> str | None:
    mapping = _follow_mapping if _follow_mapping is not None else _DEFAULT_FOLLOW_SYSTEM_THEME
    return mapping.get(os_theme) or mapping.get("default")


def follow_system(root=None, *, mapping: dict | None = None, poll_interval_ms: int = 1500) -> bool:
    """Start following the OS appearance. Pass the Tk root for live polling.

    Returns True if the OS theme was applied immediately, False otherwise.
    """
    global _follow_root, _follow_after_id, _follow_enabled, _follow_mapping

    if mapping is not None:
        merged = dict(_DEFAULT_FOLLOW_SYSTEM_THEME)
        merged.update(mapping)
        _follow_mapping = merged
    elif _follow_mapping is None:
        _follow_mapping = dict(_DEFAULT_FOLLOW_SYSTEM_THEME)

    applied = False
    os_theme = _read_os_theme()
    if os_theme is not None:
        target_name = _resolve_target_name(os_theme)
        if target_name:
            target = by_name(target_name)
            if target is not None and target is not _current:
                set_theme(target)
                applied = True
                if root is not None:
                    apply_theme_recursive(root)

    _follow_enabled = True
    _follow_root = root

    if root is not None:
        _schedule_poll(root, poll_interval_ms)
    return applied


def _schedule_poll(root, interval_ms: int) -> None:
    global _follow_after_id
    if not _follow_enabled or root is None:
        return
    with contextlib.suppress(Exception):
        _follow_after_id = root.after(interval_ms, _poll, root, interval_ms)


def _poll(root, interval_ms: int) -> None:
    global _follow_after_id, _follow_enabled
    if not _follow_enabled:
        return
    os_theme = _read_os_theme()
    if os_theme is not None:
        target_name = _resolve_target_name(os_theme)
        if target_name:
            target = by_name(target_name)
            if target is not None and target is not _current:
                set_theme(target)
                apply_theme_recursive(root)
    _schedule_poll(root, interval_ms)


def stop_following() -> None:
    global _follow_enabled, _follow_root, _follow_after_id, _follow_mapping
    _follow_enabled = False
    if _follow_root is not None and _follow_after_id is not None:
        with contextlib.suppress(Exception):
            _follow_root.after_cancel(_follow_after_id)
    _follow_root = None
    _follow_after_id = None
    _follow_mapping = None
