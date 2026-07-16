"""``modules.Uui.widgets.line_number`` — Code line number bar based on :class:`tk.Canvas`.

Design Motivation
=================

Tk's built-in :class:`tk.Text` doesn't have line numbers; there are two common
approaches for drawing line numbers in the editor sidebar:

1. Use another :class:`tk.Text` as gutter, inserting line numbers as normal text -- simple
   to implement, but line height / font following, performance, and scroll sync all depend
   on :class:`tk.Text`'s existing logic, hard to fine-tune (e.g., changing line number color /
   highlighting current line / adjusting spacing);
2. Draw using :class:`tk.Canvas` ourselves -- finer control granularity, theme switching /
   line height / current line highlight all under our control, stable performance.

This module takes approach 2. Provides :class:`LineNumberCanvas` control, which :class:`UText`
attaches to the left side of the text widget when ``show_line_numbers=True``, and achieves
bidirectional sync via ``yscrollcommand`` and ``<<Modified>>`` events.

Protocol with :class:`UText`
-----------------------------

:class:`LineNumberCanvas` receives the observed :class:`tk.Text` at construction, then:

* Attaches its own :meth:`redraw` to text's ``yscrollcommand`` hook -- redraws whenever text scrolls;
* Listens to ``<<Modified>>`` event, clears modified flag after each text change and triggers redraw;
* Listens to ``<ButtonRelease-1>`` / ``<KeyRelease>`` -- these two event types don't change
  ``modified`` flag but affect current line / visible area;
* Listens to ``<Configure>`` -- recalculates line height and visible line number range when
  text width/height changes (e.g., switching languages / adjusting font size).

Line number width automatically reserves space based on current max line number digit count,
using "2 digits for every 1 extra digit" strategy (10 lines only needs 1 digit but still
draws 2 digits width) to avoid "adding 1 more line suddenly widens gutter, pushing cursor
left/right".

Theme
-----

Line number color uses ``theme.FG_TERTIARY``, current line number color uses ``theme.FG_PRIMARY``,
gutter background uses ``theme.BG_INPUT`` (consistent with text, visually looks like the same area).
On theme refresh, :meth:`_apply_theme` redraws once.
"""

from __future__ import annotations

import contextlib
import tkinter as tk

from . import theme


class LineNumberCanvas(tk.Frame):
    """Canvas-based code line number bar.

    Must receive an already created :class:`tk.Text` control, this control will automatically
    follow its scroll, text changes, and cursor position.

    Parameters
    ----------

    text
        The observed :class:`tk.Text` control (usually :class:`UText._text`).
    pad_x
        Horizontal inner margin between line number text and right separator line (pixels).
    min_width
        Minimum gutter width (pixels), prevents width from shrinking to 0 when file is empty.
    """

    # Digit count -> pixel width empirical value (estimated for Consolas 10pt);
    # Actual width is automatically adjusted by Canvas based on current font metrics,
    # this is just the lower bound protection.
    _CHARS_PER_LEVEL = 1

    def __init__(
        self,
        text: tk.Text,
        *,
        pad_x: int = 6,
        min_width: int = 28,
        **kwargs,
    ) -> None:
        bg = kwargs.pop("bg", theme.BG_INPUT)
        super().__init__(text.master, bg=bg, highlightthickness=0, bd=0, **kwargs)

        if not isinstance(text, tk.Text):
            raise TypeError(f"LineNumberCanvas requires a tk.Text, got {type(text).__name__}")
        self._text = text
        self._pad_x = pad_x
        self._min_width = min_width

        self._canvas = tk.Canvas(
            self,
            bg=theme.BG_INPUT,
            highlightthickness=0,
            bd=0,
        )
        self._canvas.pack(side=tk.LEFT, fill=tk.Y, expand=False)
        # Stretch Canvas to same height as text; real usable height is read via
        # winfo_height in _redraw, here just to prevent pack from shrinking.
        self._canvas.configure(height=1)

        # Debounce: <Configure> triggers frequently during window drag, using a flag + after
        # to merge multiple relayouts into one _redraw.
        self._redraw_pending = False

        # Cache: current max line number; only recalculate width when text line count changes,
        # avoiding re-layout on every redraw.
        self._last_total_lines = -1
        self._last_digit_count = -1

        # Remember text's original yscrollcommand, forward in our hook, so
        # caller's previously attached scrollbar won't be swallowed. Fallback to empty callback if not found.
        self._external_scroll_cb = text.cget("yscrollcommand") or ""
        self._text.configure(
            yscrollcommand=self._on_text_yview,
        )

        # --- Event subscription ---
        # <<Modified>> sets flag after set / delete / insert; we reset it immediately
        # after reading so Tk can set flag again on next change.
        self._text.bind("<<Modified>>", self._on_text_modified, add="+")
        self._text.bind("<KeyRelease>", self._on_cursor_change, add="+")
        self._text.bind("<ButtonRelease-1>", self._on_cursor_change, add="+")
        self._text.bind("<ButtonRelease-2>", self._on_cursor_change, add="+")
        self._text.bind("<Configure>", self._on_text_configure, add="+")

        # Mouse wheel: forward directly to text widget, allowing user to scroll
        # editor area even when mouse is on gutter.
        self._canvas.bind("<MouseWheel>", self._on_mousewheel, add="+")
        self._canvas.bind(
            "<Button-4>",
            lambda e: self._text.yview_scroll(-1, "units"),
            add="+",
        )
        self._canvas.bind(
            "<Button-5>",
            lambda e: self._text.yview_scroll(1, "units"),
            add="+",
        )

        # Draw after first layout completes -- at this point text has winfo_width / height.
        self.after_idle(self._redraw)

    # ==================================================================
    # Public API
    # ==================================================================

    def redraw(self) -> None:
        """Force one redraw of line numbers. Equivalent to internal :meth:`_redraw`,
        but placed in public API for external (e.g., UText after theme switch) explicit call.
        """

        self._redraw()

    # ==================================================================
    # Event callbacks
    # ==================================================================

    def _on_text_yview(self, *args) -> None:
        """Hook for text's yscrollcommand: drives both scrollbar + line number bar redraw."""

        # Forward to original yscrollcommand (e.g., UScrollBar in UText)
        if self._external_scroll_cb:
            try:
                # args is (first, last); Tk protocol is direct set(*args)
                if callable(self._external_scroll_cb):
                    self._external_scroll_cb(*args)
                else:
                    self._text.tk.call((self._external_scroll_cb, *args))
            except Exception:
                # Protocol-external callers shouldn't crash the whole UI due to line number bar, swallow exception.
                pass
        self._schedule_redraw()

    def _on_text_modified(self, _event: tk.Event) -> None:
        # Must reset flag immediately, otherwise Tk won't trigger again on next change.
        with contextlib.suppress(tk.TclError):
            self._text.edit_modified(False)
        self._schedule_redraw()

    def _on_cursor_change(self, _event: tk.Event) -> None:
        # Cursor movement doesn't always affect <<Modified>>, trigger redraw separately to update
        # current line highlight.
        self._schedule_redraw()

    def _on_text_configure(self, _event: tk.Event) -> None:
        # Window / font size changes all cause line height changes, need to recalculate visible line number range.
        self._schedule_redraw()

    def _on_mousewheel(self, event: tk.Event) -> str | None:
        """Forward wheel event to text widget, behavior consistent with scrolling on text."""

        if not hasattr(event, "delta") or event.delta == 0:
            return None
        # Tk standard protocol: delta > 0 scrolls up. On Text, scrolling is "scroll -1 units"
        # meaning scroll up one line (content moves down); keep consistent here.
        delta = -1 if event.delta > 0 else 1
        try:
            self._text.yview_scroll(delta, "units")
        except tk.TclError:
            return None
        # "break" lets Tk stop continuing to bubble event to outer layers (e.g., PanedWindow's
        # wheel handler), otherwise there will be "scroll one line then scroll back" jitter.
        return "break"

    # ==================================================================
    # Redraw
    # ==================================================================

    def _schedule_redraw(self) -> None:
        if self._redraw_pending:
            return
        self._redraw_pending = True
        try:
            self.after_idle(self._flush_redraw)
        except tk.TclError:
            self._redraw_pending = False

    def _flush_redraw(self) -> None:
        self._redraw_pending = False
        self._redraw()

    def _redraw(self) -> None:
        with contextlib.suppress(tk.TclError):
            self._do_redraw()

    def _do_redraw(self) -> None:
        text = self._text
        canvas = self._canvas

        # Skip if text hasn't been laid out yet (winfo_* = 1), wait for idle to draw.
        text_h = text.winfo_height()
        text_w = text.winfo_width()
        if text_h <= 1 or text_w <= 1:
            return

        # Total lines (including trailing empty line; Tk's end is "next line 0 column")
        try:
            total_lines = int(text.index("end-1c").split(".")[0])
        except tk.TclError:
            return
        if total_lines < 1:
            total_lines = 1

        # Current line number
        try:
            cursor_line = int(text.index(tk.INSERT).split(".")[0])
        except tk.TclError:
            cursor_line = 1

        # 1. Adaptive width: decide gutter width by "max line number digit count",
        #    but give 2 digits width for every 1 extra digit (avoid gutter suddenly
        #    widening after adding 1 line, pushing cursor left/right by one space).
        if total_lines != self._last_total_lines:
            digits = len(str(total_lines))
            # "2 digits -> reserve 3 digits width" rule approximated with max(1, ceil(digits * 1.5)).
            self._last_digit_count = max(2, digits + (1 if digits >= 2 else 0))
            self._last_total_lines = total_lines

        digit_count = self._last_digit_count
        font = text.cget("font")
        try:
            char_w = font_metrics(font)[0]
        except Exception:
            char_w = 8
        target_width = max(
            self._min_width,
            int(digit_count * char_w + self._pad_x * 2 + 1),
        )
        # Stretch Canvas to target width, let separator line fall at right edge.
        if canvas.winfo_width() != target_width:
            canvas.configure(width=target_width)

        # 2. Visible line number range: use @0,0 / @0,H to get current screen visible index.
        try:
            top_idx = text.index("@0,0")
            bot_idx = text.index(f"@0,{text_h}")
        except tk.TclError:
            return
        top_line = int(top_idx.split(".")[0])
        bot_line = int(bot_idx.split(".")[0])
        # bot_idx may fall "after" the last line, show at least to total_lines.
        bot_line = max(bot_line, min(total_lines, top_line))

        # 3. Clear canvas, redraw
        canvas.delete("all")
        fg_normal = theme.FG_TERTIARY
        fg_cursor = theme.FG_PRIMARY
        bg = theme.BG_INPUT
        border = theme.BORDER
        canvas.configure(bg=bg)

        # Line height (pixels) - get from text's first line bbox.
        line_height = self._line_height(text)
        if line_height <= 0:
            line_height = max(14, int(font_metrics(font)[1]) + 2)

        # Current text's "first line Y offset" when scrolled (pixels, 0 means content top-aligned).
        self._y_of_line(text, top_line)

        width = target_width
        right = width - self._pad_x

        # Draw separator line (thin line between gutter and text)
        canvas.create_line(
            width - 1,
            0,
            width - 1,
            text_h,
            fill=border,
            width=1,
        )

        # Draw each line's line number
        for line_no in range(top_line, bot_line + 1):
            if line_no > total_lines:
                break
            dline = text.dlineinfo(f"{line_no}.0")
            if not dline:
                continue
            # dlineinfo returns (x, y, width, height, baseline)
            _, line_y, _, dh, _ = dline
            # dlineinfo gives text widget internal coordinates, adding text padx/pady
            # offsets gives the "y to draw on gutter canvas".
            # Gutter and text share same scroll, so text scrolling doesn't affect gutter's
            # visible position -- screen coordinates consistent, just use line_y directly.
            screen_y = line_y
            if screen_y + dh < 0 or screen_y > text_h:
                continue
            color = fg_cursor if line_no == cursor_line else fg_normal
            canvas.create_text(
                right,
                screen_y + dh / 2,
                text=str(line_no),
                anchor="e",
                fill=color,
                font=font,
            )

    @staticmethod
    def _line_height(text: tk.Text) -> int:
        bbox = text.dlineinfo("1.0")
        if not bbox:
            return 0
        return int(bbox[3])

    @staticmethod
    def _y_of_line(text: tk.Text, line_no: int) -> int:
        bbox = text.dlineinfo(f"{line_no}.0")
        if not bbox:
            return 0
        return int(bbox[1])

    # ==================================================================
    # Theme
    # ==================================================================

    def _apply_theme(self) -> None:
        """Theme switch callback: refresh canvas colors + trigger one redraw."""

        with contextlib.suppress(tk.TclError):
            self.configure(bg=theme.BG_INPUT)
        with contextlib.suppress(tk.TclError):
            self._canvas.configure(bg=theme.BG_INPUT)
        self._redraw()


def font_metrics(font) -> tuple:
    """Return approximate ``(char_pixel_width, line_pixel_height)``.

    Tk doesn't expose font metrics API (except ``measure`` for a specific string); here we use
    "0" as representative character to measure width, and ``tk.font.Font.metrics`` for height.
    The latter depends on optional ``tkinter.font``, which may not be available on some minimal
    Tk builds, we fallback to fixed estimation in exception branch.
    """

    char_w = 8
    line_h = 16
    try:
        # tk.font is available by default in Tk 8.6+, but we don't force dependency.
        from tkinter import font as tkfont

        if isinstance(font, str):
            fnt = tkfont.nametofont(font)
        elif isinstance(font, tuple):
            fnt = tkfont.Font(font=font)
        else:
            fnt = font
        char_w = max(4, int(fnt.measure("0")))
        line_h = max(10, int(fnt.metrics("linespace")))
    except Exception:
        # Fallback: assume 10pt monospace ≈ 6 x 13 pixels
        try:
            size = int(font[1]) if isinstance(font, tuple) and len(font) >= 2 else 10
        except Exception:
            size = 10
        char_w = max(4, int(size * 0.6))
        line_h = max(10, int(size * 1.4))
    return char_w, line_h


__all__ = ["LineNumberCanvas", "font_metrics"]
