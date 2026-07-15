# `modules/Uui/widgets/progressbar.py`

源文件路径：`modules/Uui/widgets/progressbar.py`

主题感知进度条（基于 `tk.Canvas`）。

## 类

### `UProgressBar(tk.Canvas)`
构造 `__init__(parent, maximum=100, value=0, height=6, color=None, **kwargs)`：
- `maximum`：上限。
- `value`：当前值。
- `height`：进度条像素高度。
- `color`：可选显示颜色（默认 `theme.BLUE`）。

方法：
- `set(value)` / `get() -> float` — 读写当前值并触发重绘。
- `_draw()` — 监听 `<Configure>`，按 `value/maximum` 在 canvas 上画矩形。
- `configure(**kwargs)` — 支持 `value=` / `maximum=` / `color=` / `bg=` 的快捷设置。