# `modules/settings/manager.py`

源文件路径：`modules/settings/manager.py`

统一对外接口 `SettingsManager`，封装"全局设置 + 可选当前项目设置"。

## 类

### `SettingsManager`
始终持有一个 `GlobalSettings`；当前项目 `ProjectSettings` 可选，通过 `attach_project` 绑定。

构造参数：
- `global_settings: Optional[GlobalSettings] = None` — 默认 `GlobalSettings()`。
- `project_settings: Optional[ProjectSettings] = None`

属性：
- `global_settings: GlobalSettings`
- `project_settings: Optional[ProjectSettings]`
- `project_root: Optional[str]` — 当前项目根目录，未挂载时为 `None`。

方法：
- `attach_project(root: str) -> ProjectSettings`
  挂载项目根目录，返回新 `ProjectSettings`。若已有项目，先 `save_all()` 持久化旧项目，再创建新项目并接入 `_relay_event`。

- `detach_project() -> None`
  卸载当前项目：保存当前项目、移除 relay 监听、清空 `_project`。

- `_resolve(scope: SettingsScope) -> Settings`
  内部根据 scope 返回对应的 `Settings` 实例；未挂项目时访问 PROJECT 抛 `LookupError`。

- `get(scope, key, default=None) -> Any` — 在指定作用域读取键值。

- `effective(key, default=None) -> Any`
  解析"项目覆盖全局"的最终生效值。顺序：当前项目（若挂载且定义了键）→ 全局值 → `default`。

- `set(scope, key, value) -> None` — 在指定作用域写入键，触发校验与事件。

- `reset(scope, key=None) -> None` — 重置作用域下的某个键或全部键。

- `add_listener(callback) -> None`
  注册 manager 级变更回调；同时把 `_relay_event` 挂到 `global_settings`，若有项目也挂到 `project_settings`。

- `remove_listener(callback) -> None`
  移除回调；若当前没有任何 manager 级监听器，相应解绑 relay。

- `_relay_event(event)` — 内部把子对象事件原样转发给所有 manager 级订阅者（异常被吞掉）。

- `save_all() -> None` — 保存全局 + 当前项目（若存在）。
- `reload_all() -> None` — 重新加载全局 + 当前项目。
- `global_all() -> Dict[str, Any]` / `project_all() -> Dict[str, Any]` — 返回对应作用域的快照。
- `effective_all() -> Dict[str, Any]` — 项目覆盖全局的合并结果。

上下文管理：
- `__enter__() / __exit__()` — `__exit__` 时自动 `save_all()`。

`__repr__` 形如 `SettingsManager(global='...', project='...')`。

## `__all__`

```python
["SettingsManager"]
```