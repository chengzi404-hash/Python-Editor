# `core.settings`

**Source layout**:

```
core/settings/
├── __init__.py
├── settings/           — global / project settings + schemas + storage
│   ├── __init__.py
│   ├── base.py
│   ├── global_settings.py
│   ├── project_settings.py
│   ├── schema.py
│   ├── storage.py
│   ├── manager.py
│   └── widgets.py
├── i18n/               — translation lookup + language marketplace
│   ├── __init__.py
│   ├── translator.py
│   └── marketplace.py
└── logging/            — unified rotating logger
    ├── __init__.py
    └── logger.py
```

The `core.settings` umbrella package exposes three independent
sub-packages plus a top-level convenience re-export. Pick the
sub-package that matches the concern:

| Sub-package | Doc |
| --- | --- |
| `core.settings.settings` | Global / project settings, schemas, JSON storage, manager |
| `core.settings.i18n` | Translation lookup, runtime language switching |
| `core.settings.logging` | Unified rotating-file logger |

```python
# Convenience re-exports
from core.settings import (
    SettingsManager, SettingsScope,
    GlobalSettings, ProjectSettings,
    SettingSpec, SettingsSchema, SettingValueType,
    SettingsChangeEvent, SettingsListener,
    GLOBAL_SCHEMA, GLOBAL_SPECS, PROJECT_SCHEMA, PROJECT_SPECS, SCHEMA_BY_SCOPE,
    JsonFileSettings, CURRENT_VERSION,
    default_global_path, default_project_path, get_schema,
)
```

---

## `core.settings.settings`

**Source**:
- [`base.py`](../../core/settings/settings/base.py) — 307 lines
- [`global_settings.py`](../../core/settings/settings/global_settings.py) — 75 lines
- [`project_settings.py`](../../core/settings/settings/project_settings.py) — 87 lines
- [`schema.py`](../../core/settings/settings/schema.py) — 483 lines
- [`storage.py`](../../core/settings/settings/storage.py) — 275 lines
- [`manager.py`](../../core/settings/settings/manager.py) — 207 lines

Unified project settings and global settings interface.

### Quick start

```python
from core.settings.settings import SettingsManager, SettingsScope

manager = SettingsManager()                # Default loads global settings
manager.attach_project("/path/to/proj")    # Attach project

# Global
manager.set(SettingsScope.GLOBAL, "ui.theme", "Light")
# Project
manager.set(SettingsScope.PROJECT, "project.python_interpreter", "/usr/bin/python3")

# Effective value (project first, fallback to global)
theme = manager.effective("ui.theme")
interpreter = manager.effective("project.python_interpreter")

# Persist (or `with SettingsManager() as m:` for auto-save)
manager.save_all()
```

### Abstract layer (`base.py`)

| Symbol | Description |
| --- | --- |
| `SettingsScope` | Enum: `GLOBAL` (shared, user home) / `PROJECT` (bound to current workspace). |
| `SettingValueType` | Enum: `STRING`, `INTEGER`, `FLOAT`, `BOOLEAN`, `CHOICE`, `LIST`, `PATH`, `BUTTON`. |
| `SettingSpec` | Metadata for a single setting (key, type, default, label, description, choices, min, max, scope). Has a `validate(value)` method. |
| `SettingsSchema` | A tuple of `SettingSpec` with key-based indexing (`get`, `__contains__`, `defaults()`). |
| `SettingsChangeEvent` | Dataclass: `scope`, `key`, `old`, `new`. `key=None` means a bulk reset. |
| `SettingsListener` | `Callable[[SettingsChangeEvent], None]`. |
| `Settings` | ABC — `get`, `set`, `has`, `all`, `defined`, `reset`, `save`, `load`, `add_listener`. |

### Storage (`storage.py`)

`JsonFileSettings(Settings)` — JSON file-based persistence. Data is
stored as `{"version": 1, "scope": ..., "values": {...}}`. All I/O is
serialized via `threading.RLock`. `save()` writes to a temp file then
`os.replace()` to avoid reading half-written state. `load()` tolerates
missing files and format errors.

Plugin-scoped keys (`plugins.<id>.*`) are detected via
`_is_plugin_key()` and stored in a separate `_extras` map that bypasses
schema validation. `CURRENT_VERSION = 1`.

### Global settings (`global_settings.py`)

```python
from core.settings.settings import GlobalSettings, default_global_path

# default_global_path() resolves cross-platform:
#  Windows: %APPDATA%/PythonEditor/settings.json (falls back to ~/AppData/Roaming/PythonEditor)
#  macOS:   ~/Library/Application Support/PythonEditor/settings.json
#  Linux:   $XDG_CONFIG_HOME/PythonEditor/settings.json (falls back to ~/.config/PythonEditor)

gs = GlobalSettings()    # auto_load=True by default
gs.save()
```

### Project settings (`project_settings.py`)

```python
from core.settings.settings import ProjectSettings, default_project_path

# default_project_path(root) -> <root>/.pyeditor/settings.json

ps = ProjectSettings(root="/path/to/proj")
ps.set("project.python_interpreter", "/usr/bin/python3")
ps.save()
```

`ProjectSettings.root` is the absolute project directory and is exposed
as a read-only property.

### Schema (`schema.py`)

The built-in schemas ship with the editor. They are surfaced as:

| Constant | Description |
| --- | --- |
| `GLOBAL_SPECS`, `GLOBAL_SCHEMA` | Built-in global setting metadata. |
| `PROJECT_SPECS`, `PROJECT_SCHEMA` | Built-in project setting metadata. |
| `SCHEMA_BY_SCOPE` | `{GLOBAL: GLOBAL_SCHEMA, PROJECT: PROJECT_SCHEMA}`. |
| `get_schema(scope)` | Lookup helper. |

#### Built-in global settings (`GLOBAL_SPECS`)

Grouped by prefix:

- `ui.*` — `theme`, `highlight_theme`, `highlight_theme_marketplace` (button), `font_family`, `font_size`, `show_line_numbers`
- `editor.*` — `tab_size`, `use_spaces`, `auto_save`, `auto_save_delay_ms`, `auto_save_format`, `word_wrap`, `highlight_delay_ms`, `suggestion_delay_ms`, `large_file_threshold_bytes`
- `completion.*` — `enabled`, `max_suggestions`, `max_visible`, `auto_trigger`, `min_chars_before_trigger`
- `checker.*` — `run_on_open`, `run_on_save`, `timeout_ms`
- `runner.*` — `timeout_ms`, `clear_output_before_run`, `stream_output`
- `startup.*` — `restore_files`
- `i18n.*` — `language`, `language_marketplace` (button)
- `logging.*` — `enabled`, `level`, `file_enabled`, `console_enabled`, `max_bytes`, `backup_count`
- `plugins.*` — `marketplace` (button)

#### Built-in project settings (`PROJECT_SPECS`)

- `project.*` — `python_interpreter`, `entry_point`, `c_compiler`, `cpp_compiler`, `exclude_paths`, `tab_size`, `use_spaces`, `name`, `description`
- `checker.*` — `enabled`, `ignore`

### `SettingsManager` (`manager.py`)

Unified manager for global + project settings. Always holds a
`GlobalSettings`; the current `ProjectSettings` is optional, bound via
`attach_project`.

```python
manager = SettingsManager()
```

| Property / Method | Description |
| --- | --- |
| `global_settings` | The bound `GlobalSettings`. |
| `project_settings` | The current `ProjectSettings` or `None`. |
| `project_root` | The current project root or `None`. |
| `attach_project(root) -> ProjectSettings` | Mount a project root; saves the previous project first. |
| `detach_project()` | Save and unmount the current project. |
| `get(scope, key, default=None)` | Read a key on the specified scope. |
| `effective(key, default=None)` | Project overrides global; falls back to `default`. |
| `set(scope, key, value)` | Write and notify. Validates against the schema. |
| `reset(scope, key=None)` | Reset one key or all keys in the scope. |
| `add_listener(cb)` / `remove_listener(cb)` | Subscribe to changes from either scope. |
| `save_all()` / `reload_all()` | Save or reload both scopes. |
| `global_all()` / `project_all()` / `effective_all()` | Snapshot dicts. |
| `__enter__` / `__exit__` | Context-manager shorthand that calls `save_all()` on exit. |

---

## `core.settings.i18n`

**Source**:
- [`translator.py`](../../core/settings/i18n/translator.py) — 176 lines
- [`marketplace.py`](../../core/settings/i18n/marketplace.py) — 124 lines

Lightweight internationalization. Zero external dependencies — JSON
files in `data/i18n/locales/<lang>.json` are the source of truth.

```python
from core.settings.i18n import t, translator, get_translator

translator.set_language("en_US")
print(t("menu.file.new"))          # -> "New"
print(t("greeting", name="Alice")) # -> "Hello, Alice!"

def on_change(lang):
    print("language switched to", lang)
translator.add_listener(on_change)
```

| Symbol | Description |
| --- | --- |
| `AVAILABLE_LANGUAGES` | `("zh_CN", "en_US")`. |
| `t(key, default=None, **kwargs)` | Module-level convenience; uses `str.format` placeholders. |
| `get_translator() -> Translator` | Process-wide singleton accessor. |
| `language_marketplace` | Marketplace object (re-exported from `marketplace`). |
| `I18nListener` | `Callable[[str], None]`. |

### `Translator`

Global translator instance.

| Property / Method | Description |
| --- | --- |
| `current_language` (property) | Active language code. |
| `available_languages` (property) | Tuple of supported languages. |
| `set_language(lang) -> bool` | Switch language; returns whether a change actually occurred. Fires all registered listeners. |
| `add_listener(cb)` / `remove_listener(cb)` | Subscribe / unsubscribe. |
| `reload()` | Re-read all language packs from disk. |
| `has(key, locale=None) -> bool` | Check translation presence. |
| `translate(key, default=None, locale=None, **kwargs) -> str` | Look up the translation. Falls back: current → `en_US` → `default` → `key`. Returns the key at minimum. |

Missing translations never raise; placeholder mismatches return the
unformatted string instead.

### Marketplace (`marketplace.py`)

Re-exported as `core.settings.i18n.language_marketplace`. Same shape as
the other marketplaces — `MarketplaceProvider` (ABC), a default
`LanguageMarketplace`, and `get_language_marketplace()` returning the
process-wide instance.

---

## `core.settings.logging`

**Source**:
- [`logger.py`](../../core/settings/logging/logger.py) — 289 lines

Unified logging: file + console + in-memory ring buffer, rotating.

```python
from core.settings.logging import configure_logging, get_logger, set_log_level, shutdown

configure_logging(level="INFO", file_enabled=True, console_enabled=True,
                  log_dir="/path/to/logs", max_bytes=5 * 1024 * 1024, backup_count=5)
log = get_logger("app")
log.info("Application starting...")
```

| Symbol | Description |
| --- | --- |
| `LogLevel` | `IntEnum`: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`. |
| `configure_logging(level, file_enabled, console_enabled, log_dir, max_bytes, backup_count)` | One-shot global config. Reconfigures every existing logger. |
| `set_log_level(level)` | Dynamically change the log level. |
| `get_logger(name="app") -> Logger` | Get or create a named logger; the same name always returns the same instance. |
| `shutdown()` | Flush all handlers. |

### `Logger`

Wraps `logging.Logger` with two extra concerns:

- A `RotatingFileHandler` writing to `<log_dir>/<name>.log`.
- An in-memory ring buffer (`_Handler`) holding the last 500 entries.
  Use `Logger.get_entries(level=None) -> list[dict]` and
  `Logger.clear_entries()` to access / reset it.

Methods: `debug`, `info`, `warning`, `error`, `critical`, `exception`,
`log(level, msg)`, `get_entries`, `clear_entries`, `flush`.

---

## Public surface

`core.settings.__all__ = ["CURRENT_VERSION", "GLOBAL_SCHEMA",
"GLOBAL_SPECS", "PROJECT_SCHEMA", "PROJECT_SPECS", "SCHEMA_BY_SCOPE",
"GlobalSettings", "JsonFileSettings", "ProjectSettings",
"SettingSpec", "SettingValueType", "Settings", "SettingsChangeEvent",
"SettingsListener", "SettingsManager", "SettingsSchema",
"SettingsScope", "default_global_path", "default_project_path",
"get_schema"]`.