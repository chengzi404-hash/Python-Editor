import tkinter as tk
from typing import Optional
from . import theme


class UFrame(tk.Frame):
    def __init__(self, parent, variant: str = 'panel',
                 bg_key: Optional[str] = None, **kwargs):
        self._variant = variant
        self._bg_key = bg_key
        self._explicit_bg = kwargs.pop('bg', None)

        if bg_key is not None:
            bg = getattr(theme, bg_key)
        elif self._explicit_bg is not None:
            bg = self._explicit_bg
        else:
            bg = self._variant_bg(variant)

        kwargs.setdefault('highlightthickness', 0)
        kwargs.setdefault('bd', 0)
        super().__init__(parent, bg=bg, **kwargs)

    def _variant_bg(self, variant: str) -> str:
        return {
            'title': theme.BG_TITLE,
            'base': theme.BG_BASE,
            'panel': theme.BG_PANEL,
            'raised': theme.BG_RAISED,
            'input': theme.BG_INPUT,
        }.get(variant, theme.BG_PANEL)

    def _apply_theme(self):
        if self._bg_key is not None:
            self.config(bg=getattr(theme, self._bg_key))
        elif self._explicit_bg is not None:
            self.config(bg=self._explicit_bg)
        else:
            self.config(bg=self._variant_bg(self._variant))
