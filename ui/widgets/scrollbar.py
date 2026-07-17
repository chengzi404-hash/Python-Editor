"""``modules.Uui.widgets.scrollbar`` — Canvas-drawn theme-aware ScrollBar.

Uses :class:`tk.Frame` + internal :class:`tk.Canvas` to completely replace
:class:`tk.Scrollbar`, because on Windows ``tk.Scrollbar`` system theme
(BG/troughcolor) cannot be reliably overridden with custom colors.

Supports:

* ``bg=""`` —— slider color, empty string defaults to :data:`theme.BG_PANEL`;
  theme switch will refresh; if caller explicitly passes non-empty color, won't override.
* ``autohidden`` —— when ``True``, ``set(first, last)`` receiving (0.0, 1.0)
  automatically ``pack_forget``; receiving non-full range uses cached ``pack_info()`` to restore layout.
* ``command`` / ``orient`` / ``troughcolor`` / ``activebackground`` /
  ``width`` —— interface consistent with :class:`tk.Scrollbar`.
* Mouse: drag slider -> ``command("moveto", first)``; click track -> page scroll;
  wheel -> unit scroll.
"""

from __future__ import annotations

import contextlib
import tkinter as tk
from collections.abc import Callable
from typing import Any, Literal

from . import theme


class UScrollBar(tk.Frame):
    """Canvas-drawn theme-aware ScrollBar.

    On theme switch, :meth:`_apply_theme` determines which color attributes to get
    from ``theme`` module via ``_theme_key_*`` attributes:

    * ``_theme_key_bg = 'BG_PANEL'``
    * ``_theme_key_trough = 'BG_INPUT'``
    * ``_theme_key_active = 'BG_HOVER'``
    """

    # Theme keys -- subclasses can override, or assign directly on instance to change theme refresh source.
    _theme_key_bg: str = "BG_PANEL"
    _theme_key_trough: str = "BG_INPUT"
    _theme_key_active: str = "BG_HOVER"

    # Minimum slider pixel, ensures always draggable
    _MIN_SLIDER_PX = 20

    def __init__(
        self,
        parent: tk.Widget,
        *,
        orient: Literal["horizontal", "vertical"] = "vertical",
        command: Callable[..., Any] | str = "",
        bg: str = "",
        autohidden: bool = True,
        troughcolor: str | None = None,
        activebackground: str | None = None,
        width: int = 10,
        **kwargs: Any,
    ) -> None:
        self._orient = orient
        # command: empty string or no callable -> None, otherwise store callable
        self._command: Callable[..., Any] | None = command if callable(command) else None
        self._autohidden = autohidden
        self._explicit_bg = bool(bg)
        self._width = width

        # --- Colors ---
        self._slider_color = bg or getattr(theme, self._theme_key_bg)
        self._trough_color = (
            troughcolor if troughcolor is not None else getattr(theme, self._theme_key_trough)
        )
        self._active_color = (
            activebackground
            if activebackground is not None
            else getattr(theme, self._theme_key_active)
        )

        # --- Scroll state ---
        self._first = 0.0
        self._last = 1.0
        self._widget_size = (
            100  # Current scrollable direction pixels (vertical=height, horizontal=width)
        )
        self._slider_pos = 0  # Slider pixel offset in _widget_size
        self._slider_sz = self._MIN_SLIDER_PX  # Slider pixel size

        # --- Drag state ---
        self._dragging = False
        self._drag_offset = 0

        # --- Autohide cache ---
        self._saved_pack: dict[str, Any] = {}

        # ---------- Build Frame ----------
        frame_kw: dict[str, Any] = {
            "highlightthickness": 0,
            "bd": 0,
            "relief": "flat",
        }
        # Vertical: fixed width, horizontal: fixed height
        if orient == "vertical":
            frame_kw["width"] = width
        else:
            frame_kw["height"] = width
        super().__init__(parent, **frame_kw)
        # Fixed Frame size: avoid pack propagation (pack_propagate defaults True) letting Canvas's
        # default 1x1 requested size expand Frame, causing width/height to be ignored.
        self.pack_propagate(False)

        # --- Internal Canvas (drawing area) ---
        self._canvas = tk.Canvas(self, highlightthickness=0, bd=0)
        self._canvas.pack(fill=tk.BOTH, expand=True)

        # --- Events ---
        self._canvas.bind("<Configure>", self._on_configure)
        self._canvas.bind("<Button-1>", self._on_press)
        self._canvas.bind("<B1-Motion>", self._on_drag)
        self._canvas.bind("<ButtonRelease-1>", self._on_release)
        self._canvas.bind("<MouseWheel>", self._on_wheel)

        # Initial draw
        self._draw()

    # ==================================================================
    # Public API
    # ==================================================================

    def set(self, first: float | str, last: float | str) -> None:
        """Called by controlled widget on view change (e.g., via yscrollcommand).

        Updates slider position/size, does not forward command (consistent with
        standard :class:`tk.Scrollbar` protocol).
        """
        f_first = float(first)
        f_last = float(last)
        self._first = f_first
        self._last = f_last
        self._draw()
        if self._autohidden:
            self._apply_autohide()

    def get(self) -> tuple[float, float]:
        """Return current (first, last)."""
        return (self._first, self._last)

    # ==================================================================
    # config / cget (intercept custom options)
    # ==================================================================

    def config(self, **kwargs: Any) -> Any:  # type: ignore[override]
        scrollbar_opts: dict[str, Any] = {}
        for key in (
            "command",
            "bg",
            "troughcolor",
            "activebackground",
            "orient",
            "autohidden",
            "width",
        ):
            if key in kwargs:
                scrollbar_opts[key] = kwargs.pop(key)
        if scrollbar_opts:
            self._apply_config(scrollbar_opts)
        if kwargs:
            super().config(**kwargs)

    configure = config  # type: ignore[assignment]

    def cget(self, key: str) -> Any:
        custom: dict[str, Any] = {
            "command": self._command if self._command else "",
            "bg": self._slider_color,
            "troughcolor": self._trough_color,
            "activebackground": self._active_color,
            "orient": self._orient,
            "autohidden": self._autohidden,
            "width": str(self._width),
            "relief": "flat",
            "bd": "0",
            "highlightthickness": "0",
        }
        if key in custom:
            return custom[key]
        return super().cget(key)

    # ==================================================================
    # Drawing
    # ==================================================================

    def _on_configure(self, event: tk.Event) -> None:
        sz = event.height if self._orient == "vertical" else event.width
        self._widget_size = sz
        self._draw()

    def _draw(self) -> None:
        cw = self._canvas.winfo_width()
        ch = self._canvas.winfo_height()
        if cw < 2 or ch < 2:
            return

        size = ch if self._orient == "vertical" else cw
        self._widget_size = size
        visible = self._last - self._first
        slider_sz = max(self._MIN_SLIDER_PX, int(size * visible))
        # first may be slightly less than 0 (float boundary), clamp
        slider_pos = max(0, int(size * self._first))
        # Out-of-bounds protection
        if slider_pos + slider_sz > size:
            slider_pos = max(0, size - slider_sz)

        self._slider_pos = slider_pos
        self._slider_sz = slider_sz

        self._canvas.delete("all")

        if self._orient == "vertical":
            # Track
            self._canvas.create_rectangle(
                0,
                0,
                cw,
                ch,
                fill=self._trough_color,
                outline="",
            )
            # Slider
            self._canvas.create_rectangle(
                1,
                slider_pos,
                cw - 1,
                slider_pos + slider_sz,
                fill=self._slider_color,
                outline="",
                tags=("slider",),
            )
        else:
            self._canvas.create_rectangle(
                0,
                0,
                cw,
                ch,
                fill=self._trough_color,
                outline="",
            )
            self._canvas.create_rectangle(
                slider_pos,
                1,
                slider_pos + slider_sz,
                ch - 1,
                fill=self._slider_color,
                outline="",
                tags=("slider",),
            )

    # ==================================================================
    # Mouse events
    # ==================================================================

    def _get_pos(self, event: tk.Event) -> int:
        return event.y if self._orient == "vertical" else event.x

    def _on_press(self, event: tk.Event) -> None:
        pos = self._get_pos(event)
        if self._slider_pos <= pos <= self._slider_pos + self._slider_sz:
            # Start dragging
            self._dragging = True
            self._drag_offset = pos - self._slider_pos
        else:
            # Track click -> page scroll
            direction = -1 if pos < self._slider_pos else 1
            if self._command is not None:
                with contextlib.suppress(Exception):
                    self._command("scroll", direction, "pages")

    def _on_drag(self, event: tk.Event) -> None:
        if not self._dragging:
            return
        pos = self._get_pos(event)
        new_start = pos - self._drag_offset
        visible = self._last - self._first
        # Normalize to [0, 1-visible]
        new_first = new_start / max(1, self._widget_size)
        new_first = max(0.0, min(1.0 - max(visible, 0.01), new_first))
        if self._command is not None:
            with contextlib.suppress(Exception):
                self._command("moveto", str(new_first))

    def _on_release(self, event: tk.Event) -> None:
        self._dragging = False

    def _on_wheel(self, event: tk.Event) -> None:
        if self._command is not None:
            delta = -1 if event.delta > 0 else 1
            with contextlib.suppress(Exception):
                self._command("scroll", delta, "units")

    # ==================================================================
    # Auto hide
    # ==================================================================

    def _apply_autohide(self) -> None:
        try:
            is_mapped = bool(self.winfo_ismapped())
        except tk.TclError:
            return
        needs_scroll = not (self._first <= 0.0 and self._last >= 1.0)

        if needs_scroll and not is_mapped:
            if self._saved_pack:
                with contextlib.suppress(tk.TclError):
                    self.pack(**self._saved_pack)
        elif not needs_scroll and is_mapped:
            try:
                info = self.pack_info()
            except tk.TclError:
                return
            self._saved_pack = {k: v for k, v in info.items() if k != "in"}
            with contextlib.suppress(tk.TclError):
                self.pack_forget()

    # ==================================================================
    # Theme refresh
    # ==================================================================

    def _apply_theme(self) -> None:
        if not self._explicit_bg:
            self._slider_color = getattr(theme, self._theme_key_bg)
        self._trough_color = getattr(theme, self._theme_key_trough)
        self._active_color = getattr(theme, self._theme_key_active)
        self._draw()

    # ==================================================================
    # Internal option setting
    # ==================================================================

    def _apply_config(self, opts: dict[str, Any]) -> None:
        if "command" in opts:
            cmd = opts.pop("command")
            self._command = cmd if callable(cmd) else None
        if "bg" in opts:
            self._slider_color = opts.pop("bg")
            self._explicit_bg = True
        if "troughcolor" in opts:
            self._trough_color = opts.pop("troughcolor")
        if "activebackground" in opts:
            self._active_color = opts.pop("activebackground")
        if "orient" in opts:
            self._orient = opts.pop("orient")
        if "autohidden" in opts:
            self._autohidden = opts.pop("autohidden")
        if "width" in opts:
            w = opts.pop("width")
            self._width = w
            if self._orient == "vertical":
                super().config(width=w)
            else:
                super().config(height=w)
        self._draw()


__all__ = ["UScrollBar"]
