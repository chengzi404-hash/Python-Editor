import tkinter as tk
from typing import Optional
from . import theme


class UProgressBar(tk.Canvas):
    def __init__(self, parent, maximum: int = 100, value: float = 0,
                 height: int = 6, color: Optional[str] = None, **kwargs):
        self._explicit_color = color
        kwargs.setdefault('bg', theme.BG_INPUT)
        kwargs.setdefault('highlightthickness', 0)
        kwargs.setdefault('bd', 0)
        super().__init__(parent, height=height, **kwargs)
        self._maximum = maximum
        self._value = value
        self.bind('<Configure>', lambda e: self._draw())
        self._draw()

    def _draw(self):
        self.delete('all')
        w = self.winfo_width()
        h = self.winfo_height()
        if w <= 1:
            return
        ratio = max(0.0, min(1.0, self._value / max(self._maximum, 1)))
        fill = self._explicit_color if self._explicit_color else theme.BLUE
        if ratio > 0:
            self.create_rectangle(0, 0, int(w * ratio), h, fill=fill, outline='')

    def set(self, value: float):
        self._value = value
        self._draw()

    def get(self) -> float:
        return self._value

    def configure(self, **kwargs):
        cnf = dict(kwargs)
        if 'value' in cnf:
            self.set(cnf.pop('value'))
        if 'maximum' in cnf:
            self._maximum = cnf.pop('maximum')
            self._draw()
        if 'color' in cnf:
            self._explicit_color = cnf.pop('color')
            self._draw()
        if 'bg' in cnf:
            super().configure(bg=cnf.pop('bg'))
        for k, v in cnf.items():
            super().configure(**{k: v})

    def _apply_theme(self):
        self.config(bg=theme.BG_INPUT)
        self._draw()

    config = configure
