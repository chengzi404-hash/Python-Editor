from __future__ import annotations

import tkinter as tk
from collections.abc import Callable

from core.settings.i18n import t
from core.settings.settings import SettingsManager

from . import theme
from .button import UButton
from .dialog import UDialog
from .label import ULabel
from .list_view import UListView


class UShortcutConfigWindow(UDialog):
    def __init__(
        self, parent, settings_manager: SettingsManager, on_apply: Callable[[], None] | None = None
    ):
        self._settings = settings_manager
        self._on_apply = on_apply
        self._shortcuts: dict[str, str] = {}
        self._default_shortcuts: dict[str, str] = {}
        self._editing_index: int | None = None
        self._capture_binding: str | None = None

        super().__init__(parent, title=t("dialog.title.shortcut_config"), width=550, height=450)
        self._build_ui()

    def _build_ui(self):
        body = self.body
        body.config(bg=theme.BG_PANEL)

        header_frame = tk.Frame(body, bg=theme.BG_TITLE, height=32)
        header_frame.pack(fill=tk.X)
        header_frame.pack_propagate(False)

        col_action = t("shortcut.column.action")
        col_shortcut = t("shortcut.column.current")
        self._list_view = UListView(
            body,
            columns=[col_action, col_shortcut],
            column_widths={col_action: 200, col_shortcut: 150},
            show_header=True,
            on_select=self._on_list_select,
        )
        self._list_view.pack(fill=tk.BOTH, expand=True, padx=12, pady=(12, 0))

        self._info_label = ULabel(body, text=t("shortcut.click_to_edit"), variant="secondary")
        self._info_label.pack(fill=tk.X, padx=12, pady=(8, 0))

        self._capture_label = ULabel(body, text="", variant="primary")
        self._capture_label.pack(fill=tk.X, padx=12, pady=(4, 0))
        self._capture_label.pack_forget()

        btn_frame = tk.Frame(body, bg=theme.BG_PANEL)
        btn_frame.pack(fill=tk.X, padx=12, pady=12)

        self._reset_btn = UButton(
            btn_frame, text=t("shortcut.reset"), variant="default", command=self._on_reset
        )
        self._reset_btn.pack(side=tk.LEFT)

        self._reset_all_btn = UButton(
            btn_frame, text=t("shortcut.reset_all"), variant="default", command=self._on_reset_all
        )
        self._reset_all_btn.pack(side=tk.LEFT, padx=(8, 0))

        spacer = tk.Frame(btn_frame, bg=theme.BG_PANEL)
        spacer.pack(side=tk.LEFT, expand=True, fill=tk.X)

        self._save_btn = UButton(
            btn_frame, text=t("settings.button.save"), variant="primary", command=self._on_save
        )
        self._save_btn.pack(side=tk.RIGHT)

        self._cancel_btn = UButton(
            btn_frame, text=t("settings.button.close"), variant="default", command=self.destroy
        )
        self._cancel_btn.pack(side=tk.RIGHT, padx=(8, 0))

        self._load_shortcuts()

    def _load_shortcuts(self):
        self._default_shortcuts = {
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

        stored = self._settings.global_settings.get("shortcuts.custom", {})
        self._shortcuts = {k: stored.get(k, v) for k, v in self._default_shortcuts.items()}

        self._refresh_list()

    def _refresh_list(self):
        col_action = t("shortcut.column.action")
        col_shortcut = t("shortcut.column.current")

        action_labels = {
            "new_file": t("menu.file.new"),
            "open_file": t("menu.file.open"),
            "open_project": t("menu.file.open_project"),
            "save_file": t("menu.file.save"),
            "save_file_as": t("menu.file.save_as"),
            "run_check": t("menu.file.check"),
            "run_code": t("menu.file.run"),
            "clear_output": t("menu.file.clear_output"),
            "undo": t("menu.edit.undo"),
            "redo": t("menu.edit.redo"),
            "find": t("menu.edit.find"),
            "replace": t("menu.edit.replace"),
            "goto_line": t("menu.edit.goto_line"),
            "goto_definition": t("menu.query.goto_definition"),
            "find_references": t("menu.query.find_references"),
            "reparse": t("menu.query.reparse"),
            "apply_highlight": t("menu.query.refresh_highlight"),
            "trigger_suggestions": t("menu.query.trigger_suggestions"),
            "show_documentation": t("menu.help.docs"),
            "toggle_comment": t("menu.edit.toggle_comment"),
            "close_tab": t("menu.file.close_tab"),
            "next_tab": t("shortcut.next_tab"),
            "prev_tab": t("shortcut.prev_tab"),
        }

        data = []
        for key, shortcut in self._shortcuts.items():
            action = action_labels.get(key, key)
            data.append({col_action: action, col_shortcut: shortcut})

        self._list_view.set_data(data)

    def _on_save(self):
        self._settings.global_settings.set("shortcuts.custom", self._shortcuts)
        self._settings.global_settings.save()
        if self._on_apply:
            self._on_apply()
        self.destroy()

    def _on_reset(self):
        selected = self._list_view.selected_index()
        if selected is not None:
            keys = list(self._shortcuts.keys())
            if 0 <= selected < len(keys):
                key = keys[selected]
                self._shortcuts[key] = self._default_shortcuts[key]
                self._refresh_list()

    def _on_reset_all(self):
        self._shortcuts = dict(self._default_shortcuts)
        self._refresh_list()

    def _on_list_select(self, index: int, data: dict):
        self._start_capture(index)

    def _start_capture(self, index: int):
        if self._editing_index is not None:
            self._cancel_capture()

        self._editing_index = index
        keys = list(self._shortcuts.keys())
        action_key = keys[index]

        action_labels = {
            "new_file": t("menu.file.new"),
            "open_file": t("menu.file.open"),
            "open_project": t("menu.file.open_project"),
            "save_file": t("menu.file.save"),
            "save_file_as": t("menu.file.save_as"),
            "run_check": t("menu.file.check"),
            "run_code": t("menu.file.run"),
            "clear_output": t("menu.file.clear_output"),
            "undo": t("menu.edit.undo"),
            "redo": t("menu.edit.redo"),
            "find": t("menu.edit.find"),
            "replace": t("menu.edit.replace"),
            "goto_line": t("menu.edit.goto_line"),
            "goto_definition": t("menu.query.goto_definition"),
            "find_references": t("menu.query.find_references"),
            "reparse": t("menu.query.reparse"),
            "apply_highlight": t("menu.query.refresh_highlight"),
            "trigger_suggestions": t("menu.query.trigger_suggestions"),
            "show_documentation": t("menu.help.docs"),
            "toggle_comment": t("menu.edit.toggle_comment"),
            "close_tab": t("menu.file.close_tab"),
            "next_tab": t("shortcut.next_tab"),
            "prev_tab": t("shortcut.prev_tab"),
        }
        action_name = action_labels.get(action_key, action_key)
        self._capture_label.config(text=t("shortcut.press_new", action=action_name))
        self._capture_label.pack(fill=tk.X, padx=12, pady=(4, 0))

        self._capture_binding = self.bind("<Key>", self._on_key_capture, add="+")

    def _cancel_capture(self):
        if self._capture_binding is not None:
            self.unbind("<Key>", self._capture_binding)
            self._capture_binding = None
        self._editing_index = None
        self._capture_label.pack_forget()

    def _on_key_capture(self, event: tk.Event):
        if self._editing_index is None:
            return

        key_name = event.keysym
        if key_name in ("Shift_L", "Shift_R", "Control_L", "Control_R", "Alt_L", "Alt_R"):
            return

        state_val = getattr(event, "state", 0)
        if isinstance(state_val, str):
            state_val = 0

        # Bitmask constants for modifier detection (platform-independent)
        # SHIFT=0x1, CONTROL=0x4, ALT=0x20000 (not 0x8 which is NumLock on Windows)
        _mod_shift = 0x1
        _mod_ctrl = 0x4
        _mod_alt = 0x20000
        modifiers = []
        if state_val & _mod_shift:
            modifiers.append("Shift")
        if state_val & _mod_ctrl:
            modifiers.append("Ctrl")
        if state_val & _mod_alt:
            modifiers.append("Alt")

        if key_name == "Tab":
            modifiers.append("Shift")
        elif key_name.lower() == "space":
            key_name = "Space"
        elif key_name.lower() == "slash":
            key_name = "Slash"
        elif len(key_name) == 1:
            key_name = key_name.upper()

        shortcut_str = "+".join([*modifiers, key_name])

        keys = list(self._shortcuts.keys())
        shortcut_key = keys[self._editing_index]
        self._shortcuts[shortcut_key] = shortcut_str

        self._cancel_capture()
        self._refresh_list()

        selected_idx = self._editing_index
        if selected_idx is not None:
            self._list_view._select(selected_idx)

    def destroy(self):
        self._cancel_capture()
        super().destroy()


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
