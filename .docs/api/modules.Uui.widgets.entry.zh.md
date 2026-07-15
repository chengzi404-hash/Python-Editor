# `modules/Uui/widgets/entry.py`

源文件路径：`modules/Uui/widgets/entry.py`

主题感知单行输入框（含 placeholder 与密码遮蔽）。

## 类

### `UEntry(tk.Frame)`
构造 `__init__(parent, textvariable=None, placeholder='', width=20, show='', **kwargs)`：
- 内部 `tk.Entry`，主题色（输入框背景、前景、插入符、选区）。
- `placeholder`：进入前以灰色显示；`show`：密码遮蔽字符（如 `*`）。
- `show` 非空时实时遮蔽（即使显示 placeholder 时也会切回 `show`）。
- 绑定 `<FocusIn>` / `<FocusOut>` 控制 placeholder 切换。

方法（节选）：
- `get() / set(text)` 等透传到 `tk.StringVar`（外部通过 `textvariable` 访问）。
- `_show_placeholder()` / `_hide_placeholder()`
- `_on_focus_in(event)` / `_on_focus_out(event)`
- `_apply_theme()`：刷新 entry 颜色。