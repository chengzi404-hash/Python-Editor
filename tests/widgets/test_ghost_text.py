"""Tests for :class:`ui.widgets.ghost_text.UGhostText`.

Headless Tk — no display required. We exercise show/hide/accept semantics and
the "buffer is unchanged until accept" invariant.
"""

from __future__ import annotations

import os
import sys

# Windows Python 3.14 can lose the Tcl/Tk library path after repeated Tk
# create/destroy cycles; pin it explicitly.
_tcl_root = os.path.join(os.path.dirname(sys.executable), "tcl")
os.environ.setdefault("TCL_LIBRARY", os.path.join(_tcl_root, "tcl8.6"))
os.environ.setdefault("TK_LIBRARY", os.path.join(_tcl_root, "tk8.6"))

import tkinter as tk  # noqa: E402

import pytest  # noqa: E402

from ui.widgets import UGhostText  # noqa: E402


@pytest.fixture(scope="session")
def session_root():
    r = tk.Tk()
    r.geometry("400x300+50+50")
    yield r
    r.destroy()


@pytest.fixture
def root(session_root):
    yield session_root


@pytest.fixture
def text_widget(root):
    w = tk.Text(root)
    w.pack(fill="both", expand=True)
    w.insert("1.0", "hello")
    w.mark_set(tk.INSERT, "1.5")
    root.update()
    yield w
    w.destroy()


class TestUGhostText:
    def test_initial_state_hidden(self, root, text_widget):
        ghost = UGhostText(root)
        assert ghost.is_visible() is False
        assert ghost.text() == ""

    def test_show_with_empty_text_stays_hidden(self, root, text_widget):
        ghost = UGhostText(root)
        assert ghost.show(text_widget, "") is False
        assert ghost.is_visible() is False

    def test_show_then_hide(self, root, text_widget):
        ghost = UGhostText(root)
        assert ghost.show(text_widget, " world") is True
        assert ghost.is_visible() is True
        assert ghost.text() == " world"
        ghost.hide()
        assert ghost.is_visible() is False
        assert ghost.text() == ""

    def test_accept_inserts_and_hides(self, root, text_widget):
        ghost = UGhostText(root)
        ghost.show(text_widget, " world")
        assert ghost.accept() is True
        # Buffer now contains the inserted text.
        assert text_widget.get("1.0", "end-1c") == "hello world"
        # Overlay is hidden after accept.
        assert ghost.is_visible() is False

    def test_accept_when_hidden_is_noop(self, root, text_widget):
        ghost = UGhostText(root)
        assert ghost.accept() is False
        assert text_widget.get("1.0", "end-1c") == "hello"

    def test_buffer_not_modified_before_accept(self, root, text_widget):
        """Ghost text is an overlay — buffer is unchanged until Tab/accept."""

        ghost = UGhostText(root)
        ghost.show(text_widget, "XYZ")
        # No buffer mutation should have occurred.
        assert text_widget.get("1.0", "end-1c") == "hello"
        # The actual on-disk buffer text (if any) is unchanged too — this is the
        # core invariant: ghost text is never persisted.
        ghost.hide()
        assert text_widget.get("1.0", "end-1c") == "hello"

    def test_update_text_replaces_content(self, root, text_widget):
        ghost = UGhostText(root)
        ghost.show(text_widget, "abc")
        ghost.update_text("xyz")
        assert ghost.text() == "xyz"

    def test_show_returns_false_if_cursor_not_visible(self, root, text_widget):
        """If the cursor is hidden (e.g. scrolled off-screen), show() refuses."""

        # Hide the cursor by setting it past the visible area: we can simulate
        # by destroying the widget to force a Tcl error inside bbox().
        text_widget.destroy()
        ghost = UGhostText(root)
        # show() must not crash and must return False on TclError.
        assert ghost.show(text_widget, "x") is False

    def test_hide_is_idempotent(self, root, text_widget):
        ghost = UGhostText(root)
        ghost.hide()
        ghost.hide()  # no exception
        assert ghost.is_visible() is False
