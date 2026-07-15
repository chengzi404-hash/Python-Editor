"""``modules.logging.logger`` — 日志核心实现。"""

from __future__ import annotations

import datetime
import logging
import logging.handlers
import os
import sys
import threading
from enum import IntEnum


class LogLevel(IntEnum):
    """日志级别枚举，按严重程度升序。"""

    DEBUG = logging.DEBUG      # 10
    INFO = logging.INFO        # 20
    WARNING = logging.WARNING  # 30
    ERROR = logging.ERROR      # 40
    CRITICAL = logging.CRITICAL  # 50


# 全局日志器字典，按 name 缓存
_loggers: dict[str, Logger] = {}
_loggers_lock = threading.Lock()

# 全局配置句柄（配置一次，所有新 logger 共享）
_configured = False
_config_lock = threading.Lock()
_config: dict = {
    "level": LogLevel.INFO,
    "file_enabled": True,
    "console_enabled": True,
    "max_bytes": 5 * 1024 * 1024,   # 5 MB
    "backup_count": 5,
    "_dir": None,                   # 日志目录路径（str）
}


def _default_log_dir() -> str:
    """返回默认日志目录 ``<项目根>/logs``。"""
    cwd = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(cwd, "logs")


def _ensure_log_dir() -> str:
    """确保日志目录存在并返回路径。"""
    log_dir = _config["_dir"] or _default_log_dir()
    os.makedirs(log_dir, exist_ok=True)
    return log_dir


class _Handler(logging.Handler):
    """内部 Handler：格式化后写入 list（供 UI 日志面板使用）。"""

    def __init__(self, max_entries: int = 500):
        super().__init__()
        self._entries: list[dict] = []
        self._lock = threading.RLock()
        self._max = max_entries

    def emit(self, record: logging.LogRecord) -> None:
        entry = {
            "timestamp": datetime.datetime.fromtimestamp(
                record.created, tz=datetime.timezone.utc,
            ).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
            "level": record.levelname,
            "name": record.name,
            "message": record.getMessage(),
            "exc_text": record.exc_text if hasattr(record, "exc_text") else None,
        }
        with self._lock:
            self._entries.append(entry)
            if len(self._entries) > self._max:
                self._entries.pop(0)

    def get_entries(self, level: int | None = None) -> list[dict]:
        """返回日志条目，level 为 None 时返回全部。"""
        with self._lock:
            if level is None:
                return list(self._entries)
            return [e for e in self._entries if e["level_int"] >= level]

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()

    @property
    def level_int(self) -> int:
        """供外部过滤用（与 LogLevel 数值对应）。"""
        return 0


class Logger:
    """统一日志封装，同时写文件 + 控制台 + 内存环形缓冲区。"""

    _instances: dict[str, Logger] = {}

    def __init__(self, name: str):
        self.name = name
        self._py_logger = logging.getLogger(name)
        self._py_logger.setLevel(logging.DEBUG)
        self._py_logger.propagate = False
        self._handler = _Handler()
        self._handler.setFormatter(
            logging.Formatter(
                "%(asctime)s  [%(levelname)s]  %(name)s  %(message)s",
                datefmt="%H:%M:%S",
            )
        )
        self._file_handler: logging.handlers.RotatingFileHandler | None = None
        self._console_handler: logging.StreamHandler | None = None
        self._lock = threading.Lock()
        self._configure_handlers()

    def _configure_handlers(self) -> None:
        """根据全局配置挂载 / 卸载 handlers。"""
        with self._lock:
            # 先清除所有已有 handler（配置可能变了）
            self._py_logger.handlers.clear()

            level = _config["level"].value
            self._py_logger.setLevel(level)

            # 内存 handler（始终存在，供 UI 读取）
            self._py_logger.addHandler(self._handler)

            if _config["console_enabled"]:
                if self._console_handler is None:
                    self._console_handler = logging.StreamHandler(sys.stdout)
                    self._console_handler.setFormatter(
                        logging.Formatter(
                            "[%(levelname)s]  %(name)s  %(message)s",
                        )
                    )
                self._py_logger.addHandler(self._console_handler)

            if _config["file_enabled"]:
                log_dir = _ensure_log_dir()
                filename = os.path.join(log_dir, f"{self.name}.log")
                if self._file_handler is None:
                    self._file_handler = logging.handlers.RotatingFileHandler(
                        filename,
                        maxBytes=_config["max_bytes"],
                        backupCount=_config["backup_count"],
                        encoding="utf-8",
                    )
                    self._file_handler.setFormatter(
                        logging.Formatter(
                            "%(asctime)s  [%(levelname)s]  %(name)s  %(message)s",
                            datefmt="%Y-%m-%d %H:%M:%S",
                        )
                    )
                else:
                    # 级别或文件名可能变化，重新创建
                    self._py_logger.removeHandler(self._file_handler)
                    self._file_handler.close()
                    self._file_handler = logging.handlers.RotatingFileHandler(
                        filename,
                        maxBytes=_config["max_bytes"],
                        backupCount=_config["backup_count"],
                        encoding="utf-8",
                    )
                    self._file_handler.setFormatter(
                        logging.Formatter(
                            "%(asctime)s  [%(levelname)s]  %(name)s  %(message)s",
                            datefmt="%Y-%m-%d %H:%M:%S",
                        )
                    )
                self._py_logger.addHandler(self._file_handler)

    def debug(self, msg: str, *args, **kwargs) -> None:
        self._py_logger.debug(msg, *args, **kwargs)

    def info(self, msg: str, *args, **kwargs) -> None:
        self._py_logger.info(msg, *args, **kwargs)

    def warning(self, msg: str, *args, **kwargs) -> None:
        self._py_logger.warning(msg, *args, **kwargs)

    def error(self, msg: str, *args, **kwargs) -> None:
        self._py_logger.error(msg, *args, **kwargs)

    def critical(self, msg: str, *args, **kwargs) -> None:
        self._py_logger.critical(msg, *args, **kwargs)

    def exception(self, msg: str, *args, **kwargs) -> None:
        """记录异常并附带堆栈跟踪。"""
        self._py_logger.exception(msg, *args, **kwargs)

    def log(self, level: int | LogLevel, msg: str, *args, **kwargs) -> None:
        self._py_logger.log(int(level), msg, *args, **kwargs)

    def get_entries(self, level: int | None = None) -> list[dict]:
        """获取内存环形缓冲区中的日志条目。"""
        return self._handler.get_entries(level)

    def clear_entries(self) -> None:
        """清空内存日志。"""
        self._handler.clear()

    def flush(self) -> None:
        """刷新所有 handler。"""
        for h in self._py_logger.handlers:
            h.flush()


# ---------------------------------------------------------------------------
# 全局配置函数
# ---------------------------------------------------------------------------

def configure_logging(
    level: str | LogLevel = "INFO",
    file_enabled: bool = True,
    console_enabled: bool = True,
    log_dir: str | None = None,
    max_bytes: int = 5 * 1024 * 1024,
    backup_count: int = 5,
) -> None:
    """一次性配置全局日志行为。

    Args:
        level: 日志级别（DEBUG/INFO/WARNING/ERROR/CRITICAL 或对应字符串）。
        file_enabled: 是否写文件日志。
        console_enabled: 是否输出到控制台（stdout）。
        log_dir: 日志文件存放目录，默认 ``<项目根>/logs``。
        max_bytes: 单个日志文件最大字节数，超出后轮转。
        backup_count: 保留的轮转备份文件数量。
    """
    global _configured

    with _config_lock:
        if isinstance(level, str):
            level = LogLevel[level.upper()]
        _config["level"] = level
        _config["file_enabled"] = file_enabled
        _config["console_enabled"] = console_enabled
        if log_dir is not None:
            _config["_dir"] = log_dir
        _config["max_bytes"] = max_bytes
        _config["backup_count"] = backup_count
        _configured = True

    # 让所有已存在的 logger 实例重新配置 handlers
    for logger in list(_loggers.values()):
        logger._configure_handlers()


def set_log_level(level: str | LogLevel) -> None:
    """动态修改日志级别（不影响其他配置）。"""
    if isinstance(level, str):
        level = LogLevel[level.upper()]
    with _config_lock:
        _config["level"] = level
    for logger in list(_loggers.values()):
        logger._py_logger.setLevel(int(level))
        for h in logger._py_logger.handlers:
            h.setLevel(int(level))


def get_logger(name: str = "app") -> Logger:
    """获取（或创建）一个命名的 Logger 实例。

    Args:
        name: 日志器名称，同时也是日志文件名（``<name>.log``）。

    Returns:
        Logger 实例。同一 name 总是返回同一实例。
    """
    if name in _loggers:
        return _loggers[name]
    with _loggers_lock:
        if name not in _loggers:
            _loggers[name] = Logger(name)
        return _loggers[name]


def shutdown() -> None:
    """程序退出前调用，刷新并关闭所有文件 handler。

    Python 的 logging 模块会在 atexit 时自动调用 shutdown，
    这里只负责刷新自定义 logger 实例的缓冲区。
    """
    for logger in list(_loggers.values()):
        logger.flush()
