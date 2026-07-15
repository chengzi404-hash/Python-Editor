# `modules.Uui.widgets`

**Location**: [`modules/Uui/widgets/`](../../modules/Uui/widgets/)

Themed replacement for `tk.*` widgets. Each widget listens to the
current `theme` and re-applies its colors on `theme.set_theme(...)`.
All public widgets re-export `__all__` from
[`modules/Uui/widgets/__init__.py`](../../modules/Uui/widgets/__init__.py).

```python
from modules.Uui.widgets import (
    theme, ui_theme_marketplace,
    UFrame, ULabel, UButton, UEntry, UText,
    UCheckButton, URadioButton, UComboBox,
    UProgressBar, USlider, UScrollBar,
    UMenuBar, UMenu,
    UEditorSuggestion, CompletionItem,
    UFileTree,
    USettingsNavBar, NavSelection,
    TreeCanvas, LineNumberCanvas,
    TabBar, Tab,
    UDialog, UTabView, UListView,
    message_box,
    ActivityBar, ActivityBarItem, SideBar,
    ExplorerCard, DebugCard, GitCard,
)
from modules.Uui.widgets.window import Window
```

## `theme` module

The single source of truth for UI colors / fonts. Defined classes:

| Class | Line | Notes |
| --- | --- | --- |
| `Theme` | `[theme.py:5]` | Base class with class-level color / font constants. |
| `DarkTheme` | `[theme.py:58]` | The default `name='Dark'`. |
| `LightTheme` | `[theme.py:62]` | `name='Light'`. |
| `SolarizedDarkTheme` | `[theme.py:~103]` | `name='Solarized Dark'`. |

`Theme` attributes include `BG_TITLE`, `BG_BASE`, `BG_PANEL`, `BG_RAISED`,
`BG_HOVER`, `BG_ACTIVE`, `BG_INPUT`, `BG_DROPDOWN`, `FG_PRIMARY`,
`FG_SECONDARY`, `FG_TERTIARY`, `FG_DISABLED`, `BORDER`, `BORDER_STRONG`,
`BORDER_FOCUS`, `RED`/`RED_HOVER`/`RED_DARK`, `YELLOW_*`, `GREEN_*`,
`BLUE_*`, `PURPLE`, `TITLE_ACCENT_WIDTH`, `TITLE_ACCENT`,
`TITLE_FONT`, `MENU_FONT`, `LABEL_FONT`, `LABEL_FONT_BOLD`,
`LABEL_FONT_SMALL`, `BUTTON_FONT`, `ICON_FONT`, `MONO_FONT`.

### Module-level functions

| Function | Description |
| --- | --- |
| `available() -> List[Theme]` | All built-in theme classes. |
| `by_name(name) -> Optional[Theme]` | Lookup by name. |
| `current() -> Theme` | The active theme. |
| `on_change(callback)` / `off_change(callback)` | `callback(theme: Theme)` subscription. |
| `set_theme(theme_obj, *, refresh_root=None)` | Activate a theme and (optionally) re-apply recursively to `refresh_root`. |
| `apply_theme_recursive(widget)` | Walk a widget subtree and re-apply colors via each widget's `_apply_theme()`. |
| `__getattr__(name)` | Delegate to `current()` so `theme.BG_BASE` always reads the active palette. |
| `follow_system(root=None, *, mapping=None, poll_interval_ms=1500)` | Poll OS theme (Windows / macOS) and auto-switch every `poll_interval_ms`. |
| `stop_following()` | Stop the auto-follow poller. |

### `FOLLOW_SYSTEM_THEME` dict

A built-in mapping from OS theme names to Uui theme names, used by
`follow_system`. Override via `mapping={...}`.

## `Window` `[window.py:30]`

```python
class Window(tk.Tk):
    def __init__(self, *, title='', custom_titlebar=True, ...): ...
```

| Method | Description |
| --- | --- |
| `start_move(event)` | Begin a custom titlebar drag. |
| `set_position(event)` | Continue the drag. |
| `set_position(x, y)` (programmatic) | Place the window. |
| `maximize()` / `minimize()` | Window control. |
| `title` (property override) | Read / write the title text. |
| `_apply_theme()` | Internal — recolour the custom titlebar. |

`WindowPlacement` (ctypes Structure) is internal; used to query the
Windows shell for the previous placement.

## Core widgets

### `UFrame(parent, *, variant='base', **kw)` `[frame.py]`

`tk.Frame` subclass with `variant` ∈ `{'title', 'base', 'panel', 'raised', 'input'}`.
`_apply_theme()` rebuilds colors when the theme changes.

### `ULabel(parent, text='', *, variant='primary', **kw)` `[label.py]`

`tk.Label` subclass with `variant` ∈ `{'primary', 'secondary', 'tertiary', 'disabled', 'blue', 'red', 'green', 'yellow'}`.

### `UButton(parent, text='', *, command=None, variant='default', state='normal', width=None, **kw)` `[button.py]`

Canvas-drawn rounded button (not `tk.Button`). `variant` ∈ `{'default', 'primary', 'success', 'danger', 'warning', 'ghost'}`. `state` ∈ `{'normal', 'disabled'}`.

### `UEntry(parent, *, textvariable=None, placeholder='', width=20, show='', **kw)` `[entry.py]`

`tk.Frame` containing `tk.Entry` with placeholder + theme-aware colors. `show` enables password masking.

### `UText(parent, *, height=10, width=40, line_numbers=False, **kw)` `[text.py]`

`tk.Frame` wrapping `tk.Text` + `UScrollBar` (optional `LineNumberCanvas`). Methods:

| Method | Description |
| --- | --- |
| `get(start='1.0', end='end')` | Get text. |
| `insert(index, text, tags=())` | Insert text. |
| `delete(start, end)` | Delete range. |
| `clear()` | Delete all. |
| `see(index)` | Scroll to a Tk index. |
| `config(**kw)` / `configure(**kw)` | Pass through to the inner `tk.Text`. |
| `_apply_theme()` | Recolor on theme change. |

### `UCheckButton(parent, *, text='', variable=None, command=None, **kw)` `[checkbutton.py]`

Custom-drawn check button.

### `URadioButton(parent, *, text='', variable=None, value=None, command=None, **kw)` `[radiobutton.py]`

Custom-drawn radio button.

### `UComboBox(parent, *, values=(), variable=None, command=None, width=20, **kw)` `[combobox.py]`

Custom dropdown built on a `tk.Toplevel`. Use like `tkinter.ttk.Combobox`.

### `UProgressBar(parent, *, maximum=100, value=0, orient='horizontal', **kw)` `[progressbar.py]`

`tk.Canvas`-drawn progress bar.

### `USlider(parent, *, minimum=0, maximum=100, value=0, orient='horizontal', command=None, **kw)` `[slider.py]`

`tk.Canvas`-drawn slider, horizontal or vertical.

### `UScrollBar(parent, *, orient='vertical', autohidden=False, **kw)` `[scrollbar.py]`

Theme-aware scroll bar.

| Method | Description |
| --- | --- |
| `set(first, last)` | Update the visible range (0.0–1.0). |
| `get()` | Return `(first, last)`. |
| `config(**kw)` / `configure(**kw)` | Pass-through configuration. |
| `cget(key)` | Get an option. |

## Menus

### `UMenu(parent, **kw)` / `UMenuBar(parent, **kw)` `[menu.py]`

`UMenu` builds an item list. `UMenuBar` is a `tk.Frame` that renders
buttons for each top-level menu. Internal helpers `_MenuItemRow` and
`_MenuDropdown` are not part of the public API.

## Completion popup

### `CompletionItem` `[editor_suggestion.py:9]`

```python
@dataclass
class CompletionItem:
    label: str
    detail: str = ''
    description: str = ''
    insert: str = ''       # defaults to label if empty
    kind: str = ''
    priority: int = 0
```

### `UEditorSuggestion(parent, items=(), on_select=None, *, max_visible=8, show_detail=True, show_description=True, grab_focus=False)` `[editor_suggestion.py:22]`

`tk.Toplevel`-based popup for code-completion. Only one popup is visible
at a time (class-level `_active`).

| Method | Description |
| --- | --- |
| `show(items, *, x, y)` | Show at screen position with new items. |
| `hide()` | Withdraw. |
| `set_items(items)` | Replace items without repositioning. |
| `select_next()` / `select_prev()` | Move selection. |
| `selected()` | Returns the highlighted `CompletionItem` or `None`. |
| `move(dx, dy)` | Reposition by delta. |
| `destroy()` | Tear down and clear `_active`. |

## Tabs

### `Tab` `[tab_bar.py:14]`

```python
@dataclass
class Tab:
    id: str
    title: str
    dirty: bool = False
    closeable: bool = True
```

### `TabBar(parent, *, on_select=None, on_close=None, on_context_menu=None, **kw)` `[tab_bar.py:22]`

Canvas-drawn tab strip.

| Method | Description |
| --- | --- |
| `set_tabs(tabs: List[Tab], active_id: Optional[str] = None)` | Render the whole list. |
| `update_tab(tab: Tab)` | Patch a single tab in place. |
| `set_active(tab_id: str)` | Highlight. |
| `remove_tab(tab_id: str)` | Remove. |

## Dialogs

### `UDialog(parent, *, title='', width=400, height=240)` `[dialog.py]`

Toplevel with custom titlebar + body. Property `body` returns the
content `UFrame` you can pack into.

### `UTabView(parent)` `[tab_view.py]`

| Method | Description |
| --- | --- |
| `add_tab(tab_id: str, label: str) -> tk.Frame` | Create a tab and return its content frame. |
| `select(tab_id: str)` | Switch. |
| `on_switch(callback: Callable[[str], None])` | Subscribe to switches. |

### `UListView(parent, *, columns=(), on_select=None)` `[list_view.py]`

Canvas-backed table.

| Method | Description |
| --- | --- |
| `set_data(rows)` | Replace all rows. |
| `clear()` | Empty. |
| `selected_index` (property) | Index of the highlighted row. |
| `selected_value` (property) | The row tuple. |

## Message boxes (`modules.Uui.widgets.message_box`)

| Function | Description |
| --- | --- |
| `askstring(parent, title, prompt, initialvalue='', **kwargs)` | Wraps `tkinter.simpledialog.askstring`. |
| `showinfo(title, message, parent=None, **kwargs)` | Modal info dialog. |
| `showerror(title, message, parent=None, **kwargs)` | Modal error dialog (red). |
| `showwarning(title, message, parent=None, **kwargs)` | Modal warning dialog (yellow). |
| `askyesno(title, message, parent=None, **kwargs) -> bool` | Yes/No dialog. |
| `askstring_custom(parent, title, prompt, initialvalue='') -> Optional[str]` | Custom `UEntry`-based prompt. |

`_UDialogBase` is internal.

## Sidebar system

### `ActivityBarItem(parent, *, icon='explorer', tooltip='', on_click=None)` `[sidebar.py:18]`

Vertical icon button.

### `ActivityBar(parent)` `[sidebar.py:86]`

Container for `ActivityBarItem` instances. Holds the active selection.

### `SideBar(UFrame)` `[sidebar.py:131]`

VSCode-style sidebar: an `ActivityBar` on the left + a content area on
the right that swaps between cards.

| Method | Description |
| --- | --- |
| `set_active(card_id: str)` | Show a card. |
| `add_card(card_id: str, widget)` | Register a card. |

### `ExplorerCard(UFrame)` `[explorer_card.py]`

| Method | Description |
| --- | --- |
| `set_root(path: str)` | Set the directory to display. |
| `refresh()` | Re-scan. |
| `_apply_theme()` | Recolor. |

### `DebugCard(UFrame)` `[debug_card.py]`

VSCode-style debug sidebar.

#### Data classes

```python
@dataclass
class DebugLocation:
    file: str
    line: int
    function: str = ''

@dataclass
class VariableInfo:
    name: str
    value: str
    type: str = ''
```

#### `DebugSession` `[debug_card.py:37]`

`pdb`-based session controller.

| Method | Description |
| --- | --- |
| `set_callbacks(on_state_change, on_variables_change, on_stack_change, on_output)` | Subscribe to events. |
| `add_breakpoint(file, line)` / `remove_breakpoint(file, line)` / `clear_breakpoints()` / `get_breakpoints() -> Dict[str, List[int]]` | Manage breakpoints. |
| `start(file, args='') -> bool` | Launch `python -m pdb <file>`. Returns `False` if already running. |
| `step_over()` / `step_into()` / `continue_()` / `stop()` | Drive the debugger via `p`/`s`/`c` commands. |
| `is_running` / `is_paused` (properties) | State queries. |
| `set_variables(vars)` / `set_call_stack(stack)` | Push state from the debugger (called internally by `_read_output`). |

#### `DebugCard(UFrame)` methods

`set_workspace_root`, `set_debug_state`, `set_variables`,
`set_call_stack`, `set_breakpoints`, `add_breakpoint`,
`remove_breakpoint`, `clear_breakpoints`, `set_current_file`.

### `GitCard(UFrame)` `[git_card.py]`

Full Git UI: branch chips, ahead/behind counts, commit composer (Ctrl+Enter),
staged / unstaged lists, push / pull / refresh / commit (Amend).

Key public methods: `set_workspace_root`, `set_on_file_click`,
`refresh`, `get_branch`, `has_staged_changes`, `get_staged_count`,
`get_unstaged_count`, `_apply_theme`.

## File / tree / line numbers

### `UFileTree(UFrame)` `[file_tree.py]`

| Method | Description |
| --- | --- |
| `set_on_activate(callback)` | Hooked when the user double-clicks. |
| `set_title(text)` | Update the header label. |
| `set_root(path)` | Change the directory. |
| `refresh()` | Re-scan. |
| `selected_path` (property) | Currently highlighted path. |

### `USettingsNavBar(UFrame)` `[settings_nav.py]`

Grouped navigation sidebar for `UProjectSettingsWindow`.

#### Module-level helpers

- `group_key(spec_key: str) -> str`
- `node_id(scope_value, group_key=None, key=None) -> str`
- `parse_node_id(iid: str) -> tuple`
- `group_keys_for_schema(schema) -> List[str]`

#### `NavSelection` `[settings_nav.py:108]`

```python
@dataclass
class NavSelection:
    scope: str             # 'global' | 'project'
    group_key: Optional[str] = None
    keys: tuple = ()       # specific SettingSpec keys in the group
    label: str = ''
```

#### `USettingsNavBar`

| Method | Description |
| --- | --- |
| `set_on_select(callback)` | `callback(selection: NavSelection)` hook. |
| `set_title(text)` | Update header. |
| `set_roots(global_schema, project_schema)` | Populate the tree. |
| `set_selected(scope, group_key=None, key=None)` | Programmatically select. |
| `get_selected() -> NavSelection` | Read current selection. |

### `TreeCanvas(UFrame)` `[tree_canvas.py]`

Canvas-based generic tree (used by `UFileTree`).

Key methods: `add_node`, `remove_node`, `clear`, `set_open`, `toggle`,
`set_selected`, `get_selected`, `exists`, `is_open`, `node_data`,
`see`, `identify_row`. Internal helper class `_Node` is private.

### `LineNumberCanvas(tk.Frame)` `[line_number.py]`

Canvas gutter for `UText`. Method `redraw()`. Helper
`font_metrics(font) -> tuple` is also exported.

## Marketplace

### `ui_theme_marketplace` `[ui_theme_marketplace.py]`

Re-exported through `modules.Uui.widgets`. Same shape as the highlight
and language marketplaces:

```python
from modules.Uui.widgets import ui_theme_marketplace
m = ui_theme_marketplace.get_ui_marketplace()
results = m.search("dark")
pkg = m.get_item("dark-default")
m.download(pkg, target_dir)
```

## Icons

### `ICON_SIZE = 20` `[icons.py]`

```python
from modules.Uui.widgets.icons import ICON_SIZE, draw_icon
draw_icon(canvas, 'explorer', color='#ffffff')   # canvas-based icons
```

Supported icon names: `'explorer'`, `'debug'`, `'git'`.