"""``modules.settings.base`` — Abstract layer for the settings module.

This file defines only ``types`` and ``protocols``, **without** any concrete implementation:

* :class:`SettingSpec` describes a setting entry (key, default value, type, label, choices, range, and other metadata).
* :class:`SettingValueType` lists allowed underlying value types for serialization validation.
* :class:`SettingsScope` distinguishes between ``global`` (shared across projects) and ``project`` (current workspace) scopes.
* :class:`Settings` is the abstract base class for settings storage, providing ``get / set / has / all / reset / save`` interfaces.
* :class:`SettingsChangeEvent` / :class:`SettingsListener` define subscription/callback signatures.

Concrete global/project settings are in :mod:`modules.settings.global_settings` and
:mod:`modules.settings.project_settings`; the unified entry point is
:class:`modules.settings.manager.SettingsManager`.
"""

from __future__ import annotations

import contextlib
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Any


class SettingsScope(str, Enum):
    """Settings scope.

    * ``GLOBAL`` — Shared across projects, stored in the user's home directory.
    * ``PROJECT`` — Bound to a specific project directory, only applies to the currently opened project.
    """

    GLOBAL = "global"
    PROJECT = "project"


class SettingValueType(str, Enum):
    """Supported underlying value types for settings."""

    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    CHOICE = "choice"  # string enum, candidates provided by ``choices``
    LIST = "list"  # list of strings (json array)
    PATH = "path"  # file system path
    BUTTON = "button"  # action button, does not store value, triggers callback on click


@dataclass(frozen=True)
class SettingSpec:
    """Metadata for a single setting entry.

    Field meanings:

    * ``key`` —— Unique identifier within the scope, using ``.`` segments (e.g., ``editor.tab_size``).
    * ``type`` —— Underlying value type, see :class:`SettingValueType`.
    * ``default`` —— Default value; type must be compatible with ``type``.
    * ``label`` —— Short title for UI display.
    * ``description`` —— Longer explanation, optional.
    * ``choices`` —— When ``type == CHOICE``, list all candidate values.
    * ``min`` / ``max`` —— Optional bounds for numeric types.
    * ``choices`` —— Candidates for ``CHOICE`` type.
    * ``scope`` —— Restricts which scope this spec is allowed in.
    """

    key: str
    type: SettingValueType
    default: Any
    label: str = ""
    description: str = ""
    choices: tuple[Any, ...] = ()
    min: float | None = None
    max: float | None = None
    scope: SettingsScope = SettingsScope.GLOBAL

    def validate(self, value: Any) -> Any:
        """Validate and coerce ``value`` to the type allowed by ``type``.

        Raises :class:`ValueError` on validation failure. Returns the "normalized" result of ``value``.
        """

        if self.type is SettingValueType.STRING:
            if not isinstance(value, str):
                raise ValueError(f"setting {self.key!r} expects str, got {type(value).__name__}")
            return value

        if self.type is SettingValueType.INTEGER:
            if isinstance(value, bool):
                raise ValueError(f"setting {self.key!r} expects int, got bool")
            if not isinstance(value, int):
                raise ValueError(f"setting {self.key!r} expects int, got {type(value).__name__}")
            if self.min is not None and value < self.min:
                raise ValueError(f"setting {self.key!r} must be >= {self.min}, got {value}")
            if self.max is not None and value > self.max:
                raise ValueError(f"setting {self.key!r} must be <= {self.max}, got {value}")
            return value

        if self.type is SettingValueType.FLOAT:
            if isinstance(value, bool):
                raise ValueError(f"setting {self.key!r} expects number, got bool")
            if not isinstance(value, (int, float)):
                raise ValueError(f"setting {self.key!r} expects number, got {type(value).__name__}")
            value = float(value)
            if self.min is not None and value < self.min:
                raise ValueError(f"setting {self.key!r} must be >= {self.min}, got {value}")
            if self.max is not None and value > self.max:
                raise ValueError(f"setting {self.key!r} must be <= {self.max}, got {value}")
            return value

        if self.type is SettingValueType.BOOLEAN:
            if not isinstance(value, bool):
                raise ValueError(f"setting {self.key!r} expects bool, got {type(value).__name__}")
            return value

        if self.type is SettingValueType.CHOICE:
            if not self.choices:
                raise ValueError(f"setting {self.key!r} is CHOICE but has no choices")
            if value not in self.choices:
                raise ValueError(
                    f"setting {self.key!r} must be one of {list(self.choices)!r}, got {value!r}"
                )
            return value

        if self.type is SettingValueType.LIST:
            if not isinstance(value, list):
                raise ValueError(f"setting {self.key!r} expects list, got {type(value).__name__}")
            for i, item in enumerate(value):
                if not isinstance(item, str):
                    raise ValueError(
                        f"setting {self.key!r}[{i}] must be str, got {type(item).__name__}"
                    )
            return list(value)

        if self.type is SettingValueType.BUTTON:
            return value

        if self.type is SettingValueType.PATH:
            if not isinstance(value, str):
                raise ValueError(
                    f"setting {self.key!r} expects str path, got {type(value).__name__}"
                )
            return value

        raise ValueError(f"unknown setting type: {self.type!r}")


@dataclass
class SettingsSchema:
    """A collection of :class:`SettingSpec` providing key-based indexing.

    Usage example::

        schema = SettingsSchema((SettingSpec("editor.tab_size",
                                             SettingValueType.INTEGER, 4),))
        spec = schema.get("editor.tab_size")
        assert spec is not None
    """

    specs: tuple[SettingSpec, ...] = ()

    def __post_init__(self) -> None:
        seen: dict[str, None] = {}
        for spec in self.specs:
            if not spec.key:
                raise ValueError("SettingSpec.key must be non-empty")
            if spec.key in seen:
                raise ValueError(f"duplicate setting key in schema: {spec.key!r}")
            seen[spec.key] = None

    def keys(self) -> list[str]:
        return [s.key for s in self.specs]

    def get(self, key: str) -> SettingSpec | None:
        for spec in self.specs:
            if spec.key == key:
                return spec
        return None

    def __contains__(self, key: object) -> bool:
        return isinstance(key, str) and self.get(key) is not None

    def __iter__(self):
        return iter(self.specs)

    def __len__(self) -> int:
        return len(self.specs)

    def defaults(self) -> dict[str, Any]:
        return {spec.key: spec.default for spec in self.specs}


@dataclass
class SettingsChangeEvent:
    """Settings change event payload.

    * ``scope`` —— Scope where the change occurred.
    * ``key`` —— Changed key (``None`` indicates a bulk reset).
    * ``old`` —— Value before change; if ``key`` is ``None``, represents the old snapshot of the entire scope.
    * ``new`` —— Value after change; if ``key`` is ``None``, represents the new snapshot of the entire scope.
    """

    scope: SettingsScope
    key: str | None
    old: Any
    new: Any


SettingsListener = Callable[[SettingsChangeEvent], None]


class Settings(ABC):
    """Abstract base class for settings storage.

    Subclasses must persist data to some backend (disk file, memory, remote, etc.),
    but externally expose only a unified access interface. This class itself
    **does not** handle project/global distinction — that is done by the scope parameter.
    """

    def __init__(
        self,
        schema: SettingsSchema,
        *,
        scope: SettingsScope = SettingsScope.GLOBAL,
    ) -> None:
        super().__init__()
        self._schema = schema
        self._scope = scope
        self._listeners: list[SettingsListener] = []

    @property
    def scope(self) -> SettingsScope:
        return self._scope

    @property
    def schema(self) -> SettingsSchema:
        return self._schema

    def add_listener(self, callback: SettingsListener) -> None:
        """Register a change callback."""

        if callback not in self._listeners:
            self._listeners.append(callback)

    def remove_listener(self, callback: SettingsListener) -> None:
        """Remove a registered callback, ignored if not registered."""

        with contextlib.suppress(ValueError):
            self._listeners.remove(callback)

    def _notify(self, event: SettingsChangeEvent) -> None:
        """Internally trigger callbacks: catch exceptions to avoid one listener affecting others."""

        for cb in list(self._listeners):
            with contextlib.suppress(Exception):
                cb(event)

    @abstractmethod
    def get(self, key: str, default: Any = None) -> Any:
        """Read a key's value.

        If the key does not exist or has not been explicitly set, should return ``default`` or the default value in the schema.
        """

    @abstractmethod
    def set(self, key: str, value: Any) -> None:
        """Write a key's value, will trigger type validation and listener callbacks."""

    @abstractmethod
    def has(self, key: str) -> bool:
        """Return whether the key has been explicitly set."""

    @abstractmethod
    def all(self) -> dict[str, Any]:
        """Return *all* keys' current values (including default value filled snapshot)."""

    @abstractmethod
    def defined(self) -> dict[str, Any]:
        """Return only key-value pairs that have been explicitly set."""

    @abstractmethod
    def reset(self, key: str | None = None) -> None:
        """Reset one key or all keys. ``key=None`` means clear all custom values."""

    @abstractmethod
    def save(self) -> None:
        """Persist the current state to underlying storage."""

    @abstractmethod
    def load(self) -> None:
        """Reload from underlying storage (overwrites current in-memory state)."""

    def spec(self, key: str) -> SettingSpec | None:
        """Return the :class:`SettingSpec` for the key, or ``None`` if not registered."""

        return self._schema.get(key)


__all__ = [
    "SettingSpec",
    "SettingValueType",
    "Settings",
    "SettingsChangeEvent",
    "SettingsListener",
    "SettingsSchema",
    "SettingsScope",
]
