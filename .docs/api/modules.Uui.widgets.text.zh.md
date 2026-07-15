# `modules/Uui/widgets/text.py`

源文件路径：`modules/Uui/widgets/text.py`

多行文本编辑框（含可选行号栏 + 主题滚动条）。

## 类

### `UText(tk.Frame)`
构造 `__init__(parent, width=40, height=10, wrap='word', font=None, show_line_numbers=False, **kwargs)`：
- `wrap`：`'none'` / `'char'` / `'word'`。
- 内部 `tk.Text` 启用 `undo=True`、`padx=8`、`pady=8`，主题色。
- 可选 `LineNumberCanvas` 作为 gutter。
- 配套 `UScrollBar(orient='vertical', command=...)`。
- 布局顺序：gutter（可选） | text | scrollbar。

公开方法：
- `get(*args)` / `insert(*args)` / `delete(*args)` / `index(*args)` — 透传到内部 `tk.Text`。
- `bind(...)` / `focus_*` — 透传。
- `_apply_theme()`：跟随主题刷新。