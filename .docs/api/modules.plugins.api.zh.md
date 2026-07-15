# `modules/plugins/api.py`

源文件路径：`modules/plugins/api.py`

插件作者可见的稳定类型定义。运行时实现在 `modules.plugins.manager`。

## 类型别名

- `HookHandler = Callable[..., None]`
- `CommandCallback = Callable[[], None]`

## 数据类

### `PluginManifest`（`@dataclass(frozen=True)`）
- `id: str` — 唯一标识符（仅字母/数字/下划线/短横线）。
- `name: str` — 人类可读名称。
- `version: str = "0.0.0"`
- `description: str = ""`
- `author: str = ""`
- `scope: str = "global"` — `'global'` 或 `'system'`。

方法：
- `validate() -> None`：校验 `id` 非空、字符合法、`name` 非空、`scope ∈ {"global", "system"}`。失败抛 `ValueError`。

### `PluginCommand`（`@dataclass(frozen=True)`）
- `plugin_id: str`
- `label: str`
- `callback: CommandCallback`
- `menu: str = "插件"`
- `shortcut: Optional[str] = None` — 例如 `"Ctrl+Shift+H"`。

### `LanguageContribution`（`@dataclass(frozen=True)`）
- `name: str` — 显示名。
- `ext: str` — 关联文件扩展名。
- `highlighter_factory: Callable[[], Any]` — 返回高亮器实例。
- `suggestion_factory: Callable[[], Any]` — 返回补全器实例。
- `sample: str = ""` — 新建文件时的示例代码。
- `runner_factory: Optional[Callable[[], Any]] = None` — 可选运行器工厂。
- `description: str = ""`

### `_HookSubscription`（`@dataclass`）
内部订阅记录。`hook: str` / `callback: HookHandler` / `plugin_id: str`。

## 异常

### `PluginLoadError(RuntimeError)`
加载/注册插件过程中抛出的统一异常。

## 协议

### `PluginHostAPI`（`@runtime_checkable Protocol`）
由 `PluginManager` 实现的内部协议，便于测试时 mock：
- `register_hook(sub: _HookSubscription) -> None`
- `register_command(cmd: PluginCommand) -> None`
- `register_language(plugin_id: str, contrib: LanguageContribution) -> None`
- `append_output(text: str) -> None`
- `setting(key: str, default: Any = None) -> Any`
- `set_setting(key: str, value: Any) -> None`

## 类

### `PluginContext`
插件与编辑器交互的唯一入口。构造参数（关键字参数）：
- `plugin_id: str`
- `plugin_name: str`
- `host: PluginHostAPI`

属性：
- `plugin_id` / `plugin_name`

方法：
- `on(hook, callback=None)` — 两种用法：
  - `ctx.on("hook", callback)` 直接注册，返回 `_HookSubscription`。
  - `@ctx.on("hook")` 装饰 `def cb()` 等价写法。
  - 校验 `hook` 为非空字符串；`callback` 必须可调用。底层调用 `host.register_hook`。

- `add_command(*, label, callback, menu="插件", shortcut=None) -> PluginCommand`：注册命令，同时写入 `host.register_command`。

- `register_language(contrib: LanguageContribution) -> None`：注册语言贡献。

- `append_output(text: str) -> None`：空文本忽略；否则转发 `host.append_output`。

- `log(level: str, message: str) -> None`：按 `level` 前缀（`info`/`warning`/`error`/其它）写入 output panel，格式为 `[LEVEL] [<plugin_id>] <message>\n`。

- `setting(key, default=None) -> Any` / `set_setting(key, value) -> None`：底层 key 会被改写为 `plugins.<plugin_id>.<key>` 再交给 host。

- `is_enabled() -> bool`：读取 `setting("enabled", True)`。

- `on_unregister(callback: Callable[[], None]) -> None`：注册卸载钩子（由 manager 在 `_unload_one` 时调用）。