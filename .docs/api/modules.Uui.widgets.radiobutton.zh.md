# `modules/Uui/widgets/radiobutton.py`

源文件路径：`modules/Uui/widgets/radiobutton.py`

主题感知单选框。

## 类

### `URadioButton(tk.Frame)`
构造 `__init__(parent, text='', value=None, variable=None, command=None, external_toggle=None, **kwargs)`：
- `value`：当前选项的值（写入 `variable` 时使用）。
- `variable`：默认 `tk.StringVar()`。
- `command`：选择回调。
- `external_toggle`：外部切换钩子。

主要内部方法：
- `_toggle(event=None)`：将 `variable` 设为 `self._value`，触发 `command`。
- `_sync()`：根据 `variable` 显示内圆。
- `_apply_theme()`：主题刷新。