# `modules/logging/logger.py`

源文件路径：`modules/logging/logger.py`

统一日志模块的核心实现。同时写文件（轮转）、控制台与内存环形缓冲区。

## 枚举

### `LogLevel(IntEnum)`
按严重程度升序：`DEBUG`(10) / `INFO`(20) / `WARNING`(30) / `ERROR`(40) / `CRITICAL`(50)。数值与标准库 `logging` 对齐。

## 内部状态

- `_loggers: dict[str, Logger]` / `_loggers_lock` — 全局按 `name` 缓存的 logger。
- `_configured: bool` / `_config_lock` — 配置标志。
- `_config: dict` — 全局配置：`level` / `file_enabled` / `console_enabled` / `max_bytes`(默认 5MB) / `backup_count`(默认 5) / `_dir`(默认 `None` → `<项目根>/logs`)。

## 模块内部辅助

### `_default_log_dir() -> str`
返回默认日志目录 `<项目根>/logs`。

### `_ensure_log_dir() -> str`
确保配置指定的日志目录存在并返回路径。

## 内部类

### `_Handler(logging.Handler)`
将每条日志写入固定大小的内存列表（默认 500 条），供 UI 直接读取。

字段：
- `_entries: list[dict]` — 每条形如 `{timestamp, level, name, message, exc_text}`。
- `_lock: threading.RLock`
- `_max: int` — 上限条数。

方法：
- `emit(record)` — 追加一条，超出 `_max` 时从头部 pop。
- `get_entries(level=None) -> list[dict]` — 返回副本；按 `level_int` 过滤（但 `level_int` 始终返回 `0`，即不过滤——可视为已知问题）。
- `clear()` — 清空条目。
- `level_int`（属性）— 当前返回常量 `0`。

## 类

### `Logger`
按 `name` 创建；同时挂载内存 handler、可选 stdout handler、可选 `RotatingFileHandler`。

类属性：
- `_instances: dict[str, Logger]` — 实例缓存（备用，主缓存使用模块级 `_loggers`）。

构造：
- 取得 `logging.getLogger(name)`，设置 `propagate=False` 与 `setLevel(DEBUG)`（实际等级通过全局配置下推）。
- 创建 `_Handler`、`_console_handler`、`_file_handler`（默认 `None`，按需懒加载）。
- 调用 `_configure_handlers()`。

#### 方法
- `_configure_handlers()`：清空已有 handlers；按 `_config` 重新挂载内存 handler、（可选）stdout handler、（可选）`RotatingFileHandler`（按 `<name>.log` 命名）。

- 五个便捷方法（签名同标准库 `logging.Logger`）：
  - `debug(msg, *args, **kwargs)`
  - `info(msg, *args, **kwargs)`
  - `warning(msg, *args, **kwargs)`
  - `error(msg, *args, **kwargs)`
  - `critical(msg, *args, **kwargs)`

- `exception(msg, *args, **kwargs)` — 记录异常并附带堆栈跟踪。

- `log(level: int | LogLevel, msg, *args, **kwargs)` — 通用入口。

- `get_entries(level: int | None = None) -> list[dict]` — 读取内存环形缓冲区（转发给 `_Handler.get_entries`）。

- `clear_entries()` — 清空内存日志。

- `flush()` — 遍历所有 handler 调用 `flush()`。

## 模块级函数

### `configure_logging(level="INFO", file_enabled=True, console_enabled=True, log_dir=None, max_bytes=5MB, backup_count=5) -> None`
一次性配置全局日志行为。
- `level` 接受字符串或 `LogLevel`。
- `log_dir` 为 `None` 时保留先前配置（默认 `<项目根>/logs`）。
- 配置后调用所有已存在 logger 的 `_configure_handlers()`。

### `set_log_level(level: str | LogLevel) -> None`
动态修改全局日志级别；遍历所有 logger 重新设置 level 与每个 handler 的 level。

### `get_logger(name: str = "app") -> Logger`
按 `name` 获取/创建全局单例 logger。

### `shutdown() -> None`
遍历所有 logger 调用 `flush()`，将缓冲区写入文件。注：标准库 `logging` 已通过 `atexit` 自动 flush，本函数主要刷新自定义 logger 的 `_Handler` 缓冲区。