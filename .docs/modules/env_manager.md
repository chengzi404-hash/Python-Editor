# `modules.env_manager`

**Source**:
- [`modules/env_manager/__init__.py`](../../modules/env_manager/__init__.py) — 7 lines
- [`modules/env_manager/manager.py`](../../modules/env_manager/manager.py) — 464 lines

Detect Python interpreters available on the host, track which one is
"current", and install / uninstall packages through it.

```python
from modules.env_manager import PythonEnvironment, EnvironmentManager, get_env_manager
```

`get_env_manager()` is the process-wide singleton accessor; the editor
holds exactly one instance in `CodeEditor._env_manager`.

## Data model

### `PythonEnvironment` `[manager.py:13]`

```python
@dataclass
class PythonEnvironment:
    name: str                    # unique key (display name)
    python_path: str             # absolute path to the python binary
    version: str = ''            # e.g. '3.11.6'
    env_type: str = 'venv'       # 'venv' | 'conda' | 'system' | 'custom'
    prefix: str = ''             # sys.prefix of the interpreter
    packages: Dict[str, str] = field(default_factory=dict)
                                 # name -> version, populated lazily

    @property
    def display_name(self) -> str: ...
                                 # 'name — Python 3.11.6'
```

`env_type` is informational; the manager treats all four types identically.

## `EnvironmentManager` `[manager.py:60]`

Thread-safe (guarded by an internal `RLock`). Maintains an internal
dictionary of environments keyed by `name`. Listeners are notified after
mutations (`scan`, `set_current`, package install/uninstall, etc.).

### Construction

```python
manager = EnvironmentManager()      # or:
manager = get_env_manager()         # singleton
```

### Listeners

| Method | Signature | Description |
| --- | --- | --- |
| `add_listener` | `(callback: Callable[[str], None]) -> None` | `callback(env_name)` is invoked after each mutation. |
| `remove_listener` | `(callback) -> None` | Silent no-op if the callback isn't registered. |

### Scanning

| Method | Signature | Description |
| --- | --- | --- |
| `scan` | `() -> Dict[str, PythonEnvironment]` | Re-discovers environments from scratch. Clears the cache, then probes `sys.executable`, `PATH`, common install locations, conda envs, and `<cwd>/.venv`. Returns the new mapping. |

`scan()` is idempotent and **slow** (it shells out to many `python --version`
and `pip list` calls). Schedule it off the UI thread if you call it
manually.

### Current environment

| Method / property | Signature | Description |
| --- | --- | --- |
| `current_name` | property → `Optional[str]` | The active environment name. |
| `get_current` | `() -> Optional[PythonEnvironment]` | The active environment object. |
| `set_current` | `(name: str) -> None` | Make `name` active. Silently no-ops if the name is unknown. Notifies listeners. |
| `get_python_path` | `() -> Optional[str]` | `python_path` of the active environment, or `None`. |

### Package management

| Method | Signature | Description |
| --- | --- | --- |
| `get_packages` | `(name: str \| None = None) -> Dict[str, str]` | Returns the package map for `name` (or the current env). Triggers a `pip list` if not cached. |
| `install_package` | `(package: str, name: str \| None = None, mirror: str = '') -> None` | Runs `python -m pip install <package> [--index-url <mirror>]` on the target env. Notifies listeners when done. |
| `uninstall_package` | `(package: str, name: str \| None = None) -> None` | Runs `python -m pip uninstall -y <package>` on the target env. |
| `search_packages_on_pypi` | `(query: str) -> List[Dict[str, str]]` | Queries the Tsinghua PyPI mirror; returns up to ~30 hits with `name`, `version`, `summary`. |

### Virtualenv creation

```python
def create_venv(self, path: str, python_path: str | None = None, name: str | None = None) -> str
```

Creates `<path>` as a new `venv`. If `python_path` is given it is used as
the base interpreter; otherwise `sys.executable`. Returns `''` on success
or an error message string on failure. After a successful create the new
environment is added to the internal map and listeners are notified.

### Listing

| Method | Signature | Description |
| --- | --- | --- |
| `list_environments` | `() -> Dict[str, PythonEnvironment]` | Snapshot of the internal map. Triggers `scan()` on first call. |

## Singleton accessor

```python
def get_env_manager() -> EnvironmentManager
```

Returns the same instance on every call (module-level singleton). Used by
`main.py` so the editor and the env-manager dialog share state.