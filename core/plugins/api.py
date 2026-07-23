"""``modules.plugins.api`` — Plugin public contract.

This layer only defines **stable types for plugin authors**, excluding loading /
registration / event dispatch runtime logic. The actual runtime implementation
is in :mod:`modules.plugins.manager`.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import (
    Any,
    Protocol,
    runtime_checkable,
)

from .hooks import HookEvents  # re-export

__all__ = [
    "HookEvents",
    "LanguageContribution",
    "PluginCommand",
    "PluginContext",
    "PluginHostAPI",
    "PluginLoadError",
    "PluginManifest",
]


HookHandler = Callable[..., None]
CommandCallback = Callable[[], None]


@dataclass(frozen=True)
class PluginManifest:
    id: str
    name: str
    version: str = "0.0.0"
    description: str = ""
    author: str = ""
    scope: str = "global"

    def validate(self) -> None:
        if not self.id or not isinstance(self.id, str):
            raise ValueError("PluginManifest.id must be a non-empty string")
        if not all(ch.isalnum() or ch in "_-" for ch in self.id):
            raise ValueError(
                f"PluginManifest.id={self.id!r} can only contain letters/digits/underscores/dashes"
            )
        if not self.name:
            raise ValueError("PluginManifest.name must be non-empty")
        if self.scope not in ("global", "system"):
            raise ValueError(
                f"PluginManifest.scope must be 'global' or 'system', got {self.scope!r}"
            )


@dataclass(frozen=True)
class PluginCommand:
    plugin_id: str
    label: str
    callback: CommandCallback
    menu: str = "Plugin"
    shortcut: str | None = None


@dataclass(frozen=True)
class LanguageContribution:
    name: str
    ext: str
    highlighter_factory: Callable[[], Any]
    suggestion_factory: Callable[[], Any]
    sample: str = ""
    runner_factory: Callable[[], Any] | None = None
    description: str = ""


@dataclass
class _HookSubscription:
    hook: str
    callback: HookHandler
    plugin_id: str


class PluginLoadError(RuntimeError):
    """Unified exception thrown during plugin loading; main window catches and displays it."""


@runtime_checkable
class PluginHostAPI(Protocol):
    """Internal protocol implemented by :class:`PluginManager`, used for mocking in tests."""

    def register_hook(self, sub: _HookSubscription) -> None: ...
    def register_command(self, cmd: PluginCommand) -> None: ...
    def register_language(
        self,
        plugin_id: str,
        contrib: LanguageContribution,
    ) -> None: ...
    def append_output(self, text: str) -> None: ...
    def setting(self, key: str, default: Any = None) -> Any: ...
    def set_setting(self, key: str, value: Any) -> None: ...

    @property
    def editor(self) -> Any: ...


class PluginContext:
    """Single entry point for plugin-editor interaction."""

    def __init__(
        self,
        *,
        plugin_id: str,
        plugin_name: str,
        host: PluginHostAPI,
    ) -> None:
        self._plugin_id = plugin_id
        self._plugin_name = plugin_name
        self._host = host
        self._hooks: list[_HookSubscription] = []
        self._commands: list[PluginCommand] = []
        self._languages: list[LanguageContribution] = []
        self._unregister_callbacks: list[Callable[[], None]] = []

    @property
    def plugin_id(self) -> str:
        return self._plugin_id

    @property
    def plugin_name(self) -> str:
        return self._plugin_name

    def on(
        self,
        hook: str,
        callback: HookHandler | None = None,
    ) -> _HookSubscription | Callable[[HookHandler], _HookSubscription]:
        """Listen for hook events.

        Two usage patterns:

        * ``ctx.on("hook", callback)`` — direct registration, returns :class:`_HookSubscription`.
        * ``@ctx.on("hook")`` decorates ``def cb():`` — equivalent form.
        """

        if not isinstance(hook, str) or not hook:
            raise ValueError("hook must be a non-empty string")

        def _register(cb: HookHandler) -> _HookSubscription:
            if not callable(cb):
                raise TypeError("hook callback must be callable")
            sub = _HookSubscription(hook=hook, callback=cb, plugin_id=self._plugin_id)
            self._hooks.append(sub)
            self._host.register_hook(sub)
            return sub

        if callback is None:
            # Decorator mode: return a small function that accepts a callback
            return _register
        return _register(callback)

    def add_command(
        self,
        *,
        label: str,
        callback: CommandCallback,
        menu: str = "Plugin",
        shortcut: str | None = None,
    ) -> PluginCommand:
        cmd = PluginCommand(
            plugin_id=self._plugin_id,
            label=label,
            callback=callback,
            menu=menu,
            shortcut=shortcut,
        )
        self._commands.append(cmd)
        self._host.register_command(cmd)
        return cmd

    def register_language(self, contrib: LanguageContribution) -> None:
        self._languages.append(contrib)
        self._host.register_language(self._plugin_id, contrib)

    def append_output(self, text: str) -> None:
        if not text:
            return
        self._host.append_output(text)

    def log(self, level: str, message: str) -> None:
        prefix = {
            "info": "[INFO]",
            "warning": "[WARN]",
            "error": "[ERROR]",
        }.get(level.lower(), "[LOG]")
        self._host.append_output(f"{prefix} [{self._plugin_id}] {message}\n")

    def _settings_key(self, key: str) -> str:
        if not key:
            raise ValueError("setting key must be non-empty")
        return f"plugins.{self._plugin_id}.{key}"

    def setting(self, key: str, default: Any = None) -> Any:
        return self._host.setting(self._settings_key(key), default)

    def set_setting(self, key: str, value: Any) -> None:
        self._host.set_setting(self._settings_key(key), value)

    @property
    def editor(self) -> Any:
        """Access the CodeEditor instance for deep UI integration."""
        return self._host.editor

    def is_enabled(self) -> bool:
        return bool(self.setting("enabled", True))

    def on_unregister(self, callback: Callable[[], None]) -> None:
        if not callable(callback):
            raise TypeError("on_unregister callback must be callable")
        self._unregister_callbacks.append(callback)
