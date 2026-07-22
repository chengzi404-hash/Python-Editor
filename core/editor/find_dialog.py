"""Modal dialogs for find / replace and references results.

These are extracted into dedicated classes so :mod:`core.editor.app` stays
focused on top-level orchestration. Each dialog exposes ``show()`` /
``wait_window()`` and stores its current query so a subsequent open call can
pre-populate the input.
"""

from __future__ import annotations

import contextlib
import tkinter as tk
from collections.abc import Callable

from core.settings.i18n import t
from ui.widgets import UButton, UFrame, ULabel, theme


class FindDialog:
    """A modal find-and-replace dialog anchored to the editor window."""

    def __init__(
        self,
        parent: tk.Misc,
        text: tk.Text,
        *,
        replace: bool = False,
        initial_query: str = "",
        initial_last_index: str | None = None,
        on_change: Callable[[], None] | None = None,
    ) -> None:
        self._parent = parent
        self._text = text
        self._replace_mode = replace
        self._initial_query = initial_query
        self._initial_last_index = initial_last_index
        self._on_change = on_change

        self._window: tk.Toplevel | None = None
        self._find_var: tk.StringVar | None = None
        self._replace_var: tk.StringVar | None = None
        self._case_var: tk.BooleanVar | None = None
        self._last_index: str | None = initial_last_index
        self._last_query: str = initial_query

    @property
    def last_query(self) -> str:
        return self._last_query

    @property
    def last_index(self) -> str | None:
        return self._last_index

    def show(self) -> None:
        dlg = tk.Toplevel(self._parent)
        self._window = dlg
        dlg.title(t("dialog.title.replace") if self._replace_mode else t("dialog.title.find"))
        dlg.configure(bg=theme.BG_PANEL)
        dlg.transient(self._parent)
        dlg.resizable(False, False)

        ULabel(dlg, text=t("find.find_label"), bg=theme.BG_PANEL).grid(
            row=0, column=0, sticky="e", padx=6, pady=6
        )
        find_var = tk.StringVar(value=self._initial_query)
        self._find_var = find_var
        find_entry = tk.Entry(
            dlg,
            textvariable=find_var,
            width=30,
            bg=theme.BG_INPUT,
            fg=theme.FG_PRIMARY,
            insertbackground=theme.FG_PRIMARY,
        )
        find_entry.grid(row=0, column=1, columnspan=2, sticky="ew", padx=6, pady=6)

        replace_var: tk.StringVar | None = None
        if self._replace_mode:
            ULabel(dlg, text=t("find.replace_label"), bg=theme.BG_PANEL).grid(
                row=1, column=0, sticky="e", padx=6, pady=6
            )
            replace_var = tk.StringVar()
            self._replace_var = replace_var
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
        self._case_var = case_var
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
            if find_var.get():
                self._search()

        def do_replace():
            self._search()
            replace_text = replace_var.get() if replace_var else ""
            sel = self._text.tag_ranges("sel")
            if sel:
                self._text.delete(sel[0], sel[1])
                self._text.insert(sel[0], replace_text)
                self._last_index = str(sel[0])
                self._notify_changed()

        def do_replace_all():
            query = find_var.get()
            if not query:
                return
            replace_text = replace_var.get() if replace_var else ""
            self._last_query = query
            text = self._text
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
            self._notify_changed()
            tk.messagebox.showinfo(  # type: ignore[attr-defined]
                t("dialog.title.replace_done"),
                t("dialog.replace.done", count=count),
                parent=dlg,
            )

        def close():
            dlg.destroy()

        btn_row = 3 if self._replace_mode else 2
        UButton(
            dlg,
            text=t("find.find_next"),
            command=do_find,
            variant="primary",
            width=80,
            height=24,
        ).grid(row=btn_row, column=0, padx=4, pady=6)
        if self._replace_mode:
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

    def wait_window(self) -> None:
        if self._window is not None:
            self._window.wait_window()

    def _search(self) -> None:
        find_var = self._find_var
        case_var = self._case_var
        if find_var is None or case_var is None:
            return
        query = find_var.get()
        if not query:
            return
        self._last_query = query
        text = self._text
        start = text.index(tk.INSERT)
        if self._last_index:
            start = self._last_index
        nocase = not case_var.get()
        pos = text.search(query, start, stopindex="end", nocase=nocase)
        if not pos:
            pos = text.search(query, "1.0", stopindex=start, nocase=nocase)
            if not pos:
                tk.messagebox.showinfo(  # type: ignore[attr-defined]
                    t("dialog.title.find_not_found"),
                    t("dialog.find.not_found"),
                    parent=self._window,
                )
                return
        end = f"{pos}+{len(query)}c"
        text.tag_remove("sel", "1.0", "end")
        text.tag_add("sel", pos, end)
        text.mark_set(tk.INSERT, end)
        text.see(pos)
        self._last_index = str(end)

    def _notify_changed(self) -> None:
        if self._on_change is not None:
            with contextlib.suppress(Exception):
                self._on_change()


class ReferencesDialog:
    """A modal dialog listing all references to a symbol in the current file."""

    def __init__(
        self,
        parent: tk.Misc,
        text: tk.Text,
        word: str,
        matches: list[tuple[int, str]],
        *,
        font_family: str,
        font_size: int,
        on_jump: Callable[[int], None] | None = None,
    ) -> None:
        self._parent = parent
        self._text = text
        self._word = word
        self._matches = matches
        self._font_family = font_family
        self._font_size = font_size
        self._on_jump = on_jump
        self._window: tk.Toplevel | None = None

    def show(self) -> None:
        parent = self._parent
        dlg = tk.Toplevel(parent)
        self._window = dlg
        dlg.title(t("dialog.title.find_references") + f": {self._word}")
        dlg.configure(bg=theme.BG_PANEL)
        dlg.transient(parent)
        dlg.geometry("560x360")
        dlg.minsize(360, 200)

        top_frame = UFrame(dlg, bg=theme.BG_PANEL)
        top_frame.pack(fill="x", padx=10, pady=(10, 4))
        ULabel(
            top_frame,
            text=t("dialog.find_references.count", symbol=self._word, count=len(self._matches)),
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

        for ln, text_content in self._matches:
            display = f"  {ln:>4} | {text_content[:80]}"
            listbox.insert("end", display)

        def on_select(_=None):
            selection = listbox.curselection()
            if not selection:
                return
            idx = selection[0]
            target_line, _ = self._matches[idx]
            self._text.mark_set(tk.INSERT, f"{target_line}.0")
            self._text.see(tk.INSERT)
            self._text.tag_remove("sel", "1.0", "end")
            self._text.tag_add("sel", f"{target_line}.0", f"{target_line}.end")
            if self._on_jump is not None:
                self._on_jump(target_line)
            dlg.destroy()

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
        dlg.wait_window()

    @staticmethod
    def show_documentation(
        parent: tk.Misc,
        word: str,
        doc: dict,
        *,
        font_family: str,
        font_size: int,
    ) -> None:
        """Show a documentation viewer for ``word`` populated from ``doc``."""
        dlg = tk.Toplevel(parent)
        dlg.title(t("dialog.find_documentation.title", word=word))
        dlg.configure(bg=theme.BG_PANEL)
        dlg.transient(parent)
        dlg.geometry("520x400")
        dlg.minsize(360, 200)

        header = ULabel(
            dlg,
            text=t("dialog.find_documentation.header", word=word, type=doc.get("type", "")),
            bg=theme.BG_PANEL,
            fg=theme.FG_PRIMARY,
            font=(font_family, font_size + 2, "bold"),
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
                font=("Consolas", font_size),
            ).pack(anchor="w")

        text_frame = UFrame(dlg, bg=theme.BG_BASE)
        text_frame.pack(fill="both", expand=True, padx=12, pady=(0, 8))

        doc_text = tk.Text(
            text_frame,
            wrap="word",
            bg=theme.BG_BASE,
            fg=theme.FG_PRIMARY,
            font=(font_family, font_size),
            relief="flat",
            padx=8,
            pady=8,
        )
        doc_text.pack(fill="both", expand=True)
        doc_text.insert("1.0", doc.get("doc", t("dialog.find_documentation.no_doc")))
        doc_text.config(state="disabled")

        scrollbar = tk.Scrollbar(text_frame, command=doc_text.yview)
        scrollbar.pack(side="right", fill="y")
        doc_text.config(yscrollcommand=scrollbar.set)

        source = doc.get("source", "")
        if source:
            ULabel(
                dlg,
                text=t("dialog.find_documentation.from_module", module=source),
                bg=theme.BG_PANEL,
                fg=theme.FG_DIM,
                font=(font_family, font_size - 1),
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
