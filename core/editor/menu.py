"""Menu bar and shortcut bindings for the CodeEditor.

The :class:`MenuBuilder` constructs (and later rebuilds on language change)
the application menu, while :class:`ShortcutBinder` wires keyboard shortcuts
to editor callbacks based on user preferences. Both rely on small host hooks
so this module never imports the giant ``CodeEditor`` class directly.
"""

from __future__ import annotations

import contextlib
import tkinter as tk
from collections.abc import Callable
from typing import Any, ClassVar, Protocol

from core.editor.helpers import tk_shortcut
from core.editor.lang_config import (
    FONT_FAMILIES,
    FONT_SIZES,
    LANG_CONFIG,
    TAB_WIDTHS,
    THEME_NAMES,
)
from core.language.highlighter import highlight_themes
from core.settings.i18n import AVAILABLE_LANGUAGES, t
from ui.widgets import UMenuBar


class MenuHost(Protocol):
    """A minimal contract :class:`MenuBuilder` needs from its host editor."""

    window: tk.Tk
    settings: Any
    current_language: str
    font_family: str
    font_size: int
    highlight_theme_name: str
    plugin_menu_actions: dict[str, list[dict]]
    plugin_menu: Any
    marketplace_menu: Any

    @property
    def actions(self) -> dict[str, Callable[[], None]]: ...


class MenuBuilder:
    """Builds and rebuilds the application menu bar."""

    def __init__(self, host: MenuHost) -> None:
        self._host = host
        self._menubar: UMenuBar | None = None
        self._plugin_menu: Any = None
        self._marketplace_menu: Any = None

    @property
    def menubar(self) -> UMenuBar | None:
        return self._menubar

    @property
    def plugin_menu(self) -> Any:
        return self._plugin_menu

    @property
    def marketplace_menu(self) -> Any:
        return self._marketplace_menu

    def build(self) -> None:
        host = self._host
        actions = host.actions

        bar = UMenuBar(host.window)
        bar.pack(fill=tk.X, padx=0, pady=0)
        self._menubar = bar

        file_menu = bar.add_cascade(t("menu.file"))
        file_menu.add_command(t("menu.file.new"), actions["new_file"], "Ctrl+N")
        file_menu.add_command(t("menu.file.open"), actions["open_file"], "Ctrl+O")
        file_menu.add_command(t("menu.file.open_project"), actions["open_project"], "Ctrl+Shift+O")
        file_menu.add_separator()
        file_menu.add_command(t("menu.file.save"), actions["save_file"], "Ctrl+S")
        file_menu.add_command(t("menu.file.save_as"), actions["save_file_as"], "Ctrl+Shift+S")
        file_menu.add_separator()
        file_menu.add_command(t("menu.file.close_tab"), actions["close_tab"], "Ctrl+W")
        file_menu.add_separator()
        file_menu.add_command(t("menu.file.open_terminal"), actions["open_shell"], "F5")
        file_menu.add_command(t("menu.file.check"), actions["run_check"], "Ctrl+R")
        file_menu.add_command(t("menu.file.clear_output"), actions["clear_output"], "Ctrl+L")
        file_menu.add_separator()
        file_menu.add_command(t("menu.file.exit"), host.window.destroy, "Alt+F4")

        edit_menu = bar.add_cascade(t("menu.edit"))
        edit_menu.add_command(t("menu.edit.undo"), actions["undo"], "Ctrl+Z")
        edit_menu.add_command(t("menu.edit.redo"), actions["redo"], "Ctrl+Y")
        edit_menu.add_separator()
        edit_menu.add_command(t("menu.edit.cut"), actions["cut"], "Ctrl+X")
        edit_menu.add_command(t("menu.edit.copy"), actions["copy"], "Ctrl+C")
        edit_menu.add_command(t("menu.edit.paste"), actions["paste"], "Ctrl+V")
        edit_menu.add_separator()
        edit_menu.add_command(t("menu.edit.select_all"), actions["select_all"], "Ctrl+A")
        edit_menu.add_separator()
        edit_menu.add_command(t("menu.edit.find"), actions["open_find"], "Ctrl+F")
        edit_menu.add_command(t("menu.edit.replace"), actions["open_replace"], "Ctrl+H")
        edit_menu.add_command(t("menu.edit.goto_line"), actions["goto_line"], "Ctrl+G")
        edit_menu.add_separator()
        edit_menu.add_command(t("menu.edit.indent"), actions["indent"], "Tab")
        edit_menu.add_command(t("menu.edit.outdent"), actions["outdent"], "Shift+Tab")
        edit_menu.add_command(
            t("menu.edit.toggle_comment"),
            actions["toggle_comment"],
            "Ctrl+/",
        )
        lang_sub = edit_menu.add_cascade(t("menu.edit.switch_language"))
        for name in LANG_CONFIG:
            lang_sub.add_radiobutton(
                name,
                value=name,
                variable=actions["lang_var_creator"](),
                command=lambda n=name: actions["switch_language"](n),
            )

        query_menu = bar.add_cascade(t("menu.query"))
        query_menu.add_command(t("menu.query.goto_definition"), actions["goto_definition"], "F12")
        query_menu.add_command(
            t("menu.query.find_references"), actions["find_references"], "Shift+F12"
        )
        query_menu.add_command(
            t("menu.query.find_documentation"),
            actions["find_documentation"],
            "Ctrl+Shift+F1",
        )
        query_menu.add_separator()
        query_menu.add_command(t("menu.query.reparse"), actions["reparse"], "F6")
        query_menu.add_command(t("menu.query.refresh_highlight"), actions["apply_highlight"], "F7")
        query_menu.add_separator()
        query_menu.add_command(
            t("menu.query.trigger_suggestions"),
            actions["trigger_suggestions"],
            "Ctrl+Space",
        )
        query_menu.add_command(t("menu.query.hide_suggestions"), actions["hide_suggestions"], "Esc")

        settings_menu = bar.add_cascade(t("menu.settings"))
        theme_sub = settings_menu.add_cascade(t("menu.settings.theme"))
        for name in THEME_NAMES:
            theme_sub.add_radiobutton(
                name,
                value=name,
                variable=actions["theme_var_creator"](),
                command=lambda n=name: actions["set_theme"](n),
            )
        theme_sub.add_separator()
        theme_sub.add_command(
            t("menu.settings.theme_marketplace"), actions["open_ui_theme_marketplace"]
        )
        hl_theme_sub = settings_menu.add_cascade(t("menu.settings.highlight_theme"))
        for name in highlight_themes.available_names():
            hl_theme_sub.add_radiobutton(
                name,
                value=name,
                variable=actions["highlight_theme_var_creator"](),
                command=lambda n=name: actions["set_highlight_theme"](n),
            )
        hl_theme_sub.add_separator()
        hl_theme_sub.add_command(
            t("menu.settings.highlight_theme_marketplace"),
            actions["open_highlight_theme_marketplace"],
        )
        font_sub = settings_menu.add_cascade(t("menu.settings.font"))
        for fnt in FONT_FAMILIES:
            font_sub.add_radiobutton(
                fnt,
                value=fnt,
                variable=actions["font_family_var_creator"](),
                command=lambda f=fnt: actions["set_font_family"](f),
            )
        size_sub = settings_menu.add_cascade(t("menu.settings.font_size"))
        for sz in FONT_SIZES:
            size_sub.add_radiobutton(
                str(sz),
                value=sz,
                variable=actions["font_size_var_creator"](),
                command=lambda s=sz: actions["set_font_size"](s),
            )
        tab_sub = settings_menu.add_cascade(t("menu.settings.tab_width"))
        for tw in TAB_WIDTHS:
            tab_sub.add_radiobutton(
                str(tw),
                value=tw,
                variable=actions["tab_width_var_creator"](),
                command=lambda t=tw: actions["set_tab_width"](t),
            )
        settings_menu.add_separator()
        settings_menu.add_checkbutton(
            t("menu.settings.enable_highlight"),
            variable=actions["highlight_var_creator"](),
            command=actions["toggle_highlighting"],
        )
        settings_menu.add_checkbutton(
            t("menu.settings.enable_suggestions"),
            variable=actions["suggestion_var_creator"](),
            command=actions["toggle_suggestions"],
        )
        settings_menu.add_checkbutton(
            t("menu.settings.auto_save"),
            variable=actions["autosave_var_creator"](),
            command=actions["toggle_autosave"],
        )
        settings_menu.add_separator()
        lang_locale_sub = settings_menu.add_cascade(t("menu.settings.language"))
        for lang in AVAILABLE_LANGUAGES:
            lang_locale_sub.add_radiobutton(
                t(f"menu.language.{lang}"),
                value=lang,
                variable=actions["lang_locale_var_creator"](),
                command=lambda code=lang: actions["set_language_locale"](code),
            )
        lang_locale_sub.add_separator()
        lang_locale_sub.add_command(
            t("menu.settings.language_marketplace"),
            actions["open_language_marketplace"],
        )
        settings_menu.add_separator()
        settings_menu.add_command(
            t("menu.settings.global_settings"), actions["open_global_settings"]
        )
        settings_menu.add_command(
            t("menu.settings.project_settings"), actions["open_project_settings"]
        )
        settings_menu.add_command(t("menu.settings.reset"), actions["reset_settings"])

        help_menu = bar.add_cascade(t("menu.help"))
        help_menu.add_command(t("menu.help.docs"), actions["show_documentation"], "F1")
        help_menu.add_command(t("menu.help.shortcuts"), actions["show_shortcuts"], "Ctrl+K")
        help_menu.add_separator()
        help_menu.add_command(t("menu.help.about"), actions["show_about"])
        help_menu.add_command(t("menu.help.check_updates"), actions["check_updates"])
        help_menu.add_command(t("menu.help.report_issue"), actions["report_issue"])

        plugin_menu = bar.add_cascade(t("menu.plugins"))
        plugin_menu.add_command(t("menu.plugins.manage"), actions["open_plugin_manager"])
        plugin_menu.add_command(t("menu.plugins.marketplace"), actions["open_plugin_marketplace"])
        self._plugin_menu = plugin_menu

        marketplace_menu = bar.add_cascade(t("menu.marketplace"))
        marketplace_menu.add_command(t("menu.marketplace.browse"), actions["open_marketplace"])
        self._marketplace_menu = marketplace_menu

    def destroy(self) -> None:
        bar = self._menubar
        if bar is None:
            return
        try:
            for btn, _ in list(getattr(bar, "_buttons", [])):
                with contextlib.suppress(tk.TclError):
                    btn.destroy()
            bar._buttons = []  # type: ignore[attr-defined]
        except Exception:
            pass


class ShortcutBinder:
    """Binds (and rebinds) keyboard shortcuts to editor actions."""

    DEFAULTS: ClassVar[dict[str, str]] = {
        "new_file": "Ctrl+N",
        "open_file": "Ctrl+O",
        "open_project": "Ctrl+Shift+O",
        "save_file": "Ctrl+S",
        "save_file_as": "Ctrl+Shift+S",
        "run_check": "Ctrl+R",
        "open_shell": "F5",
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

    def __init__(self, window: tk.Tk, settings: Any) -> None:
        self._window = window
        self._settings = settings
        self._bindings: dict[str, str] = {}

    def bind_all(self, actions: dict[str, Callable[[], None]]) -> None:
        stored = self._settings.global_settings.get("shortcuts.custom", {})
        specs = {k: stored.get(k, v) for k, v in self.DEFAULTS.items()}
        for name, default_spec in self.DEFAULTS.items():
            spec = specs.get(name, default_spec)
            binding = spec
            callback = actions.get(name)
            if callback is None:
                continue
            self._window.bind(binding, lambda _e, cb=callback: cb())


def format_shortcut(spec: str) -> str:
    """Public alias for :func:`core.editor.helpers.tk_shortcut`."""
    return tk_shortcut(spec)
