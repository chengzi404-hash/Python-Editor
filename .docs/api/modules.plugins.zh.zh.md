# `modules/plugins/__init__.py`

源文件路径：`modules/plugins/__init__.py`

`modules.plugins` 包的公开入口。插件系统：加载、卸载、事件分发、命令与语言贡献注册。

## 公开 API

- `PluginManifest` — 插件元信息。
- `PluginContext` — 插件与编辑器交互的唯一入口（注册钩子、命令、语言、读写 settings）。
- `PluginManager` — 加载/卸载/事件分发。
- `PluginCommand` — 命令描述。
- `LanguageContribution` — 语言描述（高亮、补全、运行器工厂）。
- `PluginLoadError` — 加载失败的统一异常。
- `PluginHostAPI` — `PluginManager` 实现的内部协议（测试可 mock）。
- `HookEvents` — 钩子事件名常量。
- `HookSpec` — 钩子形参签名描述。
- `HOOK_SPECS` — 所有内置钩子的元组。
- `DiscoveredPlugin` — 磁盘上发现但未加载的插件描述。
- `plugin_marketplace` — 插件市场子模块。

## 最简示例

`~/.python-editor/plugins/hello_world/__init__.py`：

```python
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
        ctx.append_output(f"[hello_world] 打开文件: {path}\n")

    ctx.add_command(
        menu="插件示例",
        label="打招呼",
        callback=lambda: ctx.append_output("Hello!\n"),
        shortcut="Ctrl+Shift+H",
    )
```

## `__all__`

```python
[
    "PluginManifest", "PluginContext", "PluginManager", "DiscoveredPlugin",
    "PluginCommand", "LanguageContribution", "PluginHostAPI", "PluginLoadError",
    "HookEvents", "HookSpec", "HOOK_SPECS", "plugin_marketplace",
]
```