# `modules/Uui/widgets/icons.py`

源文件路径：`modules/Uui/widgets/icons.py`

图标系统：用 `tkinter.Canvas` 几何绘制简单图标。

## 模块常量

- `ICON_SIZE = 20`

## 内部 / 公开函数

- `_draw_explorer(canvas, color)` — 文件夹图标（梯形主体 + 标签）。
- `_draw_debug(canvas, color)` — 调试图标（bug 轮廓 + 触角）。
- `_draw_git(canvas, color)` — Git 分支图标。
- 其它 `_draw_*` — 视源码而定。

## 公开 API

### `draw_icon(canvas: tk.Canvas, name: str, color: str) -> None`
按图标名分派到对应的 `_draw_*`。`name` 支持：`'explorer'` / `'debug'` / `'git'` 等。

> 完整函数列表见源码 74 行。