# `modules/Uui/widgets/list_view.py`

源文件路径：`modules/Uui/widgets/list_view.py`

多列列表视图（带表头与滚动条）。

## 类

### `UListView(tk.Frame)`
构造 `__init__(parent, columns=None, column_widths=None, on_select=None, show_header=True, **kwargs)`：
- `columns: List[str]` — 列名。
- `column_widths: Dict[str, int]` — 列宽。
- `on_select(idx, row_dict) -> None` — 行选中回调。
- `show_header`：是否渲染表头。

公开 API：
- `set_data(rows: List[Dict[str, str]]) -> None`：替换数据并重绘。
- `append_row(row: Dict[str, str]) -> None`
- `clear() -> None`
- `selected_index() -> Optional[int]`
- `selected_row() -> Optional[Dict[str, str]]`
- `set_on_select(callback)`：运行时改回调。
- `_apply_theme()`：主题刷新。