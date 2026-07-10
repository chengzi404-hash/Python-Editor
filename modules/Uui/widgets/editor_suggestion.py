import tkinter as tk
from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

from . import theme


@dataclass
class CompletionItem:
    label: str
    detail: str = ''
    description: str = ''
    insert: str = ''
    kind: str = ''
    priority: int = 0

    def __post_init__(self):
        if not self.insert:
            self.insert = self.label


class UEditorSuggestion(tk.Toplevel):
    _active: Optional['UEditorSuggestion'] = None

    _ITEM_HEIGHT = 24
    _FOOTER_LINES = 3
    _FOOTER_LINE_HEIGHT = 16
    _MIN_WIDTH = 200
    _MAX_WIDTH = 480
    _PAD_X = 10

    def __init__(self, parent, items: Iterable[Any] = (),
                 on_select: Optional[Callable[[CompletionItem], None]] = None,
                 *, max_visible: int = 8, show_detail: bool = True,
                 show_description: bool = True, grab_focus: bool = False) -> None:
        top = parent.winfo_toplevel() if parent is not None else getattr(tk, '_default_root', None)
        super().__init__(top)
        self._owner_top = top
        self.withdraw()
        self.overrideredirect(True)
        self.configure(bg=theme.BG_PANEL)

        self._on_select = on_select
        self._max_visible = max(1, int(max_visible))
        self._show_detail = show_detail
        self._show_description = show_description
        self._grab_focus = grab_focus

        self._items: List[CompletionItem] = []
        self._row_widgets: List[tk.Frame] = []
        self._row_widgets_map: Dict[
            tk.Frame,
            Tuple[List[tk.Widget], Optional[tk.Label], Optional[tk.Label]],
        ] = {}
        self._selected_index = -1
        self._scroll_offset = 0
        self._root_bind: Optional[str] = None

        self._outer = tk.Frame(
            self, bg=theme.BG_PANEL,
            highlightthickness=1,
            highlightbackground=theme.BORDER,
            bd=0,
        )
        self._outer.pack(fill=tk.BOTH, expand=True)

        self._list_frame = tk.Frame(self._outer, bg=theme.BG_PANEL)
        self._list_frame.pack(fill=tk.BOTH, expand=True)

        self._sep = tk.Frame(self._outer, bg=theme.BORDER, height=1)
        self._footer = tk.Label(
            self._outer, text='', bg=theme.BG_PANEL,
            fg=theme.FG_SECONDARY, font=theme.LABEL_FONT_SMALL,
            anchor='nw', justify='left', padx=self._PAD_X, pady=6,
            wraplength=0,
        )

        self.bind('<Down>', lambda e: self.select_next())
        self.bind('<Up>', lambda e: self.select_prev())
        self.bind('<Return>', lambda e: self._commit())
        self.bind('<Tab>', lambda e: self._commit())
        self.bind('<Escape>', lambda e: self.hide())

        if grab_focus:
            self.bind('<FocusOut>', lambda e: self.hide())

        self._theme_callback = self._on_theme_change
        theme.on_change(self._theme_callback)

        self.set_items(items)

    def show(self, items: Optional[Iterable[Any]] = None, *,
             x: Optional[int] = None, y: Optional[int] = None,
             attach_to: Optional[tk.Widget] = None,
             index: str = 'insert') -> None:
        if items is not None:
            self.set_items(items)

        if not self._items:
            self.hide()
            return

        active = UEditorSuggestion._active
        if active is not None and active is not self:
            active.hide()
        UEditorSuggestion._active = self

        if attach_to is not None and x is None and y is None:
            x, y = self._resolve_anchor(attach_to, index)

        if x is None:
            x = self.winfo_screenwidth() // 2
        if y is None:
            y = self.winfo_screenheight() // 2

        self._update_geometry()
        self._clamp_position(x, y)

        if self._owner_top is not None:
            self._root_bind = self._owner_top.bind(
                '<Button-1>', self._on_root_click, add='+')

        self.attributes('-topmost', True)
        self.deiconify()
        if self._grab_focus:
            self.focus_set()

    def hide(self) -> None:
        if UEditorSuggestion._active is self:
            UEditorSuggestion._active = None
        if self._root_bind is not None and self._owner_top is not None:
            try:
                self._owner_top.unbind('<Button-1>', self._root_bind)
            except tk.TclError:
                pass
            self._root_bind = None
        try:
            self.withdraw()
        except tk.TclError:
            pass

    def set_items(self, items: Iterable[Any]) -> None:
        normalized: List[CompletionItem] = []
        for it in items:
            if isinstance(it, CompletionItem):
                normalized.append(it)
            elif isinstance(it, str):
                normalized.append(CompletionItem(label=it))
            elif isinstance(it, dict):
                normalized.append(CompletionItem(
                    label=it.get('label', ''),
                    detail=it.get('detail', ''),
                    description=it.get('description', ''),
                    insert=it.get('insert', ''),
                    kind=it.get('kind', ''),
                    priority=it.get('priority', 0),
                ))
            else:
                raise TypeError(
                    f'unsupported completion item type: {type(it).__name__}')
        # Sort by priority (lower = higher priority), then alphabetically
        normalized.sort(key=lambda x: (x.priority, x.label))
        self._items = normalized
        self._selected_index = 0 if normalized else -1
        self._scroll_offset = 0
        self._rebuild_rows()

    def select_next(self) -> None:
        if not self._items:
            return
        self._selected_index = (self._selected_index + 1) % len(self._items)
        self._ensure_selected_visible()
        self._refresh_selection()

    def select_prev(self) -> None:
        if not self._items:
            return
        self._selected_index = (self._selected_index - 1) % len(self._items)
        self._ensure_selected_visible()
        self._refresh_selection()

    def selected(self) -> Optional[CompletionItem]:
        if 0 <= self._selected_index < len(self._items):
            return self._items[self._selected_index]
        return None

    def move(self, x: int, y: int) -> None:
        self._clamp_position(x, y)

    def destroy(self) -> None:
        try:
            theme.off_change(self._theme_callback)
        except ValueError:
            pass
        if UEditorSuggestion._active is self:
            UEditorSuggestion._active = None
        super().destroy()

    def _resolve_anchor(self, widget: tk.Widget, index: str) -> tuple:
        try:
            bbox_method = getattr(widget, 'bbox', None)
            if callable(bbox_method):
                bbox = bbox_method(index)
                if isinstance(bbox, (list, tuple)) and len(bbox) >= 4:
                    wx = bbox[0]
                    wy = bbox[1] + bbox[3]
                    return widget.winfo_rootx() + wx, widget.winfo_rooty() + wy
        except Exception:
            pass
        return (
            widget.winfo_rootx(),
            widget.winfo_rooty() + widget.winfo_height(),
        )

    def _clamp_position(self, x: int, y: int) -> None:
        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        w = max(self.winfo_width(), self._MIN_WIDTH)
        h = max(self.winfo_height(), 1)
        if x + w > sw:
            x = max(0, sw - w)
        if y + h > sh:
            y = max(0, sh - h)
        if x < 0:
            x = 0
        if y < 0:
            y = 0
        self.geometry(f'+{int(x)}+{int(y)}')

    def _rebuild_rows(self) -> None:
        for row in self._row_widgets:
            row.destroy()
        self._row_widgets.clear()
        self._row_widgets_map.clear()

        for idx, item in enumerate(self._items):
            row = self._build_row(item, idx)
            self._row_widgets.append(row)

        self._apply_scroll()
        self._update_footer_visibility()
        self._update_geometry()
        self._refresh_selection()

    def _build_row(self, item: CompletionItem, idx: int) -> tk.Frame:
        row = tk.Frame(
            self._list_frame, bg=theme.BG_PANEL,
            height=self._ITEM_HEIGHT,
        )
        row.pack_propagate(False)

        label = tk.Label(
            row, text=item.label, bg=theme.BG_PANEL,
            fg=theme.FG_PRIMARY, font=theme.MONO_FONT,
            anchor='w',
        )
        label.pack(side=tk.LEFT, padx=(self._PAD_X, 6), pady=3)

        widgets: List[tk.Widget] = [row, label]
        detail_label: Optional[tk.Label] = None

        if self._show_detail and item.detail:
            detail_label = tk.Label(
                row, text=item.detail, bg=theme.BG_PANEL,
                fg=theme.FG_SECONDARY, font=theme.LABEL_FONT_SMALL,
                anchor='e',
            )
            detail_label.pack(side=tk.RIGHT, padx=(6, self._PAD_X), pady=3)
            widgets.append(detail_label)

        for w in widgets:
            w.bind('<Button-1>', lambda e, i=idx: self._on_row_click(i))
            w.bind('<Enter>', lambda e, i=idx: self._set_hover(i))

        self._row_widgets_map[row] = (widgets, label, detail_label)
        return row

    def _set_hover(self, idx: int) -> None:
        if idx == self._selected_index:
            return
        self._selected_index = idx
        self._refresh_selection()

    def _on_row_click(self, idx: int) -> None:
        self._selected_index = idx
        self._refresh_selection()
        self._commit()

    def _commit(self) -> None:
        item = self.selected()
        self.hide()
        if item is not None and self._on_select is not None:
            try:
                self._on_select(item)
            except Exception:
                pass

    def _ensure_selected_visible(self) -> None:
        if self._selected_index < self._scroll_offset:
            self._scroll_offset = self._selected_index
        elif self._selected_index >= self._scroll_offset + self._max_visible:
            self._scroll_offset = self._selected_index - self._max_visible + 1
        self._apply_scroll()

    def _apply_scroll(self) -> None:
        for i, row in enumerate(self._row_widgets):
            if self._scroll_offset <= i < self._scroll_offset + self._max_visible:
                row.pack(fill=tk.X)
            else:
                row.pack_forget()

    def _update_footer_visibility(self) -> None:
        has_desc = self._show_description and any(it.description for it in self._items)
        if has_desc:
            self._sep.pack(fill=tk.X, padx=4)
            self._footer.pack(fill=tk.X)
        else:
            self._sep.pack_forget()
            self._footer.pack_forget()

    def _refresh_selection(self) -> None:
        for i, row in enumerate(self._row_widgets):
            selected = i == self._selected_index
            bg = theme.BLUE if selected else theme.BG_PANEL
            widgets, main_label, detail_label = self._row_widgets_map.get(
                row, ([row], None, None))
            for w in widgets:
                try:
                    w.config(bg=bg)  # type: ignore
                except tk.TclError:
                    pass
            if main_label is not None:
                try:
                    main_label.config(fg=theme.FG_PRIMARY)  # type: ignore
                except tk.TclError:
                    pass
            if detail_label is not None:
                try:
                    detail_label.config(
                        fg=theme.FG_PRIMARY if selected else theme.FG_SECONDARY)  # type: ignore
                except tk.TclError:
                    pass
        self._update_footer()

    def _update_footer(self) -> None:
        item = self.selected()
        if item and item.description:
            width = max(self.winfo_width() - 2 * self._PAD_X, 1)
            self._footer.config(text=item.description, wraplength=width)
        else:
            self._footer.config(text='')

    def _on_root_click(self, event: tk.Event) -> None:
        try:
            rx, ry = self.winfo_rootx(), self.winfo_rooty()
            rw, rh = self.winfo_width(), self.winfo_height()
            xr, yr = event.x_root, event.y_root
        except tk.TclError:
            self.hide()
            return
        if rx <= xr <= rx + rw and ry <= yr <= ry + rh:
            return
        self.hide()

    def _update_geometry(self) -> None:
        max_row_w = max(
            (row.winfo_reqwidth() for row in self._row_widgets),
            default=0,
        )
        width = max(self._MIN_WIDTH, min(self._MAX_WIDTH, max_row_w + 20))

        visible_count = min(self._max_visible, len(self._items))
        list_height = visible_count * self._ITEM_HEIGHT
        footer_height = 0
        if self._show_description and any(it.description for it in self._items):
            footer_height = (
                self._FOOTER_LINES * self._FOOTER_LINE_HEIGHT + 12 + 1
            )
        height = list_height + footer_height

        self._list_frame.config(height=list_height)
        self.geometry(f'{width}x{height}')

    def _on_theme_change(self, _theme: theme.Theme) -> None:
        self._apply_theme()

    def _apply_theme(self) -> None:
        try:
            self.configure(bg=theme.BG_PANEL)
        except tk.TclError:
            return
        self._outer.config(
            bg=theme.BG_PANEL,
            highlightbackground=theme.BORDER,
        )
        self._list_frame.config(bg=theme.BG_PANEL)
        self._sep.config(bg=theme.BORDER)
        self._footer.config(
            bg=theme.BG_PANEL, fg=theme.FG_SECONDARY,
            font=theme.LABEL_FONT_SMALL,
        )
        for row in self._row_widgets:
            widgets, main_label, detail_label = self._row_widgets_map.get(
                row, ([row], None, None))
            for w in widgets:
                try:
                    w.config(bg=theme.BG_PANEL)  # type: ignore
                except tk.TclError:
                    pass
            if main_label is not None:
                try:
                    main_label.config(fg=theme.FG_PRIMARY)  # type: ignore
                except tk.TclError:
                    pass
            if detail_label is not None:
                try:
                    detail_label.config(fg=theme.FG_SECONDARY)  # type: ignore
                except tk.TclError:
                    pass
        self._refresh_selection()


__all__ = ['CompletionItem', 'UEditorSuggestion']
