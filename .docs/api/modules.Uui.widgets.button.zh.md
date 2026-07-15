# `modules/Uui/widgets/button.py`

源文件路径：`modules/Uui/widgets/button.py`

主题感知圆角按钮。

## 内部辅助

### `_round_rect(canvas, x1, y1, x2, y2, r, **kwargs)`
在 canvas 上画一个圆角矩形（用 `create_polygon(..., smooth=True)`）。

### `_variant_colors(variant) -> (normal, hover, active, fg)`
映射预设 variant 到主题颜色四元组：
- `default` → `BG_RAISED` / `BG_HOVER` / `BG_ACTIVE` / `FG_PRIMARY`
- `primary` → `BLUE` / `BLUE_HOVER` / `BLUE_DARK` / `FG_PRIMARY`
- `success` → `GREEN` / `GREEN_HOVER` / `GREEN_DARK` / `#000000`
- `danger` → `RED` / `RED_HOVER` / `RED_DARK` / `FG_PRIMARY`
- `warning` → `YELLOW` / `YELLOW_HOVER` / `YELLOW_DARK` / `#000000`
- `ghost` → `BG_BASE` / `BG_RAISED` / `BG_HOVER` / `FG_PRIMARY`

## 类

### `UButton(tk.Frame)`
构造 `__init__(parent, text='', command=None, variant='default', width=96, height=28, radius=6, font=None, state='normal', **kwargs)`：
- 在内部 `tk.Canvas` 上画圆角矩形 + 居中文本。
- 绑定 `<Enter>` / `<Leave>` / `<Button-1>` / `<ButtonRelease-1>`。
- `state != 'normal'` 时调用 `_set_state`（典型 `'disabled'` 样式）。

方法（节选）：
- `_set_state(state)` — 切换样式与可用性。
- `_apply_theme()` — 跟随主题切换重新绘制（具体实现见源文件 60~120 行）。