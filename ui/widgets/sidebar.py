"""``modules.Uui.widgets.sidebar`` — VSCode-style sidebar component.

Contains:
- ActivityBar: vertical icon bar (Explorer/Debug/Git)
- SideBar: ActivityBar + content panel combination
"""

from __future__ import annotations

import contextlib
import tkinter as tk
from collections.abc import Callable

from . import theme
from .frame import UFrame
from .icons import ICON_SIZE, draw_icon


class ActivityBarItem(tk.Frame):
    """Single Activity Bar icon button."""

    def __init__(
        self,
        parent,
        icon_name: str,
        card_id: str,
        is_active: bool = False,
        command: Callable[[str], None] | None = None,
        **kwargs,
    ):
        super().__init__(
            parent,
            width=36,
            height=36,
            bg="#1e1e1e",
            highlightthickness=0,
            bd=0,
            takefocus=False,
            **kwargs,
        )
        self._card_id = card_id
        self._command = command
        self._icon_name = icon_name
        self._is_active = is_active

        self.pack_propagate(False)

        # Icon canvas
        self._canvas = tk.Canvas(
            self,
            width=ICON_SIZE,
            height=ICON_SIZE,
            bg="#1e1e1e",
            highlightthickness=0,
            bd=0,
            takefocus=False,
        )
        self._canvas.place(relx=0.5, rely=0.5, anchor="center")

        self._render_icon()

        # Hover effect
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", self._on_click)
        self._canvas.bind("<Button-1>", self._on_click)

    def _render_icon(self):
        """Render icon."""
        self._canvas.delete("all")
        draw_icon(self._canvas, self._icon_name, self._get_color())

    def _get_color(self) -> str:
        return str(theme.FG_PRIMARY if self._is_active else theme.FG_TERTIARY)

    def _update_colors(self):
        self.config(bg="#1e1e1e")
        self._canvas.config(bg="#1e1e1e")
        self._render_icon()

    def _on_enter(self, _):
        if not self._is_active:
            self.config(bg=theme.BG_RAISED)
            self._canvas.config(bg=theme.BG_RAISED)
            self._canvas.delete("all")
            draw_icon(self._canvas, self._icon_name, theme.FG_SECONDARY)

    def _on_leave(self, _):
        self._update_colors()

    def _on_click(self, _):
        if self._command:
            self._command(self._card_id)

    def set_active(self, active: bool):
        self._is_active = active
        self._update_colors()


class ActivityBar(tk.Frame):
    """Vertical Activity Bar, containing multiple icon buttons."""

    def __init__(
        self,
        parent,
        items: list[tuple[str, str, str]],
        on_select: Callable[[str], None],
        **kwargs,
    ) -> None:
        super().__init__(
            parent, width=36, bg=theme.BG_BASE, highlightthickness=0, takefocus=False, **kwargs
        )
        self._items: dict[str, ActivityBarItem] = {}
        self._on_select = on_select
        self._active_id: str | None = None

        self.pack_propagate(False)

        for icon_name, _tooltip, card_id in items:
            item = ActivityBarItem(
                self,
                icon_name=icon_name,
                card_id=card_id,
                command=self._handle_select,
            )
            item.pack(fill=tk.X, pady=(0, 0))
            self._items[card_id] = item

        # Bottom spacer, to center icons
        spacer = tk.Frame(self, bg=theme.BG_BASE)
        spacer.pack(fill=tk.Y, expand=True)

    def _handle_select(self, card_id: str):
        self._on_select(card_id)

    def set_active(self, card_id: str):
        if self._active_id and self._active_id in self._items:
            self._items[self._active_id].set_active(False)
        self._active_id = card_id
        if card_id in self._items:
            self._items[card_id].set_active(True)

    def _apply_theme(self):
        for item in self._items.values():
            item._update_colors()


class SideBar(UFrame):
    """VSCode-style sidebar: ActivityBar + content panel.

    Usage::
        sidebar = SideBar(parent, items=[
            ('explorer', 'Explorer', 'explorer'),
            ('debug', 'Debug', 'debug'),
            ('git', 'Git', 'git'),
        ], on_select=lambda id: print(f'Selected: {id}'))
    """

    def __init__(
        self,
        parent,
        *,
        items: list[tuple[str, str, str]] | None = None,
        on_select: Callable[[str], None] | None = None,
        cards: dict[str, tk.Widget] | None = None,
        **kwargs,
    ) -> None:
        kwargs.setdefault("variant", "panel")
        super().__init__(parent, **kwargs)

        self._items = items or []
        self._on_select = on_select
        self._cards: dict[str, tk.Widget] = cards or {}
        self._active_card_id: str | None = None

        self._build()

    def _build(self) -> None:
        # Left Activity Bar
        self._activity_bar = ActivityBar(
            self,
            items=self._items,
            on_select=self._on_bar_select,
        )
        self._activity_bar.pack(side=tk.LEFT, fill=tk.Y)

        # Right content panel
        self._content_frame = tk.Frame(self, bg=theme.BG_PANEL)
        self._content_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Default select first card
        if self._items:
            first_id = self._items[0][2]
            self.set_active(first_id)

    def _on_bar_select(self, card_id: str) -> None:
        self.set_active(card_id)
        if self._on_select:
            self._on_select(card_id)

    def set_active(self, card_id: str) -> None:
        # Hide current card
        if self._active_card_id and self._active_card_id in self._cards:
            self._cards[self._active_card_id].pack_forget()

        # Show new card in content panel
        self._active_card_id = card_id
        if card_id in self._cards:
            self._cards[card_id].pack(in_=self._content_frame, fill=tk.BOTH, expand=True)

        self._activity_bar.set_active(card_id)

    def add_card(self, card_id: str, widget: tk.Widget) -> None:
        self._cards[card_id] = widget
        # If no card is currently active, activate this one
        if self._active_card_id is None:
            self.set_active(card_id)

    def _apply_theme(self) -> None:
        with contextlib.suppress(tk.TclError):
            super()._apply_theme()
        self._content_frame.config(bg=theme.BG_PANEL)
        self._activity_bar._apply_theme()


__all__ = [
    "ActivityBar",
    "ActivityBarItem",
    "SideBar",
]
