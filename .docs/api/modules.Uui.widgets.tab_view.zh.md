# `modules/Uui/widgets/tab_view.py`

源文件路径：`modules/Uui/widgets/tab_view.py`

简单 Tab 容器。

## 类

### `UTabView(tk.Frame)`
构造 `__init__(parent, **kwargs)`：
- 顶部 tab bar（`BG_TITLE`）+ 内容容器（`BG_PANEL`）。

公开 API：
- `add_tab(tab_id: str, label: str) -> tk.Frame`：创建 tab 按钮，返回内容页 `tk.Frame`。
- `remove_tab(tab_id) -> None`
- `select(tab_id) -> None`
- `set_on_switch(callback: Callable[[str], None])`：tab 切换回调。
- `current_id() -> Optional[str]`
- `_apply_theme()`：主题刷新。