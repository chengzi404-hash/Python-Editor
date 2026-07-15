# `modules/Uui/widgets/checkbutton.py`

源文件路径：`modules/Uui/widgets/checkbutton.py`

主题感知复选框。

## 类

### `UCheckButton(tk.Frame)`
构造 `__init__(parent, text='', variable=None, command=None, external_toggle=None, **kwargs)`：
- 内部 `tk.Canvas` 绘制方框 + `tk.Label` 文字。
- `variable`：默认 `tk.BooleanVar()`。
- `command`：状态变化时回调。
- `external_toggle`：供外部强制切换状态时使用的回调钩子。

主要内部方法：
- `_toggle(event=None)`：点击切换 `variable`。
- `_sync()`：根据 `variable` 显示/隐藏对勾字符（`'\u2713'`）。
- `_apply_theme()`：主题刷新。