"""``modules.Uui.widgets.explorer_card`` — 文件资源管理器卡片.

包装 UFileTree, 添加 VSCode 风格的 "EXPLORER" 标题头.
"""

from __future__ import annotations

import tkinter as tk
from typing import Callable, Optional

from . import theme
from .file_tree import UFileTree
from .frame import UFrame
from .label import ULabel


class ExplorerCard(UFrame):
    """Explorer 侧边栏卡片, 包含标题头 + UFileTree."""

    def __init__(
        self,
        parent,
        *,
        title: str = 'EXPLORER',
        on_activate: Optional[Callable[[str], None]] = None,
        **kwargs,
    ) -> None:
        kwargs.setdefault('variant', 'panel')
        super().__init__(parent, **kwargs)

        self._title = title
        self._on_activate = on_activate

        self._build()

    def _build(self) -> None:
        # 标题头
        header = UFrame(self, variant='title', height=26)
        header.pack(fill=tk.X)
        header.pack_propagate(False)

        self._title_label = ULabel(
            header, text=f'  {self._title}',
            variant='secondary', bg=theme.BG_TITLE,
        )
        self._title_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # 文件树
        self._file_tree = UFileTree(
            self, title='', on_activate=self._on_activate,
        )
        self._file_tree.pack(fill=tk.BOTH, expand=True, pady=(0, 0))

    def set_root(self, path: str) -> None:
        self._file_tree.set_root(path)

    def refresh(self) -> None:
        self._file_tree.refresh()

    def _apply_theme(self) -> None:
        try:
            super()._apply_theme()
        except tk.TclError:
            pass
        self._title_label.config(bg=theme.BG_TITLE, fg=theme.FG_SECONDARY)


__all__ = ['ExplorerCard']
