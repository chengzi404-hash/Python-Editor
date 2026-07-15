import tkinter as tk

from . import theme


class UCheckButton(tk.Frame):
    def __init__(self, parent, text: str = '', variable=None, command=None,
                 external_toggle=None, **kwargs):
        bg = kwargs.pop('bg', theme.BG_BASE)
        super().__init__(parent, bg=bg, highlightthickness=0, bd=0, **kwargs)

        self._var = variable if variable is not None else tk.BooleanVar()
        self._command = command
        self._external_toggle = external_toggle

        self._size = 18
        self._box_size = 14
        self._canvas = tk.Canvas(
            self, width=self._size, height=self._size,
            bg=bg, highlightthickness=0, bd=0,
        )
        self._canvas.pack(side=tk.LEFT)

        self._box = self._canvas.create_rectangle(
            (self._size - self._box_size) // 2,
            (self._size - self._box_size) // 2,
            (self._size - self._box_size) // 2 + self._box_size,
            (self._size - self._box_size) // 2 + self._box_size,
            fill=theme.BG_INPUT, outline=theme.BORDER, width=1,
        )
        self._check = self._canvas.create_text(
            self._size // 2, self._size // 2,
            text='\u2713', fill=theme.FG_PRIMARY,
            font=theme.ICON_FONT, state='hidden',
        )

        self._label = tk.Label(
            self, text=text, bg=bg, fg=theme.FG_PRIMARY,
            font=theme.LABEL_FONT, cursor='hand2',
        )
        self._label.pack(side=tk.LEFT, padx=(6, 0))

        for w in (self._canvas, self._label):
            w.bind('<Button-1>', self._toggle)
            w.bind('<Enter>', self._on_enter)
            w.bind('<Leave>', self._on_leave)

        self._var.trace_add('write', self._on_var_change)
        self._on_var_change()

    def _toggle(self, e=None):
        if self._external_toggle is not None:
            self._external_toggle()
            return
        self._var.set(not self._var.get())
        if self._command:
            self._command()

    def _on_enter(self, e=None):
        if not self._var.get():
            self._canvas.itemconfig(self._box, outline=theme.BORDER_STRONG)

    def _on_leave(self, e=None):
        if not self._var.get():
            self._canvas.itemconfig(self._box, outline=theme.BORDER)

    def _on_var_change(self, *args):
        if self._var.get():
            self._canvas.itemconfig(self._box, fill=theme.BLUE, outline=theme.BLUE)
            self._canvas.itemconfig(self._check, state='normal')
        else:
            self._canvas.itemconfig(self._box, fill=theme.BG_INPUT, outline=theme.BORDER)
            self._canvas.itemconfig(self._check, state='hidden')

    def get(self) -> bool:
        return bool(self._var.get())

    def set(self, value: bool):
        self._var.set(bool(value))

    def _apply_theme(self):
        try:
            bg = self.master.cget('bg')
            if bg:
                self.config(bg=bg)
        except Exception:
            self.config(bg=theme.BG_BASE)
            bg = theme.BG_BASE
        self._canvas.config(bg=bg)
        self._label.config(bg=bg, fg=theme.FG_PRIMARY, font=theme.LABEL_FONT)
        self._canvas.itemconfig(self._check, fill=theme.FG_PRIMARY, font=theme.ICON_FONT)
        self._on_var_change()
