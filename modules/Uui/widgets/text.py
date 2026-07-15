import contextlib
import tkinter as tk
from typing import Literal

from . import theme
from .line_number import LineNumberCanvas
from .scrollbar import UScrollBar


class UText(tk.Frame):
    def __init__(self, parent, width: int = 40, height: int = 10,
                 wrap: Literal['none', 'char', 'word'] = 'word', font=None,
                 show_line_numbers: bool = False, **kwargs):
        bg = kwargs.pop('bg', theme.BG_BASE)
        super().__init__(parent, bg=bg, highlightthickness=0, bd=0, **kwargs)

        self._show_line_numbers = show_line_numbers
        self._line_numbers: LineNumberCanvas | None = None

        self._text = tk.Text(
            self, width=width, height=height,
            bg=theme.BG_INPUT, fg=theme.FG_PRIMARY,
            insertbackground=theme.FG_PRIMARY,
            selectbackground=theme.BLUE,
            selectforeground=theme.FG_PRIMARY,
            relief='flat', highlightthickness=1,
            highlightcolor=theme.BORDER_FOCUS,
            highlightbackground=theme.BORDER,
            bd=0, font=font or theme.MONO_FONT,
            wrap=wrap,
            undo=True,
            padx=8, pady=8,
        )
        # 收口到 :class:`UScrollBar` — 主题色、autohide 行为都集中维护。
        self._scroll = UScrollBar(
            self, orient='vertical', command=self._text.yview,
        )
        self._text.config(yscrollcommand=self._on_yview)

        # 布局顺序 (从左到右): gutter (可选) | text | scrollbar。
        # 行号栏必须在 text 之前 pack, 否则切语言时重构布局顺序会很乱。
        if show_line_numbers:
            self._line_numbers = LineNumberCanvas(self._text)
            self._line_numbers.pack(side=tk.LEFT, fill=tk.Y)
        self._scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self._text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    def get(self, *args):
        return self._text.get(*args)

    def insert(self, *args):
        self._text.insert(*args)

    def delete(self, *args):
        self._text.delete(*args)

    def clear(self):
        self._text.delete('1.0', tk.END)

    def see(self, index):
        self._text.see(index)

    def config(self, **kwargs):
        cnf = dict(kwargs)
        if 'state' in cnf:
            self._text.config(state=cnf.pop('state'))
        super().config(**cnf)

    def _on_yview(self, *args):
        """text 的 yscrollcommand 钩子: 同时驱动滚动条 + 行号栏.

        :class:`LineNumberCanvas` 也会在自身 yscrollcommand 钩子里调用
        我们的 set; 这里只关心"行号栏没启用时也要把滚动事件给 scrollbar"。
        """

        self._scroll.set(*args)
        if self._line_numbers is not None:
            # 让行号栏跟一次重画; 内部已经做了防抖, 重复触发也无副作用。
            with contextlib.suppress(tk.TclError):
                self._line_numbers.redraw()

    def _apply_theme(self):
        try:
            bg = self.master.cget('bg')
            if bg:
                self.config(bg=bg)
        except Exception:
            self.config(bg=theme.BG_BASE)
        self._text.config(
            bg=theme.BG_INPUT, fg=theme.FG_PRIMARY,
            insertbackground=theme.FG_PRIMARY,
            selectbackground=theme.BLUE,
            selectforeground=theme.FG_PRIMARY,
            highlightcolor=theme.BORDER_FOCUS,
            highlightbackground=theme.BORDER,
        )
        # UScrollBar 自己实现 _apply_theme, 转发即可 (troughcolor /
        # activebackground 跟随, bg 仅在未显式指定时跟随)。
        if hasattr(self._scroll, "_apply_theme"):
            with contextlib.suppress(Exception):
                self._scroll._apply_theme()
        # 行号栏: 颜色 + 重画一次。
        if self._line_numbers is not None:
            with contextlib.suppress(Exception):
                self._line_numbers._apply_theme()

    configure = config  # type: ignore[assignment]
