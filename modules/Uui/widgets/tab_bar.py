"""``modules.Uui.widgets.tab_bar`` — Multi-file tab bar component."""

from __future__ import annotations

import tkinter as tk
import tkinter.font as tkfont
from collections.abc import Callable
from dataclasses import dataclass

from . import theme


@dataclass
class Tab:
    """Single tab data model."""

    id: str
    title: str
    dirty: bool = False
    closeable: bool = True


class TabBar(tk.Frame):
    """Tab bar component.

    Uses Canvas to draw tab buttons, supports:
    - Active tab highlight
    - dirty state (prefix * in title)
    - Close button
    - Right-click context menu
    - Horizontal scrolling (when too many tabs)
    """

    TAB_HEIGHT = 28
    TAB_PADDING = 14
    CLOSE_SIZE = 16
    CLOSE_OFFSET = 6
    TAB_GAP = 4

    def __init__(
        self,
        parent,
        on_select: Callable[[str], None],
        on_close: Callable[[str], None],
        on_context_menu: Callable[[str, int, int], None],
        **kwargs,
    ):
        super().__init__(parent, **kwargs)
        self._on_select = on_select
        self._on_close = on_close
        self._on_context_menu = on_context_menu

        self._scroll_offset = 0
        self._tabs: dict[str, Tab] = {}
        # Layout info: tab_id -> {x1, x2, width, label_text}
        self._layout: dict[str, dict] = {}
        self._active_id: str | None = None

        self._canvas = tk.Canvas(
            self,
            height=self.TAB_HEIGHT,
            highlightthickness=0,
            bd=0,
        )
        self._canvas.pack(fill=tk.X, side=tk.TOP)
        self._canvas.config(bg=theme.BG_TITLE)

        self._tab_font = tkfont.Font(family="Segoe UI", size=9)

        # Scroll buttons
        self._left_btn = tk.Label(
            self, text="◀", font=("Segoe UI", 6), bg=str(theme.BG_TITLE), fg=str(theme.FG_SECONDARY)
        )
        self._right_btn = tk.Label(
            self, text="▶", font=("Segoe UI", 6), bg=str(theme.BG_TITLE), fg=str(theme.FG_SECONDARY)
        )
        self._left_btn.pack(side=tk.LEFT, padx=2, pady=0)
        self._right_btn.pack(side=tk.RIGHT, padx=2, pady=0)
        self._left_btn.bind("<Button-1>", lambda e: self._scroll_left())
        self._right_btn.bind("<Button-1>", lambda e: self._scroll_right())

        self._canvas.bind("<Configure>", self._on_resize)
        self._canvas.bind("<Button-1>", self._on_canvas_click)
        self._canvas.bind("<Button-3>", self._on_canvas_right_click)
        self._canvas.bind("<MouseWheel>", self._on_wheel)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_tabs(self, tabs: list[Tab], active_id: str | None) -> None:
        """Set all tabs and specify the active tab."""
        self._tabs = {t.id: t for t in tabs}
        self._active_id = active_id
        self._scroll_offset = 0
        self._redraw()

    def update_tab(self, tab_id: str, title: str, dirty: bool) -> None:
        """Update a single tab's title or dirty state."""
        if tab_id in self._tabs:
            self._tabs[tab_id].title = title
            self._tabs[tab_id].dirty = dirty
            self._redraw()

    def set_active(self, tab_id: str) -> None:
        """Switch active tab (without triggering callback)."""
        self._active_id = tab_id
        self._ensure_visible(tab_id)
        self._redraw()

    def remove_tab(self, tab_id: str) -> None:
        """Remove a tab."""
        self._tabs.pop(tab_id, None)
        self._layout.pop(tab_id, None)
        if self._active_id == tab_id:
            self._active_id = None
        self._redraw()

    def _redraw(self) -> None:
        """Redraw all tabs."""
        self._canvas.delete("all")

        canvas_w = self._canvas.winfo_width()
        if canvas_w < 2:
            canvas_w = 800

        x = 2 - self._scroll_offset
        self._layout.clear()

        for tab_id, tab in self._tabs.items():
            label_text = f"*{tab.title}" if tab.dirty else tab.title
            text_w = self._tab_font.measure(label_text)
            tab_w = text_w + self.TAB_PADDING * 2 + self.CLOSE_SIZE + self.CLOSE_OFFSET + 4

            # Record layout info
            self._layout[tab_id] = {
                "x1": x,
                "x2": x + tab_w,
                "width": tab_w,
                "label": label_text,
            }

            is_active = tab_id == self._active_id
            bg = str(theme.BG_ACTIVE) if is_active else str(theme.BG_RAISED)
            fg = str(theme.FG_PRIMARY) if is_active else str(theme.FG_SECONDARY)

            # Tab background
            self._canvas.create_rectangle(
                x,
                2,
                x + tab_w,
                self.TAB_HEIGHT - 2,
                fill=bg,
                outline=str(theme.BORDER),
                tags=("tab", f"bg_{tab_id}"),
            )

            # Text
            self._canvas.create_text(
                x + self.TAB_PADDING,
                self.TAB_HEIGHT // 2,
                text=label_text,
                fill=fg,
                anchor="w",
                font=self._tab_font,
                tags=("tab", f"label_{tab_id}"),
            )

            # Close button
            close_x = x + tab_w - self.CLOSE_SIZE - self.CLOSE_OFFSET
            close_y = self.TAB_HEIGHT // 2
            self._canvas.create_text(
                close_x,
                close_y,
                text="x",
                fill=str(theme.FG_TERTIARY),
                font=("Segoe UI", 10, "bold"),
                tags=("tab", f"close_{tab_id}"),
            )

            # Click hot zone
            self._canvas.create_rectangle(
                x,
                2,
                x + tab_w,
                self.TAB_HEIGHT - 2,
                fill="",
                outline="",
                tags=("tab", f"hit_{tab_id}"),
            )

            x += tab_w + self.TAB_GAP

        total_w = x - 2
        if total_w > canvas_w:
            self._left_btn.pack(side=tk.LEFT, padx=2, pady=0)
            self._right_btn.pack(side=tk.RIGHT, padx=2, pady=0)
        else:
            self._left_btn.pack_forget()
            self._right_btn.pack_forget()

    def _ensure_visible(self, tab_id: str) -> None:
        """Ensure the specified tab is within the visible area."""
        info = self._layout.get(tab_id)
        if not info:
            return
        canvas_w = self._canvas.winfo_width()
        if canvas_w < 2:
            return
        if info["x1"] < 0:
            self._scroll_offset += abs(info["x1"]) + 2
        elif info["x2"] > canvas_w:
            self._scroll_offset -= (info["x2"] - canvas_w) + 2

    # ------------------------------------------------------------------
    # Event handling
    # ------------------------------------------------------------------

    def _on_resize(self, e=None) -> None:
        self._redraw()

    def _on_canvas_click(self, e) -> None:
        clicked_id = self._hit_test(e.x)
        if clicked_id is None:
            return
        if self._on_close_button(e.x, clicked_id):
            self._on_select(clicked_id)
            self._on_close(clicked_id)
        else:
            self._on_select(clicked_id)

    def _on_canvas_right_click(self, e) -> None:
        tab_id = self._hit_test(e.x)
        if tab_id:
            self._on_context_menu(tab_id, e.x_root, e.y_root)

    def _on_wheel(self, e) -> None:
        delta = int(e.delta / 120)
        canvas_w = self._canvas.winfo_width()
        total_w = sum(info["width"] + self.TAB_GAP for info in self._layout.values())
        if total_w <= canvas_w:
            return
        self._scroll_offset = max(0, min(self._scroll_offset + delta * 30, total_w - canvas_w + 50))
        self._redraw()

    def _scroll_left(self, e=None) -> None:
        self._scroll_offset = max(0, self._scroll_offset - 80)
        self._redraw()

    def _scroll_right(self, e=None) -> None:
        self._scroll_offset += 80
        self._redraw()

    def _hit_test(self, x: float) -> str | None:
        """Return the tab id hit at the specified x coordinate."""
        for tab_id, info in self._layout.items():
            if info["x1"] <= x <= info["x2"]:
                return tab_id
        return None

    def _on_close_button(self, x: float, tab_id: str) -> bool:
        """Check if x falls within the close button range of tab_id."""
        info = self._layout.get(tab_id)
        if not info:
            return False
        close_x = info["x2"] - self.CLOSE_SIZE - self.CLOSE_OFFSET
        return close_x <= x <= info["x2"]

    # ------------------------------------------------------------------
    # Theme following
    # ------------------------------------------------------------------

    def _apply_theme(self) -> None:
        self._canvas.config(bg=str(theme.BG_TITLE))
        self._left_btn.config(bg=str(theme.BG_TITLE), fg=str(theme.FG_SECONDARY))
        self._right_btn.config(bg=str(theme.BG_TITLE), fg=str(theme.FG_SECONDARY))
        self._redraw()
