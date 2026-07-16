# `modules.settings`

**Source**:
- [`__init__.py`](../../modules/settings/__init__.py) — 86 lines
- [`base.py`](../../modules/settings/base.py) — 352 lines
- [`storage.py`](../../modules/settings/storage.py) — 286 lines
- [`schema.py`](../../modules/settings/schema.py) — 502 lines
- [`global_settings.py`](../../modules/settings/global_settings.py) — 79 lines
- [`project_settings.py`](../../modules/settings/project_settings.py) — 90 lines
- [`manager.py`](../../modules/settings/manager.py) — 228 lines
- [`widgets.py`](../../modules/settings/widgets.py) — 622 lines

Two-tier settings: **global** (cross-project) + **project** (per
workspace). A unified `SettingsManager` is the entry point. Persistence
is JSON via `JsonFileSettings` with atomic writes.

```python
from modules.settings import (
    SettingsManager, SettingsScope, SettingsChangeEvent,
    GlobalSettings, ProjectSettings,
    Settings, JsonFileSettings,
    SettingsSchema, SettingSpec, SettingValueType,
    SettingsListener,
    GLOBAL_SCHEMA, PROJECT_SCHEMA, GLOBAL_SPECS, PROJECT_SPECS,
    SCHEMA_BY_SCOPE, get_schema,
    default_global_path, default_project_path,
    CURRENT_VERSION,
)
```

## Types

### `SettingsScope` `[base.py:26]`

```python
class SettingsScope(str, Enum):
    GLOBAL = "global"
    PROJECT = "project"
```

### `SettingValueType` `[base.py:37]`

```python
class SettingValueType(str, Enum):
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    CHOICE = "choice"   # string enum, choices= provided
    LIST = "list"       # string list, JSON-encoded
    PATH = "path"
    BUTTON = "button"   # action button; not stored
```

### `SettingSpec` `[base.py:51]`

```python
@dataclass(frozen=True)
class SettingSpec:
    key: str
    type: SettingValueType
    default: Any
    label: str = ""
    description: str = ""
    choices: Tuple[Any, ...] = ()
    min: Optional[float] = None
    max: Optional[float] = None
    scope: SettingsScope = SettingsScope.GLOBAL

    def validate(self, value: Any) -> Any: ...
```

`validate(value)` raises `ValueError` for type mismatches or out-of-range
numbers, and returns a normalized value otherwise.

### `SettingsSchema` `[base.py:149]`

```python
@dataclass
class SettingsSchema:
    specs: Tuple[SettingSpec, ...]

    def keys(self) -> List[str]: ...
    def get(self, key: str) -> SettingSpec: ...
    def __contains__(self, key): ...
    def __iter__(self): ...
    def __len__(self): ...
    def defaults(self) -> Dict[str, Any]: ...
```

### `SettingsChangeEvent` `[base.py:194]`

```python
@dataclass
class SettingsChangeEvent:
    scope: SettingsScope
    key: str
    old: Any
    new: Any
```

### `SettingsListener` `[base.py:209]`

```python
SettingsListener = Callable[[SettingsChangeEvent], None]
```

### `Settings` (abstract base) `[base.py:212]`

```python
class Settings(ABC):
    def get(self, key, default=None) -> Any: ...
    def set(self, key, value) -> None: ...
    def has(self, key) -> bool: ...
    def all(self) -> Dict[str, Any]: ...
    def defined(self) -> Set[str]: ...           # keys explicitly set
    def reset(self, key: Optional[str] = None) -> None: ...
    def save(self) -> None: ...
    def load(self) -> None: ...
    def add_listener(self, callback) -> None: ...
    def remove_listener(self, callback) -> None: ...
    def spec(self, key) -> SettingSpec: ...
```

## Persistence

### `CURRENT_VERSION` `[storage.py:29]`

The current on-disk JSON schema version. Bumping it is the migration signal.

### `JsonFileSettings` `[storage.py:32]`

The current on-disk JSON schema version. Bumping it is the migration signal.

### `JsonFileSettings` `[storage.py:32]`

Thread-safe base class for both global and project settings.

| Behaviour | Detail |
| --- | --- |
| File format | `{"version": 1, "values": {...}, "extras": {...}}` |
| `save()` | Writes to a temp file in the same directory, then `os.replace()` to swap atomically. |
| `load()` | Tolerant: missing file, bad JSON, or wrong version → empty in-memory state. |
| Extras | Keys matching `plugins.<id>.*` bypass schema validation and live in a separate `extras` map (plugin ids are dynamic). |

Subclasses must implement `_resolve_path()` unless they pass `path=` to
the constructor.

## Concrete settings classes

### `GlobalSettings` `[global_settings.py:51]`

JSON-backed `Settings` for the global scope.

| Path (Windows) | `%APPDATA%\PythonEditor\settings.json` |
| Path (macOS)   | `~/Library/Application Support/PythonEditor/settings.json` |
| Path (Linux)   | `$XDG_CONFIG_HOME/PythonEditor/settings.json` (or `~/.config/PythonEditor/settings.json`) |

`default_global_path()` returns the platform-appropriate path; pass it
to `GlobalSettings(path=...)` to override (testing).

### `ProjectSettings` `[project_settings.py:29]`

JSON-backed `Settings` for the project scope. Path is
`<root>/.pyeditor/settings.json`; `default_project_path(root)` returns
that path. Has additional helpers:

| Property / method | Description |
| --- | --- |
| `root` | The project root the instance is bound to. |
| `project_name()` | Best-effort project name (currently reads `project.name` from settings or the directory basename). |

### `default_global_path() -> str` and `default_project_path(root) -> str`

Pure functions returning the platform-correct paths; safe to call from
tests.

## Default schemas (`modules.settings.schema`)

The editor ships with two schemas:

### `GLOBAL_SPECS` / `GLOBAL_SCHEMA` `[schema.py:27, 375]`

| Key | Type | Default | Notes |
| --- | --- | --- | --- |
| `ui.theme` | CHOICE | `"Dark"` | `"Dark"` \| `"Light"` \| `"Solarized Dark"` |
| `ui.highlight_theme` | CHOICE | `"Default Dark"` | |
| `ui.highlight_theme_marketplace` | BUTTON | — | Opens the marketplace dialog. |
| `ui.font_family` | STRING | `"Consolas"` | |
| `ui.font_size` | INTEGER | `10` | 6–72 |
| `ui.show_line_numbers` | BOOLEAN | `True` | |
| `editor.tab_size` | INTEGER | `4` | 1–16 |
| `editor.use_spaces` | BOOLEAN | `True` | |
| `editor.auto_save` | BOOLEAN | `False` | |
| `editor.auto_save_delay_ms` | INTEGER | `800` | 100–60 000 |
| `editor.auto_save_format` | STRING | `"{unix.seconds}"` | Placeholders: `{year}` `{month}` … `{unix.float}` |
| `editor.word_wrap` | BOOLEAN | `False` | |
| `editor.highlight_delay_ms` | INTEGER | `300` | |
| `editor.suggestion_delay_ms` | INTEGER | `200` | |
| `editor.large_file_threshold_bytes` | INTEGER | `1 048 576` | |
| `completion.enabled` | BOOLEAN | `True` | |
| `completion.max_suggestions` | INTEGER | `50` | |
| `completion.max_visible` | INTEGER | `10` | |
| `completion.auto_trigger` | BOOLEAN | `True` | |
| `completion.min_chars_before_trigger` | INTEGER | `1` | |
| `checker.run_on_open` | BOOLEAN | `False` | |
| `checker.run_on_save` | BOOLEAN | `False` | |
| `checker.timeout_ms` | INTEGER | `30 000` | |
| `runner.timeout_ms` | INTEGER | `30 000` | |
| `runner.clear_output_before_run` | BOOLEAN | `True` | |
| `runner.stream_output` | BOOLEAN | `True` | |
| `startup.restore_files` | BOOLEAN | `True` | |
| `i18n.language` | CHOICE | `"zh_CN"` | `"zh_CN"` \| `"en_US"` |
| `i18n.language_marketplace` | BUTTON | — | |
| `logging.enabled` | BOOLEAN | `True` | |
| `logging.level` | CHOICE | `"INFO"` | `"DEBUG"` … `"CRITICAL"` |
| `logging.file_enabled` | BOOLEAN | `True` | |
| `logging.console_enabled` | BOOLEAN | `True` | |
| `logging.max_bytes` | INTEGER | `5 242 880` | |
| `logging.backup_count` | INTEGER | `5` | |
| `plugins.marketplace` | BUTTON | — | Opens plugin marketplace. |

### `PROJECT_SPECS` / `PROJECT_SCHEMA` `[schema.py:380, 478]`

| Key | Type | Default |
| --- | --- | --- |
| `project.python_interpreter` | PATH | `""` |
| `project.entry_point` | PATH | `"main.py"` |
| `project.c_compiler` | PATH | `"gcc"` |
| `project.cpp_compiler` | PATH | `"g++"` |
| `checker.enabled` | BOOLEAN | `True` |
| `checker.ignore` | LIST | `[]` |
| `project.exclude_paths` | LIST | `[]` |
| `project.tab_size` | INTEGER | `4` |
| `project.use_spaces` | BOOLEAN | `True` |
| `project.name` | STRING | `""` |
| `project.description` | STRING | `""` |

### `SCHEMA_BY_SCOPE` `[schema.py:483]`

```python
SCHEMA_BY_SCOPE: dict = {
    SettingsScope.GLOBAL: GLOBAL_SCHEMA,
    SettingsScope.PROJECT: PROJECT_SCHEMA,
}
```

### `get_schema(scope: SettingsScope) -> SettingsSchema` `[schema.py:489]`

Convenience accessor; equivalent to indexing `SCHEMA_BY_SCOPE`.

## `SettingsManager` `[manager.py:41]`

The unified entry point used by the editor and plugins.

```python
from modules.settings import SettingsManager, SettingsScope

with SettingsManager() as manager:
    manager.set(SettingsScope.GLOBAL, "ui.theme", "Light")
    manager.attach_project("/path/to/proj")
    manager.set(SettingsScope.PROJECT, "project.python_interpreter", "/usr/bin/python3")

    theme       = manager.effective("ui.theme")
    interpreter = manager.effective("project.python_interpreter")
```

### Properties

| Property | Description |
| --- | --- |
| `global_settings: GlobalSettings` | The always-present global instance. |
| `project_settings: Optional[ProjectSettings]` | `None` until `attach_project()`. |
| `project_root: Optional[str]` | Convenience for `project_settings.root`. |

### Methods

| Method | Signature | Description |
| --- | --- | --- |
| `attach_project` | `(root: str) -> ProjectSettings` | Saves the previous project, replaces the project settings with one rooted at `root`, returns the new instance. |
| `detach_project` | `() -> None` | Saves and clears the project. |
| `get` | `(scope, key, default=None) -> Any` | Read from the given scope. `scope=PROJECT` raises `LookupError` if no project is attached. |
| `set` | `(scope, key, value) -> None` | Validate and write; fires listeners. |
| `effective` | `(key, default=None) -> Any` | Project value if defined, else global value, else `default`. |
| `reset` | `(scope, key=None) -> None` | Reset one key or the entire scope to defaults. |
| `add_listener` / `remove_listener` | `(callback)` | Listener signature: `callback(event: SettingsChangeEvent)`. |
| `save_all` / `reload_all` | `() -> None` | Persist / re-read both scopes. |
| `global_all` | `() -> Dict[str, Any]` | Snapshot of global values. |
| `project_all` | `() -> Dict[str, Any]` | Snapshot of project values (or `{}`). |
| `effective_all` | `() -> Dict[str, Any]` | Merged view: project overrides global where defined. |

`SettingsManager` supports the context-manager protocol: entering returns
`self`, exiting calls `save_all()`.

## UI (`modules.settings.widgets`)

| Class | Description |
| --- | --- |
| `USettingPanel(UFrame)` | Renders one scope's settings panel, grouped by key prefix. Methods: `apply() -> int` (commits pending edits, returns the count of changes), `revert()`, `last_error()`. |
| `UProjectSettingsWindow` | `Toplevel` window combining `USettingsNavBar` + `USettingPanel` for both scopes. Buttons: Apply / Save / Close / Reset. |

`widgets.py` is large (622 lines); see the source for layout details.