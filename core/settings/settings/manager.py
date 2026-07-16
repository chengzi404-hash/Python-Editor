"""``modules.settings.manager`` — Unified public interface :class:`SettingsManager`.

Encapsulates "global settings + (optional) current project settings", providing:

* :meth:`get` / :meth:`set` —— Read/write a single key on the specified scope.
* :meth:`effective` —— Resolve the final effective value considering "project overrides global".
* :meth:`attach_project` / :meth:`detach_project` —— Switch current project.
* :meth:`add_listener` —— Listen to both global and project changes.
* :meth:`save_all` —— Persist both sides together.

Typical usage::

    from core.settings.settings import SettingsManager, SettingsScope

    manager = SettingsManager()
    # global settings
    manager.set(SettingsScope.GLOBAL, "ui.theme", "Light")
    # attach project
    manager.attach_project("/path/to/project")
    manager.set(SettingsScope.PROJECT, "project.python_interpreter", "/usr/bin/python3")
    # effective value (project takes precedence, otherwise fallback to global)
    interpreter = manager.effective("project.python_interpreter")
"""

from __future__ import annotations

import contextlib
import threading
from typing import Any

from .base import (
    Settings,
    SettingsChangeEvent,
    SettingsListener,
    SettingsScope,
)
from .global_settings import GlobalSettings
from .project_settings import ProjectSettings


class SettingsManager:
    """Unified manager for global + project settings.

    Always holds a :class:`GlobalSettings` instance;
    the current project (:class:`ProjectSettings`) is optional, bound via :meth:`attach_project`.
    """

    def __init__(
        self,
        global_settings: GlobalSettings | None = None,
        project_settings: ProjectSettings | None = None,
    ) -> None:
        self._lock = threading.RLock()
        self._global = global_settings or GlobalSettings()
        self._project: ProjectSettings | None = project_settings
        self._user_listeners: list[SettingsListener] = []

    @property
    def global_settings(self) -> GlobalSettings:
        return self._global

    @property
    def project_settings(self) -> ProjectSettings | None:
        return self._project

    @property
    def project_root(self) -> str | None:
        return self._project.root if self._project is not None else None

    def attach_project(self, root: str) -> ProjectSettings:
        """Mount project root directory and return a new :class:`ProjectSettings` instance.

        If another project was already mounted, :meth:`save_all` will be called first to persist the old project.
        """

        with self._lock:
            if self._project is not None:
                with contextlib.suppress(Exception):
                    self.save_all()
            self._project = ProjectSettings(root=root)
            self._project.add_listener(self._relay_event)
            return self._project

    def detach_project(self) -> None:
        """Unmount current project and save."""

        with self._lock:
            if self._project is None:
                return
            with contextlib.suppress(Exception):
                self._project.save()
            self._project.remove_listener(self._relay_event)
            self._project = None

    def _resolve(self, scope: SettingsScope) -> Settings:
        if scope is SettingsScope.PROJECT:
            if self._project is None:
                raise LookupError("no project attached; call attach_project() first")
            return self._project
        return self._global

    def get(self, scope: SettingsScope, key: str, default: Any = None) -> Any:
        """Read a key's value on the specified scope."""

        target = self._resolve(scope)
        return target.get(key, default)

    def effective(self, key: str, default: Any = None) -> Any:
        """Resolve the final effective value considering "project overrides global".

        Resolution order:

        1. Current project (if mounted) defines the key → use project value.
        2. Global value (default filled).
        3. ``default`` parameter.
        """

        if self._project is not None and self._project.has(key):
            return self._project.get(key)
        return self._global.get(key, default)

    def set(self, scope: SettingsScope, key: str, value: Any) -> None:
        """Write a key on the specified scope. Triggers validation, events, and bridging listeners."""

        target = self._resolve(scope)
        target.set(key, value)

    def reset(self, scope: SettingsScope, key: str | None = None) -> None:
        """Reset one key or all keys in the scope."""

        target = self._resolve(scope)
        target.reset(key)

    def add_listener(self, callback: SettingsListener) -> None:
        """Register a change callback, listening to both global and (current) project."""

        if callback in self._user_listeners:
            return
        self._user_listeners.append(callback)
        self._global.add_listener(self._relay_event)
        if self._project is not None:
            self._project.add_listener(self._relay_event)

    def remove_listener(self, callback: SettingsListener) -> None:
        """Remove a callback."""

        try:
            self._user_listeners.remove(callback)
        except ValueError:
            return
        if not self._user_listeners:
            self._global.remove_listener(self._relay_event)
            if self._project is not None:
                self._project.remove_listener(self._relay_event)

    def _relay_event(self, event: SettingsChangeEvent) -> None:
        """Forward child object events verbatim to all manager-level subscribers."""

        for cb in list(self._user_listeners):
            with contextlib.suppress(Exception):
                cb(event)

    def save_all(self) -> None:
        """Save global + current project (if exists)."""

        self._global.save()
        if self._project is not None:
            self._project.save()

    def reload_all(self) -> None:
        """Reload global + current project."""

        self._global.load()
        if self._project is not None:
            self._project.load()

    def global_all(self) -> dict[str, Any]:
        return self._global.all()

    def project_all(self) -> dict[str, Any]:
        if self._project is None:
            return {}
        return self._project.all()

    def effective_all(self) -> dict[str, Any]:
        """Return merged effective configuration (project overrides global)."""

        merged = self._global.all()
        if self._project is not None:
            for key, value in self._project.all().items():
                if self._project.has(key):
                    merged[key] = value
        return merged

    def __enter__(self) -> SettingsManager:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        with contextlib.suppress(Exception):
            self.save_all()

    def __repr__(self) -> str:
        root = self.project_root
        return f"SettingsManager(global={self._global.path!r}, project={root!r})"


__all__ = ["SettingsManager"]
