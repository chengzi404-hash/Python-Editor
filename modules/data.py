"""``modules.data`` — Unified data file access interface.

All data files are loaded from the ``data/`` directory and accessed through
the API exposed by this module.

Supported submodules:

* ``i18n`` — Translation files, locales directory path via :func:`i18n_path`.
* ``cache`` — Runtime cache (library DOM etc.), cache directory path via :func:`cache_path`.
"""

from __future__ import annotations

import os

_ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
_CACHE_ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cache")


def i18n_path(*parts: str) -> str:
    """Return absolute path to ``data/i18n/<parts>``."""
    return os.path.join(_ROOT, "i18n", *parts)


def data_path(*parts: str) -> str:
    """Return absolute path to ``data/<parts>``."""
    return os.path.join(_ROOT, *parts)


def data_dir() -> str:
    """Return the data root directory path."""
    return _ROOT


def suggestions_path(*parts: str) -> str:
    """Return absolute path to ``data/suggestions/<parts>``."""
    return os.path.join(_ROOT, "suggestions", *parts)


def cache_dir() -> str:
    """Return cache root directory path (``cache/`` under project root); created if missing."""
    os.makedirs(_CACHE_ROOT, exist_ok=True)
    return _CACHE_ROOT


def cache_path(*parts: str) -> str:
    """Return absolute path to ``cache/<parts>``; parent directory is created automatically."""
    base = cache_dir()
    target = os.path.join(base, *parts) if parts else base
    if parts:
        os.makedirs(os.path.dirname(target) or base, exist_ok=True)
    return target


__all__ = ["cache_dir", "cache_path", "data_dir", "data_path", "i18n_path", "suggestions_path"]
