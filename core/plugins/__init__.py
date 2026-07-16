"""``core.plugins`` — Editor plugin system.

Public API
=========

* :class:`PluginManifest` — Plugin metadata.
* :class:`PluginContext` — Register hooks, commands, languages, read/write settings.
* :class:`PluginManager` — Load/unload/event dispatch.
* :class:`PluginCommand` / :class:`LanguageContribution` — Command/language descriptions.
* :data:`HookEvents` — Hook event name constants.
* :class:`PluginLoadError` — Unified exception for load failures.

Minimal example
==============

``~/.python-editor/plugins/hello_world/__init__.py``::

    from core.plugins import PluginManifest, HookEvents

    MANIFEST = PluginManifest(
        id="hello_world",
        name="Hello World",
        version="0.1.0",
        description="A minimal runnable demo plugin",
    )

    def register(ctx):
        ctx.log("info", "Hello World loaded")

        @ctx.on(HookEvents.EDITOR_FILE_OPENED)
        def _on_open(path):
            ctx.append_output(f"[hello_world] File opened: {path}\\n")

        ctx.add_command(
            menu="Plugin Examples",
            label="Say Hello",
            callback=lambda: ctx.append_output("Hello!\\n"),
            shortcut="Ctrl+Shift+H",
        )
"""

from __future__ import annotations

from . import marketplace as plugin_marketplace
from .api import (
    LanguageContribution,
    PluginCommand,
    PluginContext,
    PluginHostAPI,
    PluginLoadError,
    PluginManifest,
)
from .hooks import HOOK_SPECS, HookEvents, HookSpec
from .manager import DiscoveredPlugin, PluginManager

__all__ = [
    "HOOK_SPECS",
    "DiscoveredPlugin",
    "HookEvents",
    "HookSpec",
    "LanguageContribution",
    "PluginCommand",
    "PluginContext",
    "PluginHostAPI",
    "PluginLoadError",
    "PluginManager",
    "PluginManifest",
    "plugin_marketplace",
]
