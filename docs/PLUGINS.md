# 插件系统

## 目录

- [概述](#概述)
- [插件放在哪里](#插件放在哪里)
- [插件结构](#插件结构)
- [最小示例](#最小示例)
- [API](#api)
  - [`PluginManifest`](#pluginmanifest)
  - [`PluginContext`](#plugincontext)
  - [钩子事件](#钩子事件)
- [示例插件](#示例插件)
- [管理界面](#管理界面)
- [插件设置](#插件设置)

## 概述

Python Editor 通过 `importlib` 动态加载 **Python 源文件** 作为插件。插件可以做四件事:

1. **监听钩子事件**: 文件打开/保存/内容变更/光标移动/语言切换/运行开始与结束/检查完成/编辑器关闭。
2. **注册命令**: 在主菜单"插件"分组里加菜单项，可绑定快捷键。
3. **注册语言**: 像内置 Python/C/C++ 一样把新语言挂到顶部语言下拉框。
4. **读写自己的 settings**: 在 `settings.json` 的 `plugins.<id>.*` 命名空间下持久化。

## 插件放在哪里

两个位置都自动扫描:

| 路径 | 加载时机 |
| --- | --- |
| `~/.python-editor/plugins/<id>/__init__.py` | 编辑器启动时 |
| `<项目根>/plugins/<id>/__init__.py` | 项目打开时 |

每个插件是一个独立的子目录，**目录名就是插件 id**（也用作 `MANIFEST.id`）。

## 插件结构

```
plugins/
└── hello_world/
    └── __init__.py
```

`__init__.py` 至少包含一个 `MANIFEST` 常量和一个 `register(ctx)` 函数。

## 最小示例

```python
# ~/.python-editor/plugins/hello_world/__init__.py
from modules.plugins import HookEvents, PluginManifest

MANIFEST = PluginManifest(
    id="hello_world",
    name="Hello World",
    version="0.1.0",
    description="最小可运行的演示插件",
    author="Your Name",
)

def register(ctx):
    ctx.log("info", "Hello World 已加载")

    @ctx.on(HookEvents.EDITOR_FILE_OPENED)
    def _on_open(path: str) -> None:
        ctx.append_output(f"[hello_world] 打开文件: {path}\n")

    ctx.add_command(
        menu="示例",
        label="说 Hello",
        callback=lambda: ctx.append_output("Hello!\n"),
        shortcut="Ctrl+Shift+H",
    )
```

## API

### `PluginManifest`

| 字段 | 必填 | 说明 |
| --- | --- | --- |
| `id` | ✓ | 唯一标识。字母/数字/下划线/短横线。 |
| `name` | ✓ | 显示名称。 |
| `version` |  | 语义化版本，默认 `"0.0.0"`。 |
| `description` |  | 详细说明（管理窗口显示）。 |
| `author` |  | 作者名。 |
| `scope` |  | `"global"`（默认）或 `"system"`（随编辑器启动）。 |

### `PluginContext`

| 方法 | 说明 |
| --- | --- |
| `ctx.on(hook_name, callback)` | 监听钩子，返回订阅句柄。 |
| `ctx.add_command(*, label, callback, menu="插件", shortcut=None)` | 注册一个菜单命令。 |
| `ctx.register_language(LanguageContribution(...))` | 注册一门新语言。 |
| `ctx.append_output(text)` | 往 output 面板追加文本。 |
| `ctx.log(level, message)` | 写日志到 output 面板。 |
| `ctx.setting(key, default=None)` | 读 `plugins.<id>.<key>` 的值。 |
| `ctx.set_setting(key, value)` | 写 `plugins.<id>.<key>`。 |
| `ctx.is_enabled()` | 读 `plugins.<id>.enabled`，默认 True。 |
| `ctx.on_unregister(callback)` | 注册一个卸载清理回调。 |

### 钩子事件

| 名称 | 参数 |
| --- | --- |
| `editor:file_opened` | `(path: str)` |
| `editor:file_saved` | `(path: str)` |
| `editor:file_created` | `()` |
| `editor:content_changed` | `(code: str, cursor_pos: int)` |
| `editor:language_changed` | `(lang: str)` |
| `editor:cursor_moved` | `(line: int, col: int)` |
| `editor:run_started` | `(lang: str, temp_path: str)` |
| `editor:run_finished` | `(lang: str, returncode: int, stdout: str, stderr: str)` |
| `editor:check_finished` | `(lang: str, issues: list)` |
| `editor:closing` | `()` |

事件名常量在 `modules.plugins.HookEvents`。

## 示例插件

仓库自带三个示例，位于 `examples/plugins/`:

- `hello_world/` — 最简演示（钩子 + 命令）。
- `word_counter/` — 监听 `content_changed` 实时统计行/词数。
- `markdown_lang/` — 注册一门 Markdown 语言，含 highlighter 与示例文本。

复制到 `~/.python-editor/plugins/` 或项目下的 `plugins/` 即可启用。

## 管理界面

主菜单 **插件 → 管理插件...** 打开管理窗口，可:

- 查看已加载插件（启用/禁用、错误信息）
- 查看磁盘上发现但未启用的插件
- 启用 / 禁用 / 重新加载 / 查看详情

也可以用 **插件 → 重新扫描插件目录** 在不重启的情况下重新发现新放入的插件。

## 插件设置

每个插件在 `settings.json` 中自动获得一个 `plugins.<id>.*` 命名空间:

```json
{
  "version": 1,
  "scope": "global",
  "values": {
    "ui.theme": "Dark",
    "plugins.hello_world.enabled": true,
    "plugins.word_counter.verbose": false
  }
}
```

- `enabled` 默认 `true`，管理窗口的"禁用"按钮就是把它设成 `false`。
- 任意键都可以通过 `ctx.set_setting` / `ctx.setting` 读写，无需在 schema 里注册。