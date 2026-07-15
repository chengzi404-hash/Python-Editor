# `modules/settings/storage.py`

源文件路径：`modules/settings/storage.py`

基于 JSON 文件的 `Settings` 持久化基类。存储格式：

```json
{
  "version": 1,
  "scope": "global" | "project",
  "values": { ... }
}
```

线程安全由 `threading.RLock` 保护；写入采用临时文件 + `os.replace`，避免读到半写状态；`load` 容忍磁盘缺失或格式错误。

## 模块常量

- `CURRENT_VERSION = 1` — 当前存储格式版本号。

## 内部辅助

### `_is_plugin_key(key: str) -> bool`（静态）
判断 `key` 是否属于插件命名空间（`plugins.<id>.<sub>`，即以 `plugins.` 开头且至少含两个 `.`）。这类键不走 schema 校验，单独存放在 `_extras`。

## 类

### `JsonFileSettings(Settings)`
子类只需实现 `_resolve_path()` 告知数据写到哪个文件。

构造参数：
- `schema: SettingsSchema`
- `scope: SettingsScope`
- `path: Optional[str] = None`
- `auto_load: bool = True` — 构造时自动 `load()`。

字段：
- `_lock: threading.RLock`
- `_path: Optional[str]`
- `_values: Dict[str, Any]` — 经 schema 校验的显式赋值。
- `_extras: Dict[str, Any]` — 插件命名空间键的旁路存储。

#### 方法

- `_resolve_path() -> str`（抽象）：子类返回默认 JSON 路径；未实现时抛 `NotImplementedError`。
- `_ensure_parent_dir(path)` — 确保父目录存在。

- `path`（属性）：懒解析，若 `_path is None` 则调用 `_resolve_path()`。

- `get(key, default=None) -> Any`
  - `_values` → `_extras` → `_raw_default(key)`（即 spec.default）→ `default`。

- `set(key, value) -> None`
  - 插件键：写入 `_extras`，发 `SettingsChangeEvent`，不校验。
  - schema 键：通过 `spec.validate` 强转后写入 `_values`，发事件；值未变且已存在时直接返回。
  - 未知键抛 `KeyError`。

- `has(key) -> bool`
- `all() -> Dict[str, Any]` — 全 schema 默认值 + `_extras`。
- `defined() -> Dict[str, Any]` — `_values` + `_extras` 合并。

- `reset(key=None) -> None`
  - `key=None`：清空 `_values` 和 `_extras`，发 `key=None` 的批量事件。
  - 给定 key：从 `_extras` 或 `_values` 中移除，发对应事件。

- `save() -> None`
  - 在目标目录创建临时文件，序列化 `{"version": CURRENT_VERSION, "scope": scope.value, "values": merged_values}`，`flush + fsync` 后 `os.replace` 原子替换；异常时清理临时文件。

- `load() -> None`
  - 读取并解析 JSON；若 `values` 是 dict 则逐项校验并分到 `_values`/`_extras`；校验失败的项被忽略。文件缺失或解析错误时静默返回。

## `__all__`

```python
["JsonFileSettings", "CURRENT_VERSION"]
```