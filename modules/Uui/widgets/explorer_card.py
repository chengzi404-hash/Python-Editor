"""``modules.Uui.widgets.explorer_card`` — File explorer card.

Wraps UFileTree, adding VSCode-style "EXPLORER" title header.
"""

from __future__ import annotations

import contextlib
import tkinter as tk
from collections.abc import Callable

from . import theme
from .file_tree import UFileTree
from .frame import UFrame
from .label import ULabel


class ExplorerCard(UFrame):
    """Explorer sidebar card, containing header + UFileTree."""

    def __init__(
        self,
        parent,
        *,
        title: str = "EXPLORER",
        on_activate: Callable[[str], None] | None = None,
        **kwargs,
    ) -> None:
        kwargs.setdefault("variant", "panel")
        super().__init__(parent, **kwargs)

        self._title = title
        self._on_activate = on_activate

        self._build()

    def _build(self) -> None:
        # Title header
        header = UFrame(self, variant="title", height=26)
        header.pack(fill=tk.X)
        header.pack_propagate(False)

        # Left accent bar -- consistent visual anchor with other cards
        self._title_accent = tk.Frame(
            header,
            bg=theme.TITLE_ACCENT,
            width=theme.TITLE_ACCENT_WIDTH,
        )
        self._title_accent.pack(side=tk.LEFT, fill=tk.Y)

        self._title_label = ULabel(
            header,
            text=f"  {self._title}",
            variant="secondary",
            bg=theme.BG_TITLE,
        )
        self._title_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # File tree
        self._file_tree = UFileTree(
            self,
            title="",
            on_activate=self._on_activate,
        )
        self._file_tree.pack(fill=tk.BOTH, expand=True, pady=(0, 0))

    def set_root(self, path: str) -> None:
        self._file_tree.set_root(path)

    def refresh(self) -> None:
        self._file_tree.refresh()

    def _apply_theme(self) -> None:
        with contextlib.suppress(tk.TclError):
            super()._apply_theme()
        self._title_label.config(bg=theme.BG_TITLE, fg=theme.FG_SECONDARY)
        if hasattr(self, "_title_accent"):
            self._title_accent.config(bg=theme.TITLE_ACCENT)


__all__ = ["ExplorerCard"]
