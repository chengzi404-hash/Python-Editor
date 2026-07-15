# `modules/Uui/web/orm/connection.py`

源文件路径：`modules/Uui/web/orm/connection.py`

数据库连接管理（线程局部 + 简单后端注册）。

## 模块状态

- `_connections: Dict[str, Backend]` — alias → 后端实例。
- `_lock: threading.Lock`
- `_active_alias: str = 'default'`

## 函数

### `configure(settings) -> None`
遍历 `settings.DATABASES`：
- 已有 alias 跳过。
- `ENGINE` 以 `sqlite` 结尾 → 直接用 `SqliteBackend`。
- 否则按 `ENGINE` import；查找 `Backend` 类（或首个 `*Backend` 后缀类）；校验继承 `Backend`；实例化。
- 失败抛 `ImportError` / `ImproperlyConfigured`。

### `get_backend(alias='default') -> Backend`
返回后端实例（缺失抛 `KeyError`）。

### `get_connection(alias='default') -> Any`
返回原始连接（SQLite 即 `sqlite3.Connection`）。

### `close_all() -> None`
关闭并清空所有后端连接。

### `using(alias) -> _ConnectionContext`
返回上下文管理器（切换 `_active_alias`）。

## 内部类

### `_ConnectionContext`
- `__enter__() -> Backend`：保存旧 alias，切换为目标 alias，返回 backend。
- `__exit__(...)`：恢复旧 alias。