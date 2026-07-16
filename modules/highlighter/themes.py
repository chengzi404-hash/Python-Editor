from __future__ import annotations

import contextlib
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


@dataclass
class HighlightTheme:
    name: str
    label: str = ""
    tokens: dict[str, dict[str, Any]] = field(default_factory=dict)
    description: str = ""


def _default_dark_tokens() -> dict[str, dict[str, Any]]:
    return {
        "keyword": {"foreground": "#569cd6"},
        "builtin": {"foreground": "#dcdcaa"},
        "string": {"foreground": "#ce9178"},
        "number": {"foreground": "#b5cea8"},
        "comment": {"foreground": "#6a9955"},
        "identifier": {"foreground": "#9cdcfe"},
        "operator": {"foreground": "#d4d4d4"},
        "punctuation": {"foreground": "#d4d4d4"},
        "function": {"foreground": "#dcdcaa"},
        "class": {"foreground": "#4ec9b0"},
        "struct": {"foreground": "#4ec9b0"},
        "preprocessor": {"foreground": "#9b9b9b"},
        "decorator": {"foreground": "#dcdcaa"},
        "self": {"foreground": "#569cd6"},
        "type": {"foreground": "#4ec9b0"},
        "module": {"foreground": "#4fc1ff"},
        "key": {"foreground": "#9cdcfe"},
        "tag": {"foreground": "#569cd6"},
        "timestamp": {"foreground": "#6a9955"},
        "level_debug": {"foreground": "#808080"},
        "level_info": {"foreground": "#4ec9b0"},
        "level_warn": {"foreground": "#dcdcaa"},
        "level_error": {"foreground": "#f44747"},
        "level_critical": {"foreground": "#ff0000"},
    }


def _default_light_tokens() -> dict[str, dict[str, Any]]:
    return {
        "keyword": {"foreground": "#0000ff"},
        "builtin": {"foreground": "#795e26"},
        "string": {"foreground": "#a31515"},
        "number": {"foreground": "#098658"},
        "comment": {"foreground": "#008000"},
        "identifier": {"foreground": "#001080"},
        "operator": {"foreground": "#000000"},
        "punctuation": {"foreground": "#000000"},
        "function": {"foreground": "#795e26"},
        "class": {"foreground": "#267f99"},
        "struct": {"foreground": "#267f99"},
        "preprocessor": {"foreground": "#808080"},
        "decorator": {"foreground": "#795e26"},
        "self": {"foreground": "#0000ff"},
        "type": {"foreground": "#267f99"},
        "module": {"foreground": "#008080"},
        "key": {"foreground": "#001080"},
        "tag": {"foreground": "#800000"},
        "timestamp": {"foreground": "#008000"},
        "level_debug": {"foreground": "#808080"},
        "level_info": {"foreground": "#267f99"},
        "level_warn": {"foreground": "#795e26"},
        "level_error": {"foreground": "#ff0000"},
        "level_critical": {"foreground": "#ff0000"},
    }


def _solarized_dark_tokens() -> dict[str, dict[str, Any]]:
    return {
        "keyword": {"foreground": "#859900"},
        "builtin": {"foreground": "#b58900"},
        "string": {"foreground": "#2aa198"},
        "number": {"foreground": "#d33682"},
        "comment": {"foreground": "#586e75"},
        "identifier": {"foreground": "#93a1a1"},
        "operator": {"foreground": "#93a1a1"},
        "punctuation": {"foreground": "#93a1a1"},
        "function": {"foreground": "#b58900"},
        "class": {"foreground": "#268bd2"},
        "struct": {"foreground": "#268bd2"},
        "preprocessor": {"foreground": "#586e75"},
        "decorator": {"foreground": "#b58900"},
        "self": {"foreground": "#859900"},
        "type": {"foreground": "#268bd2"},
        "module": {"foreground": "#268bd2"},
        "key": {"foreground": "#93a1a1"},
        "tag": {"foreground": "#859900"},
        "timestamp": {"foreground": "#586e75"},
        "level_debug": {"foreground": "#586e75"},
        "level_info": {"foreground": "#268bd2"},
        "level_warn": {"foreground": "#b58900"},
        "level_error": {"foreground": "#dc322f"},
        "level_critical": {"foreground": "#dc322f"},
    }


_themes: dict[str, HighlightTheme] = {}
_current_name: str = "Default Dark"
_listeners: list[Callable[[str], None]] = []


def register(theme: HighlightTheme) -> None:
    _themes[theme.name] = theme


def unregister(name: str) -> None:
    _themes.pop(name, None)


def get(name: str) -> HighlightTheme | None:
    return _themes.get(name)


def available() -> list[HighlightTheme]:
    return list(_themes.values())


def available_names() -> list[str]:
    return list(_themes.keys())


def current_name() -> str:
    return _current_name


def current() -> HighlightTheme:
    t = _themes.get(_current_name)
    if t is None:
        names = list(_themes.keys())
        fallback = names[0] if names else "Default Dark"
        return _themes.get(fallback, HighlightTheme(name="Default Dark", tokens={}))
    return t


def tokens(name: str | None = None) -> dict[str, dict[str, Any]]:
    t = get(name or _current_name)
    if t is None:
        return {}
    return t.tokens


def set_theme(name: str) -> None:
    global _current_name
    if name not in _themes:
        return
    if _current_name == name:
        return
    _current_name = name
    for cb in list(_listeners):
        with contextlib.suppress(Exception):
            cb(name)


def on_change(callback: Callable[[str], None]) -> None:
    _listeners.append(callback)


def off_change(callback: Callable[[str], None]) -> None:
    with contextlib.suppress(ValueError):
        _listeners.remove(callback)


register(
    HighlightTheme(
        name="Default Dark",
        label="Default Dark",
        tokens=_default_dark_tokens(),
        description="VS Code Dark+ inspired syntax highlighting",
    )
)
register(
    HighlightTheme(
        name="Default Light",
        label="Default Light",
        tokens=_default_light_tokens(),
        description="VS Code Light+ inspired syntax highlighting",
    )
)
register(
    HighlightTheme(
        name="Solarized Dark",
        label="Solarized Dark",
        tokens=_solarized_dark_tokens(),
        description="Solarized Dark syntax highlighting",
    )
)


__all__ = [
    "HighlightTheme",
    "available",
    "available_names",
    "current",
    "current_name",
    "get",
    "off_change",
    "on_change",
    "register",
    "set_theme",
    "tokens",
    "unregister",
]
