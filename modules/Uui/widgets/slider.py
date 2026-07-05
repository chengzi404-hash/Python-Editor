import tkinter as tk
from typing import Optional
from . import theme


class USlider(tk.Canvas):
    def __init__(self, parent, from_: float = 0, to: float = 100,
                 value: Optional[float] = None, orient: str = 'horizontal',
                 command=None, show_value: bool = False, **kwargs):
        kwargs.setdefault('bg', theme.BG_BASE)
        kwargs.setdefault('highlightthickness', 0)
        kwargs.setdefault('bd', 0)
        super().__init__(parent, **kwargs)

        self._from = from_
        self._to = to
        self._value = value if value is not None else from_
        self._orient = orient
        self._command = command
        self._show_value = show_value
        self._radius = 7
        self._track_height = 4

        if orient == 'horizontal':
            self.config(height=22)
        else:
            self.config(width=22)

        self.bind('<Configure>', lambda e: self._draw())
        self.bind('<Button-1>', self._on_press)
        self.bind('<B1-Motion>', self._on_drag)
        self._draw()

    def _draw(self):
        self.delete('all')
        w = self.winfo_width()
        h = self.winfo_height()
        if w <= 1 or h <= 1:
            return

        if self._orient == 'horizontal':
            track_y = h // 2
            self.create_rectangle(
                self._radius, track_y - self._track_height // 2,
                w - self._radius, track_y + self._track_height // 2,
                fill=theme.BG_INPUT, outline='',
            )
            ratio = (self._value - self._from) / max(self._to - self._from, 1)
            knob_x = int(self._radius + (w - 2 * self._radius) * ratio)
            self.create_rectangle(
                self._radius, track_y - self._track_height // 2,
                knob_x, track_y + self._track_height // 2,
                fill=theme.BLUE, outline='',
            )
            self.create_oval(
                knob_x - self._radius, track_y - self._radius,
                knob_x + self._radius, track_y + self._radius,
                fill=theme.FG_PRIMARY, outline=theme.BG_BASE, width=2,
            )
            if self._show_value:
                self.create_text(
                    knob_x, track_y - self._radius - 10,
                    text=f'{int(self._value)}', fill=theme.FG_SECONDARY,
                    font=theme.LABEL_FONT_SMALL,
                )
        else:
            track_x = w // 2
            self.create_rectangle(
                track_x - self._track_height // 2, self._radius,
                track_x + self._track_height // 2, h - self._radius,
                fill=theme.BG_INPUT, outline='',
            )
            ratio = (self._value - self._from) / max(self._to - self._from, 1)
            knob_y = int(self._radius + (h - 2 * self._radius) * ratio)
            self.create_rectangle(
                track_x - self._track_height // 2, self._radius,
                track_x + self._track_height // 2, knob_y,
                fill=theme.BLUE, outline='',
            )
            self.create_oval(
                track_x - self._radius, knob_y - self._radius,
                track_x + self._radius, knob_y + self._radius,
                fill=theme.FG_PRIMARY, outline=theme.BG_BASE, width=2,
            )

    def _on_press(self, e: tk.Event):
        self._update_value(e)

    def _on_drag(self, e: tk.Event):
        self._update_value(e)

    def _update_value(self, e: tk.Event):
        w = self.winfo_width()
        h = self.winfo_height()
        if self._orient == 'horizontal':
            ratio = max(0.0, min(1.0, (e.x - self._radius) / max(w - 2 * self._radius, 1)))
        else:
            ratio = max(0.0, min(1.0, (e.y - self._radius) / max(h - 2 * self._radius, 1)))
        self._value = self._from + ratio * (self._to - self._from)
        self._draw()
        if self._command:
            self._command(self._value)

    def get(self) -> float:
        return self._value

    def set(self, value: float):
        self._value = max(self._from, min(self._to, value))
        self._draw()
        if self._command:
            self._command(self._value)

    def _apply_theme(self):
        self.config(bg=theme.BG_BASE)
        self._draw()
