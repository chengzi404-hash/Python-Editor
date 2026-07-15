# `modules/plugins/hooks.py`

源文件路径：`modules/plugins/hooks.py`

钩子事件常量与参数约定。命名空间分两类：`editor.*`（核心生命周期，所有插件可订阅）和 `language.*`（预留，当前未发出）。

## 类

### `HookEvents`
钩子事件名字符串常量：

| 常量 | 事件名 | 形参 |
|---|---|---|
| `EDITOR_FILE_OPENED` | `editor:file_opened` | `(path: str)` |
| `EDITOR_FILE_SAVED` | `editor:file_saved` | `(path: str)` |
| `EDITOR_FILE_CREATED` | `editor:file_created` | `()` |
| `EDITOR_CONTENT_CHANGED` | `editor:content_changed` | `(code: str, cursor_pos: int)` |
| `EDITOR_LANGUAGE_CHANGED` | `editor:language_changed` | `(lang: str)` |
| `EDITOR_CURSOR_MOVED` | `editor:cursor_moved` | `(line: int, col: int)` |
| `EDITOR_RUN_STARTED` | `editor:run_started` | `(lang: str, temp_path: str)` |
| `EDITOR_RUN_FINISHED` | `editor:run_finished` | `(lang: str, returncode: int, stdout: str, stderr: str)` |
| `EDITOR_CHECK_FINISHED` | `editor:check_finished` | `(lang: str, issues: list)` |
| `EDITOR_CLOSING` | `editor:closing` | `()` |

## 数据类

### `HookSpec`（`@dataclass(frozen=True)`）
钩子形参签名描述，仅供 UI 展示 / 类型检查。
- `name: str`
- `params: Tuple[str, ...]`
- `description: str = ""`

## 模块常量

### `HOOK_SPECS: Tuple[HookSpec, ...]`
所有内置钩子的元组，包含每个事件的名称、参数和中文描述。

## `__all__`

```python
["HookEvents", "HookSpec", "HOOK_SPECS"]
```