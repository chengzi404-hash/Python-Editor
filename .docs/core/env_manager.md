# `core.env_manager`

**Source**:
- [`core/env_manager/__init__.py`](../../core/env_manager/__init__.py) — 7 lines
- [`core/env_manager/manager.py`](../../core/env_manager/manager.py) — 486 lines

Detects, tracks, and operates on Python interpreters available to the
editor (system `python` / `python3` / `py`, venvs, conda envs, the
interpreter currently running the editor).

```python
from core.env_manager import (
    EnvironmentManager, PythonEnvironment, get_env_manager,
)
```

## Data model

### `PythonEnvironment` `[manager.py:14]`

```python
@dataclass
class PythonEnvironment:
    name: str
    python_path: str
    version: str = ""
    env_type: str = "venv"      # 'venv' | 'conda' | 'system' | 'custom'
    prefix: str = ""
    packages: dict[str, str] = field(default_factory=dict)

    @property
    def display_name(self) -> str:
        parts = [self.name]
        if self.version:
            parts.append(f"Python {self.version}")
        return " — ".join(parts)
```

`env_type` distinguishes how the environment was discovered. `prefix` is
the path to the env root (used by IDE features that need to know
`sys.prefix` without importing from the interpreter).

## `EnvironmentManager` `[manager.py:66]`

Thread-safe manager; backed by a single `threading.RLock`. All public
methods are safe to call from background threads.

```python
m = EnvironmentManager()
m.scan()                   # populate from PATH, common dirs, conda
m.add_listener(cb)         # cb(env_name) fires on every change
m.set_current("python 3.12")
m.install_package("requests")
```

### Listener API

| Method | Description |
| --- | --- |
| `add_listener(cb)` | `cb(name: str)` is called when the current environment changes (or when `scan()` finishes). |
| `remove_listener(cb)` | Unsubscribe; safe even if `cb` was never registered. |

### Scan / detect

| Method | Returns | Description |
| --- | --- | --- |
| `scan()` | `dict[str, PythonEnvironment]` | Full rescan. Clears existing entries, then probes: current `sys.executable`, system `python` / `python3` / `py` on `PATH`, common venv dirs (`.venv`, `venv`, `.env`, parent's `.venv`), and `conda env list --json`. Sets a sensible "current" if nothing was selected. |
| `list_environments()` | `dict[str, PythonEnvironment]` | Lazy: returns `scan()` on first call, otherwise a shallow copy of the cached map. |

Internal helpers `_probe_python(path)` and `_list_packages(path)` shell
out to `<python> --version` and `<python> -m pip list --format=json`
respectively.

### Current environment

| Property / Method | Description |
| --- | --- |
| `current_name` (property) | Currently selected key (e.g. `"python 3.12"`), or `None`. |
| `get_current() -> PythonEnvironment \| None` | The resolved environment, or `None`. |
| `set_current(name)` | Set the active key (no-op if unknown); notifies listeners. |
| `get_python_path() -> str` | The path to the active interpreter; falls back to `sys.executable`. |

### Package management

| Method | Description |
| --- | --- |
| `get_packages(name=None) -> dict[str, str]` | `python -m pip list --format=json`; caches the result on the environment. |
| `install_package(package, name=None, mirror="") -> str` | `python -m pip install <package>`; optional `-i <mirror>` for the index URL. Returns `""` on success, or the captured error string on failure. |
| `uninstall_package(package, name=None) -> str` | `python -m pip uninstall <package> -y`. Same return convention. |

Both `install_package` and `uninstall_package` time out (120 s and 60 s
respectively) and never raise — they report the error as a return
string so the UI can render it without `try/except`.

### Search

| Method | Description |
| --- | --- |
| `search_packages_on_pypi(query) -> list[dict]` | Fetches the package list from `mirrors.tuna.tsinghua.edu.cn/pypi/web/simple/`, filters client-side, and fetches the top-15 with metadata from `pypi.org/pypi/<name>/json`. The full name list is cached in a class-level attribute for the process lifetime. |

### Create / venv

| Method | Description |
| --- | --- |
| `create_venv(path, python_path=None, name=None) -> str` | `<python> -m venv <path>`. On success the new env is added to the in-memory map. Returns `""` on success or a human-readable error string. |

## `get_env_manager()` `[manager.py:482]`

Process-wide singleton accessor:

```python
env_manager = get_env_manager()       # one instance per process
env_manager.scan()
```

There is **no** setter — the singleton is created lazily and reused.
Tests can construct a fresh `EnvironmentManager()` directly instead of
using this accessor.

## Public surface

`__all__ = ["EnvironmentManager", "PythonEnvironment",
"get_env_manager"]`.