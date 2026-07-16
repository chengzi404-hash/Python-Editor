from __future__ import annotations

import tkinter as tk

from . import theme


class UDialog(tk.Toplevel):
    def __init__(
        self,
        parent,
        title: str = "",
        width: int = 600,
        height: int = 400,
        resizable: bool = True,
        **kwargs,
    ):
        super().__init__(parent, **kwargs)
        self._parent = parent
        self._ui_built = False

        self.title(title)
        self.geometry(f"{width}x{height}+{self._center_x(width)}+{self._center_y(height)}")
        self.transient(parent)
        self.grab_set()

        self._outer = tk.Frame(self, bg=theme.BG_PANEL)
        self._outer.pack(fill=tk.BOTH, expand=True)

        self._title_bar = tk.Frame(self._outer, bg=theme.BG_TITLE, height=32)
        self._title_bar.pack(fill=tk.X)
        self._title_bar.pack_propagate(False)

        self._title_label = tk.Label(
            self._title_bar,
            text=title,
            bg=theme.BG_TITLE,
            fg=theme.FG_PRIMARY,
            font=theme.LABEL_FONT_BOLD,
        )
        self._title_label.pack(side=tk.LEFT, padx=12, pady=6)

        self._body = tk.Frame(self._outer, bg=theme.BG_PANEL)
        self._body.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)

        if not resizable:
            self.resizable(False, False)

        self.protocol("WM_DELETE_WINDOW", self.destroy)

    def _center_x(self, w: int) -> int:
        try:
            sw = self.winfo_screenwidth()
            return max(0, (sw - w) // 2)
        except Exception:
            return 100

    def _center_y(self, h: int) -> int:
        try:
            sh = self.winfo_screenheight()
            return max(0, (sh - h) // 2)
        except Exception:
            return 100

    @property
    def body(self) -> tk.Frame:
        return self._body

    def _apply_theme(self):
        self._outer.config(bg=theme.BG_PANEL)
        self._title_bar.config(bg=theme.BG_TITLE)
        self._title_label.config(bg=theme.BG_TITLE, fg=theme.FG_PRIMARY)
        self._body.config(bg=theme.BG_PANEL)
