import tkinter as tk

from . import theme


class UEntry(tk.Frame):
    def __init__(
        self,
        parent,
        textvariable=None,
        placeholder: str = "",
        width: int = 20,
        show: str = "",
        **kwargs,
    ):
        bg = kwargs.pop("bg", theme.BG_BASE)
        super().__init__(parent, bg=bg, highlightthickness=0, bd=0, **kwargs)

        self._placeholder = placeholder
        self._has_placeholder = False
        self._show = show
        self._real_show = show

        self._var = textvariable if textvariable is not None else tk.StringVar()

        self._entry = tk.Entry(
            self,
            textvariable=self._var,
            bg=theme.BG_INPUT,
            fg=theme.FG_PRIMARY,
            insertbackground=theme.FG_PRIMARY,
            selectbackground=theme.BLUE,
            selectforeground=theme.FG_PRIMARY,
            relief="flat",
            highlightthickness=1,
            highlightcolor=theme.BORDER_FOCUS,
            highlightbackground=theme.BORDER,
            bd=0,
            font=theme.LABEL_FONT,
            show=show,
        )
        self._entry.pack(fill=tk.X, expand=True)

        if placeholder:
            self._entry.bind("<FocusIn>", self._on_focus_in)
            self._entry.bind("<FocusOut>", self._on_focus_out)
            self._show_placeholder()

    def _show_placeholder(self):
        if not self._var.get():
            self._has_placeholder = True
            self._var.set(self._placeholder)
            self._entry.config(fg=theme.FG_SECONDARY, show="")

    def _hide_placeholder(self):
        if self._has_placeholder:
            self._has_placeholder = False
            self._var.set("")
            self._entry.config(fg=theme.FG_PRIMARY, show=self._real_show)

    def _on_focus_in(self, e):
        self._hide_placeholder()

    def _on_focus_out(self, e):
        if not self._var.get():
            self._show_placeholder()

    def get(self) -> str:
        if self._has_placeholder:
            return ""
        return self._var.get()

    def set(self, value: str):
        if self._has_placeholder:
            self._hide_placeholder()
        self._var.set(value)

    def config(self, **kwargs):
        cnf = dict(kwargs)
        state = cnf.pop("state", None)
        if state is not None:
            self._entry.config(state=state)
        bg = cnf.pop("bg", None)
        if bg is not None:
            tk.Frame.config(self, bg=bg)
        show = cnf.pop("show", None)
        if show is not None:
            self._real_show = show
            if not self._has_placeholder:
                self._entry.config(show=show)
        super().config(**cnf)

    def _apply_theme(self):
        try:
            bg = self.master.cget("bg")
            if bg:
                self.config(bg=bg)
        except Exception:
            self.config(bg=theme.BG_BASE)
        self._entry.config(
            bg=theme.BG_INPUT,
            fg=theme.FG_PRIMARY,
            insertbackground=theme.FG_PRIMARY,
            selectbackground=theme.BLUE,
            selectforeground=theme.FG_PRIMARY,
            highlightcolor=theme.BORDER_FOCUS,
            highlightbackground=theme.BORDER,
            font=theme.LABEL_FONT,
        )
        if self._has_placeholder:
            self._entry.config(fg=theme.FG_SECONDARY)

    configure = config  # type: ignore[assignment]
