# `modules/settings/base.py`

源文件路径：`modules/settings/base.py`

设置模块的抽象层。定义枚举、Schema 数据类、`Settings` 抽象基类以及事件/监听器协议。

## 枚举

### `SettingsScope(str, Enum)`
- `GLOBAL = "global"` — 跨项目共享，存放在用户主目录下。
- `PROJECT = "project"` — 与项目目录绑定。

### `SettingValueType(str, Enum)`
支持的底层值类型：
- `STRING` / `INTEGER` / `FLOAT` / `BOOLEAN`
- `CHOICE` — 字符串枚举，由 `choices` 给出候选项。
- `LIST` — 字符串列表（JSON 数组）。
- `PATH` — 文件系统路径字符串。
- `BUTTON` — 动作按钮，不存储值。

## 数据类

### `SettingSpec`（`@dataclass(frozen=True)`）
单个设置项元信息。
- `key: str` — 作用域内唯一标识，使用 `.` 分段。
- `type: SettingValueType`
- `default: Any`
- `label: str = ""` / `description: str = ""`
- `choices: Tuple[Any, ...] = ()` — `CHOICE` 类型候选。
- `min: Optional[float] = None` / `max: Optional[float] = None` — 数值边界。
- `scope: SettingsScope = SettingsScope.GLOBAL`

方法：
- `validate(value) -> Any`：校验并强制转换为 `type` 允许的类型，失败抛 `ValueError`。
  - `INTEGER`/`FLOAT`：检查类型（不接受 `bool`）、边界，必要时转 `float`。
  - `CHOICE`：要求 `choices` 非空且 `value ∈ choices`。
  - `LIST`：要求 list 且元素全是 str。
  - `BUTTON`：直接返回。
  - 其它：`STRING`/`PATH` 要求是 str。

### `SettingsSchema`（`@dataclass`）
一组 `SettingSpec` 的集合。
- `specs: Tuple[SettingSpec, ...] = ()`

构造时校验：`__post_init__` 检查 key 非空、不重复。

方法：
- `keys() -> List[str]`
- `get(key) -> Optional[SettingSpec]`
- `__contains__(key) -> bool`
- `__iter__() / __len__()`
- `defaults() -> Dict[str, Any]` — 返回 `{key: default}` 字典。

### `SettingsChangeEvent`（`@dataclass`）
变更事件载荷。
- `scope: SettingsScope`
- `key: Optional[str]` — `None` 表示批量重置。
- `old: Any` — 变更前值（批量时为旧快照）。
- `new: Any` — 变更后值（批量时为新快照）。

类型别名：
- `SettingsListener = Callable[[SettingsChangeEvent], None]`

## 抽象类

### `Settings(ABC)`
设置存储抽象基类。构造参数：
- `schema: SettingsSchema`
- `scope: SettingsScope = SettingsScope.GLOBAL`

属性：
- `scope` / `schema`

监听：
- `add_listener(callback)` / `remove_listener(callback)`
- `_notify(event)`：调用所有监听器，单个监听器异常被忽略。

抽象方法（子类必须实现）：
- `get(key, default=None) -> Any`
- `set(key, value) -> None`
- `has(key) -> bool`
- `all() -> Dict[str, Any]` — 全部键的当前值（含默认填充）。
- `defined() -> Dict[str, Any]` — 仅显式赋值过的键。
- `reset(key: Optional[str] = None) -> None` — `key=None` 时清空所有自定义值。
- `save() -> None`
- `load() -> None`

便利方法：
- `spec(key) -> Optional[SettingSpec]` — 返回 key 对应的 spec，未注册时返回 `None`。

## `__all__`

```python
["SettingsScope", "SettingValueType", "SettingSpec",
 "SettingsSchema", "SettingsChangeEvent", "SettingsListener", "Settings"]
```