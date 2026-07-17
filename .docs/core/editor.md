# `core.editor`

**Source**:
- [`core/editor/__init__.py`](../../core/editor/__init__.py) — 25 lines
- [`core/editor/app.py`](../../core/editor/app.py) — ~2 330 lines (the bulk of the editor)
- [`core/editor/document.py`](../../core/editor/document.py) — 47 lines
- [`core/editor/lang_config.py`](../../core/editor/lang_config.py) — 78 lines

The `core.editor` package owns the data model for open documents, the
language registry, the UI constants surfaced to the menu system, and the
`CodeEditor` application controller.

```python
from core.editor import (
    Document, _Debouncer,
    FONT_FAMILIES, FONT_SIZES, HIGHLIGHT_TOKENS,
    LANG_CONFIG, TAB_WIDTHS, THEME_NAMES,
)
from core.editor.app import CodeEditor
```

## `Document` `[document.py:4]`

```python
@dataclass
class Document:
    path: str | None      # None for an unsaved Untitled tab
    content: str = ""
    dirty: bool = False
    lang: str = "Python"
    seq: int = 0          # Untitled counter (0 for files on disk)
```

Plain data class held in `CodeEditor._documents: dict[str, Document]`.
The key is an opaque `doc_id` allocated by `_new_doc_id()`.

## `_Debouncer` `[document.py:15]`

GUI-agnostic debounce scheduler. Constructed with `after(ms, cb)` and
`cancel(id)` hooks (typically Tk's `after`/`after_cancel`).

| Method | Signature | Description |
| --- | --- | --- |
| `schedule` | `(callback, delay_ms: int) -> None` | Cancel the previous pending callback, then schedule `callback` after `delay_ms` ms. |
| `cancel` | `() -> None` | Cancel the pending callback if any. |
| `pending_id` | property | The ID returned by `after()`, or `None`. |

`CodeEditor` instantiates three of these — for highlight, suggestions,
and auto-save — and pipes Tk's `window.after` / `window.after_cancel`
into them.

## Language registry (`core.editor.lang_config`)

`lang_config.py` is the central place that connects a language name to
its highlighter / suggestion experts and to a starter sample shown in
new tabs.

### `HIGHLIGHT_TOKENS` `[lang_config.py:10]`

Default `token-type → {foreground}` mapping used when no highlight theme
is active. Keys include `keyword`, `builtin`, `string`, `number`,
`comment`, `identifier`, `operator`, `punctuation`, `function`,
`class`, `struct`, `preprocessor`, `decorator`, `self`, `type`,
`module`, `key`, `tag`, `timestamp`, `level_debug`, `level_info`,
`level_warn`, `level_error`, `level_critical`.

### `LANG_CONFIG` `[lang_config.py:37]`

Registry of supported languages. Each entry is a dict:

```python
{
    "ext": ".py",
    "highlighter": PythonHighlighterExpert,
    "suggestion": PythonSuggestionExpert,
    "suggestion_factory": lambda: PythonSuggestionExpert(),
    "sample": 'def hello():\n    print("Hello, world!")\n\nhello()\n',
}
```

Built-in entries:

| Name | Extensions | Highlighter | Suggestion |
| --- | --- | --- | --- |
| `Python` | `.py` | `PythonHighlighterExpert` | `PythonSuggestionExpert` |
| `JSON` | `.json` | `JsonHighlighterExpert` | — |
| `XML` | `.xml` | `XmlHighlighterExpert` | — |
| `YAML` | `.yaml`, `.yml` | `YamlHighlighterExpert` | — |
| `LOG` | `.log` | `LogHighlighterExpert` | — |

Additional languages can be added at runtime by plugins via
`PluginContext.register_language(LanguageContribution)`.

### UI constants `[lang_config.py:75]`

| Name | Value |
| --- | --- |
| `THEME_NAMES` | `["Dark", "Light", "Solarized Dark"]` |
| `FONT_FAMILIES` | `["Consolas", "Courier New", "Menlo", "Monaco"]` |
| `FONT_SIZES` | `[9, 10, 11, 12, 14, 16]` |
| `TAB_WIDTHS` | `[2, 4, 8]` |

## `CodeEditor` `[app.py:55]`

The single application controller. Construct then call
`editor.window.mainloop()` (or use the helper `main()` in `main.py`).

```python
class CodeEditor:
    def __init__(self): ...
```

`CodeEditor` exposes one public attribute, `window` (a
`ui.widgets.Window`), and a private state namespace prefixed with
underscores. The full method list is split into logical groups below.
The line numbers are approximate; see `app.py` for the exact location.

### Constructor responsibilities `[app.py:56]`

1. Build the `Window` (custom or native titlebar).
2. Instantiate `SettingsManager`, `Translator`, themes, plugin manager.
3. Construct the menubar, toolbar, tab bar, editor, output panel, status
   bar.
4. Load global plugins and refresh plugin menus.

### Grouped method reference

#### Multi-document management

`_init_first_document`, `_new_doc_id`, `_tab_title`, `_update_tab_bar`,
`_switch_document`, `_tab_select`, `_tab_close`, `_tab_context_menu`,
`_close_other_tabs`, `_close_all_tabs`, `_mark_dirty`, `_next_tab`,
`_prev_tab`, `_close_active_tab`.

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

#### Settings

`_on_settings_changed`, `_refresh_all_from_settings`,
`_apply_loaded_theme`, `_on_language_changed`, `_clear_menubar`,
`_refresh_status_for_language`, `_write_setting`, `_on_close_request`.

Settings changes are reflected without restart. `_write_setting(scope,
key, value)` is the single chokepoint used by UI controls.

#### Project attachment

`_is_within`, `_should_reattach_for_path`, `_attach_project`.

`_attach_project(root)` switches the editor into project mode: it binds
the project-level settings (`<root>/.pyeditor/settings.json`) and
discovers project-scoped plugins.

#### Menu / shortcut / status

`_build_menubar`, `_bind_shortcuts`, `_build_toolbar`, `_build_editor`,
`_build_output_panel`, `_build_status_bar`, plus a family of `_*_var()`
helpers that lazily create Tk variables for each setting.

#### Editor behaviour

`_on_key_release`, `_on_key_press`, `_on_click`, `_on_focus_in`,
`_emit_cursor_moved`, `_apply_highlight`, `_show_suggestions`,
`_hide_suggestions`, `_on_suggestion_select`, `_index_from_pos`,
`_update_status`, `_switch_language`, `_on_lang_changed`.

The debounce layer: `_schedule_highlight`, `_schedule_suggestions`,
`_schedule_autosave` route through `_Debouncer` instances.

#### File operations

`_new_file`, `_open_file`, `_open_project`, `_save_file`,
`_save_file_as`, `_save_to_path`, `_open_path_from_tree`,
`_load_file_into_editor`, `_load_path_into_editor`,
`_stream_insert_into_editor`, `_human_size`, `_detect_lang_from_path`.

`_stream_insert_into_editor` reads large files in chunks; an
`_stream_epoch` counter guards against late callbacks overwriting
newer content.

#### Editing actions

`_undo`, `_redo`, `_cut`, `_copy`, `_paste`, `_select_all`,
`_open_find`, `_open_replace`, `_show_find_dialog`, `_goto_line`,
`_line_count`, `_indent`, `_outdent`, `_toggle_comment`.

Find/Replace is implemented in `_show_find_dialog(replace: bool)` and
the nested `do_find`, `do_replace`, `do_replace_all`, `close` helpers.

#### Navigation (stubs)

`_goto_definition`, `_find_references`, `_find_documentation`.

These exist as menu entries but currently delegate to `_reparse` and
emit a no-op status message. They are the documented extension points
for IDE features.

#### Theme / marketplace

`_reparse`, `_set_theme`, `_set_highlight_theme`,
`_open_highlight_theme_marketplace`, `_open_ui_theme_marketplace`,
`_open_plugin_marketplace`, `_open_language_marketplace`,
`_on_settings_panel_action`, `_force_redraw`, `_set_font_family`,
`_set_font_size`, `_apply_editor_font`, `_set_tab_width`,
`_toggle_highlighting`, `_toggle_suggestions`, `_toggle_autosave`.

`_set_theme(name)` switches the **UI** theme (`ui.widgets.theme`).
`_set_highlight_theme(name)` switches the **syntax** theme
(`core.language.highlighter.themes`).

#### Settings windows

`_open_global_settings`, `_open_project_settings`, `_reset_settings`.

`USettingPanel` / `UProjectSettingsWindow` from
`ui.widgets.settings_nav` are used here.

#### Plugin integration

`_emit`, `_emit_content_changed`, `_add_plugin_command`,
`_add_plugin_language`, `_refresh_plugin_menu`,
`_refresh_plugin_languages`, `_safe_run_plugin_command`,
`_show_plugin_info`, `_open_plugin_manager`, `_reload_all_plugins`.

`_emit(hook, *args, **kwargs)` delegates to `PluginManager.emit(...)`.

#### Help dialogs

`_show_documentation`, `_show_shortcuts`, `_show_about`,
`_check_updates`, `_report_issue`.

#### Run / Check

`_run_check`, `_run_code`, `_run_blocking_path`,
`_run_streaming_path`, `_append_output`, `_clear_output`.

`_run_check` picks between `Flake8Checker`, `PyrightChecker` and
`CPythonChecker` based on which tools are installed. `_run_code`
writes the buffer to a temp file and invokes `stream_command` for live
output.

## Public surface

`core.editor.__all__ = ["Document", "_Debouncer", "HIGHLIGHT_TOKENS",
"LANG_CONFIG", "THEME_NAMES", "FONT_FAMILIES", "FONT_SIZES",
"TAB_WIDTHS"]` — the editor class itself is reached via
`from core.editor.app import CodeEditor`.