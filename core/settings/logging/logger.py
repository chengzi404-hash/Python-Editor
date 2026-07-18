"""``modules.logging.logger`` — Core logging implementation."""

from __future__ import annotations

import datetime
import logging
import os
import sys
import threading
from enum import IntEnum
from typing import ClassVar


class LogLevel(IntEnum):
    """Log level enum, ordered by severity ascending."""

    DEBUG = logging.DEBUG  # 10
    INFO = logging.INFO  # 20
    WARNING = logging.WARNING  # 30
    ERROR = logging.ERROR  # 40
    CRITICAL = logging.CRITICAL  # 50


_loggers: dict[str, Logger] = {}
_loggers_lock = threading.Lock()

_configured = False
_config_lock = threading.Lock()
_config: dict = {
    "level": LogLevel.INFO,
    "console_enabled": True,
    "max_bytes": 5 * 1024 * 1024,
    "backup_count": 5,
    "_dir": None,
}

_excepthook_registered = False


def _default_log_dir() -> str:
    """Return default log directory ``<project root>/logs``."""
    cwd = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(cwd, "logs")


def _ensure_log_dir() -> str:
    """Ensure log directory exists and return the path."""
    log_dir = _config["_dir"] or _default_log_dir()
    os.makedirs(log_dir, exist_ok=True)
    return log_dir


class _Handler(logging.Handler):
    """Internal Handler: formats and writes to a list (used by UI log panel)."""

    def __init__(self, max_entries: int = 500):
        super().__init__()
        self._entries: list[dict] = []
        self._raw_entries: list[str] = []
        self._lock = threading.RLock()
        self._max = max_entries

    def emit(self, record: logging.LogRecord) -> None:
        ts = datetime.datetime.fromtimestamp(record.created, tz=datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        entry = {
            "timestamp": ts,
            "level": record.levelname,
            "name": record.name,
            "message": record.getMessage(),
            "exc_text": record.exc_text if hasattr(record, "exc_text") else None,
        }
        raw = f"{ts}  [{record.levelname}]  {record.name}  {record.getMessage()}"
        if record.exc_text:
            raw += f"\n{record.exc_text}"
        with self._lock:
            self._entries.append(entry)
            self._raw_entries.append(raw)
            if len(self._entries) > self._max:
                self._entries.pop(0)
                self._raw_entries.pop(0)

    def get_entries(self, level: int | None = None) -> list[dict]:
        """Return log entries; when level is None, return all."""
        with self._lock:
            if level is None:
                return list(self._entries)
            return [e for e in self._entries if e["level_int"] >= level]

    def get_raw_entries(self) -> list[str]:
        with self._lock:
            return list(self._raw_entries)

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()
            self._raw_entries.clear()

    @property
    def level_int(self) -> int:
        """For external filtering (corresponds to LogLevel values)."""
        return 0


class Logger:
    """Unified log wrapper: writes to console + in-memory ring buffer; file log on crash only."""

    _instances: ClassVar[dict[str, Logger]] = {}

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
        self._console_handler: logging.StreamHandler | None = None
        self._lock = threading.Lock()
        self._configure_handlers()

    def _configure_handlers(self) -> None:
        """Mount / unmount handlers according to global config."""
        with self._lock:
            self._py_logger.handlers.clear()

            level = _config["level"].value
            self._py_logger.setLevel(level)

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

    def _write_crash_log(self) -> None:
        """Write in-memory logs to file (called only on crash)."""
        log_dir = _ensure_log_dir()
        filename = os.path.join(log_dir, f"{self.name}.log")
        raw_entries = self._handler.get_raw_entries()
        if not raw_entries:
            return
        try:
            with open(filename, "a", encoding="utf-8") as f:
                f.write("\n".join(raw_entries))
                if raw_entries:
                    f.write("\n")
        except OSError:
            pass

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
        """Log an exception with stack trace."""
        self._py_logger.exception(msg, *args, **kwargs)

    def log(self, level: int | LogLevel, msg: str, *args, **kwargs) -> None:
        self._py_logger.log(int(level), msg, *args, **kwargs)

    def get_entries(self, level: int | None = None) -> list[dict]:
        """Get log entries from the in-memory ring buffer."""
        return self._handler.get_entries(level)

    def clear_entries(self) -> None:
        """Clear in-memory logs."""
        self._handler.clear()

    def flush(self) -> None:
        """Flush all handlers."""
        for h in self._py_logger.handlers:
            h.flush()


# ---------------------------------------------------------------------------
# Global configuration functions
# ---------------------------------------------------------------------------


def _crash_write_all() -> None:
    """Write crash logs for all loggers to their respective files."""
    for logger in list(_loggers.values()):
        logger._write_crash_log()


def _global_excepthook(exc_type, exc_value, exc_traceback) -> None:
    """Global exception hook: writes crash logs before propagating."""
    if exc_type is KeyboardInterrupt:
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    _crash_write_all()
    sys.__excepthook__(exc_type, exc_value, exc_traceback)


def configure_logging(
    level: str | LogLevel = "INFO",
    console_enabled: bool = True,
    log_dir: str | None = None,
    max_bytes: int = 5 * 1024 * 1024,
    backup_count: int = 5,
    file_enabled: bool = True,
) -> None:
    """Configure global logging behavior in one call.

    Args:
        level: Log level (DEBUG/INFO/WARNING/ERROR/CRITICAL or corresponding string).
        console_enabled: Whether to output to console (stdout).
        log_dir: Directory for log files, defaults to ``<project root>/logs``.
        max_bytes: Max bytes per log file before rotation.
        backup_count: Number of rotated backup files to retain.
        file_enabled: Deprecated, ignored (logs written to file on crash only).
    """
    global _configured, _excepthook_registered

    with _config_lock:
        if isinstance(level, str):
            level = LogLevel[level.upper()]
        _config["level"] = level
        _config["console_enabled"] = console_enabled
        if log_dir is not None:
            _config["_dir"] = log_dir
        _config["max_bytes"] = max_bytes
        _config["backup_count"] = backup_count
        _configured = True

    if not _excepthook_registered:
        sys.excepthook = _global_excepthook
        _excepthook_registered = True

    for logger in list(_loggers.values()):
        logger._configure_handlers()


def set_log_level(level: str | LogLevel) -> None:
    """Dynamically modify log level (does not affect other config)."""
    if isinstance(level, str):
        level = LogLevel[level.upper()]
    with _config_lock:
        _config["level"] = level
    for logger in list(_loggers.values()):
        logger._py_logger.setLevel(int(level))
        for h in logger._py_logger.handlers:
            h.setLevel(int(level))


def get_logger(name: str = "app") -> Logger:
    """Get (or create) a named Logger instance.

    Args:
        name: Logger name.

    Returns:
        Logger instance. The same name always returns the same instance.
    """
    if name in _loggers:
        return _loggers[name]
    with _loggers_lock:
        if name not in _loggers:
            _loggers[name] = Logger(name)
        return _loggers[name]


def shutdown() -> None:
    """Flush all logger handlers on shutdown."""
    for logger in list(_loggers.values()):
        logger.flush()
