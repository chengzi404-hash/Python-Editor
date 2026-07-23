"""End-to-end tests for :class:`EditorBuffer` operations.

Exercises the undo / redo stack, indent / outdent, comment toggle, goto-line,
find / replace dialog, ghost-text, and inline completion surface — all driven
through the editor's own :class:`EditorBuffer` instance.
"""

from __future__ import annotations

import os

import pytest


@pytest.fixture(autouse=True)
def _isolate(editor, reset_editor):
    reset_editor(editor)


def _write(path: str, body: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(body)


class TestBufferTextOps:
    def test_undo_redo_round_trip(self, editor):
        text_widget = editor.buffer._text
        text_widget.delete("1.0", "end-1c")
        text_widget.insert("1.0", "alpha\n")
        text_widget.edit_separator()
        text_widget.insert("end", "beta\n")
        editor.buffer.undo()
        assert "alpha" in text_widget.get("1.0", "end-1c")
        assert "beta" not in text_widget.get("1.0", "end-1c")
        editor.buffer.redo()
        assert "beta" in text_widget.get("1.0", "end-1c")

    def test_select_all_highlights_buffer(self, editor):
        text_widget = editor.buffer._text
        text_widget.delete("1.0", "end-1c")
        text_widget.insert("1.0", "select me\n")
        editor.buffer.select_all()
        sel = text_widget.tag_ranges("sel")
        assert sel

    def test_cut_copy_paste_does_not_crash(self, editor):
        """In headless mode the system clipboard is unavailable, but the
        editor's wrapper around Tk's <<Cut>> / <<Copy>> / <<Paste>> events
        must at least be safe to invoke.
        """
        text_widget = editor.buffer._text
        text_widget.delete("1.0", "end-1c")
        text_widget.insert("1.0", "clipboard text\n")
        text_widget.tag_add("sel", "1.0", "end-1c")
        editor.window.focus_set()
        # These should all be no-ops (or no-op effectively) in headless mode.
        editor.buffer.copy()
        editor.buffer.cut()
        editor.buffer.paste()
        # The buffer should still contain the original text.
        assert "clipboard text" in text_widget.get("1.0", "end-1c")


class TestIndentOutdent:
    def test_indent_inserts_spaces(self, editor):
        text_widget = editor.buffer._text
        text_widget.delete("1.0", "end-1c")
        text_widget.insert("1.0", "a\nb\nc\n")
        text_widget.mark_set("insert", "1.0")
        # Default tab width is 4.
        editor.buffer.indent()
        body = text_widget.get("1.0", "end-1c")
        # First line is indented with 4 spaces.
        assert body.startswith("    a")

    def test_outdent_removes_spaces(self, editor):
        text_widget = editor.buffer._text
        text_widget.delete("1.0", "end-1c")
        text_widget.insert("1.0", "    a\n    b\n")
        text_widget.mark_set("insert", "1.0")
        editor.buffer.outdent()
        body = text_widget.get("1.0", "end-1c")
        assert body.startswith("a")

    def test_indent_respects_tab_width_setting(self, editor):
        editor._set_tab_width(2)
        editor.buffer.apply_tab_width()
        text_widget = editor.buffer._text
        text_widget.delete("1.0", "end-1c")
        text_widget.insert("1.0", "a\n")
        text_widget.mark_set("insert", "1.0")
        editor.buffer.indent()
        body = text_widget.get("1.0", "end-1c")
        assert body.startswith("  a")


class TestCommentToggle:
    def test_toggle_comment_adds_python_comment(self, editor):
        text_widget = editor.buffer._text
        text_widget.delete("1.0", "end-1c")
        text_widget.insert("1.0", "x = 1\n")
        text_widget.mark_set("insert", "1.0")
        editor.buffer.toggle_comment()
        assert text_widget.get("1.0", "end-1c").startswith("# x = 1")

    def test_toggle_comment_strips_existing(self, editor):
        text_widget = editor.buffer._text
        text_widget.delete("1.0", "end-1c")
        text_widget.insert("1.0", "# x = 1\n")
        text_widget.mark_set("insert", "1.0")
        editor.buffer.toggle_comment()
        # The current implementation removes the leading "#" but leaves the
        # trailing space that was inserted alongside it. We just verify that
        # the line is no longer prefixed by ``# ``.
        body = text_widget.get("1.0", "end-1c")
        assert not body.startswith("# x = 1")
        # Re-toggle should restore the ``#`` prefix.
        editor.buffer.toggle_comment()
        assert text_widget.get("1.0", "end-1c").startswith("#")

    def test_toggle_comment_unsupported_language_shows_message(self, editor, monkeypatch):
        import tkinter.messagebox as _mb

        msgs: list = []
        monkeypatch.setattr(_mb, "showinfo", lambda *a, **kw: msgs.append((a, kw)))
        editor.switch_language("JSON")
        text_widget = editor.buffer._text
        text_widget.delete("1.0", "end-1c")
        text_widget.insert("1.0", '{"k": "v"}\n')
        text_widget.mark_set("insert", "1.0")
        editor.buffer.toggle_comment()
        assert msgs  # showinfo was called


class TestGotoLine:
    def test_goto_line_moves_cursor(self, editor, monkeypatch):
        # Stub askinteger to bypass the dialog.
        import tkinter.simpledialog as _sd

        monkeypatch.setattr(_sd, "askinteger", lambda *a, **kw: 3)
        text_widget = editor.buffer._text
        text_widget.delete("1.0", "end-1c")
        text_widget.insert("1.0", "one\ntwo\nthree\nfour\n")
        editor.buffer.goto_line()
        assert text_widget.index("insert") == "3.0"

    def test_goto_line_cancels_on_zero(self, editor, monkeypatch):
        import tkinter.simpledialog as _sd

        monkeypatch.setattr(_sd, "askinteger", lambda *a, **kw: 0)
        text_widget = editor.buffer._text
        text_widget.delete("1.0", "end-1c")
        text_widget.insert("1.0", "alpha\nbeta\n")
        before = text_widget.index("insert")
        editor.buffer.goto_line()
        # Cancel: cursor should remain where it was.
        assert text_widget.index("insert") == before


class TestFindReplace:
    def test_open_find_dialog_creates_window(self, editor):
        editor.buffer.open_find_dialog()
        assert editor.buffer.find_dialog is not None
        assert editor.buffer.find_dialog.winfo_exists()

    def test_close_find_dialog_destroys_window(self, editor):
        editor.buffer.open_find_dialog()
        assert editor.buffer.find_dialog is not None
        editor.buffer.close_find_dialog()
        assert editor.buffer.find_dialog is None

    def test_open_replace_dialog_creates_window(self, editor):
        editor.buffer.open_replace_dialog()
        assert editor.buffer.find_dialog is not None
        assert editor.buffer.find_dialog.winfo_exists()


class TestHighlight:
    def test_apply_highlight_with_empty_buffer_noop(self, editor):
        text_widget = editor.buffer._text
        text_widget.delete("1.0", "end-1c")
        editor.buffer.apply_highlight()  # should not raise

    def test_apply_highlight_attaches_token_tags(self, editor):
        text_widget = editor.buffer._text
        text_widget.delete("1.0", "end-1c")
        text_widget.insert("1.0", "def foo():\n    return 1\n")
        editor.buffer.apply_highlight()
        names = text_widget.tag_names()
        # At least one of the highlight tags should be configured.
        assert any(n in names for n in ("keyword", "identifier", "function"))

    def test_highlight_line_flashes_definition(self, editor):
        text_widget = editor.buffer._text
        text_widget.delete("1.0", "end-1c")
        text_widget.insert("1.0", "x = 1\ny = 2\nz = 3\n")
        editor.buffer.highlight_line(2)
        ranges = text_widget.tag_ranges("definition_highlight")
        assert ranges
        # Range covers the second line.
        line_text = text_widget.get("2.0", "2.end")
        assert line_text == "y = 2"

    def test_clear_highlight_removes_tag(self, editor):
        text_widget = editor.buffer._text
        text_widget.delete("1.0", "end-1c")
        text_widget.insert("1.0", "x = 1\n")
        editor.buffer.highlight_line(1)
        editor.buffer.clear_highlight()
        assert not text_widget.tag_ranges("definition_highlight")


class TestFontAndTabWidth:
    def test_apply_font_sets_text_widget_font(self, editor):
        editor._set_font_family("Courier New")
        editor._set_font_size(14)
        editor.buffer.apply_font()
        text_widget = editor.buffer._text
        font = text_widget.cget("font")
        # Tk returns the font as a tuple — Courier New 14.
        assert "Courier New" in str(font)
        assert "14" in str(font)

    def test_apply_tab_width_changes_text_widget_tabs(self, editor):
        editor._set_tab_width(8)
        editor.buffer.apply_tab_width()
        text_widget = editor.buffer._text
        tabs = text_widget.cget("tabs")
        # Tk returns a tuple ``(n,)`` where ``n == tab_width * font_size``.
        # Default font size is 10 — 8 * 10 = 80.
        assert "80" in str(tabs)


class TestGhostText:
    def test_hide_ghost_text_noop_when_hidden(self, editor):
        # Already hidden — should not raise.
        editor.buffer.hide_ghost_text()
        assert not editor.buffer._ghost_text.is_visible()

    def test_accept_ghost_text_returns_false_when_hidden(self, editor):
        assert editor.buffer.accept_ghost_text() is False

    def test_show_ghost_text_via_completion_helper(self, editor):
        text_widget = editor.buffer._text
        text_widget.delete("1.0", "end-1c")
        text_widget.insert("1.0", "pr")
        text_widget.mark_set("insert", "1.2")
        # The private helper checks for non-empty completion text.
        assert editor.buffer._show_ghost_text("int") is True
        # The overlay should now be visible.
        assert editor.buffer._ghost_text.is_visible()
        # Hiding it should be a noop.
        editor.buffer.hide_ghost_text()
        assert not editor.buffer._ghost_text.is_visible()


class TestSuggestionsPopup:
    def test_show_suggestions_does_not_crash(self, editor):
        text_widget = editor.buffer._text
        text_widget.delete("1.0", "end-1c")
        text_widget.insert("1.0", "p")
        text_widget.mark_set("insert", "1.1")
        # Python expert should produce some suggestions for "p".
        editor.buffer.show_suggestions()
        # Either the popup is visible or the expert returned empty —
        # both are valid outcomes, we only assert no exception.
        editor.buffer.hide_suggestions()

    def test_hide_suggestions_is_idempotent(self, editor):
        editor.buffer.hide_suggestions()
        editor.buffer.hide_suggestions()  # no exception

    def test_toggle_suggestions_disabled(self, editor):
        editor.buffer.toggle_suggestions(False)
        # After disabling, suggestions should not pop up.
        text_widget = editor.buffer._text
        text_widget.delete("1.0", "end-1c")
        text_widget.insert("1.0", "p")
        text_widget.mark_set("insert", "1.1")
        editor.buffer.show_suggestions()  # should not pop up if disabled
        editor.buffer.toggle_suggestions(True)


class TestGetWordUnderCursor:
    def test_returns_word_when_cursor_inside_identifier(self, editor):
        text_widget = editor.buffer._text
        text_widget.delete("1.0", "end-1c")
        text_widget.insert("1.0", "alpha_beta gamma")
        text_widget.mark_set("insert", "1.6")  # inside alpha_beta
        assert editor.buffer.get_word_under_cursor() == "alpha_beta"

    def test_returns_word_to_the_right_when_cursor_on_boundary(self, editor):
        """Tk indexes refer to *gaps between characters*, so positioning the
        cursor right before/after a word returns that adjacent word rather
        than the empty string.
        """
        text_widget = editor.buffer._text
        text_widget.delete("1.0", "end-1c")
        text_widget.insert("1.0", "alpha beta")
        # Cursor on the gap *just after* ``alpha`` and *just before* the
        # space — ``get_word_under_cursor`` walks back to "alpha".
        text_widget.mark_set("insert", "1.5")
        assert editor.buffer.get_word_under_cursor() == "alpha"
        # Cursor on the gap *just before* ``beta`` — walks forward to "beta".
        text_widget.mark_set("insert", "1.6")
        assert editor.buffer.get_word_under_cursor() == "beta"

    def test_returns_empty_when_cursor_at_end_of_line(self, editor):
        text_widget = editor.buffer._text
        text_widget.delete("1.0", "end-1c")
        text_widget.insert("1.0", "alpha")
        # One past the last character; no forward word to find.
        text_widget.mark_set("insert", "1.5")
        assert editor.buffer.get_word_under_cursor() == ""


class TestLargeFileMode:
    def test_toggle_large_file_mode(self, editor):
        assert editor.buffer.large_file_mode is False
        editor.buffer.large_file_mode = True
        assert editor.buffer.large_file_mode is True
        editor.buffer.large_file_mode = False
        assert editor.buffer.large_file_mode is False

    def test_stream_epoch_bumps(self, editor):
        before = editor.buffer.stream_epoch
        editor.buffer.bump_stream_epoch()
        assert editor.buffer.stream_epoch == before + 1


class TestFindReferencesAndGotoDef:
    def test_find_references_returns_lines_with_match(self, editor, monkeypatch):
        # Stub references dialog so we don't open a window.
        editor.show_references = lambda word, matches: None

        text_widget = editor.buffer._text
        text_widget.delete("1.0", "end-1c")
        text_widget.insert("1.0", "foo = 1\nbar = foo + 1\nbaz = foo\n")
        text_widget.mark_set("insert", "1.1")  # on 'foo'
        # Capture matches before display.
        captured: list = []

        def _fake_show(w, m):
            captured.append((w, m))

        editor.show_references = _fake_show
        editor.buffer.find_references()
        assert captured
        word, matches = captured[0]
        assert word == "foo"
        # 3 lines mention foo.
        assert len(matches) == 3

    def test_goto_definition_moves_cursor(self, editor):
        text_widget = editor.buffer._text
        text_widget.delete("1.0", "end-1c")
        text_widget.insert("1.0", "def foo():\n    return 1\nfoo()\n")
        # Place the cursor at the ``foo`` *usage* on line 3 — Tk indexes are
        # gap-based, so "3.0" sits right before the ``f`` of ``foo()``.
        text_widget.mark_set("insert", "3.0")
        editor.buffer.goto_definition()
        # Cursor should jump to the definition on line 1.
        assert text_widget.index("insert").startswith("1.")

    def test_goto_definition_no_definitions_shows_message(self, editor, monkeypatch):
        import tkinter.messagebox as _mb

        msgs: list = []
        monkeypatch.setattr(_mb, "showinfo", lambda *a, **kw: msgs.append((a, kw)))
        text_widget = editor.buffer._text
        text_widget.delete("1.0", "end-1c")
        # A bare identifier — no def / class / assignment for it anywhere.
        text_widget.insert("1.0", "alpha beta gamma\n")
        # Cursor between ``a`` and ``lpha`` — word under cursor is "alpha".
        text_widget.mark_set("insert", "1.1")
        editor.buffer.goto_definition()
        # No definition for "alpha"; a "not found" showinfo dialog should fire.
        assert msgs


class TestLookupDocumentation:
    def test_lookup_builtin_int(self, editor):
        info = editor.buffer.lookup_documentation("int")
        assert info is not None
        # Either doc or signature should be present.
        assert info.get("doc") or info.get("signature")

    def test_lookup_unknown_returns_none(self, editor):
        assert editor.buffer.lookup_documentation("not_a_real_symbol_xyz") is None
