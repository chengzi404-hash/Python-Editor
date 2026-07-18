"""``modules.logging`` — Unified logging module.

Supports multiple log levels, console output, and crash-only file logging.
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
