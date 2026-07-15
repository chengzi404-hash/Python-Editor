# `modules/Uui/widgets/combobox.py`

源文件路径：`modules/Uui/widgets/combobox.py`

主题感知下拉框。

## 类

### `UComboBox(tk.Frame)`
构造 `__init__(parent, values=(), textvariable=None, command=None, select_first=True, **kwargs)`：
- `values`：候选项列表。
- `textvariable`：外部 `tk.StringVar`（默认新建）。
- `command(item) -> None`：选择某项时回调。
- `select_first=True` 且 `values` 非空时，自动把第一个值赋给 variable。

主要方法：
- `_toggle(event=None)`：打开/关闭下拉浮层。
- `_build_dropdown()`：构造下拉项列表，处理点击外部关闭。
- `_on_select(item)`：把 `item` 写入 variable 并触发 `command`。
- `_on_enter/_on_leave`：hover 样式。
- `set(value)` / `get() -> str`：读写 `textvariable`。
- `_apply_theme()`：主题刷新。