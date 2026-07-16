from __future__ import annotations

import tkinter as tk
from collections.abc import Callable

from . import theme


class UTabView(tk.Frame):
    def __init__(self, parent, **kwargs):
        bg = kwargs.pop("bg", theme.BG_PANEL)
        super().__init__(parent, bg=bg, highlightthickness=0, bd=0, **kwargs)

        self._tabs: dict[str, tk.Frame] = {}
        self._buttons: dict[str, tk.Frame] = {}
        self._active: str | None = None
        self._on_switch: Callable[[str], None] | None = None

        self._bar = tk.Frame(self, bg=theme.BG_TITLE, height=30)
        self._bar.pack(fill=tk.X)
        self._bar.pack_propagate(False)

        self._content = tk.Frame(self, bg=theme.BG_PANEL)
        self._content.pack(fill=tk.BOTH, expand=True)

    def add_tab(self, tab_id: str, label: str) -> tk.Frame:
        btn_bg = theme.BG_TITLE
        btn_fg = theme.FG_SECONDARY

        btn = tk.Frame(self._bar, bg=btn_bg, cursor="hand2")
        btn.pack(side=tk.LEFT, padx=0, pady=0)

        lbl = tk.Label(
            btn,
            text=label,
            bg=btn_bg,
            fg=btn_fg,
            font=theme.LABEL_FONT,
            padx=16,
            pady=6,
        )
        lbl.pack()

        sep = tk.Frame(btn, bg=theme.BG_TITLE, width=1)
        sep.pack(side=tk.RIGHT, fill=tk.Y)

        for w in (btn, lbl):
            w.bind("<Button-1>", lambda e, tid=tab_id: self.select(tid))
            w.bind("<Enter>", lambda e, b=btn, lbl_arg=lbl: self._on_tab_enter(b, lbl_arg))
            w.bind("<Leave>", lambda e, b=btn, lbl_arg=lbl: self._on_tab_leave(b, lbl_arg, tab_id))

        content_frame = tk.Frame(self._content, bg=theme.BG_PANEL)
        self._tabs[tab_id] = content_frame
        self._buttons[tab_id] = btn

        if self._active is None:
            self.select(tab_id)

        return content_frame

    def select(self, tab_id: str):
        if tab_id not in self._tabs:
            return
        if self._active == tab_id:
            return
        if self._active:
            prev_btn = self._buttons[self._active]
            prev_lbl = prev_btn.winfo_children()[0]
            prev_lbl.config(fg=theme.FG_SECONDARY)
            self._tabs[self._active].pack_forget()
        self._active = tab_id
        btn = self._buttons[tab_id]
        lbl = btn.winfo_children()[0]
        lbl.config(fg=theme.FG_PRIMARY)
        self._tabs[tab_id].pack(fill=tk.BOTH, expand=True)

        if self._on_switch:
            self._on_switch(tab_id)

    def on_switch(self, callback: Callable[[str], None]):
        self._on_switch = callback

    def _on_tab_enter(self, btn: tk.Frame, lbl: tk.Label):
        if self._active is None or btn != self._buttons.get(self._active):
            lbl.configure(fg=str(theme.FG_PRIMARY))

    def _on_tab_leave(self, btn: tk.Frame, lbl: tk.Label, tab_id: str):
        if tab_id != self._active:
            lbl.configure(fg=str(theme.FG_SECONDARY))

    def _apply_theme(self):
        self.config(bg=theme.BG_PANEL)
        self._bar.config(bg=theme.BG_TITLE)
        self._content.config(bg=theme.BG_PANEL)
        for tid, btn in self._buttons.items():
            btn.config(bg=theme.BG_TITLE)
            lbl = btn.winfo_children()[0]
            lbl.config(
                bg=theme.BG_TITLE,
                fg=theme.FG_PRIMARY if tid == self._active else theme.FG_SECONDARY,
            )
        for cf in self._tabs.values():
            cf.config(bg=theme.BG_PANEL)
