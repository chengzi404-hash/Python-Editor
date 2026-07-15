# `modules/Uui/widgets/tree_canvas.py`

源文件路径：`modules/Uui/widgets/tree_canvas.py`

通用树形渲染层（Canvas + Frame 行），被 `UFileTree` / `USettingsNavBar` 复用。

## 设计动机

- 不依赖 `ttk.Treeview` + `ttk.Style`，颜色完全由 `theme` 决定。
- 每个可见节点用 `tk.Frame` 嵌入 `tk.Canvas.create_window`，hover / selected 仅需改 `bg`。
- 节点展开/折叠通过在每行左侧画 `▼/▶` 三角；整棵树扁平化为 `iid → row_y` 字典。
- 主题刷新只重画行背景，不重建 widget，保留选择/滚动/hover 状态。

## 类

### `TreeCanvas(tk.Canvas)`
构造 `__init__(parent, *, row_text, on_select=None, on_activate=None, on_toggle=None, indent=14, row_height=20, **kwargs)`：
- `row_text(iid) -> str`：把 iid 转成显示文本（必填）。
- `on_select(iid)` / `on_activate(iid)` / `on_toggle(iid, is_open)`：三种回调。

公开 API：
- `add_node(iid, parent=None, *, is_open=False) -> None`
- `remove_node(iid) -> None`
- `clear() -> None`
- `set_selected(iid) -> None`
- `see(iid) -> None`：滚动到目标节点。
- `open_node(iid)` / `close_node(iid)`：展开/折叠。
- `set_row_text(callable)`：运行时更新文本回调。
- `_apply_theme()`：主题刷新。

辅助：
- 内部维护 `_rows: List[str]`（可见节点 iid 序列）、`_row_widgets: Dict[iid, Frame]`、`_open: Set[iid]`、`_selected: Optional[str]`、`_hover: Optional[str]`。