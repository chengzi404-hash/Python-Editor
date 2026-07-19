import tkinter as tk
from typing import ClassVar

from . import theme


class ULabel(tk.Label):
    _VARIANT_FG_KEYS: ClassVar[dict] = {
        "primary": "FG_PRIMARY",
        "secondary": "FG_SECONDARY",
        "tertiary": "FG_TERTIARY",
        "disabled": "FG_DISABLED",
        "blue": "BLUE",
        "red": "RED",
        "green": "GREEN",
        "yellow": "YELLOW",
    }

    def __init__(
        self,
        parent,
        text: str = "",
        variant: str = "primary",
        font=None,
        bg: str | None = None,
        **kwargs,
    ):
        self._variant = variant
        self._explicit_bg = bg
        if bg is None:
            bg = self._parent_bg(parent)
            self._explicit_bg = None
        kwargs.setdefault("fg", self._variant_fg(variant))
        kwargs.setdefault("bg", bg)
        kwargs.setdefault("font", font or theme.LABEL_FONT)
        super().__init__(parent, text=text, **kwargs)

    def _variant_fg(self, variant: str) -> str:
        key = self._VARIANT_FG_KEYS.get(variant, "FG_PRIMARY")
        return str(getattr(theme, key))

    @staticmethod
    def _parent_bg(parent) -> str:
        try:
            bg = parent.cget("bg")
            if bg:
                return str(bg)
        except Exception:
            pass
        return theme.BG_BASE

    def _apply_theme(self):
        bg = self._parent_bg(self.master)
        self.config(
            fg=self._variant_fg(self._variant),
            bg=bg,
            font=theme.LABEL_FONT,
        )
