"""``modules.settings.storage`` — JSON file-based settings persistence base class.

To avoid :class:`~modules.settings.global_settings.GlobalSettings` and
:class:`~modules.settings.project_settings.ProjectSettings` duplicating implementations
for json I/O and thread safety, this file provides an abstract base class :class:`JsonFileSettings`.

* Data is stored as a single JSON object ``{"version": 1, "values": {...}}``.
* All IO operations are serialized via :class:`threading.RLock` for cross-thread safe usage.
* :meth:`save` writes to a temporary file then ``os.replace`` to avoid reading half-written state.
* :meth:`load` tolerates missing disk files or format errors (falls back to defaults).
"""

from __future__ import annotations

import contextlib
import json
import os
import tempfile
import threading
from typing import Any

from .base import (
    Settings,
    SettingsChangeEvent,
    SettingsSchema,
    SettingsScope,
)

CURRENT_VERSION = 1


class JsonFileSettings(Settings):
    """JSON file-based :class:`Settings` base class.

    Subclasses only need to implement :meth:`_resolve_path` to tell "where to write data".
    """

    def __init__(
        self,
        schema: SettingsSchema,
        *,
        scope: SettingsScope,
        path: str | None = None,
        auto_load: bool = True,
    ) -> None:
        super().__init__(schema, scope=scope)
        self._lock = threading.RLock()
        self._path: str | None = path
        self._values: dict[str, Any] = {}
        # Bypass storage: plugin-specific keys (plugins.<id>.*) do not go through schema validation,
        # because plugin IDs are dynamic and unknown at schema registration time.
        self._extras: dict[str, Any] = {}

        if auto_load:
            try:
                self.load()
            except Exception:
                self._values = {}
                self._extras = {}

    def _resolve_path(self) -> str:
        """Subclass must return the absolute path of the JSON file to use.

        When ``path`` is explicitly passed at construction, that path is used directly;
        otherwise this method is called lazily (e.g., based on user home / project directory).
        """

        raise NotImplementedError(
            "JsonFileSettings subclass must implement _resolve_path() or pass path=... explicitly."
        )

    def _ensure_parent_dir(self, path: str) -> None:
        """Ensure the parent directory of ``path`` exists. Default ``os.makedirs(..., exist_ok=True)``."""

        parent = os.path.dirname(path)
        if parent:
            os.makedirs(parent, exist_ok=True)

    @property
    def path(self) -> str:
        """Return the current file path (lazily resolved)."""

        if self._path is None:
            self._path = self._resolve_path()
        return self._path

    def _raw_default(self, key: str) -> Any:
        spec = self.spec(key)
        return spec.default if spec is not None else None

    @staticmethod
    def _is_plugin_key(key: str) -> bool:
        """Check whether ``key`` belongs to the plugin namespace (``plugins.<id>.*``).

        This namespace allows arbitrary string IDs, bypasses schema validation,
        and relies on the plugin system to ensure value correctness.
        """

        if not isinstance(key, str) or not key:
            return False
        return key.startswith("plugins.") and key.count(".") >= 2

    def get(self, key: str, default: Any = None) -> Any:
        with self._lock:
            if key in self._values:
                return self._values[key]
            if key in self._extras:
                return self._extras[key]
            if default is None:
                return self._raw_default(key)
            return default

    def set(self, key: str, value: Any) -> None:
        # Plugin namespace: goes through _extras bypass, no schema validation, but still fires events
        # so listeners other than PluginContext.set_setting can also perceive changes.
        if self._is_plugin_key(key):
            with self._lock:
                old = self._extras.get(key)
                if old == value and key in self._extras:
                    return
                self._extras[key] = value
                event = SettingsChangeEvent(
                    scope=self.scope,
                    key=key,
                    old=old,
                    new=value,
                )
            self._notify(event)
            return

        spec = self.spec(key)
        if spec is None:
            raise KeyError(f"unknown setting key in scope={self.scope.value!r}: {key!r}")
        coerced = spec.validate(value)

        with self._lock:
            old = self._values.get(key, self._raw_default(key))
            if old == coerced and key in self._values:
                return
            self._values[key] = coerced
            event = SettingsChangeEvent(
                scope=self.scope,
                key=key,
                old=old,
                new=coerced,
            )

        self._notify(event)

    def has(self, key: str) -> bool:
        with self._lock:
            return key in self._values or key in self._extras

    def all(self) -> dict[str, Any]:
        """All keys' current values, missing fields filled with defaults."""

        with self._lock:
            result: dict[str, Any] = {}
            for spec in self._schema:
                result[spec.key] = self._values.get(spec.key, spec.default)
            for k, v in self._extras.items():
                result[k] = v
            return result

    def defined(self) -> dict[str, Any]:
        with self._lock:
            merged = dict(self._values)
            merged.update(self._extras)
            return merged

    def reset(self, key: str | None = None) -> None:
        with self._lock:
            if key is None:
                if not self._values and not self._extras:
                    return
                old_snapshot = self.all()
                self._values.clear()
                self._extras.clear()
                new_snapshot = self.all()
                event = SettingsChangeEvent(
                    scope=self.scope,
                    key=None,
                    old=old_snapshot,
                    new=new_snapshot,
                )
                self._notify(event)
                return

            if key in self._extras:
                old = self._extras.pop(key)
                event = SettingsChangeEvent(
                    scope=self.scope,
                    key=key,
                    old=old,
                    new=None,
                )
                self._notify(event)
                return
            if key not in self._values:
                return  # Already at default state, no need to reset
            old = self._values.pop(key)
            new = self._raw_default(key)
            event = SettingsChangeEvent(
                scope=self.scope,
                key=key,
                old=old,
                new=new,
            )
            self._notify(event)

    def save(self) -> None:
        path = self.path
        self._ensure_parent_dir(path)

        with self._lock:
            merged_values = dict(self._values)
            merged_values.update(self._extras)
            payload = {
                "version": CURRENT_VERSION,
                "scope": self.scope.value,
                "values": merged_values,
            }

        parent = os.path.dirname(path) or "."
        fd, tmp_path = tempfile.mkstemp(prefix=".settings_", suffix=".tmp", dir=parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
                f.flush()
                with contextlib.suppress(OSError, AttributeError):
                    os.fsync(f.fileno())
            os.replace(tmp_path, path)
        except Exception:
            with contextlib.suppress(OSError):
                os.unlink(tmp_path)
            raise

    def load(self) -> None:
        path = self.path
        if not os.path.isfile(path):
            return

        try:
            with open(path, encoding="utf-8") as f:
                raw = json.load(f)
        except (OSError, json.JSONDecodeError):
            return

        if not isinstance(raw, dict):
            return

        raw_values = raw.get("values", {})
        if not isinstance(raw_values, dict):
            return

        new_values: dict[str, Any] = {}
        new_extras: dict[str, Any] = {}
        for key, value in raw_values.items():
            if self._is_plugin_key(key):
                new_extras[key] = value
                continue
            spec = self.spec(key)
            if spec is None:
                continue
            try:
                new_values[key] = spec.validate(value)
            except (ValueError, TypeError):
                continue

        with self._lock:
            self._values = new_values
            self._extras = new_extras


__all__ = ["CURRENT_VERSION", "JsonFileSettings"]
