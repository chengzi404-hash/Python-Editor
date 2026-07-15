"""``modules.logging`` — 统一日志模块。

支持多级别日志、文件日志、控制台输出、轮转归档。
"""

from .logger import (
    Logger,
    LogLevel,
    configure_logging,
    get_logger,
    set_log_level,
    shutdown,
)

__all__ = [
    "LogLevel",
    "Logger",
    "configure_logging",
    "get_logger",
    "set_log_level",
    "shutdown",
]
