# `modules.logging`

**Source**:
- [`__init__.py`](../../modules/logging/__init__.py) — 22 lines
- [`logger.py`](../../modules/logging/logger.py) — 287 lines

Unified logger that writes to stdout, to a rotating file, and to an
in-memory ring buffer (consumed by the in-app log viewer).

```python
from modules.logging import (
    LogLevel, Logger,
    get_logger, configure_logging, set_log_level, shutdown,
)
```

## `LogLevel` `[logger.py:15]`

```python
class LogLevel(IntEnum):
    DEBUG     = logging.DEBUG      # 10
    INFO      = logging.INFO       # 20
    WARNING   = logging.WARNING    # 30
    ERROR     = logging.ERROR      # 40
    CRITICAL  = logging.CRITICAL   # 50
```

Numerically identical to `logging`'s levels; values are interchangeable.

## `Logger` `[logger.py:96]`

Wraps a single named logger (one per file in `logs/`). Loggers are cached
by name in `Logger._instances` and re-configured when global settings
change.

### Methods

| Method | Signature | Description |
| --- | --- | --- |
| `debug` | `(msg, *args, **kwargs)` | |
| `info` | `(msg, *args, **kwargs)` | |
| `warning` | `(msg, *args, **kwargs)` | |
| `error` | `(msg, *args, **kwargs)` | |
| `critical` | `(msg, *args, **kwargs)` | |
| `exception` | `(msg, *args, **kwargs)` | Like `error` but includes the current traceback. |
| `log` | `(level, msg, *args, **kwargs)` | Generic entry point; `level` is `int` or `LogLevel`. |
| `get_entries` | `(level=None) -> list[dict]` | Snapshot of the in-memory ring buffer. Each entry is a dict with `asctime`, `level`, `name`, `message`. If `level` is given, only entries `>=` that level are returned. |
| `clear_entries` | `() -> None` | Empty the ring buffer. |
| `flush` | `() -> None` | Flush every handler. |

The internal ring buffer is always populated, regardless of `file_enabled`
or `console_enabled`.

## Module-level functions

### `configure_logging(...)` `[logger.py:214]`

```python
def configure_logging(
    level: str | LogLevel = "INFO",
    file_enabled: bool = True,
    console_enabled: bool = True,
    log_dir: str | None = None,
    max_bytes: int = 5 * 1024 * 1024,
    backup_count: int = 5,
) -> None
```

One-time global setup. Should be called once from `main.py` before any
`get_logger(...)`. After this call, every previously cached logger has its
handlers rebuilt — useful for tests or live log-level changes.

The editor calls it like this:

```python
configure_logging(
    level="INFO",
    file_enabled=True,
    console_enabled=True,
    log_dir="<project>/logs",
    max_bytes=5 * 1024 * 1024,
    backup_count=5,
)
```

### `set_log_level(level)` `[logger.py:251]`

```python
def set_log_level(level: str | LogLevel) -> None
```

Update only the level. Other settings (file/console, log_dir, …) are
untouched. Re-applies the level on every cached logger and handler.

### `get_logger(name='app') -> Logger` `[logger.py:263]`

Returns a named logger. Same name → same instance.

```python
log = get_logger("checker.flake8")
log.info("running flake8 on %s", path)
```

The file written for this logger is `<log_dir>/<name>.log`. Subnames use
`.` as separator in the UI but produce a flat file path.

### `shutdown() -> None` `[logger.py:280]`

Flushes all cached loggers. The Python `logging` module already calls
`atexit` shutdown for its handlers; this is for in-memory buffers. Safe to
call multiple times.

## Usage

```python
from modules.logging import configure_logging, get_logger

configure_logging(level="DEBUG")
log = get_logger("app")
log.info("started")
log.exception("oops")           # logs traceback
recent_errors = log.get_entries(level=40)
```