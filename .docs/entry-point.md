# `main.py` — Application entry point

The application is a single 3274-line module that wires every subsystem
together. This page documents its public surface; everything else is
considered private.

```text
$ python main.py [--custom-titlebar]
```

| Argument | Effect |
| --- | --- |
| `--custom-titlebar` | Use a frameless window with a custom title bar (otherwise OS-native title bar). |

## Module-level constants

| Name | Description |
| --- | --- |
| `HIGHLIGHT_TOKENS` `[main.py:112]` | Default `token-type → {foreground}` mapping used when no highlight theme is active. |
| `LANG_CONFIG` `[main.py:139]` | Registry of supported languages: `Python`, `JSON`, `XML`, `YAML`, `LOG`. Each entry maps `ext`, `highlighter`, `suggestion`, `suggestion_factory`, `sample`. |
| `THEME_NAMES` `[main.py:152]` | UI theme names known to the View menu: `['Dark', 'Light', 'Solarized Dark']`. |
| `FONT_FAMILIES` `[main.py:153]` | Font family options in the View menu. |
| `FONT_SIZES` `[main.py:154]` | Font size options in the View menu. |
| `TAB_WIDTHS` `[main.py:155]` | Tab-width options in the View menu. |

## Module-level side effects `[main.py:157]`

Before anything else runs:

1. `configure_logging(level='INFO', file_enabled=True, console_enabled=True, log_dir=<project>/logs, max_bytes=5 MiB, backup_count=5)`.
2. `get_logger('app').info('Application starting...')`.

## Public classes

### `Document` `[main.py:64]`

Data model for one open file or `Untitled` document.

```python
@dataclass
class Document:
    path: Optional[str]      # None for an unsaved Untitled tab
    content: str = ''
    dirty: bool = False
    lang: str = 'Python'
    seq: int = 0             # Untitled counter (0 for files on disk)
```

### `_Debouncer` `[main.py:74]`

GUI-agnostic debounce scheduler. Constructed with `after(ms, cb)` and
`cancel(id)` hooks (typically Tk's `after`/`after_cancel`).

| Method | Signature | Description |
| --- | --- | --- |
| `schedule` | `(callback, delay_ms: int) -> None` | Cancel the previous pending callback, then schedule `callback` after `delay_ms` ms. |
| `cancel` | `() -> None` | Cancel the pending callback if any. |
| `pending_id` | property | The ID returned by `after()`, or `None`. |

### `CodeEditor` `[main.py:195]`

The single application controller. Construct then call `run()`.

```python
class CodeEditor:
    def __init__(self): ...
    def run(self) -> None: ...                 # Tk mainloop
```

Constructor responsibilities:

1. Build the `Window` (custom or native titlebar).
2. Instantiate `SettingsManager`, `Translator`, themes, plugin manager,
   environment manager.
3. Construct the menubar, toolbar, tab bar, editor, output panel, status bar.
4. Load global plugins and refresh plugin menus.
5. Schedule an initial `EnvironmentManager.scan()` after 100 ms.

#### Lifecycle hooks

```python
editor = CodeEditor()
editor.run()              # blocks; returns when the user closes the window
```

The `Window` is held at `editor.window`. The internal state is intentionally
private (underscore prefix). Plugins interact with the editor exclusively
through the `PluginContext` passed to their entry point — see
[modules/plugins.md](modules/plugins.md).

#### Grouped method reference

The full method list is split into logical groups below. The line numbers are
approximate; see `main.py` for the exact location.

**Multi-document management** (`_init_first_document`, `_new_doc_id`,
`_tab_title`, `_update_tab_bar`, `_switch_document`, `_tab_select`,
`_tab_close`, `_tab_context_menu`, `_close_other_tabs`, `_close_all_tabs`,
`_mark_dirty`, `_next_tab`, `_prev_tab`, `_close_active_tab`)

| Method | Description |
| --- | --- |
| `_init_first_document` | Create the initial `Untitled` document. |
| `_new_doc_id` | Allocate a new tab/document id. |
| `_tab_title(doc)` | Compute the tab title (filename or `Untitled-N`). |
| `_update_tab_bar` | Re-render the `TabBar` from `self._documents`. |
| `_switch_document(doc_id)` | Make `doc_id` the active tab. |
| `_tab_close(doc_id)` | Close a tab (with unsaved-changes prompt). |
| `_next_tab` / `_prev_tab` | Cycle through tabs. |
| `_close_active_tab` | Close the currently visible tab. |

**Settings** (`_on_settings_changed`, `_refresh_all_from_settings`,
`_apply_loaded_theme`, `_on_language_changed`, `_clear_menubar`,
`_refresh_status_for_language`, `_write_setting`, `_on_close_request`)

Settings changes are reflected without restart. `_write_setting(scope, key,
value)` is the single chokepoint used by UI controls.

**Project attachment** (`_is_within`, `_should_reattach_for_path`,
`_attach_project`)

`_attach_project(root)` switches the editor into project mode: it binds the
project-level settings (`<root>/.pyeditor/settings.json`) and discovers
project-scoped plugins.

**Menu / shortcut / status**

`_build_menubar`, `_bind_shortcuts`, `_build_toolbar`, `_build_editor`,
`_build_output_panel`, `_build_status_bar`, plus a family of `_*_var()`
helpers that lazily create Tk variables for each setting.

**Editor behaviour** (`_on_key_release`, `_on_key_press`, `_on_click`,
`_on_focus_in`, `_emit_cursor_moved`, `_apply_highlight`,
`_show_suggestions`, `_hide_suggestions`, `_on_suggestion_select`,
`_index_from_pos`, `_update_status`, `_switch_language`, `_on_lang_changed`)

The debounce layer: `_schedule_highlight`, `_schedule_suggestions`,
`_schedule_autosave` route through `_Debouncer` instances.

**File operations** (`_new_file`, `_open_file`, `_open_project`,
`_save_file`, `_save_file_as`, `_save_to_path`, `_open_path_from_tree`,
`_load_file_into_editor`, `_load_path_into_editor`,
`_stream_insert_into_editor`, `_human_size`, `_detect_lang_from_path`)

`_stream_insert_into_editor` reads large files in chunks; an `_stream_epoch`
counter guards against late callbacks overwriting newer content.

**Editing actions** (`_undo`, `_redo`, `_cut`, `_copy`, `_paste`,
`_select_all`, `_open_find`, `_open_replace`, `_show_find_dialog`,
`_goto_line`, `_line_count`, `_indent`, `_outdent`, `_toggle_comment`)

Find/Replace is implemented in `_show_find_dialog(replace: bool)` and the
nested `do_find`, `do_replace`, `do_replace_all`, `close` helpers.

**Navigation (stubs)** (`_goto_definition`, `_find_references`,
`_find_documentation`)

These exist as menu entries but currently delegate to `_reparse` and emit a
no-op status message. They are the documented extension points for IDE
features.

**Theme / marketplace** (`_reparse`, `_set_theme`, `_set_highlight_theme`,
`_open_highlight_theme_marketplace`, `_open_ui_theme_marketplace`,
`_open_plugin_marketplace`, `_open_language_marketplace`,
`_on_settings_panel_action`, `_force_redraw`, `_set_font_family`,
`_set_font_size`, `_apply_editor_font`, `_set_tab_width`,
`_toggle_highlighting`, `_toggle_suggestions`, `_toggle_autosave`)

`_set_theme(name)` switches the **UI** theme (`modules.Uui.widgets.theme`).
`_set_highlight_theme(name)` switches the **syntax** theme
(`modules.highlighter.themes`).

**Settings windows** (`_open_global_settings`, `_open_project_settings`,
`_reset_settings`)

`USettingPanel` / `UProjectSettingsWindow` from
`modules.Uui.widgets.settings_nav` are used here.

**Plugin integration** (`_emit`, `_emit_content_changed`,
`_add_plugin_command`, `_add_plugin_language`, `_refresh_plugin_menu`,
`_refresh_plugin_languages`, `_safe_run_plugin_command`, `_show_plugin_info`,
`_open_plugin_manager`, `_reload_all_plugins`)

`_emit(hook, *args, **kwargs)` delegates to `PluginManager.emit(...)`.

**Help dialogs** (`_show_documentation`, `_show_shortcuts`, `_show_about`,
`_check_updates`, `_report_issue`)

**Run / Check** (`_run_check`, `_run_code`, `_run_blocking_path`,
`_run_streaming_path`, `_append_output`, `_clear_output`)

`_run_check` picks between `Flake8Checker`, `PyrightChecker` and
`CPythonChecker` based on which tools are installed. `_run_code` writes the
buffer to a temp file and invokes `stream_command` for live output.

**Environment manager UI** (`_scan_environments`, `_on_env_changed`,
`_update_env_status`, `_open_env_manager`, `_create_venv_dialog`,
`_show_env_manager_dialog`, `_env_dialog_refresh`)

A separate `UDialog` is opened on demand and contains nested callbacks
(`load_packages`, `install_pkg`, `do_search`, `do_install`, `uninstall_pkg`,
`do_create`).

#### `run(self) -> None` `[main.py:2927]`

Wraps `self.window.mainloop()`. Returns when the user closes the window.

## Entry block `[main.py:3126]`

```python
if __name__ == '__main__':
    editor = CodeEditor()
    editor.run()
```