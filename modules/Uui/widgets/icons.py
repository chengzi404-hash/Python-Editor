"""``modules.Uui.widgets.icons`` — 图标系统.

使用 tkinter Canvas 绘制简单几何图标.
"""

from __future__ import annotations

import tkinter as tk

# 图标尺寸
ICON_SIZE = 20


def _draw_explorer(canvas: tk.Canvas, color: str) -> None:
    """在现有 Canvas 上绘制文件夹图标."""
    pad = 3
    # 文件夹身体
    canvas.create_polygon([
        pad, pad + 4,
        pad + 6, pad + 4,
        pad + 6, pad + 2,
        ICON_SIZE - pad, pad + 2,
        ICON_SIZE - pad, ICON_SIZE - pad,
        pad, ICON_SIZE - pad,
    ], fill=color, outline=color)
    # 文件夹标签
    canvas.create_polygon([
        pad, pad + 4,
        pad + 6, pad + 4,
        pad + 6, pad + 2,
        pad + 10, pad + 2,
        pad + 10, pad + 4,
    ], fill=color, outline=color)


def _draw_debug(canvas: tk.Canvas, color: str) -> None:
    """在现有 Canvas 上绘制调试图标."""
    cx, cy = ICON_SIZE // 2, ICON_SIZE // 2
    r = ICON_SIZE // 4
    # 身体
    canvas.create_oval(cx - r, cy - r//2 + 2, cx + r, cy + r//2 + 2, fill=color, outline=color)
    # 头
    canvas.create_oval(cx - r//2, cy - r, cx + r//2, cy - r//2 + 2, fill=color, outline=color)


def _draw_git(canvas: tk.Canvas, color: str) -> None:
    """在现有 Canvas 上绘制 Git 图标."""
    pad = 3
    # 主干线
    canvas.create_line(ICON_SIZE//2, pad, ICON_SIZE//2, ICON_SIZE - pad, fill=color, width=2)
    # 分支
    canvas.create_line(ICON_SIZE//2, ICON_SIZE//3, ICON_SIZE - pad, ICON_SIZE//3, fill=color, width=2)
    # 圆点
    r = 2
    canvas.create_oval(ICON_SIZE//2 - r, ICON_SIZE - pad - 4, ICON_SIZE//2 + r, ICON_SIZE - pad, fill=color, outline=color)
    canvas.create_oval(ICON_SIZE//2 - r, ICON_SIZE//3 - r, ICON_SIZE//2 + r, ICON_SIZE//3 + r, fill=color, outline=color)
    canvas.create_oval(ICON_SIZE - pad - 4, ICON_SIZE//3 - r, ICON_SIZE - pad, ICON_SIZE//3 + r, fill=color, outline=color)


_DRAW_FUNCTIONS = {
    'explorer': _draw_explorer,
    'debug': _draw_debug,
    'git': _draw_git,
}


def draw_icon(canvas: tk.Canvas, name: str, color: str) -> None:
    """在 Canvas 上绘制图标."""
    if name in _DRAW_FUNCTIONS:
        _DRAW_FUNCTIONS[name](canvas, color)


__all__ = ['ICON_SIZE', 'draw_icon']
