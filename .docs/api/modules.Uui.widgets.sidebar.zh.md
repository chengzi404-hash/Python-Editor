# `modules/Uui/widgets/sidebar.py`

源文件路径：`modules/Uui/widgets/sidebar.py`

VSCode 风格的侧边栏组件（ActivityBar + 内容面板）。

## 类

### `ActivityBarItem(tk.Frame)`
单个图标按钮。
- 构造 `__init__(parent, icon_name, card_id, is_active=False, command=None, **kwargs)`：
  - `icon_name`：传给 `icons.draw_icon` 的图标名。
  - `card_id`：激活标识。
  - `command(card_id)`：点击回调。
- `_render_icon()` — 用 `draw_icon` 在内置 `tk.Canvas` 上画图标。
- `_get_color() -> str` — 激活时 `FG_PRIMARY`，否则 `FG_TERTIARY`。
- `_on_enter / _on_leave / _on_click`：hover 与点击。

### `ActivityBar(tk.Frame)`
构造 `__init__(parent, on_select=None, **kwargs)`：
- 垂直排列 `ActivityBarItem`。
- `add_item(icon_name, card_id, command=None) -> ActivityBarItem`
- `set_active(card_id) -> None`：高亮当前项。
- `set_on_select(callback)`：运行时改回调。
- `_apply_theme()`：主题刷新。

### `SideBar(tk.Frame)`
构造 `__init__(parent, on_select=None, **kwargs)`：
- 把 `ActivityBar` 与内容面板组合。
- `add_card(card_id, widget, title='') -> None`：把任意 widget 作为卡片放入内容区。
- `select(card_id) -> None`：切换当前卡片。
- `set_on_select(callback)`。
- `_apply_theme()`：主题刷新。