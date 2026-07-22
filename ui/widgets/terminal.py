"""``UTerminal`` — interactive terminal widget built on top of :class:`UText`.

The widget extends ``UText`` with:

* Color tags for stdout (default fg), stderr (red), input echo (muted) and
  status banners (muted / italic-ish separator).
* A movable ``input_end`` mark that partitions the buffer into the
  read-only "history" (process output + previous lines) and the editable
  "input line" where the user is currently typing.
* Key bindings that let the user type and submit (``<Return>``), navigate
  within the current line (``<Home>``, arrow keys, ``<BackSpace>``), and
  prevent them from deleting into the locked history region.
* ``submit_callback`` hook fired from the main thread whenever the user
  presses ``<Return>`` in the input area; the payload is the typed line
  without the trailing newline.

Upper layers (the editor) call :meth:`append_output` from background threads;
the widget marshals those calls onto the Tk main thread via ``after(0, ...)``
to keep Tkinter's single-thread invariant.
"""

from __future__ import annotations

import contextlib
import tkinter as tk
from collections.abc import Callable
from typing import Any, Literal

from . import theme
from .ansi import AnsiStyle, parse_ansi, style_key
from .text import UText

StreamName = Literal["stdout", "stderr", "system", "input"]


class UTerminal(UText):
    """A Text widget with terminal-style editable input area."""

    _INPUT_MARK = "input_end"
    _TAG_STDOUT = "term.stdout"
    _TAG_STDERR = "term.stderr"
    _TAG_SYSTEM = "term.system"
    _TAG_INPUT = "term.input"

    def __init__(
        self,
        parent,
        *,
        width: int = 80,
        height: int = 10,
        font=None,
        submit_callback: Callable[[str], None] | None = None,
        on_active_change: Callable[[bool], None] | None = None,
        **kwargs,
    ):
        super().__init__(parent, width=width, height=height, wrap="word", font=font, **kwargs)
        self._submit_callback = submit_callback
        self._on_active_change = on_active_change
        self._active = False
        self._ansi_tag_cache: set[str] = set()

        self._configure_tags()
        self._install_input_protection()

    # ------------------------------------------------------------------
    # Tag / theme setup
    # ------------------------------------------------------------------

    def _configure_tags(self) -> None:
        text = self._text
        text.tag_configure(self._TAG_STDOUT, foreground=theme.FG_PRIMARY)
        text.tag_configure(self._TAG_STDERR, foreground=theme.RED)
        text.tag_configure(self._TAG_SYSTEM, foreground=theme.FG_SECONDARY)
        text.tag_configure(self._TAG_INPUT, foreground=theme.FG_PRIMARY)

    # ------------------------------------------------------------------
    # Input-protection bindings
    # ------------------------------------------------------------------

    def _install_input_protection(self) -> None:
        text = self._text
        text.mark_set(self._INPUT_MARK, "end-1c")
        # LEFT gravity: as the user types at the cursor, the mark stays
        # anchored at the *start* of the current input line, so
        # ``get(mark, cursor)`` keeps yielding the full typed text. RIGHT
        # gravity would let the mark drift forward with every keystroke and
        # eventually reach the cursor, making the captured input look empty.
        text.mark_gravity(self._INPUT_MARK, tk.LEFT)
        text.config(undo=False)

        text.bind("<Return>", self._on_return, add="+")
        text.bind("<KP_Enter>", self._on_return, add="+")
        text.bind("<<Paste>>", self._on_paste, add="+")
        text.bind("<Button-1>", self._on_click, add="+")
        text.bind("<Key>", self._on_key, add="+")

    def _input_start_index(self) -> str:
        return self._INPUT_MARK

    def _clamp_insert_index(self) -> None:
        """If the cursor has wandered into the locked region, snap it back."""

        try:
            cur = self._text.index(tk.INSERT)
            mark = self._text.index(self._INPUT_MARK)
        except tk.TclError:
            return
        try:
            before = bool(self._text.compare(cur, "<", mark))
        except tk.TclError:
            return
        if before:
            self._text.mark_set(tk.INSERT, mark)
            self._text.see(tk.INSERT)

    def _on_key(self, event) -> str | None:
        if not self._active:
            # When the terminal is not driving an active session, behave like
            # a read-only Text: still allow copy / select-all / navigation.
            keysym = event.keysym
            if keysym in (
                "Left",
                "Right",
                "Up",
                "Down",
                "Home",
                "End",
                "Prior",
                "Next",
                "Shift_L",
                "Shift_R",
                "Control_L",
                "Control_R",
                "Alt_L",
                "Alt_R",
            ):
                return None
            if event.state & 0x4 or event.state & 0x1:
                # Allow Ctrl/Shift + key combos (e.g. Ctrl+C, Ctrl+A) to pass.
                return None
            if keysym.startswith("F") and keysym[1:].isdigit():
                return None
            return "break"

        keysym = event.keysym
        mark = self._input_start_index()

        if keysym in ("BackSpace", "Delete") and event.keysym == "BackSpace":
            with contextlib.suppress(tk.TclError):
                if self._text.compare(tk.INSERT, "<=", mark):
                    return "break"

        if keysym in ("Home",):
            with contextlib.suppress(tk.TclError):
                self._text.mark_set(tk.INSERT, mark)
            return "break"

        # After every keystroke, snap the cursor back if it crossed the mark.
        self.after_idle(self._clamp_insert_index)
        return None

    def _on_return(self, _event=None) -> str:
        if not self._active or self._submit_callback is None:
            return "break"
        line = ""
        with contextlib.suppress(tk.TclError):
            line = self._text.get(self._input_start_index(), "end-1c")
        # Echo the submitted line and prepare a fresh input line.
        self._text.insert("end", "\n")
        self._text.mark_set(self._INPUT_MARK, "end-1c")
        self._text.see("end")
        # Dispatch on the next idle tick to avoid re-entrancy inside bindings.
        cb = self._submit_callback
        self.after_idle(lambda: cb(line))
        return "break"

    def _on_paste(self, _event=None) -> str:
        # Strip newlines from clipboard so multi-line paste doesn't smuggle
        # extra ``<Return>`` events past our submit binding.
        try:
            clip = self._text.clipboard_get()
        except tk.TclError:
            return "break"
        cleaned = clip.replace("\r\n", "\n").replace("\n", " ")
        if not self._active:
            return "break"
        self._text.insert(tk.INSERT, cleaned)
        return "break"

    def _on_click(self, _event=None) -> None:
        if not self._active:
            # Stay read-only: snap the cursor back if the user clicks above.
            self._clamp_insert_index()
            return
        self._clamp_insert_index()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_active(self, active: bool) -> None:
        """Enable or disable the input area.

        When ``active`` is True, the user can type and submit. When False, the
        widget behaves like a read-only log viewer.
        """

        if active == self._active:
            return
        self._active = active
        if active:
            # Place the input mark at the very end so the user starts fresh.
            self._text.mark_set(self._INPUT_MARK, "end-1c")
            self._text.mark_gravity(self._INPUT_MARK, tk.LEFT)
        if self._on_active_change is not None:
            self._on_active_change(active)

    def is_active(self) -> bool:
        return self._active

    def focus_input(self) -> None:
        """Move keyboard focus to the input area and snap the cursor to its end."""

        with contextlib.suppress(tk.TclError):
            self._text.focus_set()
            self._text.mark_set(tk.INSERT, "end-1c")
            self._text.see("end")

    def clear(self) -> None:
        """Wipe the buffer and reset the input marker."""

        super().clear()
        self._text.mark_set(self._INPUT_MARK, "1.0")
        self._text.mark_gravity(self._INPUT_MARK, tk.LEFT)

    def append_output(self, stream: StreamName, text: str) -> None:
        """Append ``text`` to the buffer, tagged by ``stream``.

        Safe to call from any thread; marshals to the Tk main thread via
        ``after(0, ...)``. Newlines in ``text`` are preserved verbatim so the
        caller is free to pass full lines (with or without a trailing ``\n``).
        """
        if not text:
            return
        if not self._text.winfo_exists():
            return
        # Tk widgets can only be touched from their own thread. ``after(0, ...)``
        # is technically thread-safe in Tkinter but in practice calling it from
        # a non-main thread on Windows can wedge the queue. To stay robust we
        # detect the calling thread: when it's the main Tk thread we run
        # inline; otherwise we marshal via ``after``.
        import threading as _threading

        if _threading.current_thread() is _threading.main_thread():
            self._append_output_main(stream, text)
        else:
            self.after(0, self._append_output_main, stream, text)

    def _append_output_main(self, stream: StreamName, text: str) -> None:
        try:
            base_tag = {
                "stdout": self._TAG_STDOUT,
                "stderr": self._TAG_STDERR,
                "system": self._TAG_SYSTEM,
                "input": self._TAG_INPUT,
            }.get(stream, self._TAG_STDOUT)

            # Drop whatever the user was typing and stash it; we'll restore
            # it after inserting so the input area is preserved.
            input_mark = self._input_start_index()
            pending = ""
            if self._active:
                with contextlib.suppress(tk.TclError):
                    pending = self._text.get(input_mark, "end-1c")
                self._text.delete(input_mark, "end-1c")

            self._insert_with_ansi(text, base_tag)
            self._text.mark_set(self._INPUT_MARK, "end-1c")
            self._text.mark_gravity(self._INPUT_MARK, tk.LEFT)

            if self._active and pending:
                self._text.insert("end", pending, (self._TAG_INPUT,))

            self._text.see("end")
        except tk.TclError:
            # Widget was destroyed mid-flight; nothing meaningful to do.
            pass

    def _insert_with_ansi(self, text: str, base_tag: str) -> None:
        """Insert ``text`` honouring embedded ANSI colour codes.

        Splits ``text`` into ``(style, chunk)`` segments via
        :func:`parse_ansi`, creates per-style Tk tags on demand (keyed by
        ``style_key`` so identical styles share the same tag), and
        inserts each chunk with its corresponding tag union. If ``text``
        contains no ANSI codes this falls back to a single tagged insert.
        """
        segments = parse_ansi(text)
        if len(segments) == 1 and not self._has_any_ansi_style(segments[0].style):
            self._text.insert("end", text, (base_tag,))
            return

        for seg in segments:
            if not seg.text:
                continue
            tag = self._tag_for_style(base_tag, seg.style)
            self._text.insert("end", seg.text, (tag,))

    @staticmethod
    def _has_any_ansi_style(style: AnsiStyle) -> bool:
        return bool(
            style.fg
            or style.bg
            or style.bold
            or style.dim
            or style.italic
            or style.underline
            or style.inverse
        )

    def _tag_for_style(self, base_tag: str, style: AnsiStyle) -> str:
        """Return (and lazily configure) the Tk tag for ``style`` under ``base_tag``."""

        key = style_key(style)
        tag = f"{base_tag}::{key}"
        if tag in self._ansi_tag_cache:
            return tag

        font = theme.MONO_FONT
        if style.bold or style.italic:
            font = (theme.MONO_FONT[0], theme.MONO_FONT[1], "bold italic")  # type: ignore[assignment]
        elif style.bold:
            font = (theme.MONO_FONT[0], theme.MONO_FONT[1], "bold")  # type: ignore[assignment]
        elif style.italic:
            font = (theme.MONO_FONT[0], theme.MONO_FONT[1], "italic")  # type: ignore[assignment]

        opts: dict[str, Any] = {"font": font}

        # In Tk, tag priorities decide which tag's style "wins" when ranges
        # overlap. Per-style tags need higher priority than the base tag so
        # that ANSI overrides show through, but stay below INPUT so the
        # current line is always editable/visible.
        if base_tag == self._TAG_STDERR:
            opts["background"] = style.bg if style.bg else "#3a1f1f"
        elif style.bg:
            opts["background"] = style.bg

        if style.inverse:
            # Swap foreground and background of the current default.
            fg = style.fg or theme.FG_PRIMARY
            bg = style.bg or theme.BG_INPUT
            opts["foreground"] = bg
            opts["background"] = fg
        elif style.fg:
            opts["foreground"] = style.fg

        if style.underline:
            opts["underline"] = True

        self._text.tag_configure(tag, **opts)
        if base_tag == self._TAG_STDERR and not style.bg:
            # keep the dim red bg already on the base tag
            pass
        self._text.tag_raise(tag, base_tag)
        self._ansi_tag_cache.add(tag)
        return tag

    def _apply_theme(self) -> None:
        super()._apply_theme()
        with contextlib.suppress(Exception):
            self._configure_tags()
        # Drop ANSI tag cache — theme colours may have changed.
        self._ansi_tag_cache.clear()

    def get_pending_input(self) -> str:
        """Return the text currently typed by the user (between marker and cursor)."""

        with contextlib.suppress(tk.TclError):
            return self._text.get(self._input_start_index(), "end-1c")
        return ""
