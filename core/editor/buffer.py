"""Editor text-widget orchestration: highlight, suggestions, ghost text, edit ops.

The :class:`EditorBuffer` wraps the ``UText`` widget and owns:

* the highlighter / suggestion experts for the current language
* the suggestion popup (``UEditorSuggestion``) and ghost-text overlay
* highlight / suggestion / autosave debouncers
* key / cursor / focus event handlers bound to the text widget
* edit operations (undo, indent, comment, goto-line, ...)
* font / tab-width / line-highlight configuration

It does **not** know about documents or tabs — that responsibility lives in
:class:`core.editor.tabs.TabManager`.  Status updates, hook emission, and
settings retrieval are funnelled through a small :class:`BufferHost` Protocol
so this module stays independent of the giant ``CodeEditor`` class.
"""

from __future__ import annotations

import contextlib
import tkinter as tk
from typing import Any, Protocol

from core.editor.document import _Debouncer
from core.editor.find_dialog import FindDialog
from core.editor.helpers import (
    NAVIGATION_KEYS,
    find_symbol_definitions,
    pick_local_completion,
    strip_common_prefix,
)
from core.editor.lang_config import HIGHLIGHT_TOKENS, LANG_CONFIG
from core.language.highlighter import HighlightBlock, highlight_themes
from core.language.suggestion import SuggestionBlock
from core.plugins import HookEvents
from core.settings.i18n import t
from ui.widgets import UEditorSuggestion, UGhostText, theme
from ui.widgets.editor_suggestion import CompletionItem


class BufferHost(Protocol):
    """A minimal contract :class:`EditorBuffer` needs from its host editor."""

    window: tk.Tk
    settings: Any
    autosave_enabled: bool
    autosave_format: str
    autosave_delay_ms: int
    font_family: str
    font_size: int
    tab_width: int
    highlight_delay_ms: int
    definition_highlight_duration_ms: int
    suggest_delay_ms: int
    suggest_min_chars: int
    suggestions_enabled: bool
    highlighting_enabled: bool
    current_language: str
    current_partial_token_text: str
    suggestion_expert: Any
    highlighter: Any

    def get_active_id(self) -> str | None: ...
    def do_autosave(self, active_id: str) -> None: ...
    def switch_language(self, lang: str, *, from_doc_switch: bool = False) -> None: ...
    def refresh_status(self) -> None: ...
    def emit(self, hook: str, *args, **kwargs) -> None: ...
    def emit_selection_changed(self) -> None: ...
    def emit_cursor_moved(self) -> None: ...
    def emit_content_changed(self) -> None: ...
    def mark_dirty(self) -> None: ...
    def get_word_under_cursor(self, x: int | None = None, y: int | None = None) -> str: ...
    def show_references(self, word: str, matches: list[tuple[int, str]]) -> None: ...


class EditorBuffer:
    """Owns the editor text widget: highlight, suggestions, ghost-text, edits."""

    def __init__(self, host: BufferHost, text_widget: tk.Text) -> None:
        self._host = host
        self._text = text_widget
        self._editor_highlighter: Any = None
        self._suggestion_expert: Any = None
        self._suggestion_popup: UEditorSuggestion | None = None
        self._ghost_text = UGhostText(text_widget)
        self._find_dialog: tk.Toplevel | None = None
        self._find_dialog_impl: FindDialog | None = None
        self._find_query: str = ""
        self._find_last_index: str | None = None

        self._context_click_x: int | None = None
        self._context_click_y: int | None = None

        self._large_file_mode = False
        self._stream_epoch = 0

        self._highlight_debouncer = _Debouncer(host.window.after, host.window.after_cancel)
        self._suggest_debouncer = _Debouncer(host.window.after, host.window.after_cancel)
        self._autosave_debouncer = _Debouncer(host.window.after, host.window.after_cancel)
        self._ghost_text_debouncer = _Debouncer(host.window.after, host.window.after_cancel)
        self._ghost_text_epoch = 0
        self._highlight_after_id: str | None = None

        self._highlighted_line: int | None = None
        self._highlighted_line_color: str = theme.YELLOW

        # Last emitted values so we don't spam hooks on every keystroke.
        self._last_emit_code: str | None = None
        self._last_cursor: tuple[int, int] | None = None
        self._last_selection: str | None = None

        text_widget.config(undo=True)
        text_widget.bind("<KeyRelease>", self._on_key_release)
        text_widget.bind("<KeyPress>", self._on_key_press)
        text_widget.bind("<ButtonRelease-1>", self._on_click)
        text_widget.bind("<FocusIn>", self._on_focus_in)
        text_widget.bind("<FocusOut>", self._on_focus_out)
        text_widget.bind("<Button-3>", self._show_editor_context_menu)

    # ------------------------------------------------------------------
    # Public properties used by the host editor
    # ------------------------------------------------------------------

    @property
    def find_dialog(self) -> tk.Toplevel | None:
        return self._find_dialog

    @property
    def suggestion_expert(self) -> Any:
        return self._suggestion_expert

    @property
    def highlighter(self) -> Any:
        return self._editor_highlighter

    @property
    def large_file_mode(self) -> bool:
        return self._large_file_mode

    @large_file_mode.setter
    def large_file_mode(self, value: bool) -> None:
        self._large_file_mode = value

    @property
    def stream_epoch(self) -> int:
        return self._stream_epoch

    def bump_stream_epoch(self) -> None:
        self._stream_epoch += 1

    # ------------------------------------------------------------------
    # Language & content
    # ------------------------------------------------------------------

    def switch_language(self, lang: str, *, from_doc_switch: bool = False) -> None:
        self._host.highlighter = None  # type: ignore[attr-defined]
        if lang not in LANG_CONFIG:
            return
        config = LANG_CONFIG[lang]
        self._editor_highlighter = (
            config["highlighter_factory"]()
            if "highlighter_factory" in config
            else config["highlighter"]()
        )
        self._suggestion_expert = (
            config["suggestion_factory"]()
            if "suggestion_factory" in config
            else (config["suggestion"]() if callable(config["suggestion"]) else None)
        )
        self._host.suggestion_expert = self._suggestion_expert  # type: ignore[attr-defined]
        self._host.highlighter = self._editor_highlighter  # type: ignore[attr-defined]
        self._stream_epoch += 1
        self._text.config(state="normal")
        self._large_file_mode = False
        if not from_doc_switch:
            self._text.delete("1.0", tk.END)
            self._text.insert("1.0", config["sample"])
            self.apply_highlight()
        self._host.refresh_status()
        self._host.emit(HookEvents.EDITOR_LANGUAGE_CHANGED, lang)

    def set_active_content(self, content: str) -> None:
        """Replace the text-widget contents with ``content`` (for tab switches)."""
        self._text.config(state="normal")
        self._text.delete("1.0", tk.END)
        if content:
            self._text.insert("1.0", content)

    # ------------------------------------------------------------------
    # Highlighting
    # ------------------------------------------------------------------

    def apply_highlight(self) -> None:
        if self._large_file_mode or not self._host.highlighting_enabled:
            return
        code = self._text.get("1.0", "end-1c")
        if not code.strip():
            return
        block = HighlightBlock(code=code, tokens=None)
        result = self._editor_highlighter.highlight(block)
        if result.tokens is None:
            return

        hl_tokens = highlight_themes.tokens()
        if not hl_tokens:
            hl_tokens = HIGHLIGHT_TOKENS

        text = self._text

        highlight_line = self._highlighted_line
        highlight_color = self._highlighted_line_color

        for tag in text.tag_names():
            if tag != "definition_highlight":
                text.tag_delete(tag)

        for token_type, style in hl_tokens.items():
            text.tag_configure(token_type, **self._tag_style_kwargs(style))

        for token in result.tokens:
            start = self._index_from_pos(token.start)
            end = self._index_from_pos(token.end)
            tag = token.type if token.type in hl_tokens else "identifier"
            text.tag_add(tag, start, end)

        if highlight_line is not None:
            text.tag_config(
                "definition_highlight",
                background=highlight_color,
                foreground=theme.BG_BASE,
            )
            text.tag_add("definition_highlight", f"{highlight_line}.0", f"{highlight_line}.end")

    def highlight_line(self, line_no: int, color: str | None = None) -> None:
        """Highlight a specific line, then auto-clear after the configured duration."""
        if self._highlight_after_id is not None:
            self._host.window.after_cancel(self._highlight_after_id)
            self._highlight_after_id = None

        text = self._text
        self._highlighted_line = line_no
        self._highlighted_line_color = color if color is not None else theme.YELLOW
        text.tag_config(
            "definition_highlight",
            background=self._highlighted_line_color,
            foreground=theme.BG_BASE,
        )
        text.tag_remove("definition_highlight", "1.0", "end")
        text.tag_add("definition_highlight", f"{line_no}.0", f"{line_no}.end")

        if self._host.definition_highlight_duration_ms > 0:

            def _auto_clear() -> None:
                self._highlight_after_id = None
                self.clear_highlight()

            self._highlight_after_id = self._host.window.after(
                self._host.definition_highlight_duration_ms, _auto_clear
            )

    def clear_highlight(self) -> None:
        self._highlighted_line = None
        self._highlighted_line_color = theme.YELLOW
        self._text.tag_remove("definition_highlight", "1.0", "end")

    def refresh_tag_fonts(self) -> None:
        """Re-apply font attributes to every configured highlight tag."""
        text = self._text
        for tag in text.tag_names():
            if tag == "definition_highlight":
                continue
            style = self._current_tag_style(tag)
            if style is None:
                continue
            with contextlib.suppress(Exception):
                text.tag_configure(tag, **self._tag_style_kwargs(style))

    def apply_font(self) -> None:
        self._text.config(font=(self._host.font_family, self._host.font_size))
        self.refresh_tag_fonts()

    def apply_tab_width(self) -> None:
        self._text.config(tabs=(self._host.tab_width * self._host.font_size,))

    # ------------------------------------------------------------------
    # Schedule helpers (highlight / suggestion / autosave / inline)
    # ------------------------------------------------------------------

    def schedule_highlight(self) -> None:
        if not self._host.highlighting_enabled:
            self._highlight_debouncer.cancel()
            return
        self._highlight_debouncer.schedule(self._host.highlight_delay_ms, self.apply_highlight)

    def cancel_pending_highlight(self) -> None:
        self._highlight_debouncer.cancel()

    def schedule_suggestions(self) -> None:
        if not self._host.suggestions_enabled:
            self._suggest_debouncer.cancel()
            return
        self._suggest_debouncer.schedule(self._host.suggest_delay_ms, self._show_suggestions)

    def cancel_pending_suggestions(self) -> None:
        self._suggest_debouncer.cancel()

    def schedule_autosave(self) -> None:
        if not self._host.autosave_enabled:
            self._autosave_debouncer.cancel()
            return
        self._autosave_debouncer.schedule(self._host.autosave_delay_ms, self._on_autosave_due)

    def _on_autosave_due(self) -> None:
        if not self._host.autosave_enabled:
            return
        active_id = self._host.get_active_id()
        if not active_id:
            return
        self._host.do_autosave(active_id)

    def schedule_inline_completion(self, *, immediate: bool = False) -> None:
        delay_ms = (
            0
            if immediate
            else max(
                0, int(self._host.settings.global_settings.get("editor.suggestion_delay_ms", 200))
            )
        )
        self._ghost_text_epoch += 1
        epoch = self._ghost_text_epoch

        def _run() -> None:
            self._run_inline_completion(epoch)

        self._ghost_text_debouncer.schedule(delay_ms, _run)

    def cancel_pending_ghost(self) -> None:
        self._ghost_text_debouncer.cancel()

    # ------------------------------------------------------------------
    # Suggestions popup
    # ------------------------------------------------------------------

    def show_suggestions(self) -> None:
        self._show_suggestions()

    def _show_suggestions(self) -> None:
        if self._large_file_mode or not self._host.suggestions_enabled:
            return
        if self._suggestion_expert is None:
            return
        code = self._text.get("1.0", "end-1c")
        cursor = self._text.index(tk.INSERT)
        line, col = (int(p) for p in cursor.split("."))
        position = sum(len(line_text) + 1 for line_text in code.split("\n")[: line - 1]) + col
        block = SuggestionBlock(code=code, position=position)
        suggestions = self._suggestion_expert.suggest(block)

        if not suggestions:
            if self._suggestion_popup:
                self._suggestion_popup.hide()
            return

        max_suggestions = self._host.settings.global_settings.get("completion.max_suggestions", 20)
        max_visible = self._host.settings.global_settings.get("completion.max_visible", 8)
        items = [
            CompletionItem(label=s.label, priority=s.priority, kind=s.kind)
            for s in suggestions[:max_suggestions]
        ]
        if self._suggestion_popup and self._suggestion_popup.winfo_exists():
            self._suggestion_popup.set_items(items)
            self._suggestion_popup.show(attach_to=self._text, index=tk.INSERT)
        else:
            self._suggestion_popup = UEditorSuggestion(
                self._text,
                items=items,
                on_select=self._on_suggestion_select,
                max_visible=max_visible,
                show_detail=False,
                show_description=False,
                grab_focus=False,
            )
            self._suggestion_popup.show(attach_to=self._text, index=tk.INSERT)

    def hide_suggestions(self) -> None:
        if self._suggestion_popup and self._suggestion_popup.winfo_exists():
            self._suggestion_popup.hide()

    def toggle_suggestions(self, enabled: bool) -> None:
        if not enabled:
            self.hide_suggestions()

    def reset_suggestions_for_language_switch(self) -> None:
        self._suggestion_popup = None
        self.hide_suggestions()

    def _on_suggestion_select(self, item: CompletionItem) -> None:
        text = self._text
        cursor = text.index(tk.INSERT)
        line, col = (int(p) for p in cursor.split("."))

        line_start = f"{line}.0"
        line_text = text.get(line_start, cursor)
        word_start = col
        while word_start > 0 and (
            line_text[word_start - 1].isalnum() or line_text[word_start - 1] == "_"
        ):
            word_start -= 1

        text.delete(f"{line}.{word_start}", cursor)
        text.insert(f"{line}.{word_start}", item.insert)
        self.apply_highlight()

    # ------------------------------------------------------------------
    # Ghost-text inline completion
    # ------------------------------------------------------------------

    def hide_ghost_text(self) -> None:
        if self._ghost_text is not None:
            self._ghost_text.hide()

    def accept_ghost_text(self) -> bool:
        if self._ghost_text is None or not self._ghost_text.is_visible():
            return False
        if self._ghost_text.accept():
            self._host.mark_dirty()
            self.schedule_highlight()
            self.schedule_autosave()
            self._host.emit_content_changed()
            self.schedule_inline_completion(immediate=True)
            return True
        return False

    def current_partial_token(self) -> str:
        try:
            line = self._text.get("insert linestart", "insert")
        except tk.TclError:
            return ""
        token_chars: list[str] = []
        for ch in reversed(line):
            if ch.isalnum() or ch == "_" or ch == ".":
                token_chars.append(ch)
            else:
                break
        return "".join(reversed(token_chars))

    def _show_ghost_text(self, text_str: str) -> bool:
        if not text_str:
            return False
        existing = self.current_partial_token()
        suffix = strip_common_prefix(text_str, existing) if existing else text_str
        if not suffix or not suffix.strip():
            return False
        return self._ghost_text.show(self._text, suffix)

    def _run_inline_completion(self, epoch: int) -> None:
        if epoch != self._ghost_text_epoch:
            return
        if self._large_file_mode or not self._host.suggestions_enabled:
            return
        try:
            cursor = self._text.index(tk.INSERT)
        except tk.TclError:
            return
        try:
            code = self._text.get("1.0", "end-1c")
        except tk.TclError:
            return
        if not code:
            return
        try:
            line_i, col_i = (int(p) for p in cursor.split("."))
        except Exception:
            return
        offset = sum(len(line_text) + 1 for line_text in code.split("\n")[: line_i - 1]) + col_i

        partial = self.current_partial_token()
        completion = pick_local_completion(
            self._suggestion_expert, code=code, position=offset, partial=partial
        )
        if completion is None:
            self.hide_ghost_text()
            return
        self._show_ghost_text(completion)

    # ------------------------------------------------------------------
    # Edit operations
    # ------------------------------------------------------------------

    def undo(self) -> None:
        with contextlib.suppress(tk.TclError):
            self._text.edit_undo()
        self.apply_highlight()

    def redo(self) -> None:
        with contextlib.suppress(tk.TclError):
            self._text.edit_redo()
        self.apply_highlight()

    def cut(self) -> None:
        widget = self._host.window.focus_get()
        if widget is not None:
            widget.event_generate("<<Cut>>")
        self.apply_highlight()

    def copy(self) -> None:
        widget = self._host.window.focus_get()
        if widget is not None:
            widget.event_generate("<<Copy>>")

    def paste(self) -> None:
        widget = self._host.window.focus_get()
        if widget is not None:
            widget.event_generate("<<Paste>>")
        self.apply_highlight()

    def select_all(self) -> None:
        self._text.tag_add("sel", "1.0", "end")
        self._text.mark_set(tk.INSERT, "1.0")
        self._text.see(tk.INSERT)

    def goto_line(self) -> None:
        line_no = tk.simpledialog.askinteger(  # type: ignore[attr-defined]
            t("dialog.title.goto_line"),
            t("dialog.goto_line.prompt"),
            parent=self._host.window,
            minvalue=1,
            maxvalue=self._line_count(),
        )
        if not line_no:
            return
        self._text.mark_set(tk.INSERT, f"{line_no}.0")
        self._text.see(f"{line_no}.0")
        self._host.refresh_status()

    def indent(self) -> None:
        text = self._text
        sel = text.tag_ranges("sel")
        if sel:
            start_str = str(sel[0])
            end_str = str(sel[1])
        else:
            start_str = text.index(tk.INSERT)
            end_str = start_str
        start_line = int(start_str.split(".")[0])
        end_line = int(end_str.split(".")[0])
        indent = " " * self._host.tab_width
        for ln in range(start_line, end_line + 1):
            text.insert(f"{ln}.0", indent)
        new_start = f"{start_line}.0"
        new_end = f"{end_line}.{len(text.get(f'{end_line}.0', f'{end_line}.end'))}"
        text.tag_remove("sel", "1.0", "end")
        text.tag_add("sel", new_start, new_end)

    def outdent(self) -> None:
        text = self._text
        sel = text.tag_ranges("sel")
        if sel:
            start_str = str(sel[0])
            end_str = str(sel[1])
        else:
            start_str = text.index(tk.INSERT)
            end_str = start_str
        start_line = int(start_str.split(".")[0])
        end_line = int(end_str.split(".")[0])
        for ln in range(start_line, end_line + 1):
            line_start = f"{ln}.0"
            line_text = text.get(line_start, f"{ln}.end")
            stripped = line_text.lstrip()
            removed = len(line_text) - len(stripped)
            for _ in range(min(self._host.tab_width, removed)):
                # Always delete the *first* character of the line. Indexing by
                # an absolute column number would silently consume the
                # trailing newline once we run past the line content.
                text.delete(line_start)

    def toggle_comment(self) -> None:
        if self._host.current_language != "Python":
            tk.messagebox.showinfo(  # type: ignore[attr-defined]
                t("dialog.title.toggle_comment"),
                t("dialog.toggle_comment.unsupported", lang=self._host.current_language),
                parent=self._host.window,
            )
            return
        text = self._text
        sel = text.tag_ranges("sel")
        if sel:
            start_str = str(sel[0])
            end_str = str(sel[1])
        else:
            start_str = text.index(tk.INSERT)
            end_str = start_str
        start_line = int(start_str.split(".")[0])
        end_line = int(end_str.split(".")[0])
        for ln in range(start_line, end_line + 1):
            line_start = f"{ln}.0"
            line_text = text.get(line_start, f"{ln}.end")
            if line_text.lstrip().startswith("#"):
                stripped = line_text.lstrip()
                prefix = line_text[: len(line_text) - len(stripped)]
                text.delete(line_start, f"{ln}.{len(prefix) + 1}")
            else:
                text.insert(line_start, "# ")

    def find_symbol_definitions(self, code: str, symbol: str) -> list[tuple[int, str]]:
        return find_symbol_definitions(code, symbol)

    def get_word_under_cursor(self, x: int | None = None, y: int | None = None) -> str:
        text = self._text
        try:
            if x is not None and y is not None:
                cursor = text.index(f"@{x},{y}")
            else:
                cursor = text.index(tk.INSERT)
        except Exception:
            return ""
        line, col = (int(p) for p in cursor.split("."))
        line_text = text.get(f"{line}.0", f"{line}.end")
        if not line_text or col >= len(line_text):
            return ""
        start = col
        while start > 0 and (line_text[start - 1].isalnum() or line_text[start - 1] == "_"):
            start -= 1
        end = col
        while end < len(line_text) and (line_text[end].isalnum() or line_text[end] == "_"):
            end += 1
        word = line_text[start:end]
        if word and (word[0].isalpha() or word[0] == "_"):
            return word
        return ""

    def goto_definition(self) -> None:
        if self._large_file_mode:
            return
        code = self._text.get("1.0", "end-1c")
        if not code.strip():
            return
        word = self.get_word_under_cursor(self._context_click_x, self._context_click_y)
        if not word:
            return
        definitions = find_symbol_definitions(code, word)
        if not definitions:
            tk.messagebox.showinfo(  # type: ignore[attr-defined]
                t("dialog.title.goto_definition"),
                t("dialog.goto_definition.not_found", symbol=word),
                parent=self._host.window,
            )
            return
        target_line, _ = definitions[0]
        self._highlighted_line = target_line
        self._text.mark_set(tk.INSERT, f"{target_line}.0")
        self._text.see(tk.INSERT)
        self.highlight_line(target_line)

    def find_references(self) -> None:
        if self._large_file_mode:
            return
        code = self._text.get("1.0", "end-1c")
        if not code.strip():
            return
        word = self.get_word_under_cursor(self._context_click_x, self._context_click_y)
        if not word:
            return
        import re

        pattern = re.compile(r"\b" + re.escape(word) + r"\b")
        matches: list[tuple[int, str]] = []
        for ln, line_text in enumerate(code.split("\n"), start=1):
            if pattern.search(line_text):
                matches.append((ln, line_text.strip()))
        if not matches:
            tk.messagebox.showinfo(  # type: ignore[attr-defined]
                t("dialog.title.find_references"),
                t("dialog.find_references.not_found", symbol=word),
                parent=self._host.window,
            )
            return
        self._host.show_references(word, matches)

    def lookup_documentation(self, symbol: str) -> dict | None:
        parts = symbol.split(".")
        result: dict = {}
        try:
            top = parts[0]
            namespace = __import__(top)
            obj = namespace
            for part in parts[1:]:
                obj = getattr(obj, part)
            result["doc"] = (getattr(obj, "__doc__", "") or "").strip()
            result["type"] = type(obj).__name__
            if hasattr(obj, "__module__"):
                result["source"] = getattr(obj, "__module__", "")
            if callable(obj):
                import inspect

                try:
                    sig = str(inspect.signature(obj))
                    if sig != "()" or parts[0] == symbol:
                        result["signature"] = f"{symbol}{sig}"
                except (ValueError, TypeError):
                    pass
            return result if result.get("doc") or result.get("signature") else None
        except (ImportError, AttributeError, SyntaxError):
            pass

        import builtins

        obj = getattr(builtins, symbol, None)
        if obj is not None:
            result["doc"] = (getattr(obj, "__doc__", "") or "").strip()
            result["type"] = type(obj).__name__
            result["source"] = "builtins"
            return result
        return None

    # ------------------------------------------------------------------
    # Find / replace dialog
    # ------------------------------------------------------------------

    def open_find_dialog(self) -> None:
        self._show_find_dialog(replace=False)

    def open_replace_dialog(self) -> None:
        self._show_find_dialog(replace=True)

    def close_find_dialog(self) -> None:
        if self._find_dialog is not None and self._find_dialog.winfo_exists():
            with contextlib.suppress(tk.TclError):
                self._find_dialog.destroy()
        self._find_dialog = None
        self._find_dialog_impl = None

    def _show_find_dialog(self, *, replace: bool) -> None:
        if self._find_dialog is not None:
            self.close_find_dialog()
        dlg = FindDialog(
            self._host.window,
            self._text,
            replace=replace,
            initial_query=self._find_query,
            initial_last_index=self._find_last_index,
            on_change=self.apply_highlight,
        )
        dlg.show()
        self._find_dialog = dlg._window  # type: ignore[attr-defined]
        self._find_dialog_impl = dlg

    def pull_find_state(self) -> None:
        impl = self._find_dialog_impl
        if impl is None:
            return
        self._find_query = impl.last_query
        self._find_last_index = impl.last_index

    # ------------------------------------------------------------------
    # Auto-clear debounce / cursors / events
    # ------------------------------------------------------------------

    def emit_selection_changed(self) -> None:
        try:
            selection = self._text.selection_get()
        except tk.TclError:
            selection = ""
        if selection == self._last_selection:
            return
        self._last_selection = selection
        self._host.emit(HookEvents.EDITOR_SELECTION_CHANGED, selection)

    def emit_cursor_moved(self) -> None:
        try:
            cursor = self._text.index(tk.INSERT)
            line_i, col_i = (int(p) for p in cursor.split("."))
        except Exception:
            return
        if self._last_cursor == (line_i, col_i):
            return
        self._last_cursor = (line_i, col_i)
        self._host.emit(HookEvents.EDITOR_CURSOR_MOVED, line_i, col_i)

    def emit_content_changed(self) -> None:
        try:
            code = self._text.get("1.0", "end-1c")
        except tk.TclError:
            return
        if code == self._last_emit_code:
            return
        self._last_emit_code = code
        try:
            cursor = int(self._text.index(tk.INSERT).split(".")[1])
        except Exception:
            cursor = 0
        self._host.emit(HookEvents.EDITOR_CONTENT_CHANGED, code, cursor)

    def rebuild_text_after_language_switch(self, sample: str) -> None:
        self._text.config(state="normal")
        self._large_file_mode = False
        self._text.delete("1.0", tk.END)
        self._text.insert("1.0", sample)

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def _on_key_release(self, event: tk.Event | None = None) -> None:
        self._host.refresh_status()
        self.schedule_highlight()
        if self._host.suggestions_enabled:
            self.schedule_suggestions()
        self.schedule_autosave()
        self._host.mark_dirty()
        keysym = getattr(event, "keysym", "") if event is not None else ""
        if keysym and keysym not in NAVIGATION_KEYS:
            self.hide_ghost_text()
        self.emit_content_changed()
        self.emit_selection_changed()
        self.schedule_inline_completion()

    def _on_key_press(self, event: tk.Event | None = None) -> str | None:
        if self._ghost_text and self._ghost_text.is_visible():
            if event and event.keysym == "Tab":
                if self.accept_ghost_text():
                    return "break"
            elif event and event.keysym == "Escape":
                self._ghost_text.hide()
                return "break"
        if self._suggestion_popup and self._suggestion_popup.winfo_exists():
            if event and event.keysym == "Escape":
                self._suggestion_popup.hide()
            elif event and event.keysym == "Down":
                self._suggestion_popup.select_next()
                return "break"
            elif event and event.keysym == "Up":
                self._suggestion_popup.select_prev()
                return "break"
            elif event and event.keysym == "Tab":
                item = self._suggestion_popup.selected()
                self._suggestion_popup.hide()
                if item is not None:
                    self._on_suggestion_select(item)
                return "break"
        return None

    def _on_click(self, event: tk.Event | None = None) -> None:
        self._host.refresh_status()
        self.cancel_pending_suggestions()
        self.hide_ghost_text()
        self.emit_cursor_moved()
        self.emit_selection_changed()

    def _on_focus_in(self, event: tk.Event | None = None) -> None:
        self._host.refresh_status()
        self.cancel_pending_suggestions()
        self.emit_cursor_moved()
        self._host.emit(HookEvents.EDITOR_FOCUS_CHANGED, True)

    def _on_focus_out(self, event: tk.Event | None = None) -> None:
        self.hide_ghost_text()
        self._host.emit(HookEvents.EDITOR_FOCUS_CHANGED, False)

    def _show_editor_context_menu(self, event: tk.Event) -> None:
        from ui.widgets import UContextMenu

        menu = UContextMenu(self._host.window)

        menu.add_command(label=t("menu.edit.undo"), command=self.undo, shortcut="Ctrl+Z")
        menu.add_command(label=t("menu.edit.redo"), command=self.redo, shortcut="Ctrl+Y")
        menu.add_separator()
        menu.add_command(label=t("menu.edit.cut"), command=self.cut, shortcut="Ctrl+X")
        menu.add_command(label=t("menu.edit.copy"), command=self.copy, shortcut="Ctrl+C")
        menu.add_command(label=t("menu.edit.paste"), command=self.paste, shortcut="Ctrl+V")
        menu.add_separator()
        menu.add_command(
            label=t("menu.edit.select_all"),
            command=self.select_all,
            shortcut="Ctrl+A",
        )

        word = self.get_word_under_cursor(event.x, event.y)
        self._context_click_x = event.x
        self._context_click_y = event.y
        if word:
            menu.add_separator()
            menu.add_command(
                label=t("menu.query.goto_definition"),
                command=self.goto_definition,
                shortcut="F12",
            )
            menu.add_command(
                label=t("menu.query.find_references"),
                command=self.find_references,
                shortcut="Shift+F12",
            )

        menu.show(event.x_root, event.y_root)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _tag_style_kwargs(self, style: dict) -> dict:
        kwargs = dict(style)
        bold = bool(kwargs.pop("bold", False))
        italic = bool(kwargs.pop("italic", False))
        font: list = [self._host.font_family, self._host.font_size]
        if bold:
            font.append("bold")
        if italic:
            font.append("italic")
        kwargs["font"] = tuple(font)
        return kwargs

    def _current_tag_style(self, tag: str) -> dict | None:
        hl_tokens: dict = highlight_themes.tokens() or HIGHLIGHT_TOKENS
        if tag in hl_tokens:
            return dict(hl_tokens[tag])
        if tag == "identifier":
            fallback: dict = {"foreground": theme.FG_PRIMARY}
            return dict(hl_tokens.get("identifier", fallback))
        return None

    def _index_from_pos(self, pos: int) -> str:
        code = self._text.get("1.0", "end-1c")
        line = 1
        col = 0
        for i, ch in enumerate(code):
            if i >= pos:
                break
            if ch == "\n":
                line += 1
                col = 0
            else:
                col += 1
        return f"{line}.{col}"

    def _line_count(self) -> int:
        return int(self._text.index("end-1c").split(".")[0])
