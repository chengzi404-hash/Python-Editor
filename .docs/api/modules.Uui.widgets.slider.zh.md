# `modules/Uui/widgets/slider.py`

源文件路径：`modules/Uui/widgets/slider.py`

主题感知滑块（基于 `tk.Canvas`）。

## 类

### `USlider(tk.Canvas)`
构造 `__init__(parent, from_=0, to=100, value=None, orient='horizontal', command=None, show_value=False, **kwargs)`：
- `from_` / `to`：取值范围；`value`：初始值（默认 `from_`）。
- `orient`：`'horizontal'` / `'vertical'`（自动设置默认尺寸）。
- `command(value)`：拖动时回调（不阻塞）。
- `show_value`：是否在 hover 时显示数值。

方法：
- `_draw()`：绘制轨道 + 已填充段 + 旋钮。
- `_on_press(event)` / `_on_drag(event)`：根据鼠标位置更新 `_value`，调用 `command`。
- `_apply_theme()`：主题刷新。