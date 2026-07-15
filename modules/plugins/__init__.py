"""``modules.plugins`` — 编辑器插件系统。

公开 API
========

* :class:`PluginManifest` —— 插件元信息。
* :class:`PluginContext` —— 注册钩子、命令、语言、读写 settings。
* :class:`PluginManager` —— 加载/卸载/事件分发。
* :class:`PluginCommand` / :class:`LanguageContribution` —— 命令/语言描述。
* :data:`HookEvents` —— 钩子事件名常量。
* :class:`PluginLoadError` —— 加载失败统一异常。

最简示例
========

``~/.python-editor/plugins/hello_world/__init__.py``::

    from modules.plugins import PluginManifest, HookEvents

    MANIFEST = PluginManifest(
        id="hello_world",
        name="Hello World",
        version="0.1.0",
        description="最小可运行的演示插件",
    )

    def register(ctx):
        ctx.log("info", "Hello World 已加载")

        @ctx.on(HookEvents.EDITOR_FILE_OPENED)
        def _on_open(path):
            ctx.append_output(f"[hello_world] 打开文件: {path}\\n")

        ctx.add_command(
            menu="插件示例",
            label="打招呼",
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
