"""DOM cache for Python libraries — scans installed packages and caches their structure.

Cached data lives under ``cache/python_libs/`` and is keyed by package name.
Each cache entry is a JSON file containing classes, functions, and submodules.

Usage::

    from modules.highlighter.dom_cache import ensure_lib_cache, get_lib_dom

    ensure_lib_cache('os')          # scans and caches if missing/stale
    dom = get_lib_dom('os')         # returns LibraryDOM or None
"""

from __future__ import annotations

import contextlib
import json
import os
import pkgutil
import sys
from dataclasses import asdict, dataclass, field

from modules.data import cache_path

# ──────────────────────────────────────────────────────────────────────────────
# Data model
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class LibraryDOM:
    """Represents the publicly-visible structure of a Python library."""

    name: str                      # package name, e.g. "os"
    version: str = ""              # package version, if discoverable
    classes: list[str] = field(default_factory=list)
    functions: list[str] = field(default_factory=list)
    submodules: list[str] = field(default_factory=list)
    # For submodule attribute caching: lib_name -> {classes, functions}
    submodule_contents: dict[str, dict] = field(default_factory=dict)


# ──────────────────────────────────────────────────────────────────────────────
# Cache paths
# ──────────────────────────────────────────────────────────────────────────────

def _cache_dir() -> str:
    return cache_path("python_libs")


def _cache_file(lib_name: str) -> str:
    """Path to the JSON cache file for ``lib_name``."""
    safe = lib_name.replace(".", "_")
    return os.path.join(_cache_dir(), f"{safe}.json")


# ──────────────────────────────────────────────────────────────────────────────
# Core public API
# ──────────────────────────────────────────────────────────────────────────────

def get_lib_dom(lib_name: str) -> LibraryDOM | None:
    """Return cached DOM for ``lib_name``, or None if not cached."""
    path = _cache_file(lib_name)
    if not os.path.exists(path):
        return None
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        return LibraryDOM(**data)
    except (json.JSONDecodeError, OSError, TypeError):
        return None


def ensure_lib_cache(lib_name: str) -> LibraryDOM | None:
    """Ensure a fresh cache entry exists for ``lib_name``.

    Scans the installed package and writes the DOM to the cache file.
    Returns the new ``LibraryDOM``, or None if the package cannot be resolved.
    """
    dom = _scan_library(lib_name)
    if dom is None:
        return None

    os.makedirs(_cache_dir(), exist_ok=True)
    path = _cache_file(lib_name)
    try:
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(asdict(dom), fh, indent=2, ensure_ascii=False)
    except OSError:
        pass  # non-fatal — cache write failure shouldn't crash the editor

    return dom


def get_or_load_lib_dom(lib_name: str) -> LibraryDOM | None:
    """Return cached DOM if available, otherwise scan and cache it."""
    dom = get_lib_dom(lib_name)
    if dom is not None:
        return dom
    return ensure_lib_cache(lib_name)


# ──────────────────────────────────────────────────────────────────────────────
# Scanning helpers
# ──────────────────────────────────────────────────────────────────────────────

def _scan_library(lib_name: str) -> LibraryDOM | None:
    """Attempt to scan ``lib_name`` and return its ``LibraryDOM``."""

    # 1. Try to import the module and inspect it
    try:
        mod = __import__(lib_name, fromlist=[""])
    except Exception:
        return None

    classes: list[str] = []
    functions: list[str] = []
    submodules: list[str] = []

    # 2. Get public names — prefer __all__ if defined
    if hasattr(mod, "__all__"):
        public: list[str] = mod.__all__
    else:
        public = [n for n in dir(mod) if not n.startswith("_")]

    for name in public:
        try:
            obj = getattr(mod, name)
        except Exception:
            continue

        if isinstance(obj, type):
            classes.append(name)
        elif callable(obj):
            functions.append(name)
        elif hasattr(obj, "__module__") and obj.__module__ != lib_name:
            # Likely a submodule or re-export
            submodules.append(name)

    # 3. Discover submodules via pkgutil (for top-level packages only)
    try:
        # Walk the package path to find submodules
        if hasattr(mod, "__path__"):
            for _importer, modname, _ispkg in pkgutil.iter_modules(mod.__path__, lib_name + "."):
                short = modname.split(".", 1)[-1] if "." in modname else modname
                if short not in submodules:
                    submodules.append(short)
    except Exception:
        pass

    # 4. Capture submodule contents for dot-access highlighting
    submodule_contents: dict[str, dict] = {}
    for sub_name in submodules:
        full_name = f"{lib_name}.{sub_name}"
        sub_mod = None
        try:
            sub_mod = __import__(full_name, fromlist=[""])
        except (Exception, SystemExit):
            # Some packages (e.g. certifi) run argparse sys.exit() when __main__ is invoked
            try:
                # Try importing the submodule directly
                parts = full_name.split(".")
                sub_mod = __import__(full_name, fromlist=[parts[-1]])
            except (Exception, SystemExit):
                continue

        if sub_mod is None:
            continue

        sub_classes: list[str] = []
        sub_functions: list[str] = []

        if hasattr(sub_mod, "__all__"):
            sub_public = sub_mod.__all__
        else:
            sub_public = [n for n in dir(sub_mod) if not n.startswith("_")]

        for attr_name in sub_public:
            try:
                attr = getattr(sub_mod, attr_name)
            except Exception:
                continue
            if isinstance(attr, type):
                sub_classes.append(attr_name)
            elif callable(attr):
                sub_functions.append(attr_name)

        if sub_classes or sub_functions:
            submodule_contents[sub_name] = {
                "classes": sub_classes,
                "functions": sub_functions,
            }

    # 5. Try to get version
    version = ""
    try:
        import importlib.metadata
        version = importlib.metadata.version(lib_name)
    except Exception:
        try:
            import importlib.metadata as m
            version = m.version(lib_name)
        except Exception:
            pass

    return LibraryDOM(
        name=lib_name,
        version=version,
        classes=classes,
        functions=functions,
        submodules=submodules,
        submodule_contents=submodule_contents,
    )


def build_full_cache(progress_callback=None) -> int:
    """Scan all visible top-level packages and cache their DOM.

    Returns the number of packages successfully cached.
    ``progress_callback(current, total)`` is called after each package if provided.
    """
    # Get all top-level packages from sys.modules and pkgutil
    seen: set[str] = set()
    for name in sys.modules:
        if "." not in name:
            seen.add(name)

    # Also scan site-packages via pkgutil
    import site
    site_packages = site.getsitepackages()
    if hasattr(site, "getusersitepackages"):
        site_packages.append(site.getusersitepackages())

    for sp in site_packages:
        if not os.path.isdir(sp):
            continue
        try:
            for _importer, modname, ispkg in pkgutil.iter_modules([sp]):
                if ispkg:
                    seen.add(modname)
        except Exception:
            pass

    # Filter out private/stub packages and stdlib
    STDLIB_MODULES = set(sys.stdlib_module_names)
    to_cache = sorted(
        n for n in seen
        if not n.startswith("_")
        and n not in STDLIB_MODULES
        and not any(p in n for p in ("tests", "test_", "_pytest", "pytest", ".venv", "venv"))
    )

    cached = 0
    total = len(to_cache)
    for i, lib_name in enumerate(to_cache):
        if ensure_lib_cache(lib_name) is not None:
            cached += 1
        if progress_callback:
            progress_callback(i + 1, total)

    return cached


def cache_exists(lib_name: str) -> bool:
    """Return True if a cache entry exists for ``lib_name``."""
    return os.path.exists(_cache_file(lib_name))


def invalidate_lib_cache(lib_name: str) -> None:
    """Remove the cached entry for ``lib_name``."""
    path = _cache_file(lib_name)
    with contextlib.suppress(OSError):
        os.remove(path)
