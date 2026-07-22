"""Top-level :class:`CodeEditor` orchestrator.

The application logic is split across focused modules in this package:

* :mod:`core.editor.helpers` — pure helpers and constants
* :mod:`core.editor.document_io` — file streaming primitives
* :mod:`core.editor.find_dialog` — find / replace / references dialogs
* :mod:`core.editor.tabs` — :class:`~core.editor.tabs.TabManager`
* :mod:`core.editor.buffer` — :class:`~core.editor.buffer.EditorBuffer`
* :mod:`core.editor.runner_panel` — :class:`~core.editor.runner_panel.RunnerPanel`
* :mod:`core.editor.menu` — :class:`~core.editor.menu.MenuBuilder` and
  :class:`~core.editor.menu.ShortcutBinder`

:class:`CodeEditor` is the only class that lives here. It owns the
:class:`Window`, the :class:`SettingsManager`, the :class:`PluginManager`,
and a handful of UI widgets it doesn't delegate (toolbar, sidebar, status
bar, marketplace launchers).  Everything else is composed through the
modules above.

Backward-compatible re-exports
------------------------------

``_NAVIGATION_KEYS``, ``_strip_common_prefix`` and ``_pick_local_completion``
were originally defined in this module. Tests and plugin modules still import
them from :mod:`core.editor.app`, so we re-export them under the same names.
"""

from __future__ import annotations

import contextlib
import os
import sys
import tkinter as tk
import tkinter.filedialog
import tkinter.messagebox
import tkinter.simpledialog
from collections.abc import Callable
from typing import Any

from core.editor.buffer import EditorBuffer
from core.editor.document_io import (
    DEFAULT_LARGE_FILE_THRESHOLD,
    file_size,
    read_full,
    resolve_threshold,
    stream_load_file,
)
from core.editor.find_dialog import ReferencesDialog
from core.editor.helpers import (
    NAVIGATION_KEYS as _NAVIGATION_KEYS,  # noqa: F401  (re-export for tests/plugins)
    format_autosave_path as _format_autosave_path_impl,
    human_size as _human_size,
    is_within as _is_within,
    pick_local_completion as _pick_local_completion,  # noqa: F401  (re-export for tests/plugins)
    strip_common_prefix as _strip_common_prefix,  # noqa: F401  (re-export for tests/plugins)
)
from core.editor.lang_config import LANG_CONFIG
from core.editor.menu import MenuBuilder, ShortcutBinder
from core.editor.runner_panel import RunnerPanel, default_shell_argv
from core.editor.tabs import TabManager
from core.language.highlighter import highlight_themes
from core.plugins import HookEvents, LanguageContribution, PluginManager
from core.runner import RunHandle
from core.settings import SettingsChangeEvent, SettingsManager, SettingsScope
from core.settings.i18n import AVAILABLE_LANGUAGES, get_translator, t
from core.settings.logging import get_logger as get_core_logger
from ui import Window
from ui.widgets import (
    DebugCard,
    ExplorerCard,
    GitCard,
    SideBar,
    TabBar,
    UFrame,
    ULabel,
    UMarketplaceWindow,
    UShortcutConfigWindow,
    UText,
    theme,
    ui_theme_marketplace,
)

__all__ = ["CodeEditor"]


app_logger = get_core_logger("app")
app_logger.info("Application starting...")


class CodeEditor:
    """The top-level Tk editor application.

    Acts as a coordinator: it owns the main window, settings manager, plugin
    manager, and a few UI panels (toolbar, sidebar, status). It composes the
    :class:`TabManager`, :class:`EditorBuffer`, :class:`RunnerPanel`, and
    :class:`MenuBuilder` for the bulk of its responsibilities.
    """

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    def __init__(self) -> None:
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
        self._font_family = self._settings.effective("ui.font_family", "Consolas")
        self._font_size = int(self._settings.effective("ui.font_size", 10))
        self._tab_width = int(self._settings.effective("editor.tab_size", 4))
        self._highlight_delay_ms = int(self._settings.effective("editor.highlight_delay_ms", 300))
        self._definition_highlight_duration_ms = int(
            self._settings.effective("editor.definition_highlight_duration_ms", 3000)
        )
        self._suggest_delay_ms = int(self._settings.effective("editor.suggestion_delay_ms", 200))
        self._suggest_min_chars = int(
            self._settings.effective("completion.min_chars_before_trigger", 1)
        )
        self._highlighting_enabled = bool(self._settings.effective("completion.enabled", True))
        self._suggestions_enabled = bool(self._settings.effective("completion.enabled", True))
        self._autosave_enabled = bool(self._settings.effective("editor.auto_save", False))
        self._autosave_format = self._settings.effective(
            "editor.auto_save_format", "{unix.seconds}"
        )
        self._autosave_delay_ms = int(self._settings.effective("editor.auto_save_delay_ms", 800))
        self._autosave_paths: dict[str, str] = {}
        self._highlight_theme_name = self._settings.effective("ui.highlight_theme", "Default Dark")
        if self._highlight_theme_name not in highlight_themes.available_names():
            self._highlight_theme_name = "Default Dark"

        self._current_file: str | None = None
        self._current_project_root: str | None = None
        self._run_handle: RunHandle | None = None
        self._settings_window: Any = None
        self._plugin_manager_window: Any = None
        self._lang_tk_var: tk.StringVar | None = None
        self._lang_locale_tk_var: tk.StringVar | None = None
        self._font_family_tk_var: tk.StringVar | None = None
        self._font_size_tk_var: tk.IntVar | None = None
        self._tab_width_tk_var: tk.IntVar | None = None
        self._highlight_tk_var: tk.BooleanVar | None = None
        self._suggestion_tk_var: tk.BooleanVar | None = None
        self._autosave_tk_var: tk.BooleanVar | None = None
        self._highlight_theme_tk_var: tk.StringVar | None = None
        self._theme_tk_var: tk.StringVar | None = None
        self._highlighted_line: int | None = None
        self._highlighted_line_color: str = theme.YELLOW

        # Build the editor frame containing the toolbar and side-panel.
        self._build_toolbar()
        body = UFrame(self.window, variant="base")
        body.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)
        self._editor_body = body

        # The TabBar, PanedWindow, and UText go directly on the body —
        # these are still constructed here because they're layout glue.
        self._tab_bar = TabBar(
            body,
            on_select=self._on_tab_select,
            on_close=self._on_tab_close,
            on_context_menu=self._on_tab_context_menu,
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
                ("explorer", t("sidebar.explorer"), "explorer"),
                ("debug", t("sidebar.debug"), "debug"),
                ("git", t("sidebar.git.title"), "git"),
                ("ai", t("sidebar.ai"), "ai"),
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

        # Compose the four stateful components.
        self.tabs = TabManager(self)
        self.tabs.bind_tab_bar(self._tab_bar)
        self.buffer = EditorBuffer(self, self._editor._text)
        self.runner = RunnerPanel(self, self.window)
        self.menus = MenuBuilder(self)

        # Ghost-text overlay sits on top of the editor. It's owned by the
        # buffer but exposed here for the AI integration that asks the
        # editor to show / accept ghost text.
        self._ghost_text = self.buffer._ghost_text  # type: ignore[attr-defined]
        self._build_status_bar()

        # Build menu, then a stub shell command so the runner can read it.
        self._shell_argv: list[str] = default_shell_argv(self._settings)
        self.menus.build()
        self.shortcuts = ShortcutBinder(self.window, self._settings)
        self._refresh_shortcuts()

        # Initial document, language, and highlight theme.
        self.tabs.init_first_document()
        self._switch_language("Python")
        highlight_themes.set_theme(self._highlight_theme_name)
        self.buffer.apply_highlight()
        self.buffer.apply_font()
        self.buffer.apply_tab_width()

        # Plugin manager.
        self._plugin_manager = PluginManager()
        self._plugin_menus: dict[str, list[dict]] = {}
        self._plugin_lang_combo_added: list[str] = []
        self._plugin_manager.attach_editor(self)
        with contextlib.suppress(Exception):
            self._plugin_manager.load_global_plugins()
        import core.ai.plugin as _ai_plugin_module

        self._plugin_manager.register_builtin("ai_assistant", _ai_plugin_module)
        self._refresh_plugin_menu()
        self._refresh_plugin_languages()

        self._settings.add_listener(self._on_settings_changed)

        self._apply_loaded_theme()

        if bool(self._settings.effective("terminal.auto_start", True)):
            self.window.after(0, self._open_shell)

        self.window.protocol("WM_DELETE_WINDOW", self._on_close_request)
        app_logger.info(
            f"CodeEditor initialized: theme={theme.current().name}, "
            f"font={self._font_family} {self._font_size}pt, "
            f"tab_width={self._tab_width}"
        )

    # ------------------------------------------------------------------
    # Settings-managed instance attributes — read by the components
    # ------------------------------------------------------------------

    @property
    def settings(self) -> SettingsManager:
        return self._settings

    @property
    def current_file(self) -> str | None:
        return self._current_file

    @current_file.setter
    def current_file(self, value: str | None) -> None:
        self._current_file = value

    @property
    def current_project_root(self) -> str | None:
        return self._current_project_root

    @property
    def current_language(self) -> str:
        return self._lang

    @current_language.setter
    def current_language(self, value: str) -> None:
        self._lang = value

    @property
    def font_family(self) -> str:
        return self._font_family

    @font_family.setter
    def font_family(self, value: str) -> None:
        self._font_family = value

    @property
    def font_size(self) -> int:
        return self._font_size

    @font_size.setter
    def font_size(self, value: int) -> None:
        self._font_size = value

    @property
    def tab_width(self) -> int:
        return self._tab_width

    @tab_width.setter
    def tab_width(self, value: int) -> None:
        self._tab_width = value

    @property
    def autosave_format(self) -> str:
        return self._autosave_format

    @property
    def autosave_delay_ms(self) -> int:
        return self._autosave_delay_ms

    @property
    def highlight_delay_ms(self) -> int:
        return self._highlight_delay_ms

    @highlight_delay_ms.setter
    def highlight_delay_ms(self, value: int) -> None:
        self._highlight_delay_ms = value

    @property
    def definition_highlight_duration_ms(self) -> int:
        return self._definition_highlight_duration_ms

    @definition_highlight_duration_ms.setter
    def definition_highlight_duration_ms(self, value: int) -> None:
        self._definition_highlight_duration_ms = value

    @property
    def suggest_delay_ms(self) -> int:
        return self._suggest_delay_ms

    @suggest_delay_ms.setter
    def suggest_delay_ms(self, value: int) -> None:
        self._suggest_delay_ms = value

    @property
    def suggest_min_chars(self) -> int:
        return self._suggest_min_chars

    @property
    def highlighting_enabled(self) -> bool:
        return self._highlighting_enabled

    @highlighting_enabled.setter
    def highlighting_enabled(self, value: bool) -> None:
        self._highlighting_enabled = value

    @property
    def suggestions_enabled(self) -> bool:
        return self._suggestions_enabled

    @suggestions_enabled.setter
    def suggestions_enabled(self, value: bool) -> None:
        self._suggestions_enabled = value

    @property
    def autosave_enabled(self) -> bool:
        return self._autosave_enabled

    @autosave_enabled.setter
    def autosave_enabled(self, value: bool) -> None:
        self._autosave_enabled = value

    @property
    def highlighter(self) -> Any:
        return self.buffer.highlighter

    @highlighter.setter
    def highlighter(self, value: Any) -> None:
        self.buffer._editor_highlighter = value  # type: ignore[attr-defined]

    @property
    def suggestion_expert(self) -> Any:
        return self.buffer.suggestion_expert

    @suggestion_expert.setter
    def suggestion_expert(self, value: Any) -> None:
        self.buffer._suggestion_expert = value  # type: ignore[attr-defined]

    @property
    def shell_command(self) -> list[str]:
        return self._shell_argv

    # ------------------------------------------------------------------
    # Hook / shell helpers used by components
    # ------------------------------------------------------------------

    def emit(self, hook: str, *args: Any, **kwargs: Any) -> None:
        manager = getattr(self, "_plugin_manager", None)
        if manager is None:
            return
        with contextlib.suppress(Exception):
            manager.emit(hook, *args, **kwargs)

    def get_active_id(self) -> str | None:
        return self.tabs.active_id

    def get_active_path(self) -> str | None:
        if self.tabs.active_id and self.tabs.active_id in self.tabs.documents:
            return self.tabs.documents[self.tabs.active_id].path
        return None

    def get_active_document(self) -> Any:
        if self.tabs.active_id and self.tabs.active_id in self.tabs.documents:
            return self.tabs.documents[self.tabs.active_id]
        return None

    def refresh_status(self) -> None:
        if not hasattr(self, "_pos_label"):
            return
        try:
            cursor = self._editor._text.index(tk.INSERT)
            line, col = cursor.split(".")
            self._pos_label.config(text=t("status.pos", line=line, col=int(col) + 1))
        except tk.TclError:
            return

    def mark_dirty(self) -> None:
        self.tabs.mark_active_dirty()

    def emit_content_changed(self) -> None:
        self.buffer.emit_content_changed()

    def emit_selection_changed(self) -> None:
        self.buffer.emit_selection_changed()

    def emit_cursor_moved(self) -> None:
        self.buffer.emit_cursor_moved()

    def do_autosave(self, active_id: str) -> None:
        if not self._autosave_enabled:
            return
        if active_id not in self.tabs.documents:
            return
        doc = self.tabs.documents[active_id]
        if not doc.dirty:
            return
        if doc.path:
            self._save_to_path(doc.path)
        else:
            cached = self._autosave_paths.get(active_id)
            if cached and os.path.exists(cached):
                self._save_to_path(cached)
            else:
                path = self._format_autosave_path()
                with contextlib.suppress(OSError):
                    os.makedirs(os.path.dirname(path), exist_ok=True)
                self._save_to_path(path)
                doc.path = path
                self._current_file = path
                self._autosave_paths[active_id] = path

    def format_autosave_path(self) -> str:
        return _format_autosave_path_impl(self._autosave_format)

    def _format_autosave_path(self) -> str:
        return self.format_autosave_path()

    def confirm_unsaved_discard(self) -> bool:
        return bool(
            tk.messagebox.askyesno(
                t("dialog.title.unsaved_discard"),
                t("dialog.unsaved_discard.message"),
            )
        )

    def _switch_language(self, lang: str, *, from_doc_switch: bool = False) -> None:
        self.switch_language(lang, from_doc_switch=from_doc_switch)

    def switch_language(self, lang: str, *, from_doc_switch: bool = False) -> None:
        if lang not in LANG_CONFIG:
            return
        self._lang = lang
        if self._lang_tk_var is not None:
            self._lang_tk_var.set(lang)
        self.buffer.switch_language(lang, from_doc_switch=from_doc_switch)
        if not from_doc_switch:
            active_id = self.tabs.active_id
            if active_id and active_id in self.tabs.documents:
                self.tabs.documents[active_id].lang = lang
        self.refresh_status()
        self._status_label.config(text=t("status.editor_lang_changed", lang=lang))
        self.window.after(3000, lambda: self._status_label.config(text=t("status.ready")))
        self._lang_label.config(text=lang)
        app_logger.info(f"Language switched to: {lang}")

    def show_references(self, word: str, matches: list[tuple[int, str]]) -> None:
        ReferencesDialog(
            self.window,
            self._editor._text,
            word,
            matches,
            font_family=self._font_family,
            font_size=self._font_size,
            on_jump=self.refresh_status,
        ).show()

    # ------------------------------------------------------------------
    # Tk-Var helpers used by MenuBuilder
    # ------------------------------------------------------------------

    def _lang_var(self) -> tk.StringVar:
        if self._lang_tk_var is None:
            self._lang_tk_var = tk.StringVar(value=self._lang)
        return self._lang_tk_var

    def _lang_locale_var(self) -> tk.StringVar:
        if self._lang_locale_tk_var is None:
            current = self._settings.effective("i18n.language", "zh_CN")
            if current not in AVAILABLE_LANGUAGES:
                current = "zh_CN"
            self._lang_locale_tk_var = tk.StringVar(value=current)
        return self._lang_locale_tk_var

    def _theme_var(self) -> tk.StringVar:
        if self._theme_tk_var is None:
            self._theme_tk_var = tk.StringVar(value=theme.current().name)
        return self._theme_tk_var

    def _font_family_var(self) -> tk.StringVar:
        if self._font_family_tk_var is None:
            self._font_family_tk_var = tk.StringVar(value=self._font_family)
        return self._font_family_tk_var

    def _font_size_var(self) -> tk.IntVar:
        if self._font_size_tk_var is None:
            self._font_size_tk_var = tk.IntVar(value=self._font_size)
        return self._font_size_tk_var

    def _tab_width_var(self) -> tk.IntVar:
        if self._tab_width_tk_var is None:
            self._tab_width_tk_var = tk.IntVar(value=self._tab_width)
        return self._tab_width_tk_var

    def _highlight_var(self) -> tk.BooleanVar:
        if self._highlight_tk_var is None:
            self._highlight_tk_var = tk.BooleanVar(value=self._highlighting_enabled)
        return self._highlight_tk_var

    def _suggestion_var(self) -> tk.BooleanVar:
        if self._suggestion_tk_var is None:
            self._suggestion_tk_var = tk.BooleanVar(value=self._suggestions_enabled)
        return self._suggestion_tk_var

    def _autosave_var(self) -> tk.BooleanVar:
        if self._autosave_tk_var is None:
            self._autosave_tk_var = tk.BooleanVar(value=self._autosave_enabled)
        return self._autosave_tk_var

    def _highlight_theme_var(self) -> tk.StringVar:
        if self._highlight_theme_tk_var is None:
            self._highlight_theme_tk_var = tk.StringVar(value=self._highlight_theme_name)
        return self._highlight_theme_tk_var

    # ------------------------------------------------------------------
    # The dictionary of menu actions exposed for the MenuBuilder
    # ------------------------------------------------------------------

    @property
    def actions(self) -> dict[str, Callable[[], None]]:
        a: dict[str, Callable[[], None]] = {
            "new_file": self._new_file,
            "open_file": self._open_file,
            "open_project": self._open_project,
            "save_file": self._save_file,
            "save_file_as": self._save_file_as,
            "close_tab": self._close_active_tab,
            "open_shell": self._open_shell,
            "run_check": self._run_check,
            "clear_output": self._clear_output,
            "undo": self.buffer.undo,
            "redo": self.buffer.redo,
            "cut": self.buffer.cut,
            "copy": self.buffer.copy,
            "paste": self.buffer.paste,
            "select_all": self.buffer.select_all,
            "open_find": self.buffer.open_find_dialog,
            "open_replace": self.buffer.open_replace_dialog,
            "goto_line": self.buffer.goto_line,
            "indent": self.buffer.indent,
            "outdent": self.buffer.outdent,
            "toggle_comment": self.buffer.toggle_comment,
            "switch_language": self._switch_language,
            "goto_definition": self.buffer.goto_definition,
            "find_references": self.buffer.find_references,
            "find_documentation": self._find_documentation,
            "reparse": self._reparse,
            "apply_highlight": self.buffer.apply_highlight,
            "trigger_suggestions": self.buffer.show_suggestions,
            "hide_suggestions": self.buffer.hide_suggestions,
            "set_theme": self._set_theme,
            "set_highlight_theme": self._set_highlight_theme,
            "set_font_family": self._set_font_family,
            "set_font_size": self._set_font_size,
            "set_tab_width": self._set_tab_width,
            "toggle_highlighting": self._toggle_highlighting,
            "toggle_suggestions": self._toggle_suggestions,
            "toggle_autosave": self._toggle_autosave,
            "set_language_locale": self._set_language_locale,
            "open_global_settings": self._open_global_settings,
            "open_project_settings": self._open_project_settings,
            "reset_settings": self._reset_settings,
            "show_documentation": self._show_documentation,
            "show_shortcuts": self._show_shortcuts,
            "show_about": self._show_about,
            "check_updates": self._check_updates,
            "report_issue": self._report_issue,
            "open_plugin_manager": self._open_plugin_manager,
            "open_plugin_marketplace": self._open_plugin_marketplace,
            "open_marketplace": self._open_marketplace,
            "open_highlight_theme_marketplace": self._open_highlight_theme_marketplace,
            "open_ui_theme_marketplace": self._open_ui_theme_marketplace,
            "open_language_marketplace": self._open_language_marketplace,
            "next_tab": self.tabs.next_tab,
            "prev_tab": self.tabs.prev_tab,
            # tk-var creators are wrapped as 0-arg callables.
            "lang_var_creator": lambda: self._lang_var(),
            "lang_locale_var_creator": lambda: self._lang_locale_var(),
            "theme_var_creator": lambda: self._theme_var(),
            "font_family_var_creator": lambda: self._font_family_var(),
            "font_size_var_creator": lambda: self._font_size_var(),
            "tab_width_var_creator": lambda: self._tab_width_var(),
            "highlight_var_creator": lambda: self._highlight_var(),
            "suggestion_var_creator": lambda: self._suggestion_var(),
            "autosave_var_creator": lambda: self._autosave_var(),
            "highlight_theme_var_creator": lambda: self._highlight_theme_var(),
        }
        return a

    # ------------------------------------------------------------------
    # Settings bridge — listens to global settings changes
    # ------------------------------------------------------------------

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
            if self._font_family_tk_var is not None:
                self._font_family_tk_var.set(event.new)
            self.buffer.apply_font()
        elif key == "ui.font_size":
            self._font_size = int(event.new)
            if self._font_size_tk_var is not None:
                self._font_size_tk_var.set(int(event.new))
            self.buffer.apply_font()
        elif key == "editor.tab_size":
            self._set_tab_width(int(event.new), persist=False)
        elif key == "completion.enabled":
            val = bool(event.new)
            self._highlighting_enabled = val
            self._suggestions_enabled = val
            for tk_var in (self._highlight_tk_var, self._suggestion_tk_var):
                if tk_var is not None:
                    tk_var.set(val)
            if val:
                self.buffer.apply_highlight()
            else:
                text = self._editor._text
                for tag in text.tag_names():
                    text.tag_delete(tag)
                self.buffer.hide_suggestions()
        elif key == "editor.auto_save":
            self._autosave_enabled = bool(event.new)
            if self._autosave_tk_var is not None:
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
            if self._lang_locale_tk_var is not None:
                self._lang_locale_tk_var.set(new_lang)

    def _refresh_all_from_settings(self) -> None:
        with contextlib.suppress(Exception):
            self._set_theme(self._settings.effective("ui.theme"), persist=False)
        self._font_family = self._settings.effective("ui.font_family", self._font_family)
        self._font_size = int(self._settings.effective("ui.font_size", self._font_size))
        self._tab_width = int(self._settings.effective("editor.tab_size", self._tab_width))
        self._highlight_delay_ms = int(
            self._settings.effective("editor.highlight_delay_ms", self._highlight_delay_ms)
        )
        self._definition_highlight_duration_ms = int(
            self._settings.effective(
                "editor.definition_highlight_duration_ms",
                self._definition_highlight_duration_ms,
            )
        )
        self._suggest_delay_ms = int(
            self._settings.effective("editor.suggestion_delay_ms", self._suggest_delay_ms)
        )
        self._suggest_min_chars = int(
            self._settings.effective("completion.min_chars_before_trigger", self._suggest_min_chars)
        )
        self._autosave_format = self._settings.effective(
            "editor.auto_save_format", self._autosave_format
        )
        self._autosave_delay_ms = int(
            self._settings.effective("editor.auto_save_delay_ms", self._autosave_delay_ms)
        )
        try:
            hl_theme = self._settings.effective("ui.highlight_theme", self._highlight_theme_name)
            if hl_theme in highlight_themes.available_names():
                self._set_highlight_theme(hl_theme, persist=False)
        except Exception:
            pass
        for var, value in (
            (self._font_family_tk_var, self._font_family),
            (self._font_size_tk_var, int(self._font_size)),
            (self._tab_width_tk_var, int(self._tab_width)),
            (self._highlight_theme_tk_var, self._highlight_theme_name),
        ):
            if var is not None:
                with contextlib.suppress(tk.TclError):
                    var.set(value)
        self.buffer.apply_font()
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

    # ------------------------------------------------------------------
    # Language / i18n lifecycle
    # ------------------------------------------------------------------

    def _on_language_changed(self, lang: str) -> None:
        if getattr(self, "_lang_changing", False):
            return
        self._lang_changing = True
        try:
            for attr in ("_settings_window", "_plugin_manager_window"):
                win = getattr(self, attr, None)
                if win is not None and win.winfo_exists():
                    with contextlib.suppress(tk.TclError):
                        win.destroy()
            self.buffer.close_find_dialog()
            self.menus.destroy()
            self.menus = MenuBuilder(self)
            self._shell_argv = default_shell_argv(self._settings)
            self.menus.build()
            self._refresh_shortcuts()
            with contextlib.suppress(Exception):
                self._refresh_plugin_menu()
            self._refresh_status_for_language()
        finally:
            self._lang_changing = False

    def _refresh_status_for_language(self) -> None:
        if not hasattr(self, "_status_label"):
            return
        with contextlib.suppress(tk.TclError):
            self._status_label.config(text=t("status.ready"))
        self.refresh_status()

    def _set_language_locale(self, lang: str) -> None:
        if lang not in AVAILABLE_LANGUAGES:
            return
        if self._lang_locale_tk_var is not None:
            self._lang_locale_tk_var.set(lang)
        self._write_setting(SettingsScope.GLOBAL, "i18n.language", lang)

    # ------------------------------------------------------------------
    # Toolbar / status / layout
    # ------------------------------------------------------------------

    def _build_toolbar(self) -> None:
        bar = UFrame(self.window, variant="title")
        bar.pack(fill=tk.X, padx=0, pady=0)

    def _build_status_bar(self) -> None:
        status = UFrame(self.window, variant="title", height=24)
        status.pack(fill=tk.X, padx=0, pady=0)
        status.pack_propagate(False)

        self._status_label = ULabel(
            status, text=t("status.ready"), variant="secondary", bg=theme.BG_TITLE
        )
        self._status_label.pack(side=tk.LEFT, padx=10, pady=2)

        self._lang_label = ULabel(status, text=self._lang, variant="secondary", bg=theme.BG_TITLE)
        self._lang_label.pack(side=tk.RIGHT, padx=10, pady=2)

        self._pos_label = ULabel(
            status,
            text=t("status.pos", line=1, col=1),
            variant="secondary",
            bg=theme.BG_TITLE,
        )
        self._pos_label.pack(side=tk.RIGHT, padx=10, pady=2)

    # ------------------------------------------------------------------
    # Sidebar / tab callbacks
    # ------------------------------------------------------------------

    def _on_sidebar_select(self, card_id: str) -> None:
        if card_id == "explorer" and self._current_project_root:
            self._explorer_card.set_root(self._current_project_root)
        elif card_id == "git" and self._current_project_root:
            self._git_card.set_root(self._current_project_root)

    def _open_path_from_tree(self, path: str) -> None:
        self._load_file_into_editor(path)

    def _on_tab_select(self, doc_id: str) -> None:
        self.tabs.switch_to(doc_id)

    def _on_tab_close(self, doc_id: str) -> None:
        self.tabs.close(doc_id)

    def _on_tab_context_menu(self, doc_id: str, x_root: int, y_root: int) -> None:
        self.tabs.show_tab_context_menu(doc_id, x_root, y_root)

    def _close_active_tab(self) -> None:
        self.tabs.close_active()

    # ------------------------------------------------------------------
    # File operations (delicate glue between TabManager and IO helpers)
    # ------------------------------------------------------------------

    def _new_file(self) -> None:
        if self.tabs.new_file(emit=False):
            self._current_file = None
            self._status_label.config(text=t("status.new_file"))
            self.emit(HookEvents.EDITOR_FILE_CREATED)
            app_logger.info(f"New file created: {self.tabs.active_id}")

    def _open_file(self) -> None:
        active_id = self.tabs.active_id
        if active_id and active_id in self.tabs.documents:
            curr = self.tabs.documents[active_id]
            if curr.dirty and not self._confirm_unsaved_discard():
                return

        ext = LANG_CONFIG[self._lang]["ext"]
        lang_label = t("file_dialog.lang_filter", lang=self._lang)
        filetypes = [(lang_label, f"*{ext}"), (t("file_dialog.all_files"), "*.*")]
        path = tk.filedialog.askopenfilename(filetypes=filetypes)
        if not path:
            return

        for doc_id, doc in self.tabs.documents.items():
            if doc.path == path:
                self.tabs.switch_to(doc_id)
                return

        self._load_path_into_editor(path)
        app_logger.info(f"File opened: {path}")

    def _open_project(self) -> None:
        if self._is_active_dirty() and not self._confirm_unsaved_discard():
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

    def _save_file(self) -> None:
        doc = self.get_active_document()
        if doc is not None:
            if doc.path:
                self._save_to_path(doc.path)
            else:
                self._save_file_as()
        else:
            self._save_file_as()

    def _save_file_as(self) -> None:
        ext = str(LANG_CONFIG[self._lang]["ext"])
        lang_label = t("file_dialog.lang_filter", lang=self._lang)
        filetypes = [(lang_label, f"*{ext}"), (t("file_dialog.all_files"), "*.*")]
        path = tk.filedialog.asksaveasfilename(defaultextension=ext, filetypes=filetypes)
        if not path:
            return
        self._save_to_path(path)
        doc = self.get_active_document()
        if doc is not None:
            doc.path = path
        self._current_file = path
        from core.editor.helpers import detect_lang_from_path

        detected = detect_lang_from_path(path)
        if detected != self._lang:
            self._switch_language(detected, from_doc_switch=True)
        new_root = self._should_reattach_for_path(path)
        if new_root:
            self._attach_project(new_root)

    def _save_to_path(self, path: str) -> None:
        code = self._editor.get("1.0", "end-1c")
        self.emit(HookEvents.EDITOR_BEFORE_SAVE, path)
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(code)
        except OSError as e:
            app_logger.error(f"Failed to save file {path}: {e}")
            tk.messagebox.showerror(t("dialog.title.save_failed"), str(e))
            return
        self.tabs.sync_dirty(False)
        doc = self.get_active_document()
        if doc is not None:
            doc.content = code
        self._status_label.config(text=t("status.saved", name=os.path.basename(path)))
        app_logger.info(f"File saved: {path}")
        self.emit(HookEvents.EDITOR_FILE_SAVED, path)

    def _load_file_into_editor(self, path: str) -> None:
        if self._is_active_dirty() and not self._confirm_unsaved_discard():
            return
        self._load_path_into_editor(path)

    def _load_path_into_editor(self, path: str) -> None:
        threshold_raw = self._settings.effective(
            "editor.large_file_threshold_bytes", DEFAULT_LARGE_FILE_THRESHOLD
        )
        threshold = resolve_threshold(threshold_raw)
        size = file_size(path)
        is_large = threshold > 0 and size >= threshold

        if is_large:
            tk.messagebox.showwarning(
                t("dialog.title.large_file"),
                t(
                    "dialog.large_file.message",
                    size=_human_size(size),
                    threshold=_human_size(threshold),
                ),
                parent=self.window,
            )

        from core.editor.helpers import detect_lang_from_path

        detected_lang = detect_lang_from_path(path)
        self.tabs.register_opened(path, detected_lang)
        self._editor._text.config(state="normal")
        self.buffer.large_file_mode = False  # type: ignore[attr-defined]
        self._editor._text.delete("1.0", tk.END)
        self._current_file = path

        if is_large:
            self._status_label.config(
                text=t("status.loading", name=os.path.basename(path), size=_human_size(size))
            )

            def _on_complete(content: str) -> None:
                doc = self.get_active_document()
                if doc is not None:
                    doc.content = content
                self._status_label.config(text=t("status.opened", name=os.path.basename(path)))
                self.emit(HookEvents.EDITOR_FILE_OPENED, path)

            stream_load_file(
                self.window,
                self._editor._text,
                path,
                on_complete=_on_complete,
                on_error=lambda msg: tk.messagebox.showerror(
                    t("dialog.title.open_failed"), msg, parent=self.window
                ),
            )
        else:
            try:
                code = read_full(path)
            except (OSError, UnicodeDecodeError) as exc:
                tk.messagebox.showerror(t("dialog.title.open_failed"), str(exc), parent=self.window)
                return
            doc = self.get_active_document()
            if doc is not None:
                doc.content = code
            self._editor._text.insert("1.0", code)
            self._status_label.config(text=t("status.opened", name=os.path.basename(path)))

        new_root = self._should_reattach_for_path(path)
        if new_root:
            self._attach_project(new_root)

        if not is_large and detected_lang != self._lang:
            self._switch_language(detected_lang, from_doc_switch=True)
        if not is_large:
            self.buffer.apply_highlight()

    def _should_reattach_for_path(self, path: str) -> str | None:
        abs_path = os.path.abspath(path)
        file_dir = os.path.dirname(abs_path)
        if not self._current_project_root:
            return file_dir or None
        if not file_dir:
            return None
        if _is_within(file_dir, self._current_project_root):
            return None
        return file_dir

    def _is_active_dirty(self) -> bool:
        return self.tabs.dirty

    def _confirm_unsaved_discard(self) -> bool:
        return self.confirm_unsaved_discard()

    # ------------------------------------------------------------------
    # Project / settings
    # ------------------------------------------------------------------

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
        if self._explorer_card is not None:
            self._explorer_card.set_root(root)
        with contextlib.suppress(Exception):
            self._plugin_manager.load_project_plugins(root)
        self._refresh_plugin_menu()
        self._refresh_plugin_languages()

    def _open_global_settings(self) -> None:
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

    def _open_project_settings(self) -> None:
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

    def _reset_settings(self) -> None:
        if not tk.messagebox.askyesno(
            t("dialog.title.reset_settings"),
            t("dialog.reset_settings.confirm"),
            parent=self.window,
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

    def _write_setting(self, scope: SettingsScope, key: str, value: Any) -> None:
        self._suppress_settings_listener = True
        try:
            self._settings.set(scope, key, value)
        except (KeyError, ValueError):
            pass
        finally:
            self._suppress_settings_listener = False

    # ------------------------------------------------------------------
    # Theme / highlight theme / font / tab width / toggles
    # ------------------------------------------------------------------

    def _set_theme(self, name: str, *, persist: bool = True) -> None:
        try:
            target = theme.by_name(name)
            if target is None:
                return
            theme.set_theme(target, refresh_root=self.window)
            if self._theme_tk_var is not None:
                self._theme_tk_var.set(name)
            self._status_label.config(text=t("status.theme", name=name))
            self._force_redraw()
            self.buffer.cancel_pending_highlight()
            self.buffer.apply_highlight()
            self.emit(HookEvents.EDITOR_THEME_CHANGED, name)
            app_logger.info(f"Theme changed to: {name}")
        except Exception as e:
            app_logger.error(f"Failed to set theme {name}: {e}")
            self._status_label.config(text=t("status.theme_error", err=str(e)))
            return
        if persist:
            self._write_setting(SettingsScope.GLOBAL, "ui.theme", name)

    def _set_highlight_theme(self, name: str, *, persist: bool = True) -> None:
        if name not in highlight_themes.available_names():
            return
        self._highlight_theme_name = name
        highlight_themes.set_theme(name)
        if self._highlight_theme_tk_var is not None:
            self._highlight_theme_tk_var.set(name)
        self.buffer.cancel_pending_highlight()
        self.buffer.apply_highlight()
        self._status_label.config(text=t("status.highlight_theme", name=name))
        app_logger.info(f"Highlight theme changed to: {name}")
        if persist:
            self._write_setting(SettingsScope.GLOBAL, "ui.highlight_theme", name)

    def _set_font_family(self, family: str) -> None:
        self._font_family = family
        if self._font_family_tk_var is not None:
            self._font_family_tk_var.set(family)
        self.buffer.apply_font()
        self._status_label.config(text=t("status.font", name=family))
        self._write_setting(SettingsScope.GLOBAL, "ui.font_family", family)

    def _set_font_size(self, size: int) -> None:
        self._font_size = size
        if self._font_size_tk_var is not None:
            self._font_size_tk_var.set(size)
        self.buffer.apply_font()
        self._status_label.config(text=t("status.font_size", n=size))
        self._write_setting(SettingsScope.GLOBAL, "ui.font_size", int(size))

    def _set_tab_width(self, tw: int, *, persist: bool = True) -> None:
        self._tab_width = tw
        if self._tab_width_tk_var is not None:
            self._tab_width_tk_var.set(tw)
        self.buffer.apply_tab_width()
        if persist:
            self._write_setting(SettingsScope.GLOBAL, "editor.tab_size", int(tw))

    def _toggle_highlighting(self) -> None:
        if self._highlight_tk_var is not None:
            self._highlighting_enabled = bool(self._highlight_tk_var.get())
        if not self._highlighting_enabled:
            self.buffer.cancel_pending_highlight()
            text = self._editor._text
            for tag in text.tag_names():
                text.tag_delete(tag)
        else:
            self.buffer.cancel_pending_highlight()
            self.buffer.apply_highlight()
        self._write_setting(SettingsScope.GLOBAL, "completion.enabled", self._highlighting_enabled)

    def _toggle_suggestions(self) -> None:
        if self._suggestion_tk_var is not None:
            self._suggestions_enabled = bool(self._suggestion_tk_var.get())
        self.buffer.toggle_suggestions(self._suggestions_enabled)
        self._write_setting(SettingsScope.GLOBAL, "completion.enabled", self._suggestions_enabled)

    def _toggle_autosave(self) -> None:
        if self._autosave_tk_var is not None:
            self._autosave_enabled = bool(self._autosave_tk_var.get())
        self._write_setting(SettingsScope.GLOBAL, "editor.auto_save", self._autosave_enabled)

    # ------------------------------------------------------------------
    # Marketplace / plugin / help dialogs
    # ------------------------------------------------------------------

    def _on_settings_panel_action(self, key: str, value: Any) -> None:
        if key == "ui.highlight_theme_marketplace":
            self._open_highlight_theme_marketplace()
        elif key == "ui.theme_marketplace":
            self._open_ui_theme_marketplace()
        elif key == "plugins.marketplace":
            self._open_plugin_marketplace()
        elif key == "i18n.language_marketplace":
            self._open_language_marketplace()

    def _open_highlight_theme_marketplace(self) -> None:
        from core.language.highlighter import highlight_marketplace

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

    def _open_ui_theme_marketplace(self) -> None:
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

    def _open_marketplace(self) -> None:
        UMarketplaceWindow(self)

    def _open_plugin_marketplace(self) -> None:
        from core.plugins import plugin_marketplace

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

    def _open_language_marketplace(self) -> None:
        from core.settings.i18n import language_marketplace

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

    def _open_plugin_manager(self) -> None:
        from core.plugins.widgets import UPluginManagerWindow

        try:
            win = UPluginManagerWindow(
                self._plugin_manager,
                parent=self.window,
                title=t("dialog.title.plugin_manager"),
            )
            self._plugin_manager_window = win
        except Exception as exc:
            tk.messagebox.showerror(
                t("dialog.title.plugin_manager_error"),
                t("dialog.plugin_manager.load_failed", err=exc),
                parent=self.window,
            )

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
        menu = self.menus.plugin_menu
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
        return None

    def _safe_run_plugin_command(self, callback: Any) -> None:
        try:
            callback()
        except Exception as exc:
            self.runner.append_output(f"[ERROR] {t('dialog.plugin.error', err=exc)}\n")
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
        info = t(
            "plugin.info.template",
            name=m.name,
            id=m.id,
            version=version,
            author=author,
            scope=m.scope,
            location=src,
            status=status,
        )
        if error_info:
            info = f"{info}\n{error_info}"
        if desc:
            info = f"{info}\n\n{desc}"
        tk.messagebox.showinfo(t("dialog.title.plugin", name=m.name), info, parent=self.window)

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

    # ------------------------------------------------------------------
    # Run / check / shell
    # ------------------------------------------------------------------

    def _open_shell(self) -> None:
        self.runner.open_shell()

    def _run_check(self) -> None:
        self.runner.run_check()

    def _stop_running(self) -> None:
        self.runner.stop_running()

    def _clear_output(self) -> None:
        self.runner.clear_output()

    # ------------------------------------------------------------------
    # Misc actions
    # ------------------------------------------------------------------

    def _find_documentation(self) -> None:
        if self._lang != "Python":
            tk.messagebox.showinfo(
                t("dialog.title.find_documentation"),
                t("dialog.find_documentation.unsupported_lang", lang=self._lang),
                parent=self.window,
            )
            return
        word = self.buffer.get_word_under_cursor()
        if not word:
            return
        info = self.buffer.lookup_documentation(word)
        if not info:
            tk.messagebox.showinfo(
                t("dialog.title.find_documentation"),
                t("dialog.find_documentation.not_found", symbol=word),
                parent=self.window,
            )
            return
        ReferencesDialog.show_documentation(
            self.window, word, info, font_family=self._font_family, font_size=self._font_size
        )

    def _reparse(self) -> None:
        self.buffer.apply_highlight()
        self._status_label.config(text=t("status.reparsed"))

    def _force_redraw(self) -> None:
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

    def _show_documentation(self) -> None:
        tk.messagebox.showinfo(t("dialog.title.docs"), t("dialog.docs.message"), parent=self.window)

    def _show_shortcuts(self) -> None:
        win = UShortcutConfigWindow(self.window, self._settings, on_apply=self._rebind_shortcuts)
        win.wait_window()

    def _rebind_shortcuts(self) -> None:
        self._refresh_shortcuts()

    def _refresh_shortcuts(self) -> None:
        defaults = ShortcutBinder.DEFAULTS
        stored = self._settings.effective("shortcuts.custom", {})
        specs = {k: stored.get(k, v) for k, v in defaults.items()}
        for name, spec in specs.items():
            action = self.actions.get(name)
            if action is None:
                continue
            from core.editor.helpers import tk_shortcut

            binding = tk_shortcut(spec)
            with contextlib.suppress(tk.TclError):
                self.window.bind(binding, lambda _e, cb=action: cb())

    def _show_about(self) -> None:
        tk.messagebox.showinfo(t("dialog.title.about"), t("dialog.about.body"), parent=self.window)

    def _check_updates(self) -> None:
        tk.messagebox.showinfo(
            t("dialog.title.check_updates"),
            t("dialog.updates.message"),
            parent=self.window,
        )

    def _report_issue(self) -> None:
        tk.messagebox.showinfo(
            t("dialog.title.report_issue"),
            t("dialog.report_issue.message"),
            parent=self.window,
        )

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def _on_close_request(self) -> None:
        dirty_docs = [doc for doc in self.tabs.documents.values() if doc.dirty]
        if dirty_docs and not tk.messagebox.askyesno(
            t("dialog.title.unsaved_exit"),
            t("dialog.unsaved_exit.message"),
        ):
            return

        self.runner.terminate_running()
        self.buffer.cancel_pending_highlight()
        self.buffer.cancel_pending_suggestions()
        app_logger.info("Editor closing...")
        self.emit(HookEvents.EDITOR_CLOSING)
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
