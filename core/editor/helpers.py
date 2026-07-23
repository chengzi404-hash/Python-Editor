"""Pure helpers and constants used by the CodeEditor app.

This module hosts stateless utilities so the main :mod:`core.editor.app`
module can stay focused on top-level orchestration.
"""

from __future__ import annotations

import os
import re
import tempfile
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


NAVIGATION_KEYS: frozenset[str] = frozenset(
    {
        "Up",
        "Down",
        "Left",
        "Right",
        "Home",
        "End",
        "Page_Up",
        "Page_Down",
        "Tab",
        "Escape",
    }
)


AUTOSAVE_TOKEN_FIELDS: dict[str, str] = {
    "year": "{year:04d}",
    "month": "{month:02d}",
    "day": "{day:02d}",
    "hour": "{hour:02d}",
    "minute": "{minute:02d}",
    "second": "{second:02d}",
    "unix.seconds": "{unix_seconds}",
    "unix.float": "{unix_float}",
}


def strip_common_prefix(suggestion: str, partial: str) -> str:
    """Return ``suggestion`` with the leading ``partial`` removed if present."""
    if not suggestion or not partial:
        return suggestion
    if suggestion.startswith(partial):
        return suggestion[len(partial) :]
    return suggestion


def pick_local_completion(expert, *, code: str, position: int, partial: str) -> str | None:
    """Ask the local suggestion expert for a completion tail relative to ``partial``."""
    if expert is None or not code:
        return None
    from core.language.suggestion import SuggestionBlock

    try:
        block = SuggestionBlock(code=code, position=position)
        suggestions = expert.suggest(block)
    except Exception:
        return None
    if not suggestions:
        return None
    partial_lc = partial.lower() if partial else ""
    for item in suggestions:
        if not item.label:
            continue
        if partial_lc and item.label.lower().startswith(partial_lc):
            insert = item.insert or item.label
            if insert.lower().startswith(partial_lc):
                tail = insert[len(partial) :] if partial else insert
                if tail and tail.strip():
                    return tail
    return None


def is_within(path: str, root: str) -> bool:
    """Return True if ``path`` is the same as or nested inside ``root``."""
    if not path or not root:
        return False
    try:
        p = os.path.normcase(os.path.abspath(path))
        r = os.path.normcase(os.path.abspath(root))
    except (OSError, ValueError):
        return False
    if p == r:
        return True
    return p.startswith(r + os.sep)


def tk_shortcut(spec: str) -> str:
    """Translate a ``Ctrl+Shift+X`` style spec into Tk's ``<Control-Shift-x>`` form."""
    parts = [p.strip() for p in spec.split("+") if p.strip()]
    if not parts:
        return "<>"
    key = parts[-1]
    mods = parts[:-1]
    mapping = {
        "ctrl": "Control",
        "control": "Control",
        "shift": "Shift",
        "alt": "Alt",
        "meta": "Meta",
    }
    mod_str = "-".join(mapping.get(m.lower(), m.capitalize()) for m in mods)
    if key.lower() == "space":
        key = "space"
    elif key.lower() == "slash":
        key = "/"
    if mod_str:
        return f"<{mod_str}-{key}>"
    return f"<{key}>"


def human_size(nbytes: int) -> str:
    """Format a byte count as ``"1.2 MB"`` style string."""
    try:
        n = float(max(0, int(nbytes)))
    except (TypeError, ValueError):
        return f"{nbytes} B"
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024.0 or unit == "GB":
            if unit == "B":
                return f"{int(n)} {unit}"
            return f"{n:.1f} {unit}"
        n /= 1024.0
    return f"{nbytes} B"


def format_autosave_path(fmt: str) -> str:
    """Expand ``fmt`` time tokens (e.g. ``{year}``, ``{unix.seconds}``) into a filename."""
    import time

    now = time.localtime()
    ts = time.time()
    # Use underscore-separated keys — Python's ``str.format_map`` treats ``.``
    # as attribute access, which clashes with our token names. The caller can
    # still write ``{unix_seconds}`` in their format string.
    fields = {
        "year": f"{now.tm_year:04d}",
        "month": f"{now.tm_mon:02d}",
        "day": f"{now.tm_mday:02d}",
        "hour": f"{now.tm_hour:02d}",
        "minute": f"{now.tm_min:02d}",
        "second": f"{now.tm_sec:02d}",
        "unix_seconds": f"{int(ts)}",
        "unix_float": f"{ts:.3f}",
    }
    name = fmt.format_map(fields)
    name = "".join(c if c.isalnum() or c in "._- " else "_" for c in name)
    cache = os.path.join(tempfile.gettempdir(), "PythonEditor", "autosave")
    return os.path.join(cache, f"{name}.py")


def detect_lang_from_path(path: str, lang_config: dict | None = None) -> str:
    """Return the language name for ``path``, defaulting to ``"Python"``."""
    from core.editor.lang_config import LANG_CONFIG

    cfg = lang_config if lang_config is not None else LANG_CONFIG
    _, ext = os.path.splitext(path)
    ext = ext.lower()
    for lang, config in cfg.items():
        if config["ext"] == ext:
            return lang
    return "Python"


def find_symbol_definitions(code: str, symbol: str) -> list[tuple[int, str]]:
    """Return ``(line_no, line_text)`` pairs where ``symbol`` is defined in ``code``."""
    results: list[tuple[int, str]] = []
    lines = code.split("\n")

    for ln, line_text in enumerate(lines, start=1):
        stripped = line_text.strip()
        if not stripped or stripped.startswith("#"):
            continue

        m = re.match(
            r"^\s*class\s+(" + re.escape(symbol) + r")\s*(?:\([^()]*\))?\s*:",
            line_text,
        )
        if m:
            results.append((ln, line_text))
            continue

        m = re.match(
            r"^\s*(?:async\s+)?def\s+(" + re.escape(symbol) + r")\s*\(",
            line_text,
        )
        if m:
            results.append((ln, line_text))
            continue

        m = re.match(r"^\s*import\s+.*\b" + re.escape(symbol) + r"\b", line_text)
        if m:
            results.append((ln, line_text))
            continue
        m = re.match(r"^\s*from\s+\S+\s+import\s+.*\b" + re.escape(symbol) + r"\b", line_text)
        if m:
            results.append((ln, line_text))
            continue

        assign_pattern = re.compile(
            r"(?:^|\s)(?:self\.)?\b" + re.escape(symbol) + r"\s*(?::\s*[^=]+)?\s*=\s*"
        )
        if assign_pattern.search(line_text):
            results.append((ln, line_text))
            continue

        decorator_pattern = re.compile(r"^\s*@" + re.escape(symbol) + r"\b")
        if decorator_pattern.match(line_text):
            results.append((ln, line_text))
            continue

    return results
