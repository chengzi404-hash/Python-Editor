import contextlib
import tkinter as tk
from typing import Literal

from . import theme
from .line_number import LineNumberCanvas
from .scrollbar import UScrollBar


class UText(tk.Frame):
    def __init__(
        self,
        parent,
        width: int = 40,
        height: int = 10,
        wrap: Literal["none", "char", "word"] = "word",
        font=None,
        show_line_numbers: bool = False,
        **kwargs,
    ):
        bg = kwargs.pop("bg", theme.BG_BASE)
        super().__init__(parent, bg=bg, highlightthickness=0, bd=0, **kwargs)

        self._show_line_numbers = show_line_numbers
        self._line_numbers: LineNumberCanvas | None = None

        self._text = tk.Text(
            self,
            width=width,
            height=height,
            bg=theme.BG_INPUT,
            fg=theme.FG_PRIMARY,
            insertbackground=theme.FG_PRIMARY,
            selectbackground=theme.BLUE,
            selectforeground=theme.FG_PRIMARY,
            relief="flat",
            highlightthickness=1,
            highlightcolor=theme.BORDER_FOCUS,
            highlightbackground=theme.BORDER,
            bd=0,
            font=font or theme.MONO_FONT,
            wrap=wrap,
            undo=True,
            padx=8,
            pady=8,
        )
        # Unified at :class:`UScrollBar` — theme colors and autohide behavior are centrally maintained.
        self._scroll = UScrollBar(
            self,
            orient="vertical",
            command=self._text.yview,
        )
        self._text.config(yscrollcommand=self._on_yview)

        # Layout order (left to right): gutter (optional) | text | scrollbar.
        # Line number bar must be packed before text, otherwise switching languages will mess up layout order.
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
        self._text.delete("1.0", tk.END)

    def see(self, index):
        self._text.see(index)

    def config(self, **kwargs):  # type: ignore[override]
        cnf = dict(kwargs)
        if "state" in cnf:
            self._text.config(state=cnf.pop("state"))
        super().config(**cnf)

    def _on_yview(self, *args):
        """Hook for text's yscrollcommand: drives both scrollbar and line number bar.

        :class:`LineNumberCanvas` also calls our set in its own yscrollcommand hook;
        here we only care about "when line number bar is disabled, still forward scroll events to scrollbar".
        """

        self._scroll.set(*args)
        if self._line_numbers is not None:
            # Trigger line number bar redraw; debouncing is already internal, duplicate triggers have no side effect.
            with contextlib.suppress(tk.TclError):
                self._line_numbers.redraw()

    def _apply_theme(self):
        try:
            bg = self.master.cget("bg")
            if bg:
                self.config(bg=bg)
        except Exception:
            self.config(bg=theme.BG_BASE)
        self._text.config(
            bg=theme.BG_INPUT,
            fg=theme.FG_PRIMARY,
            insertbackground=theme.FG_PRIMARY,
            selectbackground=theme.BLUE,
            selectforeground=theme.FG_PRIMARY,
            highlightcolor=theme.BORDER_FOCUS,
            highlightbackground=theme.BORDER,
        )
        # UScrollBar implements _apply_theme itself, just forward (troughcolor /
        # activebackground follow, bg only follows when not explicitly set).
        if hasattr(self._scroll, "_apply_theme"):
            with contextlib.suppress(Exception):
                self._scroll._apply_theme()
        # Line number bar: colors + one redraw.
        if self._line_numbers is not None:
            with contextlib.suppress(Exception):
                self._line_numbers._apply_theme()

    configure = config  # type: ignore[assignment]
