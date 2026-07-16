"""``modules.Uui.widgets.tree_canvas`` — ``tk.Canvas``-based generic tree control.

Design Motivation:

* Currently two tree controls in the repo (:class:`UFileTree` /
  :class:`USettingsNavBar`) both use ``tkinter.ttk.Treeview`` + ``clam``
  theme, requiring :class:`ttk.Style` ``configure`` item by item to align
  with current :data:`theme`, high maintenance cost and coupled with Tk theme system.
* :class:`TreeCanvas` provides a minimal, reusable tree rendering layer; business side only
  needs to: feed in "iid + parent iid + display text", then listen to ``on_select`` /
  ``on_activate`` / ``on_toggle`` three callbacks. Colors entirely determined by
  :data:`theme`, :meth:`_apply_theme` can refresh entire tree in one line.

API Overview::

    tree = TreeCanvas(
        parent,
        row_text=lambda iid: my_label_for(iid),
        on_select=lambda iid: ...,
        on_activate=lambda iid: ...,
        on_toggle=lambda iid, is_open: ...,
    )
    tree.add_node("root", None, is_open=True)
    tree.add_node("child", "root")
    tree.set_selected("child")
    tree.see("child")
    tree.clear()

Design Points:

* Each visible node is embedded into :class:`tk.Canvas` (``create_window``) using :class:`tk.Frame`,
  so hover / selected highlight can directly modify Frame's ``bg``, no need to
  go through ttk style system.
* Node expand/collapse implemented by drawing a ``▼ / ▶`` triangle on left side of each row; entire
  tree flattened into an ``iid -> row_y`` dict, scrolling only cares about row order.
* Theme refresh only needs to redraw all row Frames' ``bg / fg``; don't rebuild widgets,
  so selection state, hover state, and scroll position are all preserved.
"""

from __future__ import annotations

import contextlib
import tkinter as tk
from collections.abc import Callable
from typing import Any

from . import theme
from .frame import UFrame
from .scrollbar import UScrollBar

# Triangle characters -- using ASCII fallback for font compatibility; visually more stable than ▼/▶.
_TRI_OPEN = "v"  # "expanded" placeholder
_TRI_CLOSED = ">"  # "collapsed" placeholder
_TRI_BLANK = " "  # leaf node (no children) placeholder


class _Node:
    """Pure data layer for tree nodes; doesn't hold any Tk references, convenient for testing and rebuilding."""

    __slots__ = ("children", "data", "iid", "is_open", "parent_iid")

    def __init__(self, iid: str, parent_iid: str | None, data: Any) -> None:
        self.iid = iid
        self.parent_iid = parent_iid
        self.children: list[str] = []
        self.is_open = False
        self.data = data


class TreeCanvas(UFrame):
    """Canvas-based reusable tree control.

    Business side only needs to provide "iid -> display text" callback and three event callbacks
    to build a clickable, expandable/collapsible, scrollable, theme-following tree. What
    "business object the iid represents" is entirely delegated to caller -- typically caller
    maintains a ``iid -> business object`` dict and reverse-lookups in callbacks.
    """

    def __init__(
        self,
        parent,
        *,
        row_text: Callable[[str], str],
        on_select: Callable[[str], None] | None = None,
        on_activate: Callable[[str], None] | None = None,
        on_toggle: Callable[[str, bool], None] | None = None,
        row_height: int = 22,
        row_indent: int = 18,
        show_disclosure: bool = True,
        **kwargs,
    ) -> None:
        # Visually isomorphic with UFileTree: self is 'panel' container.
        kwargs.setdefault("variant", "panel")
        super().__init__(parent, **kwargs)

        self._row_text = row_text
        self._on_select = on_select
        self._on_activate = on_activate
        self._on_toggle = on_toggle
        self._row_height = row_height
        self._row_indent = row_indent
        self._show_disclosure = show_disclosure

        # Tree model (pure data, no Tk dependency)
        self._nodes: dict[str, _Node] = {}
        self._root_iids: list[str] = []
        self._selected_iid: str | None = None
        self._hover_iid: str | None = None

        # Rendering layer
        self._row_frames: dict[str, tk.Frame] = {}  # iid -> row Frame
        self._row_y: dict[str, int] = {}  # iid -> canvas y
        self._row_window_id: dict[str, int] = {}  # iid -> canvas window item id
        self._pending_width_sync = False  # Debounce: multiple resize only refresh once

        self._build_canvas()

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    def _build_canvas(self) -> None:
        self._canvas = tk.Canvas(
            self,
            bg=theme.BG_INPUT,
            highlightthickness=0,
            bd=0,
        )
        # Unified at :class:`UScrollBar` -- theme colors and autohide behavior are centrally maintained;
        # The old handwritten 6 kwargs Scrollbar has scattered across 4 files, changing
        # style once required changes in 4 places, now unified here.
        self._vsb = UScrollBar(
            self,
            orient="vertical",
            command=self._canvas.yview,
        )
        self._canvas.configure(yscrollcommand=self._vsb.set)

        self._vsb.pack(side=tk.RIGHT, fill=tk.Y)
        self._canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Events
        self._canvas.bind("<Button-1>", self._on_canvas_press)
        self._canvas.bind("<Double-Button-1>", self._on_canvas_double)
        self._canvas.bind("<Return>", self._on_canvas_return)
        self._canvas.bind("<Configure>", self._on_canvas_configure)
        # Mouse wheel (Windows / macOS use delta; Linux use Button-4/5)
        self._canvas.bind("<MouseWheel>", self._on_mousewheel)
        self._canvas.bind("<Button-4>", lambda e: self._canvas.yview_scroll(-1, "units"))
        self._canvas.bind("<Button-5>", lambda e: self._canvas.yview_scroll(1, "units"))

    # ------------------------------------------------------------------
    # Public API: add / remove / modify nodes
    # ------------------------------------------------------------------

    def add_node(
        self,
        iid: str,
        parent_iid: str | None,
        *,
        is_open: bool = False,
        data: Any = None,
    ) -> None:
        """Register a node. Parent must already exist (except root with ``parent_iid=None``).

        Duplicate iid silently ignored, to avoid upstream duplicate construction clearing existing child nodes;
        if "rebuild" semantics needed, call :meth:`clear` first.
        """

        if iid in self._nodes:
            return
        node = _Node(iid=iid, parent_iid=parent_iid, data=data)
        node.is_open = is_open
        self._nodes[iid] = node
        if parent_iid is None:
            self._root_iids.append(iid)
        else:
            parent = self._nodes.get(parent_iid)
            if parent is None:
                # Defensive: parent missing, don't allow orphan nodes, otherwise will never
                # be hit by _relayout, forming "looks added but invisible" bug.
                del self._nodes[iid]
                raise ValueError(f"TreeCanvas.add_node: parent {parent_iid!r} not found")
            parent.children.append(iid)
        self._relayout()

    def remove_node(self, iid: str) -> None:
        """Delete a node and all its descendants."""

        node = self._nodes.get(iid)
        if node is None:
            return
        to_remove: list[str] = []
        self._collect_descendants(iid, to_remove)
        # Remove deleted root nodes from root list.
        for rid in to_remove:
            if rid in self._root_iids:
                self._root_iids.remove(rid)
        # Key: must also remove self from parent's children list, otherwise next
        # _relayout DFS will still encounter deleted iid, triggering KeyError.
        if node.parent_iid is not None:
            parent = self._nodes.get(node.parent_iid)
            if parent is not None and iid in parent.children:
                parent.children.remove(iid)
        # Release Tk resources + clear data layer.
        for rid in to_remove:
            self._nodes.pop(rid, None)
            self._row_frames.pop(rid, None)
            self._row_y.pop(rid, None)
            self._row_window_id.pop(rid, None)
        if self._selected_iid in to_remove:
            self._selected_iid = None
        if self._hover_iid in to_remove:
            self._hover_iid = None
        self._relayout()

    def clear(self) -> None:
        """Clear the entire tree, return to initial state."""

        for frame in self._row_frames.values():
            with contextlib.suppress(tk.TclError):
                frame.destroy()
        self._row_frames.clear()
        self._row_y.clear()
        self._row_window_id.clear()
        self._canvas.delete("all")
        self._nodes.clear()
        self._root_iids.clear()
        self._selected_iid = None
        self._hover_iid = None
        self._update_scroll_region()

    def set_open(self, iid: str, is_open: bool, *, fire_toggle: bool = True) -> None:
        """Programmatically open/close a node. When closing, if current selection is hidden, deselect."""

        node = self._nodes.get(iid)
        if node is None or node.is_open == is_open:
            return
        node.is_open = is_open
        if (
            not is_open
            and self._selected_iid is not None
            and not self._is_visible(self._selected_iid)
        ):
            self._apply_selection(None)
        self._relayout()
        if fire_toggle and self._on_toggle is not None:
            with contextlib.suppress(Exception):
                self._on_toggle(iid, is_open)

    def toggle(self, iid: str) -> None:
        node = self._nodes.get(iid)
        if node is None:
            return
        self.set_open(iid, not node.is_open)

    # ------------------------------------------------------------------
    # Public API: selection / scroll / find
    # ------------------------------------------------------------------

    def set_selected(
        self,
        iid: str | None,
        *,
        fire: bool = True,
        scroll: bool = True,
    ) -> None:
        """Programmatically select a node. Hidden nodes cannot be selected (protecting UX consistency)."""

        if iid is not None:
            if iid not in self._nodes:
                return
            if not self._is_visible(iid):
                return
        self._apply_selection(iid)
        if iid is not None and scroll:
            self.see(iid)
        if fire and iid is not None and self._on_select is not None:
            with contextlib.suppress(Exception):
                self._on_select(iid)

    def get_selected(self) -> str | None:
        return self._selected_iid

    def exists(self, iid: str) -> bool:
        return iid in self._nodes

    def is_open(self, iid: str) -> bool:
        node = self._nodes.get(iid)
        return node.is_open if node is not None else False

    def node_data(self, iid: str) -> Any:
        """Return ``data`` passed in when :meth:`add_node` was called (for business side reverse lookup)."""

        node = self._nodes.get(iid)
        return node.data if node is not None else None

    def see(self, iid: str) -> None:
        """Scroll to bring ``iid`` into visible area. Invisible nodes are silently ignored."""

        if iid not in self._nodes or not self._is_visible(iid):
            return
        y = self._row_y.get(iid)
        if y is None:
            return
        bbox = self._canvas.bbox("all")
        if not bbox:
            return
        total_h = bbox[3]
        canvas_h = self._canvas.winfo_height()
        if total_h <= canvas_h or canvas_h <= 1:
            return
        first, _ = self._canvas.yview()
        top_y = first * total_h
        if y < top_y:
            self._canvas.yview_moveto(y / total_h)
        elif y + self._row_height > top_y + canvas_h:
            self._canvas.yview_moveto((y + self._row_height - canvas_h) / total_h)

    def identify_row(self, y: int) -> str | None:
        """Reverse lookup canvas y coordinate to iid; returns ``None`` if not on a row."""

        for iid, row_y in self._row_y.items():
            if row_y <= y < row_y + self._row_height:
                return iid
        return None

    # ------------------------------------------------------------------
    # Internal: visibility / depth
    # ------------------------------------------------------------------

    def _is_visible(self, iid: str) -> bool:
        node = self._nodes.get(iid)
        if node is None:
            return False
        cur = node.parent_iid
        while cur is not None:
            parent = self._nodes.get(cur)
            if parent is None or not parent.is_open:
                return False
            cur = parent.parent_iid
        return True

    def _depth(self, iid: str) -> int:
        depth = 0
        cur = self._nodes.get(iid)
        while cur is not None and cur.parent_iid is not None:
            depth += 1
            cur = self._nodes.get(cur.parent_iid)
        return depth

    def _collect_descendants(self, iid: str, out: list[str]) -> None:
        node = self._nodes.get(iid)
        if node is None:
            return
        out.append(iid)
        for c in node.children:
            self._collect_descendants(c, out)

    # ------------------------------------------------------------------
    # Internal: relayout
    # ------------------------------------------------------------------

    def _relayout(self) -> None:
        """Flatten entire tree by current visibility, rebuild all row widgets."""

        for frame in self._row_frames.values():
            with contextlib.suppress(tk.TclError):
                frame.destroy()
        self._row_frames.clear()
        self._row_y.clear()
        self._row_window_id.clear()
        self._canvas.delete("all")

        # DFS collect visible (iid, depth) sequence.
        visible: list[tuple[str, int]] = []

        def walk(iid: str, depth: int) -> None:
            visible.append((iid, depth))
            node = self._nodes.get(iid)
            if node is None:
                return
            if node.is_open:
                for c in node.children:
                    walk(c, depth + 1)

        for r in self._root_iids:
            walk(r, 0)

        canvas_w = max(1, self._canvas.winfo_width())
        y = 0
        for iid, depth in visible:
            y = self._build_row(iid, depth, y, canvas_w)

        self._update_scroll_region()

    def _build_row(self, iid: str, depth: int, y: int, canvas_w: int) -> int:
        """Construct one row (triangle + text), embed into canvas. Returns next row's y."""

        node = self._nodes[iid]
        text = self._row_text(iid)
        is_selected = iid == self._selected_iid
        indent = depth * self._row_indent

        # Full row Frame -- accepts click events, background color determined by state.
        frame = tk.Frame(
            self._canvas,
            bg=theme.BG_INPUT,
            highlightthickness=0,
            bd=0,
            height=self._row_height,
        )
        frame.pack_propagate(False)

        # Left triangle: internal nodes draw v/>; leaves draw blank placeholder to align text.
        if self._show_disclosure:
            tri_text = _TRI_OPEN if node.is_open else _TRI_CLOSED if node.children else _TRI_BLANK
            tri = tk.Label(
                frame,
                text=tri_text,
                bg=theme.BG_INPUT,
                fg=theme.FG_TERTIARY,
                width=2,
                anchor="center",
                font=theme.LABEL_FONT_SMALL,
                cursor="hand2" if node.children else "arrow",
            )
            tri.pack(side=tk.LEFT, padx=(0, 2))
            if node.children:
                tri.bind(
                    "<Button-1>",
                    lambda e, i=iid: self._on_triangle_click(i),
                )

        # Text label.
        label = tk.Label(
            frame,
            text=text,
            bg=theme.BG_INPUT,
            fg=theme.FG_PRIMARY,
            anchor="w",
            font=theme.LABEL_FONT,
            cursor="hand2",
        )
        label.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(2, 4))

        # Events bound to label + frame (double insurance: clicking text or blank space beside text both work)."
        for w in (label, frame):
            w.bind("<Button-1>", lambda e, i=iid: self._on_row_press(i))
            w.bind(
                "<Double-Button-1>",
                lambda e, i=iid: self._on_row_double(i),
            )
            w.bind("<Enter>", lambda e, i=iid: self._on_row_enter(i))
            w.bind("<Leave>", lambda e, i=iid: self._on_row_leave(i))

        # Embed into canvas.
        win_w = max(50, canvas_w - indent - 16)
        window_id = self._canvas.create_window(
            indent,
            y,
            window=frame,
            anchor="nw",
            width=win_w,
        )
        self._row_frames[iid] = frame
        self._row_y[iid] = y
        self._row_window_id[iid] = window_id

        self._paint_row(frame, iid, is_selected=is_selected, is_hover=False)
        return y + self._row_height

    def _update_scroll_region(self) -> None:
        if self._row_y:
            max_y = max(self._row_y.values()) + self._row_height
        else:
            max_y = 0
        canvas_w = self._canvas.winfo_width() or 200
        self._canvas.configure(scrollregion=(0, 0, canvas_w, max_y))

    def _resync_widths(self) -> None:
        """When canvas width changes, adjust existing rows' embedded width without rebuilding widgets."""

        canvas_w = max(1, self._canvas.winfo_width())
        for iid, window_id in self._row_window_id.items():
            depth = self._depth(iid)
            indent = depth * self._row_indent
            with contextlib.suppress(tk.TclError):
                self._canvas.itemconfigure(
                    window_id,
                    width=max(50, canvas_w - indent - 16),
                )

    # ------------------------------------------------------------------
    # Internal: painting (hover / selected)
    # ------------------------------------------------------------------

    def _paint_row(
        self,
        frame: tk.Frame,
        iid: str,
        *,
        is_selected: bool,
        is_hover: bool,
    ) -> None:
        if is_selected:
            bg, fg = theme.BG_ACTIVE, theme.FG_PRIMARY
        elif is_hover:
            bg, fg = theme.BG_HOVER, theme.FG_PRIMARY
        else:
            bg, fg = theme.BG_INPUT, theme.FG_PRIMARY
        self._safe_config(frame, bg=bg)
        for child in frame.winfo_children():
            # isinstance narrows type, letting type checker recognize .config(bg=, fg=).
            if not isinstance(child, (tk.Frame, tk.Label)):
                continue
            if isinstance(child, tk.Label) and child.cget("text") in (
                _TRI_OPEN,
                _TRI_CLOSED,
                _TRI_BLANK,
            ):
                self._safe_config(child, bg=bg, fg=theme.FG_TERTIARY)
            else:
                self._safe_config(child, bg=bg, fg=fg)

    @staticmethod
    def _safe_config(widget: tk.Misc, **kwargs: Any) -> None:
        """Wrap ``widget.config``; during theme refresh widget may be destroyed, swallow exception.

        Narrow to ``tk.Frame`` / ``tk.Label`` via ``isinstance`` before calling
        ``.config`` — these concrete classes' ``config`` accepts ``bg`` / ``fg``,
        static checkers can see it; more type-safe than ``**kwargs`` directly calling base class
        ``tk.Misc.config`` (signature too broad).
        """

        if not isinstance(widget, (tk.Frame, tk.Label)):
            return
        with contextlib.suppress(tk.TclError):
            widget.config(**kwargs)

    def _apply_selection(self, iid: str | None) -> None:
        """Update selection state and redraw related rows; doesn't trigger callback or scroll."""

        self._selected_iid = iid
        for rid, frame in self._row_frames.items():
            self._paint_row(
                frame,
                rid,
                is_selected=(rid == iid),
                is_hover=(rid == self._hover_iid),
            )

    # ------------------------------------------------------------------
    # Internal: events
    # ------------------------------------------------------------------

    def _on_canvas_press(self, event: tk.Event) -> None:
        iid = self.identify_row(event.y)
        if iid is None:
            return
        # If click falls in "triangle zone" (leftmost 16 pixels after indent), toggle expand.
        node = self._nodes.get(iid)
        if node and node.children and self._show_disclosure:
            depth = self._depth(iid)
            indent = depth * self._row_indent
            if event.x < indent + 16:
                self.toggle(iid)
                return
        self.set_selected(iid)

    def _on_canvas_double(self, event: tk.Event) -> None:
        iid = self.identify_row(event.y)
        if iid is None:
            return
        if self._on_activate is not None:
            with contextlib.suppress(Exception):
                self._on_activate(iid)

    def _on_canvas_return(self, _event: tk.Event) -> None:
        iid = self._selected_iid
        if iid is None or self._on_activate is None:
            return
        with contextlib.suppress(Exception):
            self._on_activate(iid)

    def _on_canvas_configure(self, _event: tk.Event) -> None:
        # Debounce: dragging window causes a string of <Configure>, only refresh once within 50ms.
        if self._pending_width_sync:
            return
        self._pending_width_sync = True
        try:
            self._canvas.after(50, self._do_width_sync)
        except tk.TclError:
            self._pending_width_sync = False

    def _do_width_sync(self) -> None:
        self._pending_width_sync = False
        self._resync_widths()
        self._update_scroll_region()

    def _on_mousewheel(self, event: tk.Event) -> None:
        if not hasattr(event, "delta") or event.delta == 0:
            return
        # Windows / macOS: delta is multiple of ±120; one line per scroll.
        delta = -1 if event.delta > 0 else 1
        self._canvas.yview_scroll(delta, "units")

    def _on_row_press(self, iid: str) -> None:
        self.set_selected(iid)

    def _on_row_double(self, iid: str) -> None:
        if self._on_activate is None:
            return
        with contextlib.suppress(Exception):
            self._on_activate(iid)

    def _on_triangle_click(self, iid: str) -> None:
        self.toggle(iid)

    def _on_row_enter(self, iid: str) -> None:
        if self._hover_iid == iid:
            return
        self._hover_iid = iid
        frame = self._row_frames.get(iid)
        if frame is not None:
            self._paint_row(
                frame,
                iid,
                is_selected=(iid == self._selected_iid),
                is_hover=True,
            )

    def _on_row_leave(self, iid: str) -> None:
        if self._hover_iid != iid:
            return
        self._hover_iid = None
        frame = self._row_frames.get(iid)
        if frame is not None:
            self._paint_row(
                frame,
                iid,
                is_selected=(iid == self._selected_iid),
                is_hover=False,
            )

    # ------------------------------------------------------------------
    # Theme
    # ------------------------------------------------------------------

    def _apply_theme(self) -> None:
        with contextlib.suppress(tk.TclError):
            super()._apply_theme()
        with contextlib.suppress(tk.TclError):
            self._canvas.config(bg=theme.BG_INPUT)
        # UScrollBar implements _apply_theme itself, just forward.
        if hasattr(self._vsb, "_apply_theme"):
            with contextlib.suppress(tk.TclError):
                self._vsb._apply_theme()
        # Redraw all rows -- don't rebuild widgets, preserve selection/hover/scroll position.
        for iid, frame in self._row_frames.items():
            self._paint_row(
                frame,
                iid,
                is_selected=(iid == self._selected_iid),
                is_hover=(iid == self._hover_iid),
            )


__all__ = ["TreeCanvas"]
