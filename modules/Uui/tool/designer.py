"""Uui Visual Widget Designer — Qt Creator inspired layout."""

import contextlib
import re
import tkinter as tk
import xml.etree.ElementTree as ET
from pathlib import Path
from tkinter import filedialog, messagebox

from Uui import Window
from Uui.widgets import (
    UButton,
    UCheckButton,
    UComboBox,
    UEntry,
    UFrame,
    ULabel,
    UMenuBar,
    UProgressBar,
    URadioButton,
    UScrollBar,
    USlider,
    UText,
    theme,
)

DESIGNER_VERSION = "2.0"

WIDGET_TYPES = [
    "UFrame",
    "ULabel",
    "UButton",
    "UEntry",
    "UText",
    "UCheckButton",
    "URadioButton",
    "UComboBox",
    "UProgressBar",
    "USlider",
]

WIDGET_CLASSES = {
    "UFrame": UFrame,
    "ULabel": ULabel,
    "UButton": UButton,
    "UEntry": UEntry,
    "UText": UText,
    "UCheckButton": UCheckButton,
    "URadioButton": URadioButton,
    "UComboBox": UComboBox,
    "UProgressBar": UProgressBar,
    "USlider": USlider,
}

DEFAULT_PROPS = {
    "UFrame": {"variant": "panel"},
    "ULabel": {"text": "Label", "variant": "primary"},
    "UButton": {"text": "Button", "variant": "default"},
    "UEntry": {"placeholder": "", "show": ""},
    "UText": {},
    "UCheckButton": {"text": "Check"},
    "URadioButton": {"text": "Radio"},
    "UComboBox": {"values": ""},
    "UProgressBar": {"maximum": 100, "value": 0, "color": ""},
    "USlider": {"from_": 0, "to": 100, "value": 0, "orient": "horizontal", "show_value": False},
}

DEFAULT_SIZE = {
    "UFrame": (200, 120),
    "ULabel": (120, 24),
    "UButton": (96, 28),
    "UEntry": (160, 28),
    "UText": (200, 100),
    "UCheckButton": (140, 24),
    "URadioButton": (140, 24),
    "UComboBox": (160, 32),
    "UProgressBar": (160, 6),
    "USlider": (160, 22),
}

VARIANT_OPTIONS = {
    "UFrame": ["title", "base", "panel", "raised", "input"],
    "ULabel": ["primary", "secondary", "tertiary", "disabled", "blue", "red", "green", "yellow"],
    "UButton": ["default", "primary", "success", "danger", "warning", "ghost"],
}

NUMERIC_PROPS = {"x", "y", "width", "height", "maximum", "value", "from_", "to"}
BOOL_PROPS = {"show_value"}


WIDGET_GROUPS = [
    ("Layouts", []),
    ("Spacers", []),
    (
        "Buttons",
        [
            ("UButton", "PushButton", "▶"),
            ("UCheckButton", "CheckBox", "☑"),
            ("URadioButton", "RadioButton", "◉"),
        ],
    ),
    ("Item Widgets", [("UComboBox", "ComboBox", "▼")]),
    ("Input Widgets", [("UEntry", "LineEdit", "|"), ("UText", "TextEdit", "¶")]),
    (
        "Display",
        [
            ("ULabel", "Label", "T"),
            ("UProgressBar", "ProgressBar", "▰"),
            ("USlider", "Slider", "━"),
        ],
    ),
    ("Containers", [("UFrame", "Frame", "▢")]),
]

WIDGET_ICON = {wtype: icon for _, items in WIDGET_GROUPS for wtype, _, icon in items}
WIDGET_ICON = {
    **WIDGET_ICON,
    "UFrame": "▢",
    "ULabel": "T",
    "UButton": "▶",
    "UEntry": "|",
    "UText": "¶",
    "UCheckButton": "☑",
    "URadioButton": "◉",
    "UComboBox": "▼",
    "UProgressBar": "▰",
    "USlider": "━",
}


COMMON_GEOMETRY = ["x", "y", "width", "height"]
COMMON_OBJECT = ["name"]

TYPE_PROPS = {
    "UFrame": [("Form", ["variant"])],
    "ULabel": [("Text", ["text", "variant"])],
    "UButton": [("Text", ["text", "variant"]), ("Code", ["command"])],
    "UEntry": [("Input", ["placeholder", "show"])],
    "UText": [],
    "UCheckButton": [("Text", ["text"]), ("Code", ["command"])],
    "URadioButton": [("Text", ["text"]), ("Code", ["command"])],
    "UComboBox": [("Items", ["values"]), ("Code", ["command"])],
    "UProgressBar": [("Value", ["maximum", "value", "color"])],
    "USlider": [("Range", ["from_", "to", "value", "orient", "show_value"]), ("Code", ["command"])],
}

PROP_LABELS = {
    "name": "objectName",
    "x": "X",
    "y": "Y",
    "width": "width",
    "height": "height",
    "text": "text",
    "variant": "variant",
    "placeholder": "placeholder",
    "show": "echoMode",
    "values": "items",
    "maximum": "maximum",
    "value": "value",
    "from_": "minimum",
    "to": "maximum",
    "orient": "orientation",
    "show_value": "showValue",
    "color": "color",
    "command": "callback",
}


class _FlatButton(tk.Frame):
    """Compact flat button used in the toolbar (icon + hover state)."""

    HEIGHT = 28

    def __init__(
        self,
        parent,
        text: str,
        command=None,
        width: int = 30,
        tooltip: str = "",
        font=None,
        accent: bool = False,
    ):
        super().__init__(
            parent, bg=theme.BG_TITLE, highlightthickness=0, bd=0, width=width, height=self.HEIGHT
        )
        self.pack_propagate(False)
        self._command = command
        self._tooltip = tooltip
        self._armed = False
        self._normal_bg = theme.BLUE if accent else theme.BG_TITLE

        self._label = tk.Label(
            self,
            text=text,
            bg=self._normal_bg,
            fg=theme.FG_PRIMARY,
            font=font or theme.MENU_FONT,
            cursor="hand2",
            padx=4,
        )
        self._label.pack(fill=tk.BOTH, expand=True)

        for w in (self, self._label):
            w.bind("<Enter>", self._on_enter)
            w.bind("<Leave>", self._on_leave)
            w.bind("<Button-1>", self._on_press)
            w.bind("<ButtonRelease-1>", self._on_release)

        self._tooltip_id = None

    def _on_enter(self, e=None):
        if self._armed:
            return
        self._label.config(bg=theme.BG_ACTIVE)

    def _on_leave(self, e=None):
        self._armed = False
        self._label.config(bg=self._normal_bg)

    def _on_press(self, e=None):
        self._armed = True
        self._label.config(bg=theme.BLUE_DARK)

    def _on_release(self, e=None):
        was_armed = self._armed
        self._armed = False
        self._label.config(bg=theme.BG_ACTIVE)
        if was_armed and self._command:
            self._command()


class _PanelSection(tk.Frame):
    """Section header + content frame (collapsible)."""

    def __init__(self, parent, title: str, expanded: bool = True):
        super().__init__(parent, bg=theme.BG_PANEL, highlightthickness=0, bd=0)
        self._expanded = expanded

        self._header = tk.Frame(self, bg=theme.BG_PANEL, height=22)
        self._header.pack(fill=tk.X)
        self._header.pack_propagate(False)

        self._arrow = tk.Label(
            self._header,
            text="\u25be" if expanded else "\u25b8",
            bg=theme.BG_PANEL,
            fg=theme.FG_SECONDARY,
            font=("Arial", 9),
            width=2,
            anchor="center",
        )
        self._arrow.pack(side=tk.LEFT)

        self._title = tk.Label(
            self._header,
            text=title.upper(),
            bg=theme.BG_PANEL,
            fg=theme.FG_SECONDARY,
            font=("Arial", 9, "bold"),
            anchor="w",
        )
        self._title.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))

        self._body = tk.Frame(self, bg=theme.BG_PANEL)
        if expanded:
            self._body.pack(fill=tk.X)

        for w in (self._header, self._arrow, self._title):
            w.bind("<Button-1>", self._toggle)
            w.bind("<Enter>", self._on_enter)
            w.bind("<Leave>", self._on_leave)

    def _on_enter(self, e=None):
        for w in (self._header, self._arrow, self._title):
            w.config(bg=theme.BG_RAISED)

    def _on_leave(self, e=None):
        for w in (self._header, self._arrow, self._title):
            w.config(bg=theme.BG_PANEL)

    def _toggle(self, e=None):
        self._expanded = not self._expanded
        if self._expanded:
            self._arrow.config(text="\u25be")
            self._body.pack(fill=tk.X)
        else:
            self._arrow.config(text="\u25b8")
            self._body.pack_forget()

    def body(self) -> tk.Frame:
        return self._body

    def _apply_theme(self):
        try:
            self.config(bg=theme.BG_PANEL)
            self._header.config(bg=theme.BG_PANEL)
            self._arrow.config(bg=theme.BG_PANEL, fg=theme.FG_SECONDARY)
            self._title.config(bg=theme.BG_PANEL, fg=theme.FG_SECONDARY)
            self._body.config(bg=theme.BG_PANEL)
        except tk.TclError:
            pass


class _SidebarTabBar(tk.Frame):
    """Two-pane tab switcher used on the sidebars (Palette/Object, Props/Actions)."""

    def __init__(self, parent, tabs, command=None):
        super().__init__(parent, bg=theme.BG_TITLE, height=28)
        self.pack_propagate(False)
        self._command = command
        self._buttons = []
        self._active = 0

        for idx, label in enumerate(tabs):
            btn = tk.Label(
                self,
                text=label,
                bg=theme.BG_TITLE,
                fg=theme.FG_SECONDARY,
                font=theme.LABEL_FONT_SMALL,
                padx=14,
                pady=4,
                cursor="hand2",
            )
            btn.pack(side=tk.LEFT, fill=tk.X, expand=True)
            btn.bind("<Button-1>", lambda e, i=idx: self._select(i))
            btn.bind("<Enter>", lambda e, b=btn: b.config(bg=theme.BG_PANEL))
            btn.bind(
                "<Leave>",
                lambda e, b=btn, i=idx: b.config(
                    bg=theme.BG_PANEL if i == self._active else theme.BG_TITLE
                ),
            )
            self._buttons.append(btn)
        self._select(0, fire=False)

    def _select(self, idx: int, fire: bool = True):
        self._active = idx
        for i, btn in enumerate(self._buttons):
            if i == idx:
                btn.config(bg=theme.BG_PANEL, fg=theme.FG_PRIMARY)
            else:
                btn.config(bg=theme.BG_TITLE, fg=theme.FG_SECONDARY)
        if fire and self._command is not None:
            self._command(idx)


class DesignerApp(Window):
    def __init__(self, project_file=None):
        super().__init__(title="Uui Designer")
        self.geometry("1320x800+60+40")

        self._project_path = Path(project_file) if project_file else None
        self._widgets = []
        self._widget_instances = {}
        self._selected_id = None
        self._selection_frames = []
        self._resize_handle = None
        self._drag_offset = (0, 0)
        self._resize_start = None
        self._rename_overlay = None

        self._theme_name = "Dark"
        self._window_title = "Untitled"
        self._geometry = "800x600+100+100"
        self._surface_width = 800
        self._surface_height = 600

        self._prop_vars = {}
        self._prop_widgets = {}
        self._prop_sections = {}

        self._mode = "design"  # 'design' or 'preview'

        self._create_menu()
        self._create_toolbar()
        self._create_body()
        self._create_status_bar()

        self._left_tabs._select(0)
        self._right_tabs._select(0)

        if self._project_path and self._project_path.exists():
            self._load_xml(self._project_path)
        else:
            self._new_project()

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _create_menu(self):
        self._menubar = UMenuBar(self)
        file_menu = self._menubar.add_cascade("File")
        file_menu.add_command("New", self._new_project, "Ctrl+N")
        file_menu.add_command("Open...", self._open_project, "Ctrl+O")
        file_menu.add_command("Save", self._save_project, "Ctrl+S")
        file_menu.add_command("Save As...", self._save_as_project)
        file_menu.add_separator()
        file_menu.add_command("Export Python...", self._export_python)
        file_menu.add_separator()
        file_menu.add_command("Exit", self.destroy)

        edit_menu = self._menubar.add_cascade("Edit")
        edit_menu.add_command("Undo", lambda: self._toast("Undo"), "Ctrl+Z")
        edit_menu.add_command("Redo", lambda: self._toast("Redo"), "Ctrl+Y")
        edit_menu.add_separator()
        edit_menu.add_command("Delete Widget", self._delete_selected, "Delete")
        edit_menu.add_command("Select All", self._select_all, "Ctrl+A")

        view_menu = self._menubar.add_cascade("View")
        view_menu.add_command("Toggle Sidebar", lambda: self._toast("Sidebar"), "Ctrl+1")
        view_menu.add_command("Toggle Properties", lambda: self._toast("Properties"), "Ctrl+2")
        view_menu.add_separator()
        view_menu.add_command("Reset Layout", self._reset_layout)

        form_menu = self._menubar.add_cascade("Form")
        form_menu.add_command("Preview", lambda: self._set_mode("preview"), "Ctrl+R")
        form_menu.add_command("Edit Mode", lambda: self._set_mode("design"), "Ctrl+E")
        form_menu.add_separator()
        form_menu.add_command(
            "Rename...",
            lambda: self._rename_widget(self._selected_id) if self._selected_id else None,
            "F2",
        )

        help_menu = self._menubar.add_cascade("Help")
        help_menu.add_command("About Designer", self._show_about)

        self.bind("<Control-n>", lambda e: self._new_project())
        self.bind("<Control-o>", lambda e: self._open_project())
        self.bind("<Control-s>", lambda e: self._save_project())
        self.bind("<Control-a>", lambda e: self._select_all())
        self.bind("<Delete>", lambda e: self._delete_selected())
        self.bind(
            "<F2>", lambda e: self._rename_widget(self._selected_id) if self._selected_id else None
        )

    def _create_toolbar(self):
        self._toolbar = tk.Frame(self, bg=theme.BG_TITLE, height=32)
        self._toolbar.pack(fill=tk.X)
        self._toolbar.pack_propagate(False)

        actions = [
            ("⎘", self._new_project, "New (Ctrl+N)"),
            ("⤓", self._open_project, "Open... (Ctrl+O)"),
            ("⤒", self._save_project, "Save (Ctrl+S)"),
            None,
            ("↶", lambda: self._toast("Undo"), "Undo (Ctrl+Z)"),
            ("↷", lambda: self._toast("Redo"), "Redo (Ctrl+Y)"),
            None,
            ("✕", self._delete_selected, "Delete (Del)"),
            ("▦", lambda: self._toast("Grid"), "Toggle Grid"),
            ("⛶", self._reset_layout, "Reset Layout"),
            None,
            ("▶", lambda: self._set_mode("preview"), "Preview (Ctrl+R)"),
            ("◼", lambda: self._set_mode("design"), "Edit Mode (Ctrl+E)"),
        ]

        for item in actions:
            if item is None:
                sep = tk.Frame(self._toolbar, bg=theme.BORDER, width=1)
                sep.pack(side=tk.LEFT, fill=tk.Y, pady=6, padx=4)
                continue
            glyph, cmd, tip = item
            btn = _FlatButton(
                self._toolbar, text=glyph, command=cmd, tooltip=tip, width=32, font=("Arial", 12)
            )
            btn.pack(side=tk.LEFT)

        spacer = tk.Frame(self._toolbar, bg=theme.BG_TITLE)
        spacer.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self._mode_label = tk.Label(
            self._toolbar,
            text="DESIGN",
            bg=theme.BG_TITLE,
            fg=theme.BLUE,
            font=("Arial", 9, "bold"),
            padx=10,
        )
        self._mode_label.pack(side=tk.RIGHT, padx=8)

    def _set_mode(self, mode: str):
        self._mode = mode
        if mode == "preview":
            self._mode_label.config(text="PREVIEW", fg=theme.GREEN)
            self._set_preview(True)
        else:
            self._mode_label.config(text="DESIGN", fg=theme.BLUE)
            self._set_preview(False)

    def _set_preview(self, on: bool):
        """Hide design-time chrome in preview mode."""
        if on:
            self._toolbar.pack_forget()
            self._left_paned.pack_forget()
            self._right_paned.pack_forget()
            self._status_bar.pack_forget()
            self._canvas_outer.config(bg=theme.BG_BASE)
            self._canvas.config(bg=theme.BG_BASE)
        else:
            self._toolbar.pack(fill=tk.X, before=self._body)
            self._left_paned.pack(fill=tk.BOTH, expand=True, side=tk.LEFT, in_=self._body)
            self._right_paned.pack(fill=tk.BOTH, side=tk.RIGHT, in_=self._body)
            self._status_bar.pack(fill=tk.X, side=tk.BOTTOM, after=self._body)
            self._canvas_outer.config(bg=theme.BG_INPUT)
            self._redraw_checker()

    def _create_body(self):
        self._body = UFrame(self, variant="base")
        self._body.pack(fill=tk.BOTH, expand=True)

        sash_kw = {
            "sashrelief": str(tk.FLAT),
            "sashwidth": 4,
            "sashpad": 0,
            "bg": str(theme.BORDER),
            "bd": 0,
        }
        try:
            self._left_paned = tk.PanedWindow(
                self._body,
                orient=tk.HORIZONTAL,
                **sash_kw,
            )
            self._right_paned = tk.PanedWindow(
                self._body,
                orient=tk.HORIZONTAL,
                **sash_kw,
            )
        except tk.TclError:
            self._left_paned = tk.PanedWindow(self._body, orient=tk.HORIZONTAL)
            self._right_paned = tk.PanedWindow(self._body, orient=tk.HORIZONTAL)

        self._left_paned.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        self._right_paned.pack(fill=tk.BOTH, side=tk.RIGHT)

        self._build_left_sidebar()
        self._build_center()
        self._build_right_sidebar()

        self._left_paned.add(self._left_frame, minsize=200, width=260)
        self._left_paned.add(self._center_outer, minsize=320, stretch="always")
        self._right_paned.add(self._center_outer, minsize=320, stretch="always")
        self._right_paned.add(self._right_frame, minsize=220, width=300)

    def _build_left_sidebar(self):
        self._left_frame = UFrame(self._left_paned, variant="panel")

        self._left_tabs = _SidebarTabBar(
            self._left_frame,
            ["Widget Box", "Object Explorer"],
            command=self._on_left_tab_change,
        )
        self._left_tabs.pack(fill=tk.X)

        self._left_body = UFrame(self._left_frame, variant="panel")
        self._left_body.pack(fill=tk.BOTH, expand=True)

        self._build_widget_palette()
        self._build_object_explorer()
        self._show_palette_page()

    def _build_widget_palette(self):
        self._palette_page = UFrame(self._left_body, variant="panel")

        self._palette_scroll_outer = UFrame(self._palette_page, variant="panel")
        self._palette_scroll_outer.pack(fill=tk.BOTH, expand=True, padx=4, pady=(4, 4))

        self._palette_canvas = tk.Canvas(
            self._palette_scroll_outer,
            bg=theme.BG_PANEL,
            highlightthickness=0,
            bd=0,
        )
        self._palette_vsb = UScrollBar(
            self._palette_scroll_outer,
            orient=tk.VERTICAL,
            command=self._palette_canvas.yview,
            troughcolor=theme.BG_PANEL,
            width=8,
        )
        self._palette_vsb._theme_key_trough = "BG_PANEL"
        self._palette_canvas.config(yscrollcommand=self._palette_vsb.set)
        self._palette_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self._palette_vsb.pack(side=tk.RIGHT, fill=tk.Y)

        self._palette_inner = UFrame(self._palette_canvas, variant="panel")
        self._palette_window_id = self._palette_canvas.create_window(
            (0, 0),
            window=self._palette_inner,
            anchor="nw",
        )
        self._palette_inner.bind(
            "<Configure>",
            lambda e: self._palette_canvas.config(scrollregion=self._palette_canvas.bbox("all")),
        )
        self._palette_canvas.bind(
            "<Configure>",
            lambda e: self._palette_canvas.itemconfig(self._palette_window_id, width=e.width),
        )
        self._palette_canvas.bind_all(
            "<MouseWheel>",
            lambda e: self._palette_canvas.yview_scroll(int(-e.delta / 120), "units"),
        )

        filter_row = UFrame(self._palette_page, variant="panel")
        filter_row.pack(fill=tk.X, padx=8, pady=(8, 4))
        filter_row.pack_propagate(False)

        search_icon = tk.Label(
            filter_row, text="⌕", bg=theme.BG_PANEL, fg=theme.FG_SECONDARY, font=("Arial", 11)
        )
        search_icon.pack(side=tk.LEFT, padx=(0, 4))

        self._palette_filter = tk.StringVar()
        self._palette_filter.trace_add("write", lambda *a: self._refresh_palette())
        filter_entry = UEntry(
            filter_row, textvariable=self._palette_filter, placeholder="Filter widgets..."
        )
        filter_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

    def _refresh_palette(self):
        for child in self._palette_inner.winfo_children():
            child.destroy()
        query = self._palette_filter.get().strip().lower()

        for group_name, items in WIDGET_GROUPS:
            if not items:
                continue
            matched = []
            for wtype, friendly, _ in items:
                if not query or query in wtype.lower() or query in friendly.lower():
                    matched.append((wtype, friendly))
            if not matched:
                continue
            self._build_palette_group(group_name, matched)
        self._palette_inner.update_idletasks()
        self._palette_canvas.config(scrollregion=self._palette_canvas.bbox("all"))

    def _build_palette_group(self, title: str, items):
        header = tk.Frame(self._palette_inner, bg=theme.BG_PANEL, height=22)
        header.pack(fill=tk.X, padx=8, pady=(8, 2))
        header.pack_propagate(False)
        tk.Label(
            header,
            text=title.upper(),
            bg=theme.BG_PANEL,
            fg=theme.FG_SECONDARY,
            font=("Arial", 8, "bold"),
        ).pack(side=tk.LEFT)

        grid = UFrame(self._palette_inner, variant="panel")
        grid.pack(fill=tk.X, padx=8, pady=(0, 4))

        for idx, (wtype, friendly) in enumerate(items):
            row = idx // 2
            col = idx % 2
            self._make_palette_cell(grid, wtype, friendly).grid(
                row=row,
                column=col,
                sticky="ew",
                padx=2,
                pady=2,
            )
        grid.grid_columnconfigure(0, weight=1)
        grid.grid_columnconfigure(1, weight=1)

    def _make_palette_cell(self, parent, wtype: str, friendly: str) -> tk.Frame:
        cell = tk.Frame(
            parent,
            bg=theme.BG_RAISED,
            highlightthickness=1,
            highlightbackground=theme.BORDER,
            bd=0,
            cursor="hand2",
        )
        cell._wtype = wtype  # type: ignore[attr-defined]

        icon_box = tk.Label(
            cell,
            text=WIDGET_ICON.get(wtype, "?"),
            bg=theme.BG_PANEL,
            fg=theme.FG_PRIMARY,
            font=("Arial", 11, "bold"),
            width=2,
            height=1,
        )
        icon_box.grid(row=0, column=0, padx=(6, 4), pady=4, sticky="w")

        name_lbl = tk.Label(
            cell,
            text=friendly,
            bg=theme.BG_RAISED,
            fg=theme.FG_PRIMARY,
            font=theme.LABEL_FONT_SMALL,
            anchor="w",
        )
        name_lbl.grid(row=0, column=1, sticky="ew", padx=(0, 6), pady=4)
        cell.grid_columnconfigure(1, weight=1)

        for w in (cell, icon_box, name_lbl):
            w.bind("<Button-1>", lambda e, t=wtype: self._add_widget(t))
            w.bind(
                "<Enter>",
                lambda e, c=cell, n=name_lbl, i=icon_box: (
                    c.config(bg=theme.BG_HOVER),
                    n.config(bg=theme.BG_HOVER),
                    i.config(bg=theme.BG_HOVER),
                ),
            )
            w.bind(
                "<Leave>",
                lambda e, c=cell, n=name_lbl, i=icon_box: (
                    c.config(bg=theme.BG_RAISED),
                    n.config(bg=theme.BG_RAISED),
                    i.config(bg=theme.BG_PANEL),
                ),
            )

        def _on_drag(e, t=wtype):
            self._add_widget(t)

        for w in (cell, icon_box, name_lbl):
            w.bind("<Double-Button-1>", _on_drag)
        return cell

    def _build_object_explorer(self):
        self._explorer_page = UFrame(self._left_body, variant="panel")

        header = UFrame(self._explorer_page, variant="panel")
        header.pack(fill=tk.X, padx=8, pady=(8, 4))
        tk.Label(
            header,
            text="FORM OBJECTS",
            bg=theme.BG_PANEL,
            fg=theme.FG_SECONDARY,
            font=("Arial", 8, "bold"),
        ).pack(side=tk.LEFT)

        self._explorer_canvas = tk.Canvas(
            self._explorer_page,
            bg=theme.BG_PANEL,
            highlightthickness=0,
            bd=0,
        )
        self._explorer_vsb = UScrollBar(
            self._explorer_page,
            orient=tk.VERTICAL,
            command=self._explorer_canvas.yview,
            troughcolor=theme.BG_PANEL,
            width=8,
        )
        self._explorer_vsb._theme_key_trough = "BG_PANEL"
        self._explorer_canvas.config(yscrollcommand=self._explorer_vsb.set)
        self._explorer_canvas.pack(
            side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(8, 0), pady=(0, 8)
        )
        self._explorer_vsb.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 8), pady=(0, 8))

        self._explorer_inner = UFrame(self._explorer_canvas, variant="panel")
        self._explorer_window_id = self._explorer_canvas.create_window(
            (0, 0),
            window=self._explorer_inner,
            anchor="nw",
        )
        self._explorer_inner.bind(
            "<Configure>",
            lambda e: self._explorer_canvas.config(scrollregion=self._explorer_canvas.bbox("all")),
        )
        self._explorer_canvas.bind(
            "<Configure>",
            lambda e: self._explorer_canvas.itemconfig(self._explorer_window_id, width=e.width),
        )

    def _refresh_explorer(self):
        for child in self._explorer_inner.winfo_children():
            child.destroy()

        root_row = self._make_explorer_row(
            self._explorer_inner,
            "Form",
            "main",
            "\u25a2",
            is_header=True,
        )
        root_row.pack(fill=tk.X, padx=2, pady=(2, 0))

        for item in self._widgets:
            row = self._make_explorer_row(
                self._explorer_inner,
                item["type"],
                item["name"],
                WIDGET_ICON.get(item["type"], "?"),
                item_id=item["id"],
                indent=1,
            )
            row.pack(fill=tk.X, padx=2, pady=1)
        self._explorer_inner.update_idletasks()
        self._explorer_canvas.config(scrollregion=self._explorer_canvas.bbox("all"))

    def _make_explorer_row(
        self,
        parent,
        kind: str,
        name: str,
        icon: str,
        item_id=None,
        indent: int = 0,
        is_header: bool = False,
    ):
        bg = theme.BG_PANEL
        selected = item_id is not None and item_id == self._selected_id

        row = tk.Frame(parent, bg=theme.BG_HOVER if selected else bg, height=22)
        row.pack_propagate(False)

        for _ in range(indent):
            tk.Frame(row, bg=bg, width=12).pack(side=tk.LEFT)

        icon_lbl = tk.Label(
            row,
            text=icon,
            bg=row["bg"],
            fg=theme.FG_PRIMARY,
            font=("Arial", 10),
            width=2,
        )
        icon_lbl.pack(side=tk.LEFT, padx=(4, 2))

        name_lbl = tk.Label(
            row,
            text=name,
            bg=row["bg"],
            fg=theme.FG_PRIMARY if is_header or selected else theme.FG_SECONDARY,
            font=theme.LABEL_FONT_SMALL,
            anchor="w",
        )
        name_lbl.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))

        kind_lbl = tk.Label(
            row,
            text=kind,
            bg=row["bg"],
            fg=theme.FG_TERTIARY,
            font=("Arial", 8),
            anchor="e",
        )
        kind_lbl.pack(side=tk.RIGHT, padx=(0, 6))

        def _enter(e=None):
            for w in (row, icon_lbl, name_lbl, kind_lbl):
                w.config(bg=theme.BG_RAISED)

        def _leave(e=None):
            new_bg = theme.BG_HOVER if selected else bg
            for w in (row, icon_lbl, name_lbl, kind_lbl):
                w.config(bg=new_bg)

        def _click(e=None):
            if item_id is not None:
                self._select(item_id)

        for w in (row, icon_lbl, name_lbl, kind_lbl):
            w.bind("<Enter>", _enter)
            w.bind("<Leave>", _leave)
            w.bind("<Button-1>", _click)

        row._widgets = (row, icon_lbl, name_lbl, kind_lbl)  # type: ignore[attr-defined]
        row._selected = selected  # type: ignore[attr-defined]
        return row

    def _on_left_tab_change(self, idx: int):
        if idx == 0:
            self._show_palette_page()
        else:
            self._show_explorer_page()

    def _show_palette_page(self):
        self._explorer_page.pack_forget()
        self._palette_page.pack(fill=tk.BOTH, expand=True)
        self._refresh_palette()

    def _show_explorer_page(self):
        self._palette_page.pack_forget()
        self._explorer_page.pack(fill=tk.BOTH, expand=True)
        self._refresh_explorer()

    def _build_center(self):
        self._center_outer = UFrame(self._body, variant="base")

        bar = tk.Frame(self._center_outer, bg=theme.BG_TITLE, height=30)
        bar.pack(fill=tk.X)
        bar.pack_propagate(False)

        ULabel(bar, text="Theme:", variant="primary").pack(side=tk.LEFT, padx=(8, 4), pady=4)
        self._theme_var = tk.StringVar(value=self._theme_name)
        self._theme_combo = UComboBox(
            bar,
            values=[t.name for t in theme.available()],
            textvariable=self._theme_var,
            command=self._on_theme_change,
            width=140,
        )
        self._theme_combo.pack(side=tk.LEFT, padx=(0, 8), pady=4)

        sep = tk.Frame(bar, bg=theme.BORDER, width=1)
        sep.pack(side=tk.LEFT, fill=tk.Y, pady=6, padx=4)

        ULabel(bar, text="Title:", variant="primary").pack(side=tk.LEFT, padx=(4, 4), pady=4)
        self._title_var = tk.StringVar(value=self._window_title)
        self._title_entry = UEntry(bar, textvariable=self._title_var, width=18)
        self._title_entry.pack(side=tk.LEFT, padx=(0, 8), pady=4)
        self._title_var.trace_add("write", lambda *a: self._set_title(self._title_var.get()))

        sep = tk.Frame(bar, bg=theme.BORDER, width=1)
        sep.pack(side=tk.LEFT, fill=tk.Y, pady=6, padx=4)

        ULabel(bar, text="Size:", variant="primary").pack(side=tk.LEFT, padx=(4, 4), pady=4)
        self._geom_var = tk.StringVar(value=self._geometry)
        self._geom_entry = UEntry(bar, textvariable=self._geom_var, width=14)
        self._geom_entry.pack(side=tk.LEFT, padx=(0, 8), pady=4)
        self._geom_var.trace_add("write", lambda *a: self._set_geometry(self._geom_var.get()))

        bar_right = tk.Frame(bar, bg=theme.BG_TITLE)
        bar_right.pack(side=tk.RIGHT, padx=8)
        self._cursor_label = tk.Label(
            bar_right,
            text="X: 0   Y: 0",
            bg=theme.BG_TITLE,
            fg=theme.FG_SECONDARY,
            font=("Consolas", 10),
        )
        self._cursor_label.pack(side=tk.RIGHT, pady=4)

        self._canvas_outer = UFrame(self._center_outer, variant="input")
        self._canvas_outer.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)

        self._hscroll = UScrollBar(
            self._canvas_outer,
            orient=tk.HORIZONTAL,
        )
        self._vscroll = UScrollBar(
            self._canvas_outer,
            orient=tk.VERTICAL,
        )
        self._canvas = tk.Canvas(
            self._canvas_outer,
            bg=theme.BG_INPUT,
            highlightthickness=0,
            bd=0,
            xscrollcommand=self._hscroll.set,
            yscrollcommand=self._vscroll.set,
        )
        self._hscroll.config(command=self._canvas.xview)
        self._vscroll.config(command=self._canvas.yview)

        self._canvas.grid(row=0, column=0, sticky="nsew")
        self._vscroll.grid(row=0, column=1, sticky="ns")
        self._hscroll.grid(row=1, column=0, sticky="ew")
        self._canvas_outer.grid_rowconfigure(0, weight=1)
        self._canvas_outer.grid_columnconfigure(0, weight=1)

        self._surface = UFrame(self._canvas, variant="base")
        self._surface_id = self._canvas.create_window((0, 0), window=self._surface, anchor="nw")
        self._configure_surface()

        self._canvas.bind("<Motion>", self._on_canvas_motion)
        self._canvas.bind("<Leave>", lambda e: self._cursor_label.config(text="X: -   Y: -"))

        self._center_outer.bind("<Configure>", lambda e: self._redraw_checker())
        self._redraw_checker()

    def _redraw_checker(self):
        """Draw a Qt-Creator-like checker pattern around the form surface."""
        if not self._canvas.winfo_exists():
            return
        self._canvas.delete("checker")
        cw = self._canvas.winfo_width()
        ch = self._canvas.winfo_height()
        if cw <= 1 or ch <= 1:
            self.update_idletasks()
            cw = self._canvas.winfo_width()
            ch = self._canvas.winfo_height()
        w = min(max(cw, self._surface_width + 80), 4000)
        h = min(max(ch, self._surface_height + 80), 4000)
        cell = 12
        c1 = theme.BG_INPUT
        c2 = theme.BG_BASE
        for y in range(0, h, cell):
            for x in range(0, w, cell):
                if ((x // cell) + (y // cell)) % 2 == 0:
                    color = c1
                else:
                    color = c2
                self._canvas.create_rectangle(
                    x,
                    y,
                    x + cell,
                    y + cell,
                    fill=color,
                    outline="",
                    tags="checker",
                )
        self._canvas.tag_lower("checker", self._surface_id)

    def _on_canvas_motion(self, event):
        try:
            x = self._canvas.canvasx(event.x)
            y = self._canvas.canvasy(event.y)
            self._cursor_label.config(text=f"X: {int(x)}   Y: {int(y)}")
        except tk.TclError:
            pass

    def _configure_surface(self):
        self._surface.config(width=self._surface_width, height=self._surface_height)
        self._canvas.config(
            scrollregion=(0, 0, self._surface_width + 40, self._surface_height + 40)
        )
        self.after(50, self._redraw_checker)

    def _build_right_sidebar(self):
        self._right_frame = UFrame(self._right_paned, variant="panel")

        self._right_tabs = _SidebarTabBar(
            self._right_frame,
            ["Properties", "Actions"],
            command=self._on_right_tab_change,
        )
        self._right_tabs.pack(fill=tk.X)

        self._right_body = UFrame(self._right_frame, variant="panel")
        self._right_body.pack(fill=tk.BOTH, expand=True)

        self._build_properties_page()
        self._build_actions_page()

        self._props_page.pack(fill=tk.BOTH, expand=True)

    def _on_right_tab_change(self, idx: int):
        if idx == 0:
            self._actions_page.pack_forget()
            self._props_page.pack(fill=tk.BOTH, expand=True)
        else:
            self._props_page.pack_forget()
            self._actions_page.pack(fill=tk.BOTH, expand=True)

    def _build_properties_page(self):
        self._props_page = UFrame(self._right_body, variant="panel")

        self._props_canvas = tk.Canvas(
            self._props_page,
            bg=theme.BG_PANEL,
            highlightthickness=0,
            bd=0,
        )
        self._props_vsb = UScrollBar(
            self._props_page,
            orient=tk.VERTICAL,
            command=self._props_canvas.yview,
            troughcolor=theme.BG_PANEL,
            width=8,
        )
        self._props_vsb._theme_key_trough = "BG_PANEL"
        self._props_canvas.config(yscrollcommand=self._props_vsb.set)
        self._props_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(4, 0), pady=4)
        self._props_vsb.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 4), pady=4)

        self._props_inner = UFrame(self._props_canvas, variant="panel")
        self._props_window_id = self._props_canvas.create_window(
            (0, 0),
            window=self._props_inner,
            anchor="nw",
        )
        self._props_inner.bind(
            "<Configure>",
            lambda e: self._props_canvas.config(scrollregion=self._props_canvas.bbox("all")),
        )
        self._props_canvas.bind(
            "<Configure>",
            lambda e: self._props_canvas.itemconfig(self._props_window_id, width=e.width),
        )

        self._no_selection_lbl = tk.Label(
            self._props_inner,
            text="\nNo widget selected.\n\nClick a widget on the canvas,\nor pick one from the\nObject Explorer.",
            bg=theme.BG_PANEL,
            fg=theme.FG_SECONDARY,
            font=theme.LABEL_FONT_SMALL,
            justify=tk.CENTER,
        )
        self._no_selection_lbl.pack(pady=24)

    def _build_actions_page(self):
        self._actions_page = UFrame(self._right_body, variant="panel")

        ULabel(
            self._actions_page,
            text="FORM ACTIONS",
            bg=theme.BG_PANEL,
            fg=theme.FG_SECONDARY,
            font=("Arial", 8, "bold"),
        ).pack(anchor=tk.W, padx=12, pady=(12, 4))

        actions = [
            ("New Form", self._new_project),
            ("Open .xml...", self._open_project),
            ("Save .xml", self._save_project),
            ("Save As...", self._save_as_project),
            ("Export Python", self._export_python),
        ]
        for label, cmd in actions:
            btn = UButton(self._actions_page, text=label, variant="default", command=cmd)
            btn.pack(fill=tk.X, padx=12, pady=3)

        sep = UFrame(self._actions_page, bg_key="BORDER", height=1)
        sep.pack(fill=tk.X, padx=12, pady=10)

        ULabel(
            self._actions_page,
            text="SELECTION",
            bg=theme.BG_PANEL,
            fg=theme.FG_SECONDARY,
            font=("Arial", 8, "bold"),
        ).pack(anchor=tk.W, padx=12, pady=(0, 4))

        sel_actions = [
            (
                "Rename... (F2)",
                lambda: self._rename_widget(self._selected_id) if self._selected_id else None,
            ),
            ("Delete (Del)", self._delete_selected),
            ("Select All", self._select_all),
        ]
        for label, cmd in sel_actions:
            UButton(self._actions_page, text=label, variant="ghost", command=cmd).pack(
                fill=tk.X, padx=12, pady=3
            )

    def _create_status_bar(self):
        self._status_bar = tk.Frame(self, bg=theme.BG_TITLE, height=22)
        self._status_bar.pack(fill=tk.X, side=tk.BOTTOM)
        self._status_bar.pack_propagate(False)

        sep = tk.Frame(self._status_bar, bg=theme.BORDER, height=1)
        sep.pack(side=tk.TOP, fill=tk.X)

        self._status_left = tk.Label(
            self._status_bar,
            text="Ready",
            bg=theme.BG_TITLE,
            fg=theme.FG_SECONDARY,
            font=("Consolas", 9),
            padx=8,
        )
        self._status_left.pack(side=tk.LEFT)

        self._status_widget = tk.Label(
            self._status_bar,
            text="No selection",
            bg=theme.BG_TITLE,
            fg=theme.FG_PRIMARY,
            font=("Consolas", 9),
            padx=8,
        )
        self._status_widget.pack(side=tk.LEFT)

        self._status_geom = tk.Label(
            self._status_bar,
            text="",
            bg=theme.BG_TITLE,
            fg=theme.FG_SECONDARY,
            font=("Consolas", 9),
            padx=8,
        )
        self._status_geom.pack(side=tk.RIGHT)

        self._status_path = tk.Label(
            self._status_bar,
            text="",
            bg=theme.BG_TITLE,
            fg=theme.FG_SECONDARY,
            font=("Consolas", 9),
            padx=8,
        )
        self._status_path.pack(side=tk.RIGHT)

        self._update_status_bar()

    def _update_status_bar(self, message: str = ""):
        if message:
            self._status_left.config(text=message)
        else:
            self._status_left.config(text="Ready")
        if self._project_path:
            self._status_path.config(text=f"  {self._project_path}  ")
        else:
            self._status_path.config(text="  Untitled  ")
        self._status_geom.config(text=f"  {self._surface_width} × {self._surface_height}  ")
        item = self._item_by_id(self._selected_id)
        if item:
            self._status_widget.config(
                text=f"  {item['type']}  ·  {item['name']}  ·  "
                f"({item['x']}, {item['y']})  ·  "
                f"{item['width']} × {item['height']}"
            )
        else:
            self._status_widget.config(text="  No selection  ")

    def _toast(self, message: str):
        self._status_left.config(text=message)
        self.after(2000, lambda: self._status_left.config(text="Ready"))

    def _add_property_section(self, section_title: str, names):
        section = _PanelSection(self._props_inner, section_title)
        section.pack(fill=tk.X, padx=4, pady=(8, 0))
        body = section.body()

        for idx, name in enumerate(names):
            label_text = PROP_LABELS.get(name) or name
            label = tk.Label(
                body,
                text=label_text,
                bg=theme.BG_PANEL,
                fg=theme.FG_SECONDARY,
                font=theme.LABEL_FONT_SMALL,
                anchor="w",
            )
            label.grid(row=idx, column=0, sticky="w", padx=(4, 6), pady=2)

            var = tk.StringVar()
            self._prop_vars[name] = var

            if name == "variant":
                widget = UComboBox(body, textvariable=var, command=lambda v: self._apply_props())
            elif name == "orient":
                widget = UComboBox(
                    body,
                    textvariable=var,
                    values=["horizontal", "vertical"],
                    command=lambda v: self._apply_props(),
                )
            elif name == "show_value":
                widget = UComboBox(
                    body,
                    textvariable=var,
                    values=["False", "True"],
                    command=lambda v: self._apply_props(),
                )
            else:
                widget = UEntry(body, textvariable=var)
                widget._entry.bind("<Return>", lambda e: self._apply_props())
                widget._entry.bind("<FocusOut>", lambda e: self._apply_props())

            widget.grid(row=idx, column=1, sticky="ew", padx=(0, 4), pady=2)
            self._prop_widgets[name] = (label, widget)

        body.grid_columnconfigure(1, weight=1)
        self._prop_sections[section_title] = section

    def _populate_prop_values(self):
        item = self._item_by_id(self._selected_id)
        for child in list(self._props_inner.winfo_children()):
            if child is self._no_selection_lbl:
                continue
            child.destroy()
        self._prop_vars.clear()
        self._prop_widgets.clear()
        self._prop_sections.clear()

        if item is None:
            self._no_selection_lbl.pack(pady=24)
            self._update_status_bar()
            return
        self._no_selection_lbl.pack_forget()

        self._add_property_section("QObject", COMMON_OBJECT)
        self._add_property_section("Geometry", COMMON_GEOMETRY)

        wtype = item["type"]
        type_sections = TYPE_PROPS.get(wtype, [])
        if not type_sections and wtype == "UCheckButton":
            type_sections = [("Text", ["text"]), ("Code", ["command"])]
        for title, props in type_sections:
            if props:
                self._add_property_section(f"{wtype[1:]} · {title}", props)

        if "variant" in self._prop_widgets:
            self._prop_widgets["variant"][1].set_values(VARIANT_OPTIONS.get(wtype, []))

        for name, var in self._prop_vars.items():
            if name == "show_value":
                var.set("True" if self._to_bool(item.get(name, False)) else "False")
            elif name == "values":
                val = item.get(name, "")
                if isinstance(val, (list, tuple)):
                    var.set(", ".join(str(v) for v in val))
                else:
                    var.set(str(val))
            else:
                var.set(str(item.get(name, "")))
        self._update_status_bar()

    def _show_prop_rows(self, names):
        pass

    def _apply_props(self):
        item = self._item_by_id(self._selected_id)
        if item is None:
            return
        wtype = item["type"]
        editable = set(COMMON_GEOMETRY) | set(COMMON_OBJECT)
        for _, props in TYPE_PROPS.get(wtype, []):
            editable.update(props)

        for name in editable:
            if name not in self._prop_vars:
                continue
            var = self._prop_vars[name]
            value = var.get().strip()
            if name in NUMERIC_PROPS:
                if name in ("x", "y", "width", "height", "maximum"):
                    item[name] = self._to_int(value, 0)
                else:
                    item[name] = self._to_float(value, 0)
            elif name in BOOL_PROPS:
                item[name] = value == "True"
            else:
                item[name] = value

        self._render_widget(item)
        self._refresh_selection()
        self._update_status_bar()

    def _set_title(self, value):
        self._window_title = value or "Untitled"

    def _set_geometry(self, value):
        self._geometry = value or "800x600+100+100"
        self._parse_geometry()
        self._configure_surface()
        self._update_status_bar()

    def _parse_geometry(self):
        m = re.match(r"^(\d+)x(\d+)(?:([+-]\d+)([+-]\d+))?$", self._geometry)
        if m:
            self._surface_width = int(m.group(1))
            self._surface_height = int(m.group(2))
        else:
            self._surface_width = 800
            self._surface_height = 600

    def _on_theme_change(self, value):
        t = theme.by_name(value)
        if t is None:
            return
        self._theme_name = value
        theme.set_theme(t)
        theme.apply_theme_recursive(self)
        theme.apply_theme_recursive(self._surface)
        self._canvas.config(bg=theme.BG_INPUT)
        self._canvas_outer.config(bg=theme.BG_INPUT)
        self._redraw_checker()
        self._refresh_toolbar_theme()

    def _refresh_toolbar_theme(self):
        self._mode_label.config(
            bg=theme.BG_TITLE,
            fg=theme.GREEN if self._mode == "preview" else theme.BLUE,
        )

    def _new_project(self):
        self._clear_widgets()
        self._theme_name = "Dark"
        self._theme_var.set(self._theme_name)
        self._window_title = "Untitled"
        self._title_var.set(self._window_title)
        self._geometry = "800x600+100+100"
        self._geom_var.set(self._geometry)
        self._parse_geometry()
        self._configure_surface()
        self._project_path = None
        self.title("Uui Designer - Untitled")
        t = theme.by_name(self._theme_name)
        if t is not None:
            theme.set_theme(t)
            theme.apply_theme_recursive(self)
            theme.apply_theme_recursive(self._surface)
        self._refresh_list()
        self._update_status_bar("New form created")

    def _clear_widgets(self):
        for item in self._widgets:
            self._destroy_widget_instance(item["id"])
        self._widgets.clear()
        self._widget_instances.clear()
        self._selected_id = None
        self._clear_selection()
        self._refresh_list()
        self._populate_prop_values()

    def _unique_name(self, wtype):
        base = wtype[1:].lower()
        used = {w["name"] for w in self._widgets}
        idx = 1
        while f"{base}_{idx}" in used:
            idx += 1
        return f"{base}_{idx}"

    def _rename_widget(self, item_id):
        item = self._item_by_id(item_id)
        if item is None:
            return
        self._destroy_rename_overlay()

        var = tk.StringVar(value=item["name"])
        overlay = UEntry(self._surface, textvariable=var, width=max(8, len(item["name"]) + 4))
        overlay.place(
            x=item["x"],
            y=item["y"],
            width=max(160, item["width"]),
            height=max(28, item["height"]),
        )
        overlay_data = {"entry": overlay, "var": var, "item_id": item_id, "committed": False}
        self._rename_overlay = overlay_data

        def _on_commit(event=None):
            data = self._rename_overlay
            if data is None or data is not overlay_data or data["committed"]:
                return "break"
            new_name = var.get().strip()
            target = self._item_by_id(item_id)
            if target is None:
                data["committed"] = True
                self.after(10, self._destroy_rename_overlay)
                return "break"
            if not new_name:
                messagebox.showwarning("Rename Widget", "Name cannot be empty.", parent=self)
                overlay._entry.focus_set()
                overlay._entry.select_range(0, tk.END)
                return "break"
            if new_name != target["name"]:
                used = {w["name"] for w in self._widgets if w["id"] != item_id}
                if new_name in used:
                    messagebox.showwarning(
                        "Rename Widget",
                        f'Name "{new_name}" is already used by another widget.',
                        parent=self,
                    )
                    overlay._entry.focus_set()
                    overlay._entry.select_range(0, tk.END)
                    return "break"
                target["name"] = new_name
                self._populate_prop_values()
                self.after(10, self._refresh_explorer)
            data["committed"] = True
            self.after(10, self._destroy_rename_overlay)
            return "break"

        def _on_cancel(event=None):
            data = self._rename_overlay
            if data is None or data is not overlay_data or data["committed"]:
                return "break"
            data["committed"] = True
            self.after(10, self._destroy_rename_overlay)
            return "break"

        overlay._entry.bind("<Return>", _on_commit)
        overlay._entry.bind("<KP_Enter>", _on_commit)
        overlay._entry.bind("<Escape>", _on_cancel)
        overlay._entry.bind("<FocusOut>", _on_commit)

        def _focus():
            overlay._entry.focus_set()
            overlay._entry.select_range(0, tk.END)
            overlay._entry.icursor(tk.END)

        self.after_idle(_focus)

    def _destroy_rename_overlay(self):
        overlay_data = getattr(self, "_rename_overlay", None)
        if overlay_data is None:
            return
        self._rename_overlay = None
        entry = overlay_data["entry"]
        with contextlib.suppress(tk.TclError):
            entry.destroy()

    def _add_widget(self, wtype):
        width, height = DEFAULT_SIZE.get(wtype, (120, 24))
        x = 20 + (len(self._widgets) % 8) * 16
        y = 20 + (len(self._widgets) % 8) * 16
        item = {
            "id": f"w{len(self._widgets) + 1}",
            "type": wtype,
            "name": self._unique_name(wtype),
            "x": x,
            "y": y,
            "width": width,
            "height": height,
            "command": "",
        }
        for k, v in DEFAULT_PROPS.get(wtype, {}).items():
            item[k] = v
        self._widgets.append(item)
        self._render_widget(item)
        self._refresh_list()
        self._select(item["id"])

    def _render_widget(self, item):
        self._destroy_widget_instance(item["id"])
        cls = WIDGET_CLASSES[item["type"]]
        kwargs = self._build_kwargs(item)
        try:
            widget = cls(self._surface, **kwargs)
        except Exception as e:
            print(f"Failed to create {item['type']}: {e}")
            return
        widget.place(x=item["x"], y=item["y"], width=item["width"], height=item["height"])
        self._widget_instances[item["id"]] = widget
        self._bind_design_events(widget, item["id"])

    def _build_kwargs(self, item):
        kwargs = {}
        wtype = item["type"]
        if "text" in item:
            kwargs["text"] = item["text"]
        if "variant" in item and wtype in VARIANT_OPTIONS:
            kwargs["variant"] = item["variant"]
        if "placeholder" in item:
            kwargs["placeholder"] = item["placeholder"]
        if "show" in item:
            kwargs["show"] = item["show"]
        if "values" in item:
            val = str(item["values"]).strip()
            if val:
                kwargs["values"] = [v.strip() for v in val.split(",")]
        if "maximum" in item:
            kwargs["maximum"] = self._to_int(item["maximum"], 100)
        if "value" in item:
            kwargs["value"] = self._to_float(item["value"], 0)
        if "from_" in item:
            kwargs["from_"] = self._to_float(item["from_"], 0)
        if "to" in item:
            kwargs["to"] = self._to_float(item["to"], 100)
        if "orient" in item:
            kwargs["orient"] = item["orient"]
        if "show_value" in item:
            kwargs["show_value"] = self._to_bool(item["show_value"])
        if "color" in item and str(item.get("color", "")).strip():
            kwargs["color"] = item["color"]
        if wtype == "UButton":
            kwargs["width"] = self._to_int(item.get("width", 96), 96)
            kwargs["height"] = self._to_int(item.get("height", 28), 28)
        return kwargs

    def _bind_design_events(self, widget, item_id):
        def _press(event):
            self._select(item_id)
            self._drag_offset = (event.x, event.y)
            return "break"

        def _double_click(event):
            self._select(item_id)
            self._rename_widget(item_id)
            return "break"

        def _drag(event):
            item = self._item_by_id(item_id)
            if item is None:
                return "break"
            x = event.x_root - self._surface.winfo_rootx() - self._drag_offset[0]
            y = event.y_root - self._surface.winfo_rooty() - self._drag_offset[1]
            item["x"] = max(0, x)
            item["y"] = max(0, y)
            self._update_geometry(item)
            return "break"

        for w in self._collect_descendants(widget):
            w.bind("<Button-1>", _press)
            w.bind("<Double-Button-1>", _double_click)
            w.bind("<B1-Motion>", _drag)

    def _collect_descendants(self, widget):
        result = [widget]
        try:
            children = widget.winfo_children()
        except tk.TclError:
            children = []
        for child in children:
            result.extend(self._collect_descendants(child))
        return result

    def _item_by_id(self, item_id):
        for item in self._widgets:
            if item["id"] == item_id:
                return item
        return None

    def _update_geometry(self, item):
        widget = self._widget_instances.get(item["id"])
        if widget is None:
            return
        with contextlib.suppress(tk.TclError):
            widget.place_configure(
                x=item["x"], y=item["y"], width=item["width"], height=item["height"]
            )
        self._refresh_selection()
        self._update_status_bar()

    def _select(self, item_id):
        if self._selected_id == item_id:
            return
        self._selected_id = item_id
        self._refresh_selection()
        self._populate_prop_values()
        self._show_explorer_page_or_update()

    def _show_explorer_page_or_update(self):
        try:
            active = self._left_tabs._active
        except Exception:
            active = 0
        if active == 1:
            self._refresh_explorer()

    def _select_all(self):
        if not self._widgets:
            return
        self._select(self._widgets[-1]["id"])

    def _refresh_selection(self):
        self._clear_selection()
        if self._selected_id is None:
            return
        item = self._item_by_id(self._selected_id)
        if item is None:
            return
        widget = self._widget_instances.get(self._selected_id)
        if widget is None:
            return
        try:
            x = item["x"]
            y = item["y"]
            w = item["width"]
            h = item["height"]
        except tk.TclError:
            return
        color = theme.BLUE
        self._selection_frames = [
            tk.Frame(self._surface, bg=color, width=w, height=2),
            tk.Frame(self._surface, bg=color, width=w, height=2),
            tk.Frame(self._surface, bg=color, width=2, height=h + 4),
            tk.Frame(self._surface, bg=color, width=2, height=h + 4),
        ]
        self._selection_frames[0].place(x=x, y=y - 2)
        self._selection_frames[1].place(x=x, y=y + h)
        self._selection_frames[2].place(x=x - 2, y=y - 2)
        self._selection_frames[3].place(x=x + w, y=y - 2)

        for frame in self._selection_frames:
            frame.bind("<Button-1>", lambda e, iid=self._selected_id: self._select(iid) or "break")

        self._resize_handle = tk.Frame(self._surface, bg=color, width=8, height=8, cursor="sizing")
        self._resize_handle.place(x=x + w - 4, y=y + h - 4)
        self._resize_handle.bind("<Button-1>", self._on_resize_press)
        self._resize_handle.bind("<B1-Motion>", self._on_resize_drag)

    def _clear_selection(self):
        for frame in self._selection_frames:
            frame.destroy()
        self._selection_frames = []
        if self._resize_handle is not None:
            self._resize_handle.destroy()
            self._resize_handle = None

    def _on_resize_press(self, event):
        item = self._item_by_id(self._selected_id)
        if item is None:
            return "break"
        self._resize_start = (event.x_root, event.y_root, item["width"], item["height"])
        return "break"

    def _on_resize_drag(self, event):
        if self._resize_start is None:
            return "break"
        sx, sy, sw, sh = self._resize_start
        dx = event.x_root - sx
        dy = event.y_root - sy
        item = self._item_by_id(self._selected_id)
        if item is None:
            return "break"
        item["width"] = max(10, sw + dx)
        item["height"] = max(10, sh + dy)
        self._update_geometry(item)
        return "break"

    def _refresh_list(self):
        for child in self._explorer_inner.winfo_children():
            child.destroy()
        self._refresh_explorer()

    def _delete_selected(self):
        if self._selected_id is None:
            return
        item = self._item_by_id(self._selected_id)
        if item is None:
            return
        self._destroy_widget_instance(self._selected_id)
        self._widgets.remove(item)
        self._selected_id = None
        self._clear_selection()
        self._refresh_list()
        self._populate_prop_values()

    def _destroy_widget_instance(self, item_id):
        widget = self._widget_instances.pop(item_id, None)
        if widget is not None:
            with contextlib.suppress(tk.TclError):
                widget.destroy()

    def _to_int(self, value, default=0):
        try:
            return int(float(value))
        except (ValueError, TypeError):
            return default

    def _to_float(self, value, default=0.0):
        try:
            return float(value)
        except (ValueError, TypeError):
            return default

    def _to_bool(self, value):
        if isinstance(value, bool):
            return value
        return str(value).lower() in ("true", "1", "yes", "on")

    def _load_xml(self, path):
        try:
            tree = ET.parse(path)
        except Exception as e:
            messagebox.showerror("Open Project", f"Failed to load {path}:\n{e}")
            return
        root = tree.getroot()
        if root.tag != "designer":
            messagebox.showerror("Open Project", "Invalid project file.")
            return

        self._clear_widgets()
        self._theme_name = root.get("theme", "Dark")
        self._theme_var.set(self._theme_name)
        self._geometry = root.get("geometry", "800x600+100+100")
        self._geom_var.set(self._geometry)
        self._parse_geometry()

        window = root.find("window")
        if window is not None:
            self._window_title = window.get("title", "Untitled")
            self._title_var.set(self._window_title)
            self._surface_width = self._to_int(
                window.get("width", self._surface_width), self._surface_width
            )
            self._surface_height = self._to_int(
                window.get("height", self._surface_height), self._surface_height
            )

        self._configure_surface()

        for idx, elem in enumerate(
            window.findall("widget") if window is not None else root.findall("widget"), start=1
        ):
            item = self._widget_from_element(elem, idx)
            if item is not None:
                self._widgets.append(item)
                self._render_widget(item)

        self._refresh_list()
        self._project_path = Path(path)
        self.title(f"Uui Designer - {self._project_path.name}")

        t = theme.by_name(self._theme_name)
        if t is not None:
            theme.set_theme(t)
            theme.apply_theme_recursive(self)
            theme.apply_theme_recursive(self._surface)
        self._update_status_bar(f"Loaded {self._project_path.name}")

    def _widget_from_element(self, elem, idx):
        wtype = elem.get("type")
        if wtype not in WIDGET_CLASSES:
            return None
        item = {
            "id": f"w{idx}",
            "type": wtype,
            "name": elem.get("name", self._unique_name(wtype)),
            "x": self._to_int(elem.get("x", 20), 20),
            "y": self._to_int(elem.get("y", 20), 20),
            "width": self._to_int(
                elem.get("width", DEFAULT_SIZE[wtype][0]), DEFAULT_SIZE[wtype][0]
            ),
            "height": self._to_int(
                elem.get("height", DEFAULT_SIZE[wtype][1]), DEFAULT_SIZE[wtype][1]
            ),
            "command": elem.get("command", ""),
        }
        for k, v in DEFAULT_PROPS.get(wtype, {}).items():
            if k == "show_value":
                item[k] = self._to_bool(elem.get(k, v))
            else:
                item[k] = elem.get(k, v)
        return item

    def _save_xml(self, path):
        root = ET.Element(
            "designer",
            {
                "version": DESIGNER_VERSION,
                "theme": self._theme_name,
                "geometry": self._geometry,
            },
        )
        window = ET.SubElement(
            root,
            "window",
            {
                "title": self._window_title,
                "width": str(self._surface_width),
                "height": str(self._surface_height),
            },
        )
        for item in self._widgets:
            self._widget_to_element(item, window)

        tree = ET.ElementTree(root)
        try:
            tree.write(path, encoding="utf-8", xml_declaration=True)
        except Exception as e:
            messagebox.showerror("Save Project", f"Failed to save {path}:\n{e}")
            return False
        return True

    def _widget_to_element(self, item, parent):
        attrs = {
            "type": item["type"],
            "name": item["name"],
            "x": str(item["x"]),
            "y": str(item["y"]),
            "width": str(item["width"]),
            "height": str(item["height"]),
        }
        for k, v in item.items():
            if k in ("id", "type", "name", "x", "y", "width", "height"):
                continue
            if v is None or v == "":
                continue
            if k == "show_value":
                attrs[k] = "true" if self._to_bool(v) else "false"
            elif k == "values" and isinstance(v, (list, tuple)):
                attrs[k] = ", ".join(str(x) for x in v)
            else:
                attrs[k] = str(v)
        ET.SubElement(parent, "widget", attrs)

    def _save_project(self):
        if self._project_path is None:
            self._save_as_project()
            return
        if self._save_xml(self._project_path):
            self.title(f"Uui Designer - {self._project_path.name}")
            self._update_status_bar(f"Saved {self._project_path.name}")

    def _save_as_project(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".xml",
            filetypes=[("Uui project", "*.xml"), ("All files", "*.*")],
            title="Save Uui Project As",
        )
        if not path:
            return
        self._project_path = Path(path)
        self._save_project()

    def _open_project(self):
        path = filedialog.askopenfilename(
            defaultextension=".xml",
            filetypes=[("Uui project", "*.xml"), ("All files", "*.*")],
            title="Open Uui Project",
        )
        if path:
            self._load_xml(path)

    def _export_python(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".py",
            filetypes=[("Python file", "*.py"), ("All files", "*.*")],
            title="Export Python",
        )
        if not path:
            return
        content = self._generate_python()
        try:
            Path(path).write_text(content, encoding="utf-8")
        except Exception as e:
            messagebox.showerror("Export Python", f"Failed to export {path}:\n{e}")
            return
        messagebox.showinfo("Export Python", f"Saved {path}")

    def _generate_python(self):
        used_types = sorted({w["type"] for w in self._widgets})
        imports = ""
        if used_types:
            imports = (
                "from Uui.widgets import (\n" + "".join(f"    {t},\n" for t in used_types) + ")\n"
            )
        lines = [
            '"""Generated by Uui Designer."""',
            "",
            "import tkinter as tk",
            "",
            "from Uui import Window",
            "from Uui.widgets import theme",
            imports,
            "",
            f"DEFAULT_THEME = {self._theme_name!r}",
            f"DEFAULT_GEOMETRY = {self._geometry!r}",
            "",
            "",
            "def build(window: Window) -> None:",
        ]
        for item in self._widgets:
            name = self._safe_name(item["name"])
            cls = item["type"]
            kwargs = self._export_kwargs(item)
            kw = ""
            if kwargs:
                kw = ", " + ", ".join(f"{k}={v}" for k, v in kwargs.items())
            lines.append(f"    {name} = {cls}(window{kw})")
            lines.append(
                f"    {name}.place(x={item['x']}, y={item['y']}, "
                f"width={item['width']}, height={item['height']})"
            )
        if not self._widgets:
            lines.append("    pass")
        lines.extend(
            [
                "",
                "",
                "def main() -> None:",
                f"    window = Window(title={self._window_title!r})",
                "    window.geometry(DEFAULT_GEOMETRY)",
                "    window.configure(bg=theme.BG_BASE)",
                "",
                "    build(window)",
                "",
                "    target = theme.by_name(DEFAULT_THEME)",
                "    if target is not None:",
                "        theme.set_theme(target)",
                "        theme.apply_theme_recursive(window)",
                "",
                "    window.mainloop()",
                "",
                "",
                "if __name__ == '__main__':",
                "    main()",
                "",
            ]
        )
        return "\n".join(lines)

    def _export_kwargs(self, item):
        kwargs = {}
        wtype = item["type"]
        if item.get("text"):
            kwargs["text"] = repr(item["text"])
        if "variant" in item and wtype in VARIANT_OPTIONS:
            kwargs["variant"] = repr(item["variant"])
        if item.get("placeholder"):
            kwargs["placeholder"] = repr(item["placeholder"])
        if item.get("show"):
            kwargs["show"] = repr(item["show"])
        if "values" in item and str(item["values"]).strip():
            vals = [v.strip() for v in str(item["values"]).split(",")]
            kwargs["values"] = repr(vals)
        if "maximum" in item:
            kwargs["maximum"] = self._to_int(item["maximum"], 100)
        if "value" in item:
            kwargs["value"] = self._to_float(item["value"], 0)
        if "from_" in item:
            kwargs["from_"] = self._to_float(item["from_"], 0)
        if "to" in item:
            kwargs["to"] = self._to_float(item["to"], 100)
        if "orient" in item:
            kwargs["orient"] = repr(item["orient"])
        if "show_value" in item:
            kwargs["show_value"] = self._to_bool(item["show_value"])
        if "color" in item and str(item.get("color", "")).strip():
            kwargs["color"] = repr(item["color"])
        if "command" in item and str(item.get("command", "")).strip():
            cmd = str(item["command"]).strip()
            kwargs["command"] = cmd
        if wtype == "UButton":
            kwargs["width"] = self._to_int(item.get("width", 96), 96)
            kwargs["height"] = self._to_int(item.get("height", 28), 28)
        return kwargs

    def _safe_name(self, name):
        safe = "".join(c if c.isalnum() or c == "_" else "_" for c in name)
        if not safe or safe[0].isdigit():
            safe = "w_" + safe
        return safe

    def _reset_layout(self):
        self.geometry("1320x800+60+40")
        try:
            self._left_paned.sash_place(0, 260, 0)
            self._right_paned.sash_place(0, self._right_paned.winfo_width() - 300, 0)
        except tk.TclError:
            pass
        self._toast("Layout reset")

    def _show_about(self):
        messagebox.showinfo(
            "Uui Designer",
            "Uui Visual Widget Designer\n"
            "Qt Creator inspired layout\n\n"
            f"Version {DESIGNER_VERSION}\n"
            "Drag widgets from the palette.\n"
            "Double-click on the canvas to rename.\n"
            "Press Delete to remove.",
            parent=self,
        )

    def _on_close(self):
        if messagebox.askokcancel("Quit", "Close Uui Designer?"):
            self.destroy()


def main(project_file=None):
    app = DesignerApp(project_file)
    app.mainloop()


if __name__ == "__main__":
    main()
