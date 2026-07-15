# `modules/Uui/widgets/dialog.py`

源文件路径：`modules/Uui/widgets/dialog.py`

主题感知对话框基类（`tk.Toplevel`）。

## 类

### `UDialog(tk.Toplevel)`
构造 `__init__(parent, title='', width=600, height=400, resizable=True, **kwargs)`：
- 自动 `transient(parent)` / `grab_set()` / 居中几何（`_center_x` / `_center_y`）。
- 内部三段布局：
  - `_outer: tk.Frame`（`BG_PANEL`）
  - `_title_bar: tk.Frame`（`BG_TITLE`，高 32，含加粗标题 label）
  - `_body: tk.Frame`（`BG_PANEL`，留给子类填充）
- `resizable=False` 时锁死尺寸。
- 绑定 `WM_DELETE_WINDOW` 到 `destroy`。

属性：
- `_parent`
- `_ui_built: bool` — 占位位。
- `body`（属性）→ `tk.Frame` — 子类在此 `pack` 内容。

内部辅助：
- `_center_x(w)` / `_center_y(h)`：基于屏幕宽高计算居中偏移。
- `_apply_theme()`：主题刷新。