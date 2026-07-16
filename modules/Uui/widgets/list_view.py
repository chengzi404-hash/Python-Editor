from __future__ import annotations

import contextlib
import tkinter as tk
from collections.abc import Callable
from typing import Any

from . import theme
from .scrollbar import UScrollBar


class UListView(tk.Frame):
    def __init__(
        self,
        parent,
        columns: list[str] | None = None,
        column_widths: dict[str, int] | None = None,
        on_select: Callable[[int, dict[str, str]], None] | None = None,
        show_header: bool = True,
        **kwargs,
    ):
        bg = kwargs.pop("bg", theme.BG_PANEL)
        super().__init__(parent, bg=bg, highlightthickness=0, bd=0, **kwargs)

        self._columns = columns or []
        self._column_widths = column_widths or {}
        self._on_select_cb = on_select
        self._show_header = show_header
        self._data: list[dict[str, str]] = []
        self._items: list[dict[str, Any]] = []
        self._selected_index: int | None = None

        outer = tk.Frame(self, bg=theme.BG_PANEL)
        outer.pack(fill=tk.BOTH, expand=True)

        # ── header ──
        self._header_frame = tk.Frame(outer, bg=theme.BG_TITLE, height=28)
        self._header_labels: list[tk.Label] = []
        self._header_spacer: tk.Frame | None = None

        if show_header:
            self._header_frame.pack(fill=tk.X)
        self._header_frame.pack_propagate(False)

        for col_idx, col in enumerate(self._columns):
            lbl = tk.Label(
                self._header_frame,
                text=col,
                bg=theme.BG_TITLE,
                fg=theme.FG_PRIMARY,
                font=theme.LABEL_FONT_BOLD,
                anchor="w",
                padx=8,
            )
            lbl.grid(row=0, column=col_idx, sticky="nsew")
            self._header_labels.append(lbl)

        for col_idx, col in enumerate(self._columns):
            w = self._column_widths.get(col, 100)
            self._header_frame.columnconfigure(col_idx, weight=w, minsize=w)

        self._header_spacer = tk.Frame(self._header_frame, bg=theme.BG_TITLE)
        self._header_spacer.grid(row=0, column=len(self._columns), sticky="ns")
        self._header_frame.columnconfigure(len(self._columns), weight=0, minsize=0)

        # ── body (canvas + scrollbar) ──
        body_frame = tk.Frame(outer, bg=theme.BG_PANEL)
        body_frame.pack(fill=tk.BOTH, expand=True)

        self._canvas = tk.Canvas(body_frame, bg=theme.BG_PANEL, highlightthickness=0, bd=0)
        self._canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self._vbar = UScrollBar(body_frame, orient="vertical", command=self._canvas.yview)
        self._vbar.pack(side=tk.RIGHT, fill=tk.Y)

        self._canvas.configure(yscrollcommand=self._vbar.set)

        self._canvas.bind("<Configure>", self._on_canvas_configure)
        self._canvas.bind("<MouseWheel>", self._on_wheel)

        self._items_frame = tk.Frame(self._canvas, bg=theme.BG_PANEL)
        self._canvas_window = self._canvas.create_window(
            (0, 0),
            window=self._items_frame,
            anchor="nw",
            tags="inner",
        )
        self._items_frame.bind("<Configure>", self._on_inner_configure)

        self._after_resize_id = None

    def _sync_header_spacer(self):
        spacer = self._header_spacer
        if spacer is None:
            return
        try:
            sb_w = self._vbar.winfo_width() if self._vbar.winfo_ismapped() else 0
            spacer.configure(width=sb_w)
        except tk.TclError:
            pass

    def set_data(self, data: list[dict[str, str]]):
        self._data = data
        self._selected_index = None
        self._rebuild()

    def clear(self):
        self._data = []
        self._selected_index = None
        self._rebuild()

    def selected_index(self) -> int | None:
        return self._selected_index

    def selected_value(self) -> dict[str, str] | None:
        if self._selected_index is not None and 0 <= self._selected_index < len(self._data):
            return self._data[self._selected_index]
        return None

    def _rebuild(self):
        for w in self._items_frame.winfo_children():
            w.destroy()
        self._items.clear()

        ncols = len(self._columns)
        for col_idx in range(ncols):
            w = self._column_widths.get(self._columns[col_idx], 100)
            self._items_frame.columnconfigure(col_idx, weight=w, minsize=w)

        for idx, row in enumerate(self._data):
            is_even = idx % 2 == 0
            row_bg = theme.BG_BASE if is_even else theme.BG_PANEL

            item_bg = row_bg
            if idx == self._selected_index:
                item_bg = theme.BLUE

            row_container = tk.Frame(self._items_frame, bg=item_bg, cursor="hand2")
            row_container.pack(fill=tk.X)

            for col_idx, col in enumerate(self._columns):
                val = row.get(col, "")
                cell = tk.Label(
                    row_container,
                    text=val,
                    bg=item_bg,
                    fg=theme.FG_PRIMARY,
                    font=theme.LABEL_FONT,
                    anchor="w",
                    padx=8,
                )
                cell.grid(row=0, column=col_idx, sticky="nsew")

            for col_idx in range(ncols):
                w = self._column_widths.get(self._columns[col_idx], 100)
                row_container.columnconfigure(col_idx, weight=w, minsize=w)

            for child in (row_container,):
                child.bind("<Button-1>", lambda e, i=idx: self._select(i))
                for c in child.winfo_children():
                    c.bind("<Button-1>", lambda e, i=idx: self._select(i))

            self._items.append(
                {
                    "container": row_container,
                    "bg": row_bg,
                }
            )

        self._schedule_sync()

    def _select(self, index: int):
        if self._selected_index is not None and 0 <= self._selected_index < len(self._items):
            old = self._items[self._selected_index]
            old_bg = old["bg"]
            old["container"].config(bg=old_bg)
            for child in old["container"].winfo_children():
                child.config(bg=old_bg)

        self._selected_index = index
        item = self._items[index]
        item["container"].config(bg=theme.BLUE)
        for child in item["container"].winfo_children():
            child.config(bg=theme.BLUE)

        if self._on_select_cb and 0 <= index < len(self._data):
            self._on_select_cb(index, self._data[index])

    def _on_canvas_configure(self, e):
        self._canvas.itemconfig(self._canvas_window, width=e.width)
        self._schedule_sync()

    def _schedule_sync(self):
        if self._after_resize_id:
            with contextlib.suppress(Exception):
                self.after_cancel(self._after_resize_id)
        self._after_resize_id = self.after(20, self._sync_header_spacer)

    def _on_inner_configure(self, e):
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))

    def _on_wheel(self, e):
        self._canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")

    def _apply_theme(self):
        self.config(bg=theme.BG_PANEL)
        self._header_frame.config(bg=theme.BG_TITLE)
        for h in self._header_labels:
            h.config(bg=theme.BG_TITLE, fg=theme.FG_PRIMARY)
        if self._header_spacer:
            self._header_spacer.config(bg=theme.BG_TITLE)
        for item in self._items:
            bg = item["bg"]
            item["container"].config(bg=bg)
            for child in item["container"].winfo_children():
                child.config(bg=bg, fg=theme.FG_PRIMARY)
        if self._selected_index is not None and 0 <= self._selected_index < len(self._items):
            item = self._items[self._selected_index]
            item["container"].config(bg=theme.BLUE)
            for child in item["container"].winfo_children():
                child.config(bg=theme.BLUE)
        self._canvas.config(bg=theme.BG_PANEL)
