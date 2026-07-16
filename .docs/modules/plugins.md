# `modules.plugins`

**Source**:
- [`__init__.py`](../../modules/plugins/__init__.py) — 70 lines
- [`api.py`](../../modules/plugins/api.py) — 215 lines
- [`hooks.py`](../../modules/plugins/hooks.py) — 85 lines
- [`manager.py`](../../modules/plugins/manager.py) — 719 lines
- [`marketplace.py`](../../modules/plugins/marketplace.py) — 130 lines
- [`widgets.py`](../../modules/plugins/widgets.py) — 346 lines

Plugin system. Each plugin is a directory containing `__init__.py`
(or `plugin.py`) that exposes a `MANIFEST` and a `register(ctx)` function.
The host (`PluginManager`) loads it via `importlib`, registers hooks /
commands / language contributions, and dispatches editor events.

```python
from modules.plugins import (
    PluginManifest, PluginContext, PluginManager,
    DiscoveredPlugin, PluginCommand, LanguageContribution,
    PluginHostAPI, PluginLoadError,
    HookEvents, HookSpec, HOOK_SPECS,
    plugin_marketplace,
)
```

A user guide lives in `docs/PLUGINS.md` (Chinese). This page is the API
reference.

## Discovery layout

```
<config-root>/plugins/<plugin_id>/__init__.py     # global plugins
<project-root>/plugins/<plugin_id>/__init__.py    # project plugins
```

Global plugin path defaults to `<settings_dir>/plugins/`; project plugins
are loaded when the editor attaches a project.

## Plugin-side API (`modules.plugins.api`)

### `HookHandler`, `CommandCallback`

```python
HookHandler = Callable[..., None]
CommandCallback = Callable[[], None]
```

### `PluginManifest` `[api.py:38]`

```python
@dataclass(frozen=True)
class PluginManifest:
    id: str
    name: str
    version: str = "0.0.0"
    description: str = ""
    author: str = ""
    scope: str = "global"        # 'global' | 'system'

    def validate(self) -> None: ...
```

`validate()` raises `ValueError` for empty `id`, illegal characters in
`id` (only `a-z`, `0-9`, `_`, `-` allowed), empty `name`, or an invalid
`scope`.

### `PluginCommand` `[api.py:62]`

```python
@dataclass(frozen=True)
class PluginCommand:
    plugin_id: str
    label: str
    callback: Callable[[], None]
    menu: str = "插件"
    shortcut: Optional[str] = None
```

### `LanguageContribution` `[api.py:71]`

```python
@dataclass(frozen=True)
class LanguageContribution:
    name: str
    ext: str                                  # e.g. '.go'
    highlighter_factory: Callable[[], Any]    # -> HighlighterExpert
    suggestion_factory: Callable[[], Any]     # -> SuggestionExpert | None
    sample: str = ""
    runner_factory: Optional[Callable[[], Any]] = None
    description: str = ""
```

### `PluginLoadError` `[api.py:89]`

`RuntimeError` subclass. Thrown when loading a plugin fails. The manager
catches it, records the error on the plugin record, and continues with
other plugins.

### `PluginHostAPI` `[api.py:93]`

`@runtime_checkable` `Protocol`. Defines the methods `PluginManager`
implements for `PluginContext`. Plugin code does **not** import this
directly; it goes through `ctx`.

### `PluginContext` `[api.py:107]`

The interface a plugin sees. Constructed by `PluginManager` and passed to
your `register(ctx)` function.

#### Properties

| Property | Type | Description |
| --- | --- | --- |
| `plugin_id` | `str` | The manifest id. |
| `plugin_name` | `str` | The manifest name. |

#### Methods

| Method | Signature | Description |
| --- | --- | --- |
| `on` | `(hook: str, callback=None)` | Two forms: direct `ctx.on('editor:file_opened', cb)` or decorator `@ctx.on('editor:file_opened')` over a function. Returns a `_HookSubscription`. |
| `add_command` | `(*, label, callback, menu='插件', shortcut=None) -> PluginCommand` | Register a menu item. `menu` is the menu name (default `"插件"`). `shortcut` uses `"Ctrl+Shift+H"` syntax. |
| `register_language` | `(contrib: LanguageContribution) -> None` | Add a new language with its highlighter + suggestion experts. |
| `append_output` | `(text: str) -> None` | Append to the editor output panel. |
| `log` | `(level: str, message: str) -> None` | Convenience: writes a `[LEVEL] [plugin_id] message` line to output. `level` ∈ `info` / `warning` / `error`. |
| `setting` | `(key: str, default=None) -> Any` | Read the effective value of `plugins.<plugin_id>.<key>`. |
| `set_setting` | `(key: str, value: Any) -> None` | Write `plugins.<plugin_id>.<key>`. |
| `is_enabled` | `() -> bool` | `bool(setting('enabled', True))`. |
| `on_unregister` | `(callback: Callable[[], None]) -> None` | Subscribe to plugin teardown; called before commands / languages are removed. |

## Hooks (`modules.plugins.hooks`)

### `HookEvents` `[hooks.py:35]`

| Constant | Value | Args |
| --- | --- | --- |
| `EDITOR_FILE_OPENED` | `"editor:file_opened"` | `(path: str)` |
| `EDITOR_FILE_SAVED` | `"editor:file_saved"` | `(path: str)` |
| `EDITOR_FILE_CREATED` | `"editor:file_created"` | `()` |
| `EDITOR_CONTENT_CHANGED` | `"editor:content_changed"` | `(code: str, cursor_pos: int)` |
| `EDITOR_LANGUAGE_CHANGED` | `"editor:language_changed"` | `(lang: str)` |
| `EDITOR_CURSOR_MOVED` | `"editor:cursor_moved"` | `(line: int, col: int)` |
| `EDITOR_RUN_STARTED` | `"editor:run_started"` | `(lang: str, temp_path: str)` |
| `EDITOR_RUN_FINISHED` | `"editor:run_finished"` | `(lang: str, returncode: int, stdout: str, stderr: str)` |
| `EDITOR_CHECK_FINISHED` | `"editor:check_finished"` | `(lang: str, issues: list)` |
| `EDITOR_CLOSING` | `"editor:closing"` | `()` |

### `HookSpec` `[hooks.py:50]`

```python
@dataclass(frozen=True)
class HookSpec:
    name: str
    params: Tuple[str, ...]
    description: str = ""
```

### `HOOK_SPECS` `[hooks.py:59]`

Tuple of `HookSpec` entries, one per `HookEvents` constant. The plugin
manager window iterates this list to render its hook reference.

## `PluginManager` (`modules.plugins.manager`)

Singleton used by the editor. Thread-safe (internally uses `RLock`); the
constructor doesn't need Tk, but commands only render to the menu after
`attach_editor`.

```python
manager = PluginManager()
manager.attach_editor(editor)
manager.load_global_plugins()
```

### Editor binding

| Method | Description |
| --- | --- |
| `attach_editor(editor)` | Wire up the editor (delayed until `CodeEditor._build_menubar` returns). |
| `detach_editor()` | Disconnect. |

### Discovery (no I/O side effects)

| Method | Returns |
| --- | --- |
| `discover_global() -> List[DiscoveredPlugin]` | Scans `<config>/plugins/`. |
| `discover_project(root) -> List[DiscoveredPlugin]` | Scans `<root>/plugins/`. |

A directory is considered a plugin if it contains `__init__.py` or
`plugin.py` (in that order of preference).

### Loading

| Method | Description |
| --- | --- |
| `load_global_plugins()` | Discovers + loads every system-scope plugin that is enabled. |
| `load_project_plugins(root)` | Loads `<root>/plugins/`; called when the editor attaches a project. |
| `unload_project_plugins()` | Unloads project-scope plugins only. |
| `unload_all()` | Unloads everything (used on `editor:_closing`). |

### Per-plugin

| Method | Description |
| --- | --- |
| `enable(plugin_id)` | Enable a discovered-but-disabled plugin. Loads it on first call. |
| `disable(plugin_id)` | Disable; removes commands / languages from UI but keeps the record. |
| `reload(plugin_id)` | Re-import the module (clears `sys.modules` cache) and call `register` again. Useful while developing a plugin. |

### Event dispatch

```python
manager.emit(HookEvents.EDITOR_FILE_OPENED, "/path/to/file.py")
```

`emit(hook, *args, **kwargs)` calls each subscribed handler in registration
order. Exceptions are caught, logged, and emitted to the output panel as
`[ERROR] [plugin_id] 钩子 'X' 回调失败: <msg>`.

### Query API

| Method | Returns |
| --- | --- |
| `list_loaded() -> List[_PluginRecord]` | Currently loaded plugins (internal record type). |
| `list_discovered() -> List[DiscoveredPlugin]` | All discovered plugins, including failed ones. |
| `get_commands() -> List[PluginCommand]` | Active commands across all enabled plugins. |
| `get_languages() -> List[Tuple[str, LanguageContribution]]` | Active language contributions. |

### Internal helpers (not public API)

- `_install_command`, `_install_language`: push a single record's
  contributions into the editor UI. Called by `enable` and during load.
- `_tk_shortcut(spec: str) -> str`: convert `"Ctrl+Shift+H"` to
  `"<Control-Shift-H>"` for Tk.

### `PluginHostAPI` implementation

`PluginManager` implements the `PluginHostAPI` protocol so that
`PluginContext` can call back into it:

```python
manager.register_hook(sub)         # internal
manager.register_command(cmd)
manager.register_language(plugin_id, contrib)
manager.append_output(text)
manager.setting(key, default)
manager.set_setting(key, value)
```

## `DiscoveredPlugin` `[manager.py:70]`

```python
@dataclass
class DiscoveredPlugin:
    manifest: PluginManifest
    location: str                   # absolute path to the plugin directory
    scope: str                      # 'system' | 'project'
```

## Marketplace (`modules.plugins.marketplace`)

Re-exported as `modules.plugins.plugin_marketplace`. Same shape as the
other marketplaces — `MarketplaceProvider` (ABC), a default
`PluginMarketplace`, and `get_plugin_marketplace()` returning the
process-wide instance.

## `UPluginManagerWindow` (`modules.plugins.widgets`)

`tk.Toplevel` window listing loaded + discovered plugins with
enable / disable / reload / info / close actions. Construct with
`(editor, manager)`.