# `modules/logging/__init__.py`

源文件路径：`modules/logging/__init__.py`

`modules.logging` 包的公开入口。统一的多级别日志模块，支持文件轮转、控制台输出与内存环形缓冲区（供 UI 日志面板使用）。

## 重新导出

- `LogLevel` — 日志级别枚举（`DEBUG`/`INFO`/`WARNING`/`ERROR`/`CRITICAL`）。
- `Logger` — 日志器封装类。
- `get_logger(name="app")` — 按名称获取/创建单例日志器。
- `configure_logging(...)` — 一次性配置全局日志行为。
- `set_log_level(level)` — 动态修改日志级别。
- `shutdown()` — 退出前刷新所有 logger 缓冲区。

## `__all__`

```python
["LogLevel", "Logger", "get_logger", "configure_logging", "set_log_level", "shutdown"]
```