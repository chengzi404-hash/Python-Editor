import contextlib
import sys
import tkinter as tk

from .widgets import (
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
from .widgets.window import Window

BOLD = ("Arial", 12, "bold")
H1 = ("Arial", 14, "bold")


def build_demo(window: Window) -> None:
    _build_menu(window)
    _build_header(window)
    body, canvas = _build_scrollable_body(window)

    _section(canvas, "Buttons  —  6 variants", body)
    _build_button_row(canvas, body)

    _section(canvas, "Text Input  —  UEntry / UText", body)
    _build_inputs(canvas, body)

    _section(canvas, "Selection  —  UCheckButton / URadioButton / UComboBox", body)
    _build_selection(canvas, body)

    _section(canvas, "Progress & Slider", body)
    _build_progress_and_slider(canvas, body)

    _section(canvas, "Live Editor  —  UText", body)
    _build_text_demo(canvas, body)

    body.update_idletasks()
    canvas.config(scrollregion=canvas.bbox("all"))

    theme.follow_system(window, poll_interval_ms=2000)


def _build_menu(window: Window) -> None:
    menu_bar = UMenuBar(window)
    menu_bar.pack(fill=tk.X)

    file_menu = menu_bar.add_cascade("File")
    file_menu.add_command("New", lambda: print("[File] New"), "Ctrl+N")
    file_menu.add_command("Open...", lambda: print("[File] Open"), "Ctrl+O")
    file_menu.add_separator()
    file_menu.add_command("Save", lambda: print("[File] Save"), "Ctrl+S")
    file_menu.add_command("Save As...", lambda: print("[File] Save As"), "Ctrl+Shift+S")
    file_menu.add_separator()
    file_menu.add_command("Exit", window.destroy, "Alt+F4")

    edit_menu = menu_bar.add_cascade("Edit")
    edit_menu.add_command("Undo", lambda: print("[Edit] Undo"), "Ctrl+Z")
    edit_menu.add_command("Redo", lambda: print("[Edit] Redo"), "Ctrl+Y")
    edit_menu.add_separator()
    edit_menu.add_command("Cut", lambda: print("[Edit] Cut"), "Ctrl+X")
    edit_menu.add_command("Copy", lambda: print("[Edit] Copy"), "Ctrl+C")
    edit_menu.add_command("Paste", lambda: print("[Edit] Paste"), "Ctrl+V")

    view_menu = menu_bar.add_cascade("View")
    view_menu.add_command("Reload", lambda: print("[View] Reload"), "F5")
    view_menu.add_separator()
    view_var = tk.StringVar(value="grid")
    view_menu.add_radiobutton("Grid", "grid", view_var)
    view_menu.add_radiobutton("List", "list", view_var)
    view_menu.add_radiobutton("Tree", "tree", view_var)
    view_menu.add_separator()
    view_menu.add_checkbutton("Show Sidebar", tk.BooleanVar(value=True))
    view_menu.add_checkbutton("Show Status Bar", tk.BooleanVar(value=True))

    help_menu = menu_bar.add_cascade("Help")
    help_menu.add_command("Documentation", lambda: print("[Help] Docs"))
    help_menu.add_command("About Uui", lambda: print("[Help] About Uui"))


def _build_header(window: Window) -> None:
    header = UFrame(window, variant="panel")
    header.pack(fill=tk.X, padx=16, pady=(16, 0))

    title_row = UFrame(header, variant="panel")
    title_row.pack(fill=tk.X, padx=16, pady=(12, 0))

    ULabel(title_row, text="Uui  Component  Gallery", font=H1, variant="primary").pack(
        side=tk.LEFT, anchor=tk.W
    )

    theme_picker = _build_theme_picker(title_row, window)
    theme_picker.pack(side=tk.RIGHT, anchor=tk.E, pady=4)

    ULabel(
        header,
        text="Tkinter components, all sharing the same theme palette.",
        variant="secondary",
    ).pack(anchor=tk.W, padx=16, pady=(2, 12))


def _build_theme_picker(parent, window: Window) -> UFrame:
    picker = UFrame(parent, variant="panel")

    ULabel(picker, text="Theme", variant="secondary", font=theme.LABEL_FONT_SMALL).pack(
        side=tk.LEFT, padx=(0, 8)
    )

    names = [t.name for t in theme.available()]
    var = tk.StringVar(value=theme.current().name)
    combo = UComboBox(picker, values=names, textvariable=var, width=160)
    combo.pack(side=tk.LEFT)

    def on_select(name: str):
        target = theme.by_name(name)
        if target is not None and target is not theme.current():
            theme.set_theme(target, refresh_root=window)

    combo._command = on_select

    follow_var = tk.BooleanVar(value=False)
    follow_check = UCheckButton(picker, text="Follow system", variable=follow_var)
    follow_check.pack(side=tk.LEFT, padx=(12, 0))

    def on_toggle():
        if follow_var.get():
            theme.follow_system(window, poll_interval_ms=2000)
            cur = theme.current()
            combo.set(cur.name)
        else:
            theme.stop_following()

    def handle_check_click():
        follow_var.set(not follow_var.get())
        on_toggle()

    follow_check._command = on_toggle
    follow_check._external_toggle = handle_check_click

    def _on_theme_change(new_theme):
        var.set(new_theme.name)
        with contextlib.suppress(Exception):
            combo.set(new_theme.name)

    theme.on_change(_on_theme_change)

    return picker


class _ThemeCanvas(tk.Canvas):
    def _apply_theme(self):
        self.config(bg=theme.BG_BASE)


class _ThemeScrollbar(UScrollBar):
    """Demo panel scrollbar — matches the _ThemeCanvas (BG_BASE) tone."""

    _theme_key_trough = "BG_BASE"

    def __init__(self, parent, **kwargs):
        kwargs.setdefault("troughcolor", theme.BG_BASE)
        super().__init__(parent, **kwargs)


def _build_scrollable_body(window: Window):
    outer = UFrame(window, variant="base")
    outer.pack(fill=tk.BOTH, expand=True, padx=16, pady=16)

    canvas = _ThemeCanvas(outer, highlightthickness=0, bd=0)
    canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    scroll = _ThemeScrollbar(
        outer,
        orient="vertical",
        command=canvas.yview,
    )
    scroll.pack(side=tk.RIGHT, fill=tk.Y)
    canvas.config(yscrollcommand=scroll.set)

    body = UFrame(canvas, variant="base")
    window_item = canvas.create_window((0, 0), window=body, anchor="nw")

    def _on_canvas_resize(e):
        canvas.itemconfig(window_item, width=e.width)

    canvas.bind("<Configure>", _on_canvas_resize)

    def _on_mouse_wheel(e):
        canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")

    if sys.platform.startswith("win") or sys.platform == "darwin":
        canvas.bind_all("<MouseWheel>", _on_mouse_wheel)
    else:
        canvas.bind_all("<Button-4>", lambda e: canvas.yview_scroll(-1, "units"))
        canvas.bind_all("<Button-5>", lambda e: canvas.yview_scroll(1, "units"))

    return body, canvas


def _section(parent, title: str, body) -> None:
    title_row = UFrame(body, variant="base")
    title_row.pack(fill=tk.X, pady=(8, 6))
    ULabel(title_row, text=title, font=BOLD, variant="primary").pack(side=tk.LEFT)
    sep = UFrame(title_row, bg_key="BORDER", height=1)
    sep.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(12, 0), pady=8)


def _build_button_row(canvas, body) -> None:
    row = UFrame(body, variant="base")
    row.pack(fill=tk.X, pady=(0, 4))

    variants = ["default", "primary", "success", "danger", "warning", "ghost"]
    labels = ["Default", "Primary", "Success", "Danger", "Warning", "Ghost"]

    for label, variant in zip(labels, variants, strict=False):
        UButton(
            row,
            text=label,
            variant=variant,
            command=lambda v=variant: print(f"[button] {v}"),
        ).pack(side=tk.LEFT, padx=4, pady=4)

    UButton(row, text="Disabled", command=lambda: None, variant="primary", state="disabled").pack(
        side=tk.LEFT, padx=4, pady=4
    )

    ULabel(
        body,
        text="Click any button to print its variant to the console.",
        variant="tertiary",
        font=theme.LABEL_FONT_SMALL,
    ).pack(anchor=tk.W, pady=(0, 18))


def _build_inputs(canvas, body) -> None:
    grid = UFrame(body, variant="base")
    grid.pack(fill=tk.X, pady=(0, 18))
    grid.columnconfigure(1, weight=1)

    ULabel(grid, text="Name").grid(row=0, column=0, sticky=tk.W, pady=6, padx=(0, 12))
    UEntry(grid, placeholder="Enter your name").grid(row=0, column=1, sticky=tk.EW, pady=6)

    ULabel(grid, text="Email").grid(row=1, column=0, sticky=tk.W, pady=6, padx=(0, 12))
    UEntry(grid, placeholder="someone@example.com").grid(row=1, column=1, sticky=tk.EW, pady=6)

    ULabel(grid, text="Password").grid(row=2, column=0, sticky=tk.W, pady=6, padx=(0, 12))
    UEntry(grid, show="\u2022", placeholder="At least 8 chars").grid(
        row=2, column=1, sticky=tk.EW, pady=6
    )

    ULabel(grid, text="Search").grid(row=3, column=0, sticky=tk.W, pady=6, padx=(0, 12))
    UEntry(grid, placeholder="Type to search...").grid(row=3, column=1, sticky=tk.EW, pady=6)


def _build_selection(canvas, body) -> None:
    wrap = UFrame(body, variant="base")
    wrap.pack(fill=tk.X, pady=(0, 18))

    left = UFrame(wrap, variant="base")
    left.pack(side=tk.LEFT, fill=tk.X, expand=True)

    ULabel(left, text="Preferences", font=BOLD, variant="secondary").pack(anchor=tk.W, pady=(0, 6))
    UCheckButton(left, text="Enable notifications").pack(anchor=tk.W, pady=3)
    UCheckButton(left, text="Auto-save every 30 seconds").pack(anchor=tk.W, pady=3)
    UCheckButton(left, text="Show line numbers").pack(anchor=tk.W, pady=3)
    UCheckButton(left, text="Spell check").pack(anchor=tk.W, pady=3)

    mid = UFrame(wrap, variant="base")
    mid.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(32, 0))

    ULabel(mid, text="Difficulty", font=BOLD, variant="secondary").pack(anchor=tk.W, pady=(0, 6))
    diff = tk.StringVar(value="medium")
    URadioButton(mid, text="Easy", value="easy", variable=diff).pack(anchor=tk.W, pady=3)
    URadioButton(mid, text="Medium", value="medium", variable=diff).pack(anchor=tk.W, pady=3)
    URadioButton(mid, text="Hard", value="hard", variable=diff).pack(anchor=tk.W, pady=3)
    URadioButton(mid, text="Insane", value="insane", variable=diff).pack(anchor=tk.W, pady=3)

    right = UFrame(wrap, variant="base")
    right.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(32, 0))

    ULabel(right, text="Theme", font=BOLD, variant="secondary").pack(anchor=tk.W, pady=(0, 6))
    UComboBox(
        right,
        values=["Dark (default)", "Darker", "High Contrast", "Solarized Dark", "Monokai"],
        command=lambda v: print(f"[theme-tag] {v}"),
    ).pack(fill=tk.X, pady=2)


def _build_progress_and_slider(canvas, body) -> None:
    wrap = UFrame(body, variant="base")
    wrap.pack(fill=tk.X, pady=(0, 18))

    progress = UProgressBar(wrap, value=35, height=8)
    progress.pack(fill=tk.X, pady=(0, 6))
    progress_label = ULabel(
        wrap,
        text="Loading assets... 35%",
        variant="secondary",
        font=theme.LABEL_FONT_SMALL,
    )
    progress_label.pack(anchor=tk.W, pady=(0, 18))

    vol_label = ULabel(
        wrap,
        text="Volume  —  50",
        variant="primary",
        font=BOLD,
    )
    vol_label.pack(anchor=tk.W, pady=(0, 4))

    vol_value = [50]

    def on_volume(v: float):
        vol_value[0] = int(v)
        vol_label.config(text=f"Volume  —  {int(v)}")
        ratio = int(v)
        progress.set(ratio)
        progress_label.config(text=f"Loading assets... {ratio}%")

    USlider(wrap, from_=0, to=100, value=50, command=on_volume).pack(fill=tk.X, pady=(0, 6))

    ULabel(
        wrap,
        text="Drag the slider — the progress bar above updates live.",
        variant="tertiary",
        font=theme.LABEL_FONT_SMALL,
    ).pack(anchor=tk.W, pady=(0, 4))


def _build_text_demo(canvas, body) -> None:
    editor = UText(body, height=8, wrap="word")
    editor.pack(fill=tk.BOTH, expand=True, pady=(0, 8))
    sample = (
        "The Uui widget kit mirrors the macOS dark aesthetic of the title bar:\n"
        "\n"
        "  • black title strip with traffic-light dots\n"
        "  • layered grey panels\n"
        "  • blue accent for focus and primary actions\n"
        "  • rounded buttons with hover/press states\n"
        "\n"
        "This text area supports undo (Ctrl+Z), standard shortcuts and the same\n"
        "selection / focus styling as every other input in the kit.\n"
    )
    editor.insert("1.0", sample)


def main() -> None:
    window = Window(title="Uui  Component  Gallery")
    window.geometry("860x760+80+60")
    window.configure(bg=theme.BG_BASE)
    window.resizable(width=True, height=True)

    build_demo(window)

    window.mainloop()


if __name__ == "__main__":
    main()
