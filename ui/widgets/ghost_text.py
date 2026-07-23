"""``modules.Uui.widgets.ghost_text`` — Inline ghost-text completion overlay.

A borderless :class:`tk.Toplevel` that renders **one line** of suggestion text
in a gray-italic style, anchored to the cursor of a target ``tk.Text`` widget.
The host calls :meth:`show` / :meth:`update_text` / :meth:`hide`; the user
typically presses :kbd:`Tab` to accept (which inserts the text at the cursor).

Why a Toplevel instead of buffer tags:

* The ghost text is **never part of the buffer**, so saving the file just works
  without stripping logic.
* Cursor / scroll / theme changes never leave stale rendering behind.
* The label can be themed independently (italic, dim foreground) without
  fighting the syntax highlighter.

Usage::

    ghost = UGhostText(parent_window)
    ghost.show(text_widget, "len(self.items)")
    # ... later, in a key handler:
    if ghost.is_visible() and event.keysym == "Tab":
        ghost.accept()      # inserts at cursor and hides
        return "break"
    if ghost.is_visible() and event.keysym == "Escape":
        ghost.hide()
        return "break"
"""

from __future__ import annotations

import contextlib
import tkinter as tk
from typing import Any

from . import theme


def _italic_mono_font() -> tuple[Any, ...]:
    """Return ``theme.MONO_FONT`` augmented with the ``italic`` style.

    Tkinter only accepts italic via the family/size/slugs tuple shape — the
    raw ``MONO_FONT`` is a 2-element list (family + size), so we wrap it here.
    """

    base = theme.MONO_FONT
    return (base[0], base[1], "italic")


class UGhostText(tk.Toplevel):
    """Inline ghost-text overlay anchored to a ``tk.Text`` cursor."""

    def __init__(self, parent: tk.Misc) -> None:
        super().__init__(parent)
        self.withdraw()
        self.overrideredirect(True)
        with contextlib.suppress(tk.TclError):
            self.attributes("-topmost", True)
        self.configure(bg=theme.BG_BASE)

        self._text_widget: tk.Text | None = None
        self._text: str = ""
        self._font = _italic_mono_font()

        self._label = tk.Label(
            self,
            text="",
            font=self._font,
            fg=theme.FG_DIM,
            bg=theme.BG_BASE,
            padx=0,
            pady=0,
            anchor="w",
            justify="left",
        )
        self._label.pack()

        # Theme reactivity — re-apply colours when the theme switches.
        theme.on_change(lambda _name: self._apply_theme())

    # ---- Public API -------------------------------------------------------

    def show(self, text_widget: tk.Text, text: str) -> bool:
        """Show *text* as ghost text anchored to *text_widget*'s cursor.

        Returns ``True`` if the overlay was actually shown, ``False`` if the
        input was empty or the widget could not be positioned.
        """

        if text_widget is None or not text:
            self.hide()
            return False
        self._text_widget = text_widget
        self._text = text
        self._label.config(text=text)
        if not self._update_position():
            self.hide()
            return False
        try:
            self.deiconify()
        except tk.TclError:
            return False
        return True

    def update_text(self, text: str) -> bool:
        """Replace the displayed suggestion in place (no repositioning)."""

        if not text or self._text_widget is None:
            return False
        self._text = text
        self._label.config(text=text)
        return True

    def hide(self) -> None:
        """Hide the overlay and forget the current suggestion."""

        self._text = ""
        self._text_widget = None
        with contextlib.suppress(tk.TclError):
            self.withdraw()

    def accept(self) -> bool:
        """Insert the suggestion at the cursor and hide. Returns success."""

        if not self.is_visible() or self._text_widget is None or not self._text:
            return False
        try:
            self._text_widget.insert(tk.INSERT, self._text)
        except tk.TclError:
            self.hide()
            return False
        self.hide()
        return True

    def is_visible(self) -> bool:
        """Return True if the overlay is currently mapped to the screen."""

        try:
            return bool(self.winfo_ismapped())
        except tk.TclError:
            return False

    def text(self) -> str:
        """Return the currently displayed suggestion (empty if hidden)."""

        return self._text

    def target_widget(self) -> tk.Text | None:
        """Return the widget the overlay is currently anchored to."""

        return self._text_widget

    def set_font(self, font) -> None:
        """Override the label font (defaults to italic MONO_FONT)."""

        self._font = font
        self._label.config(font=font)

    # ---- Internal ---------------------------------------------------------

    def _update_position(self) -> bool:
        """Position the overlay at the INSERT cursor of the target widget."""

        target = self._text_widget
        if target is None:
            return False
        try:
            bbox = target.bbox(tk.INSERT)
        except tk.TclError:
            return False
        if not bbox:
            self.withdraw()
            return False
        x, y, w, _ = bbox
        try:
            target.update_idletasks()
            abs_x = target.winfo_rootx() + x + w
            abs_y = target.winfo_rooty() + y
            self.geometry(f"+{abs_x}+{abs_y}")
        except tk.TclError:
            return False
        return True

    def _apply_theme(self) -> None:
        """React to theme changes by refreshing the label colours."""

        try:
            self.configure(bg=theme.BG_BASE)
            self._font = _italic_mono_font()
            self._label.config(
                font=self._font,
                fg=theme.FG_DIM,
                bg=theme.BG_BASE,
            )
        except tk.TclError:
            pass


__all__ = ["UGhostText"]
