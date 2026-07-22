"""``modules.Uui.widgets.icons`` — Icon system.

Uses tkinter Canvas to draw simple geometric icons.
"""

from __future__ import annotations

import tkinter as tk

# Icon size
ICON_SIZE = 20


def _draw_explorer(canvas: tk.Canvas, color: str) -> None:
    """Draw folder icon on existing Canvas."""
    pad = 3
    # Folder body
    canvas.create_polygon(
        [
            pad,
            pad + 4,
            pad + 6,
            pad + 4,
            pad + 6,
            pad + 2,
            ICON_SIZE - pad,
            pad + 2,
            ICON_SIZE - pad,
            ICON_SIZE - pad,
            pad,
            ICON_SIZE - pad,
        ],
        fill=color,
        outline=color,
    )
    # Folder tab
    canvas.create_polygon(
        [
            pad,
            pad + 4,
            pad + 6,
            pad + 4,
            pad + 6,
            pad + 2,
            pad + 10,
            pad + 2,
            pad + 10,
            pad + 4,
        ],
        fill=color,
        outline=color,
    )


def _draw_debug(canvas: tk.Canvas, color: str) -> None:
    """Draw debug icon on existing Canvas."""
    cx, cy = ICON_SIZE // 2, ICON_SIZE // 2
    r = ICON_SIZE // 4
    # Body
    canvas.create_oval(cx - r, cy - r // 2 + 2, cx + r, cy + r // 2 + 2, fill=color, outline=color)
    # Head
    canvas.create_oval(cx - r // 2, cy - r, cx + r // 2, cy - r // 2 + 2, fill=color, outline=color)


def _draw_git(canvas: tk.Canvas, color: str) -> None:
    """Draw Git icon on existing Canvas."""
    pad = 3
    # Main branch
    canvas.create_line(ICON_SIZE // 2, pad, ICON_SIZE // 2, ICON_SIZE - pad, fill=color, width=2)
    # Branch
    canvas.create_line(
        ICON_SIZE // 2, ICON_SIZE // 3, ICON_SIZE - pad, ICON_SIZE // 3, fill=color, width=2
    )
    # Dots
    r = 2
    canvas.create_oval(
        ICON_SIZE // 2 - r,
        ICON_SIZE - pad - 4,
        ICON_SIZE // 2 + r,
        ICON_SIZE - pad,
        fill=color,
        outline=color,
    )
    canvas.create_oval(
        ICON_SIZE // 2 - r,
        ICON_SIZE // 3 - r,
        ICON_SIZE // 2 + r,
        ICON_SIZE // 3 + r,
        fill=color,
        outline=color,
    )
    canvas.create_oval(
        ICON_SIZE - pad - 4,
        ICON_SIZE // 3 - r,
        ICON_SIZE - pad,
        ICON_SIZE // 3 + r,
        fill=color,
        outline=color,
    )


def _draw_marketplace(canvas: tk.Canvas, color: str) -> None:
    """Draw Marketplace icon on existing Canvas."""
    pad = 3
    bar_width = 3
    bar_gap = 2
    start_x = pad + 2
    for i in range(3):
        x = start_x + i * (bar_width + bar_gap)
        canvas.create_rectangle(x, pad, x + bar_width, ICON_SIZE - pad, fill=color, outline=color)


def _draw_ai(canvas: tk.Canvas, color: str) -> None:
    """Draw a sparkles / AI icon on existing Canvas."""
    # Two 4-pointed sparkles — large on the upper-left, small on the lower-right.
    pad = 3
    cx1, cy1 = ICON_SIZE // 2 - 2, ICON_SIZE // 2 - 2
    arm1 = 4
    canvas.create_polygon(
        [
            cx1,
            cy1 - arm1,
            cx1 + 1,
            cy1 - 1,
            cx1 + arm1,
            cy1,
            cx1 + 1,
            cy1 + 1,
            cx1,
            cy1 + arm1,
            cx1 - 1,
            cy1 + 1,
            cx1 - arm1,
            cy1,
            cx1 - 1,
            cy1 - 1,
        ],
        fill=color,
        outline=color,
    )
    cx2, cy2 = ICON_SIZE - pad - 3, ICON_SIZE - pad - 3
    arm2 = 2
    canvas.create_polygon(
        [
            cx2,
            cy2 - arm2,
            cx2 + 1,
            cy2 - 1,
            cx2 + arm2,
            cy2,
            cx2 + 1,
            cy2 + 1,
            cx2,
            cy2 + arm2,
            cx2 - 1,
            cy2 + 1,
            cx2 - arm2,
            cy2,
            cx2 - 1,
            cy2 - 1,
        ],
        fill=color,
        outline=color,
    )


_DRAW_FUNCTIONS = {
    "explorer": _draw_explorer,
    "debug": _draw_debug,
    "git": _draw_git,
    "marketplace": _draw_marketplace,
    "ai": _draw_ai,
}


def draw_icon(canvas: tk.Canvas, name: str, color: str) -> None:
    """Draw icon on Canvas."""
    if name in _DRAW_FUNCTIONS:
        _DRAW_FUNCTIONS[name](canvas, color)


__all__ = ["ICON_SIZE", "draw_icon"]
