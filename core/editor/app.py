import contextlib
import os
import re
import sys
import tempfile
import tkinter as tk
import tkinter.filedialog
import tkinter.messagebox
import tkinter.simpledialog
from typing import Any

from core.editor.document import Document, _Debouncer
from core.editor.lang_config import (
    FONT_FAMILIES,
    FONT_SIZES,
    HIGHLIGHT_TOKENS,
    LANG_CONFIG,
    TAB_WIDTHS,
    THEME_NAMES,
)
from core.language.checker import CPythonChecker
from core.language.highlighter import (
    HighlightBlock,
    highlight_marketplace,
    highlight_themes,
)
from core.language.suggestion import SuggestionBlock
from core.plugins import HookEvents, LanguageContribution, PluginManager, plugin_marketplace
from core.plugins.widgets import UPluginManagerWindow
from core.runner import RunResult, stream_command
from core.settings import SettingsChangeEvent, SettingsManager, SettingsScope
from core.settings.i18n import AVAILABLE_LANGUAGES, get_translator, language_marketplace, t
from core.settings.logging import get_logger as get_core_logger
from ui import Window
from ui.widgets import (
    DebugCard,
    ExplorerCard,
    GitCard,
    SideBar,
    Tab,
    TabBar,
    UButton,
    UContextMenu,
    UFrame,
    ULabel,
    UMenuBar,
    UShortcutConfigWindow,
    UText,
    theme,
    ui_theme_marketplace,
)
from ui.widgets.editor_suggestion import CompletionItem, UEditorSuggestion

app_logger = get_core_logger("app")
app_logger.info("Application starting...")


class CodeEditor:
    def __init__(self):
        custom_titlebar = "--custom-titlebar" in sys.argv
        self.window = Window(title=t("window.title"), custom_titlebar=custom_titlebar)
        self.window.geometry("960x680+200+100")
        self.window.configure(bg=theme.BG_BASE)
        self.window.resizable(width=True, height=True)

        self._settings = SettingsManager()
        self._suppress_settings_listener = False

        self._translator = get_translator()
        initial_lang = self._settings.effective("i18n.language", "zh_CN")
        if initial_lang in AVAILABLE_LANGUAGES:
            self._translator.set_language(initial_lang)
        self._translator.add_listener(self._on_language_changed)

        self._lang = "Python"
        self._current_file: str | None = None
        self._current_project_root: str | None = None
        self._suggestion_popup: UEditorSuggestion | None = None
        self._dirty = False

        self._documents: dict[str, Document] = {}
        self._active_id: str | None = None
        self._next_untitled_seq: int = 1
        self._tab_bar: TabBar | None = None

        gs = self._settings.global_settings
        self._highlighting_enabled = gs.get("completion.enabled", True)
        self._suggestions_enabled = gs.get("completion.enabled", True)
        self._autosave_enabled = gs.get("editor.auto_save", False)

        self._highlight_theme_name = gs.get("ui.highlight_theme", "Default Dark")
        if self._highlight_theme_name not in highlight_themes.available_names():
            self._highlight_theme_name = "Default Dark"

        self._font_family = gs.get("ui.font_family", "Consolas")
        self._font_size = int(gs.get("ui.font_size", 10))
        self._tab_width = int(gs.get("editor.tab_size", 4))
        self._highlight_delay_ms = int(gs.get("editor.highlight_delay_ms", 300))
        self._definition_highlight_duration_ms = int(
            gs.get("editor.definition_highlight_duration_ms", 3000)
        )
        self._suggest_delay_ms = int(gs.get("editor.suggestion_delay_ms", 200))
        self._suggest_min_chars = int(gs.get("completion.min_chars_before_trigger", 1))

        self._highlight_debouncer = _Debouncer(self.window.after, self.window.after_cancel)
        self._suggest_debouncer = _Debouncer(self.window.after, self.window.after_cancel)
        self._autosave_debouncer = _Debouncer(self.window.after, self.window.after_cancel)
        self._highlight_after_id: int | None = None
        self._autosave_format = gs.get("editor.auto_save_format", "{unix.seconds}")
        self._autosave_delay_ms = int(gs.get("editor.auto_save_delay_ms", 800))
        self._autosave_paths: dict[str, str] = {}

        self._find_dialog: tk.Toplevel | None = None
        self._find_query = ""
        self._find_last_index: str | None = None

        self._large_file_mode: bool = False
        self._stream_epoch: int = 0
        self._highlighted_line: int | None = None
        self._highlighted_line_color: str = theme.YELLOW
        self._context_click_x: int | None = None
        self._context_click_y: int | None = None

        self._font_family_tk_var: tk.StringVar | None = None
        self._font_size_tk_var: tk.IntVar | None = None
        self._tab_width_tk_var: tk.IntVar | None = None
        self._highlight_tk_var: tk.BooleanVar | None = None
        self._suggestion_tk_var: tk.BooleanVar | None = None
        self._autosave_tk_var: tk.BooleanVar | None = None
        self._highlight_theme_tk_var: tk.StringVar | None = None
        self._theme_tk_var: tk.StringVar | None = None
        self._lang_tk_var: tk.StringVar | None = None
        self._lang_locale_tk_var: tk.StringVar | None = None

        self._build_menubar()
        self._build_toolbar()
        self._build_editor()
        self._init_first_document()
        self._build_output_panel()
        self._build_status_bar()

        self._plugin_manager = PluginManager()
        self._plugin_menus: dict[str, Any] = {}
        self._plugin_lang_combo_added: list[str] = []
        self._plugin_manager.attach_editor(self)
        with contextlib.suppress(Exception):
            self._plugin_manager.load_global_plugins()
        self._refresh_plugin_menu()
        self._refresh_plugin_languages()

        self._settings.add_listener(self._on_settings_changed)

        self._apply_loaded_theme()
        self._apply_editor_font()
        self._set_tab_width(self._tab_width)
        self._switch_language("Python")

        self._bind_shortcuts()
        self.window.protocol("WM_DELETE_WINDOW", self._on_close_request)
        app_logger.info(
            f"CodeEditor initialized: theme={theme.current().name}, "
            f"font={self._font_family} {self._font_size}pt, "
            f"tab_width={self._tab_width}"
        )

    def _init_first_document(self) -> None:
        doc_id = self._new_doc_id()
        self._documents[doc_id] = Document(
            path=None, content="", dirty=False, lang=self._lang, seq=1
        )
        self._active_id = doc_id
        self._next_untitled_seq = 2
        self._update_tab_bar()

    def _new_doc_id(self) -> str:
        return f"__untitled_{self._next_untitled_seq}__"

    def _tab_title(self, doc: Document) -> str:
        if doc.path:
            return os.path.basename(doc.path)
        return f"Untitled-{doc.seq}"

    def _update_tab_bar(self) -> None:
        if self._tab_bar is None:
            return
        tabs = []
        for doc_id, doc in self._documents.items():
            title = self._tab_title(doc)
            closeable = len(self._documents) > 1
            tabs.append(Tab(id=doc_id, title=title, dirty=doc.dirty, closeable=closeable))
        self._tab_bar.set_tabs(tabs, self._active_id)

    def _switch_document(self, doc_id: str) -> None:
        if doc_id not in self._documents:
            return
        if self._active_id and self._active_id in self._documents:
            curr = self._documents[self._active_id]
            try:
                curr.content = self._editor.get("1.0", "end-1c")
            except tk.TclError:
                curr.content = ""
            curr.lang = self._lang

        self._active_id = doc_id
        doc = self._documents[doc_id]
        self._editor._text.config(state="normal")
        self._editor._text.delete("1.0", tk.END)
        if doc.content:
            self._editor._text.insert("1.0", doc.content)
        self._dirty = doc.dirty
        self._lang = doc.lang
        self._switch_language(doc.lang, from_doc_switch=True)
        self._tab_bar.set_active(doc_id)  # type: ignore[union-attr]
        self._apply_highlight()
        self._update_status()

    def _tab_select(self, doc_id: str) -> None:
        if doc_id == self._active_id:
            return
        self._switch_document(doc_id)
        self._emit(HookEvents.EDITOR_TAB_CHANGED, doc_id)

    def _tab_close(self, doc_id: str) -> None:
        if doc_id not in self._documents:
            return
        doc = self._documents[doc_id]
        if doc.dirty:
            result = tk.messagebox.askyesno(
                t("dialog.title.unsaved_discard"),
                t("dialog.unsaved_discard.message"),
            )
            if not result:
                return

        del self._documents[doc_id]
        self._tab_bar.remove_tab(doc_id)  # type: ignore[union-attr]

        if not self._documents:
            self._init_first_document()
        elif self._active_id == doc_id:
            other_id = next(iter(self._documents.keys()))
            self._active_id = other_id
            doc = self._documents[other_id]
            self._editor._text.config(state="normal")
            self._editor._text.delete("1.0", tk.END)
            if doc.content:
                self._editor._text.insert("1.0", doc.content)
            self._dirty = doc.dirty
            self._lang = doc.lang
            self._switch_language(doc.lang, from_doc_switch=True)
            self._apply_highlight()
            self._update_status()
        self._update_tab_bar()

    def _tab_context_menu(self, doc_id: str, x_root: int, y_root: int) -> None:
        menu = UContextMenu(self.window)
        menu.add_command(
            label=t("sidebar.tab.close", default="Close"),
            command=lambda: self._tab_close(doc_id),
        )
        menu.add_command(
            label=t("sidebar.tab.close_others", default="Close Others"),
            command=lambda: self._close_other_tabs(doc_id),
        )
        menu.add_command(
            label=t("sidebar.tab.close_all", default="Close All"),
            command=self._close_all_tabs,
        )
        menu.show(x_root, y_root)

    def _show_editor_context_menu(self, event: tk.Event) -> None:
        """Show the editor right-click context menu."""
        menu = UContextMenu(self.window)

        menu.add_command(
            label=t("menu.edit.undo"),
            command=self._undo,
            shortcut="Ctrl+Z",
        )
        menu.add_command(
            label=t("menu.edit.redo"),
            command=self._redo,
            shortcut="Ctrl+Y",
        )
        menu.add_separator()
        menu.add_command(
            label=t("menu.edit.cut"),
            command=self._cut,
            shortcut="Ctrl+X",
        )
        menu.add_command(
            label=t("menu.edit.copy"),
            command=self._copy,
            shortcut="Ctrl+C",
        )
        menu.add_command(
            label=t("menu.edit.paste"),
            command=self._paste,
            shortcut="Ctrl+V",
        )
        menu.add_separator()
        menu.add_command(
            label=t("menu.edit.select_all"),
            command=self._select_all,
            shortcut="Ctrl+A",
        )

        word = self._get_word_under_cursor(event.x, event.y)
        self._context_click_x = event.x
        self._context_click_y = event.y
        if word:
            menu.add_separator()
            menu.add_command(
                label=t("menu.query.goto_definition"),
                command=self._goto_definition,
                shortcut="F12",
            )
            menu.add_command(
                label=t("menu.query.find_references"),
                command=self._find_references,
                shortcut="Shift+F12",
            )

        menu.show(event.x_root, event.y_root)

    def _close_other_tabs(self, keep_id: str) -> None:
        for did in [d for d in self._documents if d != keep_id]:
            self._tab_close(did)

    def _close_all_tabs(self) -> None:
        if len(self._documents) <= 1:
            self._new_file()
            return
        for did in list(self._documents.keys()):
            self._tab_close(did)

    def _mark_dirty(self) -> None:
        if self._active_id and self._active_id in self._documents:
            self._documents[self._active_id].dirty = True
            self._dirty = True
            self._update_tab_bar()

    def _next_tab(self) -> None:
        if not self._documents:
            return
        ids = list(self._documents.keys())
        if self._active_id in ids:
            idx = ids.index(self._active_id)
            self._switch_document(ids[(idx + 1) % len(ids)])

    def _prev_tab(self) -> None:
        if not self._documents:
            return
        ids = list(self._documents.keys())
        if self._active_id in ids:
            idx = ids.index(self._active_id)
            self._switch_document(ids[(idx - 1) % len(ids)])

    def _close_active_tab(self) -> None:
        if self._active_id:
            self._tab_close(self._active_id)

    def _on_settings_changed(self, event: SettingsChangeEvent) -> None:
        if self._suppress_settings_listener:
            return
        if event.scope is not SettingsScope.GLOBAL:
            return
        if event.key is None:
            self._refresh_all_from_settings()
            return
        key = event.key
        if key == "ui.theme":
            with contextlib.suppress(Exception):
                self._set_theme(event.new, persist=False)
        elif key == "ui.highlight_theme":
            with contextlib.suppress(Exception):
                self._set_highlight_theme(event.new, persist=False)
        elif key == "ui.font_family":
            self._font_family = event.new
            if hasattr(self, "_font_family_tk_var"):
                self._font_family_tk_var.set(event.new)
            self._apply_editor_font()
        elif key == "ui.font_size":
            self._font_size = int(event.new)
            if hasattr(self, "_font_size_tk_var"):
                self._font_size_tk_var.set(int(event.new))
            self._apply_editor_font()
        elif key == "editor.tab_size":
            self._set_tab_width(int(event.new), persist=False)
        elif key == "completion.enabled":
            val = bool(event.new)
            self._highlighting_enabled = val
            self._suggestions_enabled = val
            for tk_var in (
                getattr(self, "_highlight_tk_var", None),
                getattr(self, "_suggestion_tk_var", None),
            ):
                if tk_var is not None:
                    tk_var.set(val)
            if val:
                self._apply_highlight()
            else:
                text = self._editor._text
                for tag in text.tag_names():
                    text.tag_delete(tag)
                self._hide_suggestions()
        elif key == "editor.auto_save":
            self._autosave_enabled = bool(event.new)
            if hasattr(self, "_autosave_tk_var"):
                self._autosave_tk_var.set(bool(event.new))
        elif key == "editor.auto_save_format":
            self._autosave_format = str(event.new) if event.new else "{unix.seconds}"
        elif key == "editor.auto_save_delay_ms":
            try:
                self._autosave_delay_ms = max(100, int(event.new))
            except (TypeError, ValueError):
                self._autosave_delay_ms = 800
        elif key == "editor.highlight_delay_ms":
            try:
                self._highlight_delay_ms = max(0, int(event.new))
            except (TypeError, ValueError):
                self._highlight_delay_ms = 300
        elif key == "editor.definition_highlight_duration_ms":
            try:
                self._definition_highlight_duration_ms = max(0, int(event.new))
            except (TypeError, ValueError):
                self._definition_highlight_duration_ms = 3000
        elif key == "editor.suggestion_delay_ms":
            try:
                self._suggest_delay_ms = max(0, int(event.new))
            except (TypeError, ValueError):
                self._suggest_delay_ms = 200
        elif key == "completion.min_chars_before_trigger":
            try:
                self._suggest_min_chars = max(0, int(event.new))
            except (TypeError, ValueError):
                self._suggest_min_chars = 1
        elif key == "i18n.language":
            new_lang = event.new if event.new in AVAILABLE_LANGUAGES else "zh_CN"
            if self._translator.current_language != new_lang:
                self._translator.set_language(new_lang)
            if hasattr(self, "_lang_locale_tk_var") and self._lang_locale_tk_var is not None:
                self._lang_locale_tk_var.set(new_lang)

    def _refresh_all_from_settings(self) -> None:
        with contextlib.suppress(Exception):
            self._set_theme(self._settings.effective("ui.theme"), persist=False)
        gs = self._settings.global_settings
        self._font_family = gs.get("ui.font_family", self._font_family)
        self._font_size = int(gs.get("ui.font_size", self._font_size))
        self._tab_width = int(gs.get("editor.tab_size", self._tab_width))
        self._highlight_delay_ms = int(
            gs.get("editor.highlight_delay_ms", self._highlight_delay_ms)
        )
        self._definition_highlight_duration_ms = int(
            gs.get(
                "editor.definition_highlight_duration_ms", self._definition_highlight_duration_ms
            )
        )
        self._suggest_delay_ms = int(gs.get("editor.suggestion_delay_ms", self._suggest_delay_ms))
        self._suggest_min_chars = int(
            gs.get("completion.min_chars_before_trigger", self._suggest_min_chars)
        )
        self._autosave_format = gs.get("editor.auto_save_format", self._autosave_format)
        self._autosave_delay_ms = int(gs.get("editor.auto_save_delay_ms", self._autosave_delay_ms))
        try:
            hl_theme = gs.get("ui.highlight_theme", self._highlight_theme_name)
            if hl_theme in highlight_themes.available_names():
                self._set_highlight_theme(hl_theme, persist=False)
        except Exception:
            pass
        if hasattr(self, "_font_family_tk_var"):
            self._font_family_tk_var.set(self._font_family)
        if hasattr(self, "_font_size_tk_var"):
            self._font_size_tk_var.set(int(self._font_size))
        if hasattr(self, "_tab_width_tk_var"):
            self._tab_width_tk_var.set(int(self._tab_width))
        if hasattr(self, "_highlight_theme_tk_var"):
            self._highlight_theme_tk_var.set(self._highlight_theme_name)
        self._apply_editor_font()
        self._set_tab_width(self._tab_width, persist=False)

    def _apply_loaded_theme(self) -> None:
        try:
            target = self._settings.effective("ui.theme", "Dark")
            self._set_theme(target, persist=False)
        except Exception:
            pass
        try:
            hl_target = self._settings.effective("ui.highlight_theme", "Default Dark")
            if hl_target in highlight_themes.available_names():
                self._set_highlight_theme(hl_target, persist=False)
        except Exception:
            pass

    def _on_language_changed(self, lang: str) -> None:
        if hasattr(self, "_lang_changing") and self._lang_changing:
            return
        self._lang_changing = True
        try:
            for attr in ("_find_dialog", "_settings_window", "_plugin_manager_window"):
                win = getattr(self, attr, None)
                if win is not None and win.winfo_exists():
                    with contextlib.suppress(tk.TclError):
                        win.destroy()
                if attr == "_find_dialog":
                    self._find_dialog = None

            self._clear_menubar()
            self._build_menubar()

            with contextlib.suppress(Exception):
                self._refresh_plugin_menu()

            with contextlib.suppress(Exception):
                self._refresh_status_for_language()
        finally:
            self._lang_changing = False

    def _clear_menubar(self) -> None:
        bar = getattr(self, "_menubar", None)
        if bar is None:
            return
        try:
            for btn, _ in list(getattr(bar, "_buttons", [])):
                with contextlib.suppress(tk.TclError):
                    btn.destroy()
            bar._buttons = []
        except Exception:
            pass

    def _refresh_status_for_language(self) -> None:
        if not hasattr(self, "_status_label"):
            return
        with contextlib.suppress(tk.TclError):
            self._status_label.config(text=t("status.ready"))
        if hasattr(self, "_pos_label"):
            with contextlib.suppress(Exception):
                self._update_status()

    def _write_setting(self, scope: SettingsScope, key: str, value) -> None:
        self._suppress_settings_listener = True
        try:
            self._settings.set(scope, key, value)
        except (KeyError, ValueError):
            pass
        finally:
            self._suppress_settings_listener = False

    def _on_close_request(self) -> None:
        dirty_docs = [doc for doc in self._documents.values() if doc.dirty]
        if dirty_docs and not tk.messagebox.askyesno(
            t("dialog.title.unsaved_exit"),
            t("dialog.unsaved_exit.message"),
        ):
            return

        self._cancel_pending_highlight()
        self._cancel_pending_suggestions()
        app_logger.info("Editor closing...")
        self._emit(HookEvents.EDITOR_CLOSING)
        with contextlib.suppress(Exception):
            self._plugin_manager.unload_all()
        self._plugin_manager.detach_editor()
        self._settings.detach_project()
        try:
            self._settings.save_all()
        except Exception as exc:
            tk.messagebox.showerror(t("dialog.title.save_settings_failed"), str(exc))
        app_logger.info("Editor closed. Exiting.")
        self.window.destroy()

    @staticmethod
    def _is_within(path: str, root: str) -> bool:
        if not path or not root:
            return False
        try:
            p = os.path.normcase(os.path.abspath(path))
            r = os.path.normcase(os.path.abspath(root))
        except (OSError, ValueError):
            return False
        if p == r:
            return True
        return p.startswith(r + os.sep)

    def _should_reattach_for_path(self, path: str) -> str | None:
        abs_path = os.path.abspath(path)
        file_dir = os.path.dirname(abs_path)
        current_root = self._current_project_root
        if not current_root:
            return file_dir or None
        if not file_dir:
            return None
        if self._is_within(file_dir, current_root):
            return None
        return file_dir

    def _build_menubar(self):
        self._menubar = UMenuBar(self.window)
        self._menubar.pack(fill=tk.X, padx=0, pady=0)

        file_menu = self._menubar.add_cascade(t("menu.file"))
        file_menu.add_command(t("menu.file.new"), self._new_file, "Ctrl+N")
        file_menu.add_command(t("menu.file.open"), self._open_file, "Ctrl+O")
        file_menu.add_command(t("menu.file.open_project"), self._open_project, "Ctrl+Shift+O")
        file_menu.add_separator()
        file_menu.add_command(t("menu.file.save"), self._save_file, "Ctrl+S")
        file_menu.add_command(t("menu.file.save_as"), self._save_file_as, "Ctrl+Shift+S")
        file_menu.add_separator()
        file_menu.add_command(t("menu.file.close_tab"), self._close_active_tab, "Ctrl+W")
        file_menu.add_separator()
        file_menu.add_command(t("menu.file.run"), self._run_code, "F5")
        file_menu.add_command(t("menu.file.check"), self._run_check, "Ctrl+R")
        file_menu.add_command(t("menu.file.clear_output"), self._clear_output, "Ctrl+L")
        file_menu.add_separator()
        file_menu.add_command(t("menu.file.exit"), self.window.destroy, "Alt+F4")

        edit_menu = self._menubar.add_cascade(t("menu.edit"))
        edit_menu.add_command(t("menu.edit.undo"), self._undo, "Ctrl+Z")
        edit_menu.add_command(t("menu.edit.redo"), self._redo, "Ctrl+Y")
        edit_menu.add_separator()
        edit_menu.add_command(t("menu.edit.cut"), self._cut, "Ctrl+X")
        edit_menu.add_command(t("menu.edit.copy"), self._copy, "Ctrl+C")
        edit_menu.add_command(t("menu.edit.paste"), self._paste, "Ctrl+V")
        edit_menu.add_separator()
        edit_menu.add_command(t("menu.edit.select_all"), self._select_all, "Ctrl+A")
        edit_menu.add_separator()
        edit_menu.add_command(t("menu.edit.find"), self._open_find, "Ctrl+F")
        edit_menu.add_command(t("menu.edit.replace"), self._open_replace, "Ctrl+H")
        edit_menu.add_command(t("menu.edit.goto_line"), self._goto_line, "Ctrl+G")
        edit_menu.add_separator()
        edit_menu.add_command(t("menu.edit.indent"), self._indent, "Tab")
        edit_menu.add_command(t("menu.edit.outdent"), self._outdent, "Shift+Tab")
        edit_menu.add_command(t("menu.edit.toggle_comment"), self._toggle_comment, "Ctrl+/")
        lang_sub = edit_menu.add_cascade(t("menu.edit.switch_language"))
        for name in LANG_CONFIG:
            lang_sub.add_radiobutton(
                name,
                value=name,
                variable=self._lang_var(),
                command=lambda n=name: self._switch_language(n),
            )

        query_menu = self._menubar.add_cascade(t("menu.query"))
        query_menu.add_command(t("menu.query.goto_definition"), self._goto_definition, "F12")
        query_menu.add_command(t("menu.query.find_references"), self._find_references, "Shift+F12")
        query_menu.add_command(
            t("menu.query.find_documentation"), self._find_documentation, "Ctrl+Shift+F1"
        )
        query_menu.add_separator()
        query_menu.add_command(t("menu.query.reparse"), self._reparse, "F6")
        query_menu.add_command(t("menu.query.refresh_highlight"), self._apply_highlight, "F7")
        query_menu.add_separator()
        query_menu.add_command(
            t("menu.query.trigger_suggestions"), self._show_suggestions, "Ctrl+Space"
        )
        query_menu.add_command(t("menu.query.hide_suggestions"), self._hide_suggestions, "Esc")

        settings_menu = self._menubar.add_cascade(t("menu.settings"))
        theme_sub = settings_menu.add_cascade(t("menu.settings.theme"))
        for name in THEME_NAMES:
            theme_sub.add_radiobutton(
                name,
                value=name,
                variable=self._theme_var(),
                command=lambda n=name: self._set_theme(n),
            )
        theme_sub.add_separator()
        theme_sub.add_command(t("menu.settings.theme_marketplace"), self._open_ui_theme_marketplace)
        hl_theme_sub = settings_menu.add_cascade(t("menu.settings.highlight_theme"))
        for name in highlight_themes.available_names():
            hl_theme_sub.add_radiobutton(
                name,
                value=name,
                variable=self._highlight_theme_var(),
                command=lambda n=name: self._set_highlight_theme(n),
            )
        hl_theme_sub.add_separator()
        hl_theme_sub.add_command(
            t("menu.settings.highlight_theme_marketplace"), self._open_highlight_theme_marketplace
        )
        font_sub = settings_menu.add_cascade(t("menu.settings.font"))
        for fnt in FONT_FAMILIES:
            font_sub.add_radiobutton(
                fnt,
                value=fnt,
                variable=self._font_family_var(),
                command=lambda f=fnt: self._set_font_family(f),
            )
        size_sub = settings_menu.add_cascade(t("menu.settings.font_size"))
        for sz in FONT_SIZES:
            size_sub.add_radiobutton(
                str(sz),
                value=sz,
                variable=self._font_size_var(),
                command=lambda s=sz: self._set_font_size(s),
            )
        tab_sub = settings_menu.add_cascade(t("menu.settings.tab_width"))
        for tw in TAB_WIDTHS:
            tab_sub.add_radiobutton(
                str(tw),
                value=tw,
                variable=self._tab_width_var(),
                command=lambda t=tw: self._set_tab_width(t),
            )
        settings_menu.add_separator()
        settings_menu.add_checkbutton(
            t("menu.settings.enable_highlight"),
            variable=self._highlight_var(),
            command=self._toggle_highlighting,
        )
        settings_menu.add_checkbutton(
            t("menu.settings.enable_suggestions"),
            variable=self._suggestion_var(),
            command=self._toggle_suggestions,
        )
        settings_menu.add_checkbutton(
            t("menu.settings.auto_save"),
            variable=self._autosave_var(),
            command=self._toggle_autosave,
        )
        settings_menu.add_separator()
        lang_locale_sub = settings_menu.add_cascade(t("menu.settings.language"))
        for lang in AVAILABLE_LANGUAGES:
            lang_locale_sub.add_radiobutton(
                t(f"menu.language.{lang}"),
                value=lang,
                variable=self._lang_locale_var(),
                command=lambda code=lang: self._set_language_locale(code),
            )
        lang_locale_sub.add_separator()
        lang_locale_sub.add_command(
            t("menu.settings.language_marketplace"), self._open_language_marketplace
        )
        settings_menu.add_separator()
        settings_menu.add_command(t("menu.settings.global_settings"), self._open_global_settings)
        settings_menu.add_command(t("menu.settings.project_settings"), self._open_project_settings)
        settings_menu.add_command(t("menu.settings.reset"), self._reset_settings)

        help_menu = self._menubar.add_cascade(t("menu.help"))
        help_menu.add_command(t("menu.help.docs"), self._show_documentation, "F1")
        help_menu.add_command(t("menu.help.shortcuts"), self._show_shortcuts, "Ctrl+K")
        help_menu.add_separator()
        help_menu.add_command(t("menu.help.about"), self._show_about)
        help_menu.add_command(t("menu.help.check_updates"), self._check_updates)
        help_menu.add_command(t("menu.help.report_issue"), self._report_issue)

        self._plugin_menu = self._menubar.add_cascade(t("menu.plugins"))
        self._plugin_menu.add_command(t("menu.plugins.manage"), self._open_plugin_manager)
        self._plugin_menu.add_command(t("menu.plugins.marketplace"), self._open_plugin_marketplace)

    def _bind_shortcuts(self):
        stored = self._settings.global_settings.get("shortcuts.custom", {})
        defaults = {
            "new_file": "Ctrl+N",
            "open_file": "Ctrl+O",
            "open_project": "Ctrl+Shift+O",
            "save_file": "Ctrl+S",
            "save_file_as": "Ctrl+Shift+S",
            "run_check": "Ctrl+R",
            "run_code": "F5",
            "clear_output": "Ctrl+L",
            "undo": "Ctrl+Z",
            "redo": "Ctrl+Y",
            "find": "Ctrl+F",
            "replace": "Ctrl+H",
            "goto_line": "Ctrl+G",
            "goto_definition": "F12",
            "find_references": "Shift+F12",
            "reparse": "F6",
            "apply_highlight": "F7",
            "trigger_suggestions": "Ctrl+Space",
            "show_documentation": "F1",
            "toggle_comment": "Ctrl+Slash",
            "close_tab": "Ctrl+W",
            "next_tab": "Ctrl+Tab",
            "prev_tab": "Ctrl+Shift+Tab",
        }
        shortcuts = {k: stored.get(k, v) for k, v in defaults.items()}

        self._shortcut_bindings = {
            "new_file": self.window.bind(
                self._tk_shortcut(shortcuts["new_file"]), lambda e: self._new_file()
            ),
            "open_file": self.window.bind(
                self._tk_shortcut(shortcuts["open_file"]), lambda e: self._open_file()
            ),
            "open_project": self.window.bind(
                self._tk_shortcut(shortcuts["open_project"]), lambda e: self._open_project()
            ),
            "save_file": self.window.bind(
                self._tk_shortcut(shortcuts["save_file"]), lambda e: self._save_file()
            ),
            "save_file_as": self.window.bind(
                self._tk_shortcut(shortcuts["save_file_as"]), lambda e: self._save_file_as()
            ),
            "run_check": self.window.bind(
                self._tk_shortcut(shortcuts["run_check"]), lambda e: self._run_check()
            ),
            "run_code": self.window.bind(
                self._tk_shortcut(shortcuts["run_code"]), lambda e: self._run_code()
            ),
            "clear_output": self.window.bind(
                self._tk_shortcut(shortcuts["clear_output"]), lambda e: self._clear_output()
            ),
            "undo": self.window.bind(self._tk_shortcut(shortcuts["undo"]), lambda e: self._undo()),
            "redo": self.window.bind(self._tk_shortcut(shortcuts["redo"]), lambda e: self._redo()),
            "find": self.window.bind(
                self._tk_shortcut(shortcuts["find"]), lambda e: self._open_find()
            ),
            "replace": self.window.bind(
                self._tk_shortcut(shortcuts["replace"]), lambda e: self._open_replace()
            ),
            "goto_line": self.window.bind(
                self._tk_shortcut(shortcuts["goto_line"]), lambda e: self._goto_line()
            ),
            "goto_definition": self.window.bind(
                self._tk_shortcut(shortcuts["goto_definition"]), lambda e: self._goto_definition()
            ),
            "find_references": self.window.bind(
                self._tk_shortcut(shortcuts["find_references"]), lambda e: self._find_references()
            ),
            "reparse": self.window.bind(
                self._tk_shortcut(shortcuts["reparse"]), lambda e: self._reparse()
            ),
            "apply_highlight": self.window.bind(
                self._tk_shortcut(shortcuts["apply_highlight"]), lambda e: self._apply_highlight()
            ),
            "trigger_suggestions": self.window.bind(
                self._tk_shortcut(shortcuts["trigger_suggestions"]),
                lambda e: self._show_suggestions(),
            ),
            "show_documentation": self.window.bind(
                self._tk_shortcut(shortcuts["show_documentation"]),
                lambda e: self._show_documentation(),
            ),
            "toggle_comment": self.window.bind(
                self._tk_shortcut(shortcuts["toggle_comment"]), lambda e: self._toggle_comment()
            ),
            "close_tab": self.window.bind(
                self._tk_shortcut(shortcuts["close_tab"]), lambda e: self._close_active_tab()
            ),
            "next_tab": self.window.bind(
                self._tk_shortcut(shortcuts["next_tab"]), lambda e: self._next_tab()
            ),
            "prev_tab": self.window.bind(
                self._tk_shortcut(shortcuts["prev_tab"]), lambda e: self._prev_tab()
            ),
        }

    @staticmethod
    def _tk_shortcut(spec: str) -> str:
        parts = [p.strip() for p in spec.split("+") if p.strip()]
        if not parts:
            return "<>"
        key = parts[-1]
        mods = parts[:-1]
        mapping = {
            "ctrl": "Control",
            "control": "Control",
            "shift": "Shift",
            "alt": "Alt",
            "meta": "Meta",
        }
        mod_str = "-".join(mapping.get(m.lower(), m.capitalize()) for m in mods)
        if key.lower() == "space":
            key = "space"
        elif key.lower() == "slash":
            key = "/"
        if mod_str:
            return f"<{mod_str}-{key}>"
        return f"<{key}>"

    def _rebind_shortcuts(self):
        self._bind_shortcuts()

    def _lang_var(self) -> tk.StringVar:
        if not hasattr(self, "_lang_tk_var") or self._lang_tk_var is None:
            self._lang_tk_var = tk.StringVar(value=self._lang)
        return self._lang_tk_var

    def _lang_locale_var(self) -> tk.StringVar:
        if not hasattr(self, "_lang_locale_tk_var") or self._lang_locale_tk_var is None:
            current = self._settings.effective("i18n.language", "zh_CN")
            if current not in AVAILABLE_LANGUAGES:
                current = "zh_CN"
            self._lang_locale_tk_var = tk.StringVar(value=current)
        return self._lang_locale_tk_var

    def _set_language_locale(self, lang: str) -> None:
        if lang not in AVAILABLE_LANGUAGES:
            return
        if hasattr(self, "_lang_locale_tk_var") and self._lang_locale_tk_var is not None:
            self._lang_locale_tk_var.set(lang)
        self._write_setting(SettingsScope.GLOBAL, "i18n.language", lang)

    def _theme_var(self) -> tk.StringVar:
        if not hasattr(self, "_theme_tk_var") or self._theme_tk_var is None:
            self._theme_tk_var = tk.StringVar(value=theme.current().name)
        return self._theme_tk_var

    def _font_family_var(self) -> tk.StringVar:
        if not hasattr(self, "_font_family_tk_var") or self._font_family_tk_var is None:
            self._font_family_tk_var = tk.StringVar(value=self._font_family)
        return self._font_family_tk_var

    def _font_size_var(self) -> tk.IntVar:
        if not hasattr(self, "_font_size_tk_var") or self._font_size_tk_var is None:
            self._font_size_tk_var = tk.IntVar(value=self._font_size)
        return self._font_size_tk_var

    def _tab_width_var(self) -> tk.IntVar:
        if not hasattr(self, "_tab_width_tk_var") or self._tab_width_tk_var is None:
            self._tab_width_tk_var = tk.IntVar(value=self._tab_width)
        return self._tab_width_tk_var

    def _highlight_var(self) -> tk.BooleanVar:
        if not hasattr(self, "_highlight_tk_var") or self._highlight_tk_var is None:
            self._highlight_tk_var = tk.BooleanVar(value=self._highlighting_enabled)
        return self._highlight_tk_var

    def _suggestion_var(self) -> tk.BooleanVar:
        if not hasattr(self, "_suggestion_tk_var") or self._suggestion_tk_var is None:
            self._suggestion_tk_var = tk.BooleanVar(value=self._suggestions_enabled)
        return self._suggestion_tk_var

    def _autosave_var(self) -> tk.BooleanVar:
        if not hasattr(self, "_autosave_tk_var") or self._autosave_tk_var is None:
            self._autosave_tk_var = tk.BooleanVar(value=self._autosave_enabled)
        return self._autosave_tk_var

    def _highlight_theme_var(self) -> tk.StringVar:
        if not hasattr(self, "_highlight_theme_tk_var") or self._highlight_theme_tk_var is None:
            self._highlight_theme_tk_var = tk.StringVar(value=self._highlight_theme_name)
        return self._highlight_theme_tk_var

    def _build_toolbar(self):
        bar = UFrame(self.window, variant="title")
        bar.pack(fill=tk.X, padx=0, pady=0)

    def _build_editor(self):
        body = UFrame(self.window, variant="base")
        body.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)

        self._tab_bar = TabBar(
            body,
            on_select=self._tab_select,
            on_close=self._tab_close,
            on_context_menu=self._tab_context_menu,
        )
        self._tab_bar.pack(fill=tk.X, padx=0, pady=0)

        main_paned = tk.PanedWindow(
            body,
            orient=tk.HORIZONTAL,
            sashwidth=4,
            sashrelief="flat",
            bg=theme.BORDER,
            bd=0,
            showhandle=False,
        )
        main_paned.pack(fill=tk.BOTH, expand=True)

        self._editor = UText(main_paned, width=80, height=20, show_line_numbers=True)
        main_paned.add(self._editor, minsize=200, stretch="always")

        self._sidebar = SideBar(
            main_paned,
            items=[
                ("explorer", "Explorer", "explorer"),
                ("debug", "Debug", "debug"),
                ("git", "Git", "git"),
            ],
            on_select=self._on_sidebar_select,
        )
        main_paned.add(self._sidebar, minsize=240, stretch="never")

        self._explorer_card = ExplorerCard(self._sidebar, on_activate=self._open_path_from_tree)
        self._sidebar.add_card("explorer", self._explorer_card)

        self._debug_card = DebugCard(self._sidebar)
        self._sidebar.add_card("debug", self._debug_card)

        self._git_card = GitCard(self._sidebar)
        self._sidebar.add_card("git", self._git_card)

        self._sidebar.set_active("explorer")

        self._editor._text.bind("<KeyRelease>", self._on_key_release)
        self._editor._text.bind("<KeyPress>", self._on_key_press)
        self._editor._text.bind("<ButtonRelease-1>", self._on_click)
        self._editor._text.bind("<FocusIn>", self._on_focus_in)
        self._editor._text.bind("<FocusOut>", self._on_focus_out)
        self._editor._text.bind("<Button-3>", self._show_editor_context_menu)
        self._editor._text.config(undo=True)

    def _on_sidebar_select(self, card_id: str) -> None:
        if card_id == "explorer" and self._current_project_root:
            self._explorer_card.set_root(self._current_project_root)
        elif card_id == "git" and self._current_project_root:
            self._git_card.set_workspace_root(self._current_project_root)

    def _open_path_from_tree(self, path: str) -> None:
        self._load_file_into_editor(path)

    def _load_file_into_editor(self, path: str) -> None:
        if self._dirty and not tk.messagebox.askyesno(
            t("dialog.title.unsaved_discard"),
            t("dialog.unsaved_discard.message"),
        ):
            return
        self._load_path_into_editor(path)

    @staticmethod
    def _detect_lang_from_path(path: str) -> str:
        _, ext = os.path.splitext(path)
        ext = ext.lower()
        for lang, config in LANG_CONFIG.items():
            if config["ext"] == ext:
                return lang
        return "Python"

    def _load_path_into_editor(self, path: str) -> None:
        threshold_raw = self._settings.global_settings.get(
            "editor.large_file_threshold_bytes", 5 * 1024 * 1024
        )
        try:
            threshold = max(0, int(threshold_raw))
        except (TypeError, ValueError):
            threshold = 5 * 1024 * 1024

        try:
            size = os.path.getsize(path)
        except OSError as e:
            tk.messagebox.showerror(t("dialog.title.open_failed"), str(e), parent=self.window)
            return

        is_large = threshold > 0 and size >= threshold

        if is_large:
            tk.messagebox.showwarning(
                t("dialog.title.large_file"),
                t(
                    "dialog.large_file.message",
                    size=self._human_size(size),
                    threshold=self._human_size(threshold),
                ),
                parent=self.window,
            )

        self._stream_epoch += 1
        self._editor._text.config(state="normal")
        self._large_file_mode = False

        doc_id = path
        detected_lang = self._detect_lang_from_path(path)
        doc = Document(path=path, content="", dirty=False, lang=detected_lang, seq=0)
        self._documents[doc_id] = doc
        self._active_id = doc_id

        self._editor._text.delete("1.0", tk.END)
        self._current_file = path
        self._dirty = False

        if is_large:
            self._status_label.config(
                text=t("status.loading", name=os.path.basename(path), size=self._human_size(size))
            )
            self._stream_insert_into_editor(path, size, doc_id)
        else:
            try:
                with open(path, encoding="utf-8") as f:
                    code = f.read()
            except OSError as e:
                self._active_id = None
                self._documents.pop(doc_id, None)
                self._current_file = None
                self._editor._text.delete("1.0", tk.END)
                tk.messagebox.showerror(t("dialog.title.open_failed"), str(e), parent=self.window)
                return
            except UnicodeDecodeError as e:
                self._active_id = None
                self._documents.pop(doc_id, None)
                self._current_file = None
                self._editor._text.delete("1.0", tk.END)
                tk.messagebox.showerror(t("dialog.title.open_failed"), str(e), parent=self.window)
                return
            doc.content = code
            self._editor._text.insert("1.0", code)
            self._status_label.config(text=t("status.opened", name=os.path.basename(path)))

        self._update_tab_bar()

        new_root = self._should_reattach_for_path(path)
        if new_root:
            self._attach_project(new_root)

        if not is_large:
            if detected_lang != self._lang:
                self._switch_language(detected_lang, from_doc_switch=True)
            self._apply_highlight()
        if is_large:
            self._last_emit_code = None
        else:
            self._last_emit_code = self._editor.get("1.0", "end-1c")
        self._emit(HookEvents.EDITOR_FILE_OPENED, path)

    def _stream_insert_into_editor(self, path: str, total_size: int, doc_id: str) -> None:
        chunk_size = 64 * 1024
        try:
            f = open(path, encoding="utf-8", errors="replace")  # noqa: SIM115
        except OSError as e:
            tk.messagebox.showerror(t("dialog.title.open_failed"), str(e), parent=self.window)
            self._large_file_mode = False
            self._editor._text.config(state="normal")
            self._status_label.config(text=t("status.open_failed"))
            return

        self._stream_epoch += 1
        my_epoch = self._stream_epoch
        self._large_file_mode = True
        self._editor._text.config(state="disabled")
        accumulated: list[str] = []

        def insert_chunk() -> None:
            if my_epoch != self._stream_epoch:
                with contextlib.suppress(Exception):
                    f.close()
                return
            try:
                chunk = f.read(chunk_size)
            except OSError as e:
                with contextlib.suppress(Exception):
                    f.close()
                self._editor._text.config(state="normal")
                self._large_file_mode = False
                tk.messagebox.showerror(t("dialog.title.read_failed"), str(e), parent=self.window)
                self._status_label.config(text=t("status.read_failed"))
                return

            if not chunk:
                with contextlib.suppress(Exception):
                    f.close()
                self._editor._text.config(state="normal")
                self._large_file_mode = False
                self._status_label.config(text=t("status.opened", name=os.path.basename(path)))
                if doc_id in self._documents:
                    self._documents[doc_id].content = "".join(accumulated)
                with contextlib.suppress(tk.TclError):
                    self._last_emit_code = self._editor.get("1.0", "end-1c")
                self._emit(HookEvents.EDITOR_FILE_OPENED, path)
                return

            accumulated.append(chunk)
            self._editor._text.insert(self._editor._text.index("end-1c"), chunk)
            self.window.after(1, insert_chunk)

        self.window.after(1, insert_chunk)

    @staticmethod
    def _human_size(nbytes: int) -> str:
        try:
            n = float(max(0, int(nbytes)))
        except (TypeError, ValueError):
            return f"{nbytes} B"
        for unit in ("B", "KB", "MB", "GB"):
            if n < 1024.0 or unit == "GB":
                if unit == "B":
                    return f"{int(n)} {unit}"
                return f"{n:.1f} {unit}"
            n /= 1024.0
        return f"{nbytes} B"

    def _build_output_panel(self):
        self._output_frame = UFrame(self.window, variant="panel", height=120)
        self._output_frame.pack(fill=tk.X, padx=0, pady=0)
        self._output_frame.pack_propagate(False)

        header = UFrame(self._output_frame, variant="title")
        header.pack(fill=tk.X)
        ULabel(header, text=t("panel.output"), variant="secondary", bg=theme.BG_TITLE).pack(
            side=tk.LEFT, padx=4, pady=2
        )

        self._output = UText(self._output_frame, width=80, height=5)
        self._output.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)
        self._output._text.config(state="disabled")

    def _build_status_bar(self):
        status = UFrame(self.window, variant="title", height=24)
        status.pack(fill=tk.X, padx=0, pady=0)
        status.pack_propagate(False)

        self._status_label = ULabel(
            status, text=t("status.ready"), variant="secondary", bg=theme.BG_TITLE
        )
        self._status_label.pack(side=tk.LEFT, padx=10, pady=2)

        self._lang_label = ULabel(status, text="Python", variant="secondary", bg=theme.BG_TITLE)
        self._lang_label.pack(side=tk.RIGHT, padx=10, pady=2)

        self._pos_label = ULabel(status, text="Ln 1, Col 1", variant="secondary", bg=theme.BG_TITLE)
        self._pos_label.pack(side=tk.RIGHT, padx=10, pady=2)

    def _switch_language(self, lang, *, from_doc_switch: bool = False):
        if lang not in LANG_CONFIG:
            return
        self._lang = lang
        if hasattr(self, "_lang_tk_var") and self._lang_tk_var is not None:
            self._lang_tk_var.set(lang)
        config = LANG_CONFIG[lang]
        if "highlighter_factory" in config:
            self._highlighter = config["highlighter_factory"]()
            self._suggestion_expert = config["suggestion_factory"]()
        else:
            self._highlighter = config["highlighter"]()
            self._suggestion_expert = config["suggestion"]()
        self._lang_label.config(text=lang)
        self._stream_epoch += 1
        self._editor._text.config(state="normal")
        self._large_file_mode = False
        if not from_doc_switch:
            self._editor._text.delete("1.0", tk.END)
            self._editor._text.insert("1.0", config["sample"])
            if self._active_id and self._active_id in self._documents:
                self._documents[self._active_id].lang = lang
            self._apply_highlight()
        self._update_status()
        self._status_label.config(text=t("status.editor_lang_changed", lang=lang))
        self.window.after(3000, lambda: self._status_label.config(text=t("status.ready")))
        app_logger.info(f"Language switched to: {lang}")
        self._emit(HookEvents.EDITOR_LANGUAGE_CHANGED, lang)

    def _on_lang_changed(self, value):
        self._switch_language(value)

    def _on_key_release(self, event=None):
        self._update_status()
        self._schedule_highlight()
        if self._suggestions_enabled:
            self._schedule_suggestions()
        self._schedule_autosave()
        self._mark_dirty()
        self._emit_content_changed()
        self._emit_selection_changed()

    def _schedule_highlight(self) -> None:
        if not self._highlighting_enabled:
            self._highlight_debouncer.cancel()
            return
        self._highlight_debouncer.schedule(self._run_scheduled_highlight, self._highlight_delay_ms)

    def _cancel_pending_highlight(self) -> None:
        self._highlight_debouncer.cancel()

    def _run_scheduled_highlight(self) -> None:
        self._apply_highlight()

    def _schedule_suggestions(self) -> None:
        if not self._suggestions_enabled:
            self._suggest_debouncer.cancel()
            return
        self._suggest_debouncer.schedule(self._run_scheduled_suggestions, self._suggest_delay_ms)

    def _cancel_pending_suggestions(self) -> None:
        self._suggest_debouncer.cancel()

    def _run_scheduled_suggestions(self) -> None:
        try:
            self._show_suggestions()
        except Exception:
            app_logger.exception("_run_scheduled_suggestions failed")

    def _schedule_autosave(self) -> None:
        if not self._autosave_enabled:
            self._autosave_debouncer.cancel()
            return
        self._autosave_debouncer.schedule(self._do_autosave, self._autosave_delay_ms)

    def _do_autosave(self) -> None:
        if not self._autosave_enabled:
            return
        if not (self._active_id and self._active_id in self._documents):
            return
        doc = self._documents[self._active_id]
        if not doc.dirty:
            return
        if doc.path:
            self._save_to_path(doc.path)
        else:
            path = self._autosave_paths.get(self._active_id)
            if path and os.path.exists(path):
                self._save_to_path(path)
            else:
                path = self._format_autosave_path()
                with contextlib.suppress(OSError):
                    os.makedirs(os.path.dirname(path), exist_ok=True)
                self._save_to_path(path)
                self._documents[self._active_id].path = path
                self._current_file = path
                self._autosave_paths[self._active_id] = path

    def _format_autosave_path(self) -> str:
        import time

        now = time.localtime()
        ts = time.time()
        fields = {
            "year": f"{now.tm_year:04d}",
            "month": f"{now.tm_mon:02d}",
            "day": f"{now.tm_mday:02d}",
            "hour": f"{now.tm_hour:02d}",
            "minute": f"{now.tm_min:02d}",
            "second": f"{now.tm_sec:02d}",
            "unix.seconds": f"{int(ts)}",
            "unix.float": f"{ts:.3f}",
        }
        fmt = self._autosave_format
        name = fmt.format_map(dict(fields.items()))
        name = "".join(c if c.isalnum() or c in "._- " else "_" for c in name)
        cache = os.path.join(tempfile.gettempdir(), "PythonEditor", "autosave")
        return os.path.join(cache, f"{name}.py")

    def _on_key_press(self, event=None):
        if self._suggestion_popup and self._suggestion_popup.winfo_exists():
            if event and event.keysym in ("Escape",):
                self._suggestion_popup.hide()
            elif event and event.keysym in ("Down", "Up", "Return", "Tab"):
                return

    def _on_click(self, event=None):
        self._update_status()
        self._cancel_pending_suggestions()
        self._emit_cursor_moved()
        self._emit_selection_changed()

    def _emit_selection_changed(self) -> None:
        try:
            selection = self._editor._text.selection_get()
        except tk.TclError:
            selection = ""
        last = getattr(self, "_last_selection", None)
        if last == selection:
            return
        self._last_selection = selection
        self._emit(HookEvents.EDITOR_SELECTION_CHANGED, selection)

    def _on_focus_in(self, event=None):
        self._update_status()
        self._cancel_pending_suggestions()
        self._emit_cursor_moved()
        self._emit(HookEvents.EDITOR_FOCUS_CHANGED, True)

    def _on_focus_out(self, event=None):
        self._emit(HookEvents.EDITOR_FOCUS_CHANGED, False)

    def _emit_cursor_moved(self) -> None:
        try:
            cursor = self._editor._text.index(tk.INSERT)
            line, col = cursor.split(".")
            line_i, col_i = int(line), int(col)
        except Exception:
            return
        last = getattr(self, "_last_cursor", None)
        if last == (line_i, col_i):
            return
        self._last_cursor = (line_i, col_i)
        self._emit(HookEvents.EDITOR_CURSOR_MOVED, line_i, col_i)

    def _apply_highlight(self):
        if self._large_file_mode:
            return
        if not self._highlighting_enabled:
            return
        code = self._editor.get("1.0", "end-1c")
        if not code.strip():
            return
        block = HighlightBlock(code=code, tokens=None)
        result = self._highlighter.highlight(block)
        if result.tokens is None:
            return

        hl_tokens = highlight_themes.tokens()
        if not hl_tokens:
            hl_tokens = HIGHLIGHT_TOKENS

        text = self._editor._text

        highlight_line = getattr(self, "_highlighted_line", None)
        highlight_color = getattr(self, "_highlighted_line_color", theme.YELLOW)

        for tag in text.tag_names():
            if tag != "definition_highlight":
                text.tag_delete(tag)

        for token_type, style in hl_tokens.items():
            text.tag_configure(token_type, **style)

        for token in result.tokens:
            start = self._index_from_pos(token.start)
            end = self._index_from_pos(token.end)
            tag = token.type if token.type in hl_tokens else "identifier"
            text.tag_add(tag, start, end)

        if highlight_line is not None:
            text.tag_config(
                "definition_highlight", background=highlight_color, foreground=theme.BG_BASE
            )
            text.tag_add("definition_highlight", f"{highlight_line}.0", f"{highlight_line}.end")

    def highlight_line(self, line_no: int, color: str | None = None) -> None:
        """Highlight a specific line with an optional color.

        Args:
            line_no: Line number to highlight (1-indexed)
            color: Background color for the highlight, defaults to theme.YELLOW
        """
        if self._highlight_after_id is not None:
            self.window.after_cancel(self._highlight_after_id)
            self._highlight_after_id = None

        text = self._editor._text
        self._highlighted_line = line_no
        self._highlighted_line_color = color if color is not None else theme.YELLOW
        text.tag_config(
            "definition_highlight",
            background=self._highlighted_line_color,
            foreground=theme.BG_BASE,
        )
        text.tag_remove("definition_highlight", "1.0", "end")
        text.tag_add("definition_highlight", f"{line_no}.0", f"{line_no}.end")

        if self._definition_highlight_duration_ms > 0:

            def _auto_clear():
                self._highlight_after_id = None
                self.clear_highlight()

            self._highlight_after_id = self.window.after(
                self._definition_highlight_duration_ms, _auto_clear
            )

    def clear_highlight(self) -> None:
        """Clear the line highlight."""
        self._highlighted_line = None
        self._highlighted_line_color = theme.YELLOW
        text = self._editor._text
        text.tag_remove("definition_highlight", "1.0", "end")

    def _show_suggestions(self):
        if self._large_file_mode:
            return
        if not self._suggestions_enabled:
            return
        if self._suggestion_expert is None:
            return
        code = self._editor.get("1.0", "end-1c")
        cursor = self._editor._text.index(tk.INSERT)
        line, col = map(int, cursor.split("."))
        position = sum(len(line_text) + 1 for line_text in code.split("\n")[: line - 1]) + col
        block = SuggestionBlock(code=code, position=position)
        suggestions = self._suggestion_expert.suggest(block)

        if not suggestions:
            if self._suggestion_popup:
                self._suggestion_popup.hide()
            return

        max_suggestions = self._settings.global_settings.get("completion.max_suggestions", 20)
        max_visible = self._settings.global_settings.get("completion.max_visible", 8)
        items = [
            CompletionItem(label=s.label, priority=s.priority, kind=s.kind)
            for s in suggestions[:max_suggestions]
        ]
        if self._suggestion_popup and self._suggestion_popup.winfo_exists():
            self._suggestion_popup.set_items(items)
            self._suggestion_popup.show(attach_to=self._editor._text, index=tk.INSERT)
        else:
            self._suggestion_popup = UEditorSuggestion(
                self._editor,
                items=items,
                on_select=self._on_suggestion_select,
                max_visible=max_visible,
                show_detail=False,
                show_description=False,
            )
            self._suggestion_popup.show(attach_to=self._editor._text, index=tk.INSERT)

    def _hide_suggestions(self):
        if self._suggestion_popup and self._suggestion_popup.winfo_exists():
            self._suggestion_popup.hide()

    def _on_suggestion_select(self, item):
        text = self._editor._text
        cursor = text.index(tk.INSERT)
        line, col = map(int, cursor.split("."))

        line_start = f"{line}.0"
        line_text = text.get(line_start, cursor)
        word_start = col
        while word_start > 0 and (
            line_text[word_start - 1].isalnum() or line_text[word_start - 1] == "_"
        ):
            word_start -= 1

        text.delete(f"{line}.{word_start}", cursor)
        text.insert(f"{line}.{word_start}", item.insert)
        self._apply_highlight()

    def _get_word_under_cursor(self, x: int | None = None, y: int | None = None) -> str:
        """Get the identifier (word) at cursor position or at given coordinates."""
        text = self._editor._text
        try:
            if x is not None and y is not None:
                cursor = text.index(f"@{x},{y}")
            else:
                cursor = text.index(tk.INSERT)
        except Exception:
            return ""
        line, col = map(int, cursor.split("."))
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

    def _find_symbol_definitions(self, code: str, symbol: str) -> list[tuple[int, str]]:
        """Find all definition locations (line_no, line_text) for a symbol in code.
        Uses regex to find class/function definitions, variable assignments,
        and import statements. Returns list sorted by line number.
        """
        results: list[tuple[int, str]] = []
        lines = code.split("\n")

        for ln, line_text in enumerate(lines, start=1):
            stripped = line_text.strip()
            # Skip comments and empty lines
            if not stripped or stripped.startswith("#"):
                continue

            # Class definition: class Symbol(...):
            m = re.match(
                r"^\s*class\s+(" + re.escape(symbol) + r")\s*(?:\([^()]*\))?\s*:",
                line_text,
            )
            if m:
                results.append((ln, line_text))
                continue

            # Function/method definition: def symbol(...):
            m = re.match(
                r"^\s*(?:async\s+)?def\s+(" + re.escape(symbol) + r")\s*\(",
                line_text,
            )
            if m:
                results.append((ln, line_text))
                continue

            # Import: import symbol or from ... import symbol
            m = re.match(r"^\s*import\s+.*\b" + re.escape(symbol) + r"\b", line_text)
            if m:
                results.append((ln, line_text))
                continue
            m = re.match(r"^\s*from\s+\S+\s+import\s+.*\b" + re.escape(symbol) + r"\b", line_text)
            if m:
                results.append((ln, line_text))
                continue

            # Variable/attribute assignment: symbol = ... or self.symbol = ...
            assign_pattern = re.compile(
                r"(?:^|\s)(?:self\.)?\b" + re.escape(symbol) + r"\s*(?::\s*[^=]+)?\s*=\s*"
            )
            if assign_pattern.search(line_text):
                results.append((ln, line_text))
                continue

            # Class/function decorator assignment (e.g., @symbol)
            decorator_pattern = re.compile(r"^\s*@" + re.escape(symbol) + r"\b")
            if decorator_pattern.match(line_text):
                results.append((ln, line_text))
                continue

        return results

    def _index_from_pos(self, pos):
        code = self._editor.get("1.0", "end-1c")
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

    def _update_status(self):
        cursor = self._editor._text.index(tk.INSERT)
        line, col = cursor.split(".")
        self._pos_label.config(text=t("status.pos", line=line, col=int(col) + 1))

    def _new_file(self):
        if self._active_id and self._documents.get(self._active_id):
            curr = self._documents[self._active_id]
            if curr.dirty:
                result = tk.messagebox.askyesno(
                    t("dialog.title.unsaved_discard"),
                    t("dialog.unsaved_discard.message"),
                )
                if not result:
                    return

        seq = self._next_untitled_seq
        doc_id = self._new_doc_id()
        self._documents[doc_id] = Document(
            path=None, content="", dirty=False, lang=self._lang, seq=seq
        )
        self._next_untitled_seq += 1
        self._active_id = doc_id

        self._stream_epoch += 1
        self._editor._text.config(state="normal")
        self._large_file_mode = False
        self._editor._text.delete("1.0", tk.END)
        self._current_file = None
        self._dirty = False
        self._last_emit_code = ""
        self._status_label.config(text=t("status.new_file"))
        self._update_tab_bar()
        self._emit(HookEvents.EDITOR_FILE_CREATED)
        app_logger.info(f"New file created: {doc_id}")

    def _open_file(self):
        if self._active_id and self._documents.get(self._active_id):
            curr = self._documents[self._active_id]
            if curr.dirty:
                result = tk.messagebox.askyesno(
                    t("dialog.title.unsaved_discard"),
                    t("dialog.unsaved_discard.message"),
                )
                if not result:
                    return

        ext = LANG_CONFIG[self._lang]["ext"]
        lang_label = t("file_dialog.lang_filter", lang=self._lang)
        filetypes = [(lang_label, f"*{ext}"), (t("file_dialog.all_files"), "*.*")]
        path = tk.filedialog.askopenfilename(filetypes=filetypes)
        if not path:
            return

        for doc_id, doc in self._documents.items():
            if doc.path == path:
                self._switch_document(doc_id)
                return

        self._load_path_into_editor(path)
        app_logger.info(f"File opened: {path}")

    def _open_project(self):
        if self._dirty and not tk.messagebox.askyesno(
            t("dialog.title.unsaved_discard"),
            t("dialog.unsaved_discard.message"),
        ):
            return
        initial = self._current_project_root or os.getcwd()
        chosen = tk.filedialog.askdirectory(
            title=t("dialog.title.choose_project"),
            initialdir=initial if os.path.isdir(initial) else None,
            parent=self.window,
        )
        if not chosen:
            return
        self._attach_project(chosen)
        if os.path.isdir(chosen):
            self._status_label.config(
                text=t("status.project", name=os.path.basename(chosen) or chosen)
            )

    def _save_file(self):
        if self._active_id and self._documents.get(self._active_id):
            doc = self._documents[self._active_id]
            if doc.path:
                self._save_to_path(doc.path)
            else:
                self._save_file_as()
        else:
            self._save_file_as()

    def _save_file_as(self):
        ext = str(LANG_CONFIG[self._lang]["ext"])
        lang_label = t("file_dialog.lang_filter", lang=self._lang)
        filetypes = [(lang_label, f"*{ext}"), (t("file_dialog.all_files"), "*.*")]
        path = tk.filedialog.asksaveasfilename(defaultextension=ext, filetypes=filetypes)
        if path:
            self._save_to_path(path)
            if self._active_id and self._active_id in self._documents:
                self._documents[self._active_id].path = path
            self._current_file = path
            detected_lang = self._detect_lang_from_path(path)
            if detected_lang != self._lang:
                self._switch_language(detected_lang, from_doc_switch=True)
            new_root = self._should_reattach_for_path(path)
            if new_root:
                self._attach_project(new_root)

    def _save_to_path(self, path: str):
        code = self._editor.get("1.0", "end-1c")
        self._emit(HookEvents.EDITOR_BEFORE_SAVE, path)
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(code)
        except OSError as e:
            app_logger.error(f"Failed to save file {path}: {e}")
            tk.messagebox.showerror(t("dialog.title.save_failed"), str(e))
            return
        self._dirty = False
        if self._active_id and self._active_id in self._documents:
            self._documents[self._active_id].dirty = False
            self._documents[self._active_id].content = code
        self._update_tab_bar()
        app_logger.info(f"File saved: {path}")
        self._status_label.config(text=t("status.saved", name=os.path.basename(path)))
        self._emit(HookEvents.EDITOR_FILE_SAVED, path)

    def _undo(self):
        with contextlib.suppress(tk.TclError):
            self._editor._text.edit_undo()
        self._apply_highlight()

    def _redo(self):
        with contextlib.suppress(tk.TclError):
            self._editor._text.edit_redo()
        self._apply_highlight()

    def _cut(self):
        widget = self.window.focus_get()
        if widget is not None:
            widget.event_generate("<<Cut>>")
        self._apply_highlight()

    def _copy(self):
        widget = self.window.focus_get()
        if widget is not None:
            widget.event_generate("<<Copy>>")

    def _paste(self):
        widget = self.window.focus_get()
        if widget is not None:
            widget.event_generate("<<Paste>>")
        self._apply_highlight()

    def _select_all(self):
        self._editor._text.tag_add("sel", "1.0", "end")
        self._editor._text.mark_set(tk.INSERT, "1.0")
        self._editor._text.see(tk.INSERT)

    def _open_find(self):
        self._show_find_dialog(replace=False)

    def _open_replace(self):
        self._show_find_dialog(replace=True)

    def _show_find_dialog(self, replace: bool):
        if self._find_dialog and self._find_dialog.winfo_exists():
            self._find_dialog.destroy()
        dlg = tk.Toplevel(self.window)
        dlg.title(t("dialog.title.replace") if replace else t("dialog.title.find"))
        dlg.configure(bg=theme.BG_PANEL)
        dlg.transient(self.window)
        dlg.resizable(False, False)

        ULabel(dlg, text=t("find.find_label"), bg=theme.BG_PANEL).grid(
            row=0, column=0, sticky="e", padx=6, pady=6
        )
        find_var = tk.StringVar(value=self._find_query)
        find_entry = tk.Entry(
            dlg,
            textvariable=find_var,
            width=30,
            bg=theme.BG_INPUT,
            fg=theme.FG_PRIMARY,
            insertbackground=theme.FG_PRIMARY,
        )
        find_entry.grid(row=0, column=1, columnspan=2, sticky="ew", padx=6, pady=6)

        replace_var = None
        replace_entry = None
        if replace:
            ULabel(dlg, text=t("find.replace_label"), bg=theme.BG_PANEL).grid(
                row=1, column=0, sticky="e", padx=6, pady=6
            )
            replace_var = tk.StringVar()
            replace_entry = tk.Entry(
                dlg,
                textvariable=replace_var,
                width=30,
                bg=theme.BG_INPUT,
                fg=theme.FG_PRIMARY,
                insertbackground=theme.FG_PRIMARY,
            )
            replace_entry.grid(row=1, column=1, columnspan=2, sticky="ew", padx=6, pady=6)

        case_var = tk.BooleanVar(value=False)
        tk.Checkbutton(
            dlg,
            text=t("find.case_sensitive"),
            variable=case_var,
            bg=theme.BG_PANEL,
            fg=theme.FG_PRIMARY,
            selectcolor=theme.BG_RAISED,
            activebackground=theme.BG_PANEL,
        ).grid(row=2, column=0, columnspan=3, sticky="w", padx=6)

        def do_find(*_):
            query = find_var.get()
            if not query:
                return
            self._find_query = query
            text = self._editor._text
            start = text.index(tk.INSERT)
            if self._find_last_index:
                start = self._find_last_index
            nocase = not case_var.get()
            pos = text.search(query, start, stopindex="end", nocase=nocase)
            if not pos:
                pos = text.search(query, "1.0", stopindex=start, nocase=nocase)
                if not pos:
                    tk.messagebox.showinfo(
                        t("dialog.title.find_not_found"), t("dialog.find.not_found"), parent=dlg
                    )
                    return
            end = f"{pos}+{len(query)}c"
            text.tag_remove("sel", "1.0", "end")
            text.tag_add("sel", pos, end)
            text.mark_set(tk.INSERT, end)
            text.see(pos)
            self._find_last_index = str(end)

        def do_replace():
            do_find()
            replace_text = replace_var.get() if replace_var else ""
            sel = self._editor._text.tag_ranges("sel")
            if sel:
                self._editor._text.delete(sel[0], sel[1])
                self._editor._text.insert(sel[0], replace_text)
                self._find_last_index = str(sel[0])
                self._apply_highlight()

        def do_replace_all():
            query = find_var.get()
            if not query:
                return
            replace_text = replace_var.get() if replace_var else ""
            self._find_query = query
            text = self._editor._text
            nocase = not case_var.get()
            count = 0
            pos = text.search(query, "1.0", stopindex="end", nocase=nocase)
            while pos:
                end = f"{pos}+{len(query)}c"
                text.delete(pos, end)
                text.insert(pos, replace_text)
                count += 1
                pos = text.search(
                    query, f"{pos}+{len(replace_text)}c", stopindex="end", nocase=nocase
                )
            self._apply_highlight()
            tk.messagebox.showinfo(
                t("dialog.title.replace_done"), t("dialog.replace.done", count=count), parent=dlg
            )

        def close():
            self._find_dialog = None
            dlg.destroy()

        btn_row = 3 if replace else 2
        UButton(
            dlg,
            text=t("find.find_next"),
            command=do_find,
            variant="primary",
            width=80,
            height=24,
        ).grid(row=btn_row, column=0, padx=4, pady=6)
        if replace:
            UButton(
                dlg,
                text=t("find.replace"),
                command=do_replace,
                variant="default",
                width=60,
                height=24,
            ).grid(row=btn_row, column=1, padx=4, pady=6)
            UButton(
                dlg,
                text=t("find.replace_all"),
                command=do_replace_all,
                variant="warning",
                width=80,
                height=24,
            ).grid(row=btn_row, column=2, padx=4, pady=6)
        else:
            UButton(
                dlg, text=t("find.close"), command=close, variant="default", width=60, height=24
            ).grid(row=btn_row, column=1, columnspan=2, padx=4, pady=6, sticky="ew")

        dlg.protocol("WM_DELETE_WINDOW", close)
        find_entry.focus_set()
        self._find_dialog = dlg

    def _goto_line(self):
        line_no = tk.simpledialog.askinteger(
            t("dialog.title.goto_line"),
            t("dialog.goto_line.prompt"),
            parent=self.window,
            minvalue=1,
            maxvalue=self._line_count(),
        )
        if not line_no:
            return
        self._editor._text.mark_set(tk.INSERT, f"{line_no}.0")
        self._editor._text.see(f"{line_no}.0")
        self._update_status()

    def _line_count(self) -> int:
        return int(self._editor._text.index("end-1c").split(".")[0])

    def _indent(self):
        text = self._editor._text
        sel = text.tag_ranges("sel")
        if sel:
            start_obj = sel[0]
            end_obj = sel[1]
            start_str = str(start_obj)
            end_str = str(end_obj)
        else:
            start_str = text.index(tk.INSERT)
            end_str = start_str
        start_line = int(start_str.split(".")[0])
        end_line = int(end_str.split(".")[0])
        indent = " " * self._tab_width
        for ln in range(start_line, end_line + 1):
            line_start = f"{ln}.0"
            text.insert(line_start, indent)
        new_start = f"{start_line}.0"
        new_end = f"{end_line}.{len(text.get(f'{end_line}.0', f'{end_line}.end'))}"
        text.tag_remove("sel", "1.0", "end")
        text.tag_add("sel", new_start, new_end)

    def _outdent(self):
        text = self._editor._text
        sel = text.tag_ranges("sel")
        if sel:
            start_obj = sel[0]
            end_obj = sel[1]
            start_str = str(start_obj)
            end_str = str(end_obj)
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
            for i in range(min(self._tab_width, removed)):
                if line_text[i] == " ":
                    text.delete(f"{ln}.{i}")
                else:
                    break

    def _toggle_comment(self):
        if self._lang != "Python":
            tk.messagebox.showinfo(
                t("dialog.title.toggle_comment"),
                t("dialog.toggle_comment.unsupported", lang=self._lang),
                parent=self.window,
            )
            return
        text = self._editor._text
        sel = text.tag_ranges("sel")
        if sel:
            start_obj = sel[0]
            end_obj = sel[1]
            start_str = str(start_obj)
            end_str = str(end_obj)
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

    def _goto_definition(self):
        """Jump to the definition of the symbol under the cursor."""
        if self._large_file_mode:
            return
        code = self._editor.get("1.0", "end-1c")
        if not code.strip():
            return
        word = self._get_word_under_cursor(self._context_click_x, self._context_click_y)
        if not word:
            return
        definitions = self._find_symbol_definitions(code, word)
        if not definitions:
            tk.messagebox.showinfo(
                t("dialog.title.goto_definition"),
                t("dialog.goto_definition.not_found", symbol=word),
                parent=self.window,
            )
            return
        # Jump to the first definition
        target_line, _ = definitions[0]
        self._highlighted_line = target_line
        self._editor._text.mark_set(tk.INSERT, f"{target_line}.0")
        self._editor._text.see(tk.INSERT)
        self.highlight_line(target_line)
        self._status_label.config(text=t("status.goto_definition", line=target_line))

    def _find_references(self):
        """Find all references of the symbol under the cursor in the current file."""
        if self._large_file_mode:
            return
        code = self._editor.get("1.0", "end-1c")
        if not code.strip():
            return
        word = self._get_word_under_cursor(self._context_click_x, self._context_click_y)
        if not word:
            return

        # Search for all occurrences of the word (as a whole word)
        pattern = re.compile(r"\b" + re.escape(word) + r"\b")
        matches: list[tuple[int, str]] = []
        for ln, line_text in enumerate(code.split("\n"), start=1):
            if pattern.search(line_text):
                matches.append((ln, line_text.strip()))

        if not matches:
            tk.messagebox.showinfo(
                t("dialog.title.find_references"),
                t("dialog.find_references.not_found", symbol=word),
                parent=self.window,
            )
            return

        # Build a results popup
        self._show_references_dialog(word, matches)

    def _find_documentation(self):
        """Show documentation for the symbol under the cursor via Python introspection."""
        if self._lang != "Python":
            tk.messagebox.showinfo(
                t("dialog.title.find_documentation"),
                t("dialog.find_documentation.unsupported_lang", lang=self._lang),
                parent=self.window,
            )
            return
        word = self._get_word_under_cursor()
        if not word:
            return

        doc = self._lookup_documentation(word)
        if doc is None:
            tk.messagebox.showinfo(
                t("dialog.title.find_documentation"),
                t("dialog.find_documentation.not_found", symbol=word),
                parent=self.window,
            )
            return

        # Show documentation in a scrolled messagebox-style dialog
        dlg = tk.Toplevel(self.window)
        dlg.title(t("dialog.title.find_documentation") + f": {word}")
        dlg.configure(bg=theme.BG_PANEL)
        dlg.transient(self.window)
        dlg.geometry("520x400")
        dlg.minsize(360, 200)

        header = ULabel(
            dlg,
            text=f"**{word}**  " + doc.get("type", ""),
            bg=theme.BG_PANEL,
            fg=theme.FG_PRIMARY,
            font=(self._font_family, self._font_size + 2, "bold"),
        )
        header.pack(fill="x", padx=12, pady=(12, 4))

        sig_frame = UFrame(dlg, bg=theme.BG_PANEL)
        sig_frame.pack(fill="x", padx=12, pady=(0, 4))
        sig = doc.get("signature", "")
        if sig:
            ULabel(
                sig_frame,
                text=sig,
                bg=theme.BG_PANEL,
                fg=theme.FG_ACCENT,
                font=("Consolas", self._font_size),
            ).pack(anchor="w")

        # Docstring text area
        text_frame = UFrame(dlg, bg=theme.BG_BASE)
        text_frame.pack(fill="both", expand=True, padx=12, pady=(0, 8))

        doc_text = tk.Text(
            text_frame,
            wrap="word",
            bg=theme.BG_BASE,
            fg=theme.FG_PRIMARY,
            font=(self._font_family, self._font_size),
            relief="flat",
            padx=8,
            pady=8,
        )
        doc_text.pack(fill="both", expand=True)
        doc_text.insert("1.0", doc.get("doc", t("dialog.find_documentation.no_doc")))
        doc_text.config(state="disabled")

        # Scrollbar
        scrollbar = tk.Scrollbar(text_frame, command=doc_text.yview)
        scrollbar.pack(side="right", fill="y")
        doc_text.config(yscrollcommand=scrollbar.set)

        # Source info
        source = doc.get("source", "")
        if source:
            ULabel(
                dlg,
                text=t("dialog.find_documentation.from_module", module=source),
                bg=theme.BG_PANEL,
                fg=theme.FG_DIM,
                font=(self._font_family, self._font_size - 1),
            ).pack(fill="x", padx=12, pady=(0, 4))

        close_btn = UButton(
            dlg,
            text=t("find.close"),
            command=dlg.destroy,
            variant="primary",
            width=80,
            height=28,
        )
        close_btn.pack(pady=(0, 12))

        dlg.wait_window()

    def _lookup_documentation(self, symbol: str) -> dict | None:
        """Try to introspect a Python symbol and return its documentation info.

        Returns dict with keys: 'doc', 'type', 'signature', 'source'
        or None if unresolvable.
        """
        parts = symbol.split(".")
        result: dict = {}
        try:
            # Try importing the top-level module
            top = parts[0]
            namespace = __import__(top)
            obj = namespace
            # Walk the dotted path
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

        # Fallback: check builtins
        import builtins

        obj = getattr(builtins, symbol, None)
        if obj is not None:
            result["doc"] = (getattr(obj, "__doc__", "") or "").strip()
            result["type"] = type(obj).__name__
            result["source"] = "builtins"
            return result

        return None

    def _show_references_dialog(self, word: str, matches: list[tuple[int, str]]):
        """Display a dialog listing all reference locations."""
        dlg = tk.Toplevel(self.window)
        dlg.title(t("dialog.title.find_references") + f": {word}")
        dlg.configure(bg=theme.BG_PANEL)
        dlg.transient(self.window)
        dlg.geometry("560x360")
        dlg.minsize(360, 200)

        top_frame = UFrame(dlg, bg=theme.BG_PANEL)
        top_frame.pack(fill="x", padx=10, pady=(10, 4))
        ULabel(
            top_frame,
            text=t("dialog.find_references.count", symbol=word, count=len(matches)),
            bg=theme.BG_PANEL,
            fg=theme.FG_PRIMARY,
            font=(self._font_family, self._font_size),
        ).pack(anchor="w")

        list_frame = UFrame(dlg, bg=theme.BG_BASE)
        list_frame.pack(fill="both", expand=True, padx=10, pady=(0, 8))

        scrollbar = tk.Scrollbar(list_frame, orient="vertical")
        scrollbar.pack(side="right", fill="y")

        listbox = tk.Listbox(
            list_frame,
            bg=theme.BG_BASE,
            fg=theme.FG_PRIMARY,
            selectbackground=theme.BG_SELECTED,
            selectforeground=theme.FG_PRIMARY,
            font=("Consolas", self._font_size),
            yscrollcommand=scrollbar.set,
            relief="flat",
            highlightthickness=0,
        )
        listbox.pack(fill="both", expand=True, side="left")
        scrollbar.config(command=listbox.yview)

        for ln, text_content in matches:
            display = f"  {ln:>4} | {text_content[:80]}"
            listbox.insert("end", display)

        def on_select(_=None):
            selection = listbox.curselection()
            if not selection:
                return
            idx = selection[0]
            target_line, _ = matches[idx]
            self._editor._text.mark_set(tk.INSERT, f"{target_line}.0")
            self._editor._text.see(tk.INSERT)
            self._editor._text.tag_remove("sel", "1.0", "end")
            self._editor._text.tag_add("sel", f"{target_line}.0", f"{target_line}.end")
            dlg.destroy()
            self._update_status()

        listbox.bind("<Double-Button-1>", on_select)
        listbox.bind("<Return>", on_select)

        btn_frame = UFrame(dlg, bg=theme.BG_PANEL)
        btn_frame.pack(fill="x", padx=10, pady=(0, 10))

        UButton(
            btn_frame,
            text=t("find.find_next"),
            command=on_select,
            variant="primary",
            width=80,
            height=28,
        ).pack(side="left", padx=(0, 6))

        UButton(
            btn_frame,
            text=t("find.close"),
            command=dlg.destroy,
            variant="default",
            width=60,
            height=28,
        ).pack(side="left")

        listbox.focus_set()
        self._find_dialog = dlg  # reuse find_dialog tracking for singleton
        dlg.protocol("WM_DELETE_WINDOW", lambda: self._cleanup_references_dialog(dlg))
        dlg.wait_window()

    def _cleanup_references_dialog(self, dlg):
        if self._find_dialog is dlg:
            self._find_dialog = None
        dlg.destroy()

    def _reparse(self):
        self._apply_highlight()
        self._status_label.config(text=t("status.reparsed"))

    def _set_theme(self, name: str, *, persist: bool = True):
        try:
            target = theme.by_name(name)
            if target is None:
                return
            theme.set_theme(target, refresh_root=self.window)
            if hasattr(self, "_theme_tk_var") and self._theme_tk_var is not None:
                self._theme_tk_var.set(name)
            self._status_label.config(text=t("status.theme", name=name))
            self._force_redraw()
            self._emit(HookEvents.EDITOR_THEME_CHANGED, name)
            app_logger.info(f"Theme changed to: {name}")
        except Exception as e:
            app_logger.error(f"Failed to set theme {name}: {e}")
            self._status_label.config(text=t("status.theme_error", err=str(e)))
            return
        if persist:
            self._write_setting(SettingsScope.GLOBAL, "ui.theme", name)

    def _set_highlight_theme(self, name: str, *, persist: bool = True):
        if name not in highlight_themes.available_names():
            return
        self._highlight_theme_name = name
        highlight_themes.set_theme(name)
        if hasattr(self, "_highlight_theme_tk_var") and self._highlight_theme_tk_var is not None:
            self._highlight_theme_tk_var.set(name)
        self._cancel_pending_highlight()
        self._apply_highlight()
        self._status_label.config(text=t("status.highlight_theme", name=name))
        app_logger.info(f"Highlight theme changed to: {name}")
        if persist:
            self._write_setting(SettingsScope.GLOBAL, "ui.highlight_theme", name)

    def _open_highlight_theme_marketplace(self):
        marketplace = highlight_marketplace.get_marketplace()
        providers = marketplace.providers
        if not providers:
            tk.messagebox.showinfo(
                t("dialog.title.highlight_theme_marketplace"),
                t("dialog.highlight_theme_marketplace.no_providers"),
                parent=self.window,
            )
        else:
            tk.messagebox.showinfo(
                t("dialog.title.highlight_theme_marketplace"),
                t("dialog.highlight_theme_marketplace.placeholder"),
                parent=self.window,
            )

    def _open_ui_theme_marketplace(self):
        marketplace = ui_theme_marketplace.get_ui_marketplace()
        providers = marketplace.providers
        if not providers:
            tk.messagebox.showinfo(
                t("dialog.title.ui_theme_marketplace"),
                t("dialog.ui_theme_marketplace.no_providers"),
                parent=self.window,
            )
        else:
            tk.messagebox.showinfo(
                t("dialog.title.ui_theme_marketplace"),
                t("dialog.ui_theme_marketplace.placeholder"),
                parent=self.window,
            )

    def _open_plugin_marketplace(self):
        marketplace = plugin_marketplace.get_plugin_marketplace()
        providers = marketplace.providers
        if not providers:
            tk.messagebox.showinfo(
                t("dialog.title.plugin_marketplace"),
                t("dialog.plugin_marketplace.no_providers"),
                parent=self.window,
            )
        else:
            tk.messagebox.showinfo(
                t("dialog.title.plugin_marketplace"),
                t("dialog.plugin_marketplace.placeholder"),
                parent=self.window,
            )

    def _open_language_marketplace(self):
        marketplace = language_marketplace.get_marketplace()
        providers = marketplace.providers
        if not providers:
            tk.messagebox.showinfo(
                t("dialog.title.language_marketplace"),
                t("dialog.language_marketplace.no_providers"),
                parent=self.window,
            )
        else:
            tk.messagebox.showinfo(
                t("dialog.title.language_marketplace"),
                t("dialog.language_marketplace.placeholder"),
                parent=self.window,
            )

    def _on_settings_panel_action(self, key: str, value: Any) -> None:
        if key == "ui.highlight_theme_marketplace":
            self._open_highlight_theme_marketplace()
        elif key == "ui.theme_marketplace":
            self._open_ui_theme_marketplace()
        elif key == "plugins.marketplace":
            self._open_plugin_marketplace()
        elif key == "i18n.language_marketplace":
            self._open_language_marketplace()

    def _force_redraw(self):
        try:
            self.window.update_idletasks()
            self.window.update()
            geom = self.window.geometry()
            self.window.geometry(geom)
            self.window.update_idletasks()
            self.window.update()
            self.window.tk.eval("update")
            if getattr(self.window, "_custom_titlebar", True):
                self.window.overrideredirect(False)
                self.window.update_idletasks()
                self.window.overrideredirect(True)
                self.window.update_idletasks()
                self.window.update()
        except Exception:
            pass

    def _set_font_family(self, family: str):
        self._font_family = family
        if hasattr(self, "_font_family_tk_var") and self._font_family_tk_var is not None:
            self._font_family_tk_var.set(family)
        self._apply_editor_font()
        self._status_label.config(text=t("status.font", name=family))
        self._write_setting(SettingsScope.GLOBAL, "ui.font_family", family)

    def _set_font_size(self, size: int):
        self._font_size = size
        if hasattr(self, "_font_size_tk_var") and self._font_size_tk_var is not None:
            self._font_size_tk_var.set(size)
        self._apply_editor_font()
        self._status_label.config(text=t("status.font_size", n=size))
        self._write_setting(SettingsScope.GLOBAL, "ui.font_size", int(size))

    def _apply_editor_font(self):
        font = (self._font_family, self._font_size)
        self._editor._text.config(font=font)

    def _set_tab_width(self, tw: int, *, persist: bool = True):
        self._tab_width = tw
        if hasattr(self, "_tab_width_tk_var") and self._tab_width_tk_var is not None:
            self._tab_width_tk_var.set(tw)
        self._editor._text.config(tabs=(tw * self._font_size,))
        if persist:
            self._write_setting(SettingsScope.GLOBAL, "editor.tab_size", int(tw))

    def _toggle_highlighting(self):
        self._highlighting_enabled = bool(self._highlight_tk_var.get())
        if not self._highlighting_enabled:
            self._cancel_pending_highlight()
            text = self._editor._text
            for tag in text.tag_names():
                text.tag_delete(tag)
        else:
            self._cancel_pending_highlight()
            self._apply_highlight()
        self._write_setting(SettingsScope.GLOBAL, "completion.enabled", self._highlighting_enabled)

    def _toggle_suggestions(self):
        self._suggestions_enabled = bool(self._suggestion_tk_var.get())
        if not self._suggestions_enabled:
            self._hide_suggestions()
        self._write_setting(SettingsScope.GLOBAL, "completion.enabled", self._suggestions_enabled)

    def _toggle_autosave(self):
        self._autosave_enabled = bool(self._autosave_tk_var.get())
        self._write_setting(SettingsScope.GLOBAL, "editor.auto_save", self._autosave_enabled)

    def _open_global_settings(self):
        from core.settings.settings.widgets import UProjectSettingsWindow

        try:
            win = UProjectSettingsWindow(
                self._settings,
                parent=self.window,
                title=t("dialog.title.settings"),
                on_change=self._on_settings_panel_action,
            )
            self._settings_window = win
            win._switch(SettingsScope.GLOBAL)
        except Exception as exc:
            tk.messagebox.showerror(
                t("dialog.title.settings_load_failed"),
                t("dialog.settings.load_failed", err=exc),
                parent=self.window,
            )

    def _open_project_settings(self):
        if self._settings.project_settings is None:
            if not tk.messagebox.askyesno(
                t("dialog.title.project_load_failed"),
                t("dialog.project_settings.no_project"),
                parent=self.window,
            ):
                return
            chosen = tk.filedialog.askdirectory(
                title=t("dialog.title.choose_project"), parent=self.window
            )
            if not chosen:
                return
            self._attach_project(chosen)
        from core.settings.settings.widgets import UProjectSettingsWindow

        try:
            win = UProjectSettingsWindow(
                self._settings, parent=self.window, title=t("dialog.title.project_settings")
            )
            with contextlib.suppress(Exception):
                win._switch(SettingsScope.PROJECT)
            self._settings_window = win
        except Exception as exc:
            tk.messagebox.showerror(
                t("dialog.title.project_load_failed"),
                t("dialog.project_settings.load_failed", err=exc),
                parent=self.window,
            )

    def _attach_project(self, root: str) -> None:
        root = os.path.abspath(root)
        if self._current_project_root == root:
            return
        with contextlib.suppress(Exception):
            self._plugin_manager.unload_project_plugins()
        self._settings.detach_project()
        try:
            self._settings.attach_project(root)
            self._current_project_root = root
            app_logger.info(f"Project attached: {root}")
        except Exception as exc:
            app_logger.error(f"Failed to attach project {root}: {exc}")
            tk.messagebox.showerror(
                t("dialog.title.project_attach_failed"),
                t("dialog.project_settings.attach_failed", root=root, err=exc),
                parent=self.window,
            )
            return
        if hasattr(self, "_explorer_card") and self._explorer_card is not None:
            self._explorer_card.set_root(root)
        with contextlib.suppress(Exception):
            self._plugin_manager.load_project_plugins(root)
        self._refresh_plugin_menu()
        self._refresh_plugin_languages()

    def _reset_settings(self):
        if not tk.messagebox.askyesno(
            t("dialog.title.reset_settings"), t("dialog.reset_settings.confirm"), parent=self.window
        ):
            return
        with contextlib.suppress(Exception):
            self._settings.reset(SettingsScope.GLOBAL)
        self._refresh_all_from_settings()
        try:
            self._settings.save_all()
        except Exception as exc:
            tk.messagebox.showerror(t("dialog.title.reset_failed"), str(exc), parent=self.window)
            return
        self._status_label.config(text=t("status.settings_reset"))

    def _emit(self, hook: str, *args: Any, **kwargs: Any) -> None:
        manager = getattr(self, "_plugin_manager", None)
        if manager is None:
            return
        with contextlib.suppress(Exception):
            manager.emit(hook, *args, **kwargs)

    def _emit_content_changed(self) -> None:
        if not hasattr(self, "_last_emit_code"):
            self._last_emit_code = None
        try:
            code = self._editor.get("1.0", "end-1c")
        except tk.TclError:
            return
        if code == self._last_emit_code:
            return
        self._last_emit_code = code
        try:
            cursor = int(self._editor._text.index(tk.INSERT).split(".")[1])
        except Exception:
            cursor = 0
        self._emit(HookEvents.EDITOR_CONTENT_CHANGED, code, cursor)

    def _add_plugin_command(self, record: Any, cmd: Any) -> None:
        groups = self._plugin_menus.setdefault(cmd.menu, [])
        for existing in groups:
            if existing["plugin_id"] == cmd.plugin_id and existing["label"] == cmd.label:
                return
        groups.append(
            {
                "plugin_id": cmd.plugin_id,
                "label": cmd.label,
                "callback": cmd.callback,
                "shortcut": cmd.shortcut,
            }
        )

    def _add_plugin_language(self, plugin_id: str, contrib: LanguageContribution) -> None:
        if contrib.name in LANG_CONFIG:
            return
        LANG_CONFIG[contrib.name] = {
            "ext": contrib.ext,
            "highlighter": type(contrib.highlighter_factory()),
            "suggestion": type(contrib.suggestion_factory()),
            "highlighter_factory": contrib.highlighter_factory,
            "suggestion_factory": contrib.suggestion_factory,
            "sample": contrib.sample,
            "plugin_id": plugin_id,
        }
        if contrib.name not in self._plugin_lang_combo_added:
            self._plugin_lang_combo_added.append(contrib.name)

    def _refresh_plugin_menu(self) -> None:
        menu = getattr(self, "_plugin_menu", None)
        if menu is None:
            return
        menu._items.clear()
        loaded = self._plugin_manager.list_loaded()
        if not loaded:
            menu.add_command(t("menu.plugins.none"), lambda: None)
        else:
            for rec in loaded:
                status = (
                    t("plugin.info.status.enabled")
                    if rec.enabled
                    else t("plugin.info.status.disabled")
                )
                err = t("plugin.menu.errors_prefix", err=rec.error) if rec.error else ""
                menu.add_command(
                    t("plugin.menu.item", name=rec.manifest.name, status=status, error=err),
                    lambda r=rec: self._show_plugin_info(r),
                )
        menu.add_separator()
        for group_name, items in self._plugin_menus.items():
            sub = menu.add_cascade(group_name)
            sub._items.clear()
            if not items:
                sub.add_command(t("menu.plugins.empty"), lambda: None)
                continue
            for item in items:
                label = item["label"]
                if item["shortcut"]:
                    label = f"{label}\t{item['shortcut']}"
                sub.add_command(
                    label, lambda cb=item["callback"]: self._safe_run_plugin_command(cb)
                )
        menu.add_separator()
        menu.add_command(t("menu.plugins.manage"), self._open_plugin_manager)
        menu.add_command(t("menu.plugins.marketplace"), self._open_plugin_marketplace)
        menu.add_command(t("menu.plugins.rescan"), self._reload_all_plugins)

    def _refresh_plugin_languages(self) -> None:
        pass

    def _safe_run_plugin_command(self, callback: Any) -> None:
        try:
            callback()
        except Exception as exc:
            self._append_output(f"[ERROR] {t('dialog.plugin.error', err=exc)}\n")
            with contextlib.suppress(Exception):
                tk.messagebox.showerror(
                    t("dialog.title.plugin_error"), str(exc), parent=self.window
                )

    def _show_plugin_info(self, record: Any) -> None:
        m = record.manifest
        author = m.author if m.author else t("plugin.info.author_unknown")
        desc = m.description if m.description else t("plugin.info.description_none")
        version = m.version if m.version else t("plugin.info.version_unknown")
        src = getattr(record, "src_path", t("plugin.info.source_unknown"))
        status = (
            t("plugin.info.status.enabled") if record.enabled else t("plugin.info.status.disabled")
        )
        error_info = t("plugin.info.error", err=record.error) if record.error else ""
        info = "\n".join(
            [
                f"Name: {m.name}",
                f"ID: {m.id}",
                f"Version: {version}",
                f"Author: {author}",
                f"Description: {desc}",
                f"Source: {src}",
                f"Status: {status}",
                error_info,
            ]
        )
        tk.messagebox.showinfo(t("dialog.title.plugin_info", name=m.name), info, parent=self.window)

    def _reload_all_plugins(self) -> None:
        with contextlib.suppress(Exception):
            self._plugin_manager.unload_all()
        with contextlib.suppress(Exception):
            self._plugin_manager.load_global_plugins()
        if self._current_project_root:
            with contextlib.suppress(Exception):
                self._plugin_manager.load_project_plugins(self._current_project_root)
        self._refresh_plugin_menu()
        self._refresh_plugin_languages()
        tk.messagebox.showinfo(
            t("dialog.title.plugins_reloaded"),
            t("dialog.plugins_reloaded.message"),
            parent=self.window,
        )

    def _open_plugin_manager(self):

        try:
            win = UPluginManagerWindow(  # type: ignore[name-defined]
                self._plugin_manager, parent=self.window, title=t("dialog.title.plugin_manager")
            )
            self._plugin_manager_window = win
        except Exception as exc:
            tk.messagebox.showerror(
                t("dialog.title.plugin_manager_error"),
                t("dialog.plugin_manager.load_failed", err=exc),
                parent=self.window,
            )

    def _append_output(self, text: str) -> None:
        try:
            self._output._text.config(state="normal")
            self._output._text.insert("end", text)
            self._output._text.see("end")
            self._output._text.config(state="disabled")
        except Exception:
            pass

    def _clear_output(self) -> None:
        try:
            self._output._text.config(state="normal")
            self._output._text.delete("1.0", "end")
            self._output._text.config(state="disabled")
        except Exception:
            pass

    def _run_code(self) -> None:
        code = self._editor.get("1.0", "end-1c")
        if not code.strip():
            self._status_label.config(text=t("status.no_code_to_run"))
            return
        self._append_output(f"{'=' * 40}\n")
        self._append_output(f"{t('output.running')}...\n")
        self._status_label.config(text=t("status.running"))
        lang = self._lang
        self._emit(HookEvents.EDITOR_BEFORE_RUN, lang)
        if lang == "Python":
            self._run_python_code(code)
        elif lang in ("C", "C++"):
            self._run_cpp_code(code)
        else:
            self._append_output(f"{t('output.unsupported_lang', lang=lang)}\n")

    def _run_python_code(self, code: str) -> None:
        python_path = sys.executable
        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".py", delete=False, encoding="utf-8"
            ) as f:
                f.write(code)
                temp_path = f.name

            def on_line(line: str):
                self._append_output(line)

            def on_done(result: RunResult):
                self._append_output(f"\n{t('output.exit_code')}: {result.returncode}\n")
                self._status_label.config(text=t("status.ready"))

            self._cancel_pending_suggestions()
            stream_command(
                [python_path, temp_path],
                cwd=os.path.dirname(temp_path),
                line_callback=on_line,
                done_callback=on_done,
            )
        except Exception as exc:
            self._append_output(f"{t('output.error')}: {exc}\n")
            self._status_label.config(text=t("status.ready"))

    def _run_cpp_code(self, code: str) -> None:
        self._append_output(f"{t('output.cpp_not_implemented')}\n")
        self._status_label.config(text=t("status.ready"))

    def _run_check(self) -> None:
        code = self._editor.get("1.0", "end-1c")
        if not code.strip():
            self._status_label.config(text=t("status.no_code_to_check"))
            return
        lang = self._lang
        if lang == "Python":
            self._check_python_code(code)
        else:
            self._append_output(f"{t('output.check_unsupported', lang=lang)}\n")

    def _check_python_code(self, code: str) -> None:
        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".py", delete=False, encoding="utf-8"
            ) as f:
                f.write(code)
                temp_path = f.name

            self._append_output(f"{t('output.checking')}...\n")

            checker = CPythonChecker()
            result = checker.check(temp_path)
            for row in result.row:
                self._append_output(f"{row}\n")
            self._append_output(f"{t('output.check_done')}\n")
        except Exception as exc:
            self._append_output(f"{t('output.error')}: {exc}\n")

    def _show_documentation(self):
        tk.messagebox.showinfo(
            t("dialog.title.documentation"), t("dialog.documentation.message"), parent=self.window
        )

    def _show_shortcuts(self):
        win = UShortcutConfigWindow(self.window, self._settings, on_apply=self._rebind_shortcuts)
        win.wait_window()

    def _show_about(self):
        tk.messagebox.showinfo(
            t("dialog.title.about"),
            "Python Editor v0.1.0\nA Tkinter-based code editor",
            parent=self.window,
        )

    def _check_updates(self):
        tk.messagebox.showinfo(
            t("dialog.title.check_updates"), t("dialog.check_updates.message"), parent=self.window
        )

    def _report_issue(self):
        tk.messagebox.showinfo(
            t("dialog.title.report_issue"), t("dialog.report_issue.message"), parent=self.window
        )
