import tkinter as tk

from . import theme


class URadioButton(tk.Frame):
    def __init__(self, parent, text: str = '', value=None, variable=None,
                 command=None, external_toggle=None, **kwargs):
        bg = kwargs.pop('bg', theme.BG_BASE)
        super().__init__(parent, bg=bg, highlightthickness=0, bd=0, **kwargs)

        self._value = value
        self._var = variable if variable is not None else tk.StringVar()
        self._command = command
        self._external_toggle = external_toggle

        self._size = 18
        self._canvas = tk.Canvas(
            self, width=self._size, height=self._size,
            bg=bg, highlightthickness=0, bd=0,
        )
        self._canvas.pack(side=tk.LEFT)

        self._outer = self._canvas.create_oval(
            2, 2, self._size - 2, self._size - 2,
            fill=theme.BG_INPUT, outline=theme.BORDER, width=1,
        )
        self._inner = self._canvas.create_oval(
            6, 6, self._size - 6, self._size - 6,
            fill=theme.BLUE, outline='', state='hidden',
        )

        self._label = tk.Label(
            self, text=text, bg=bg, fg=theme.FG_PRIMARY,
            font=theme.LABEL_FONT, cursor='hand2',
        )
        self._label.pack(side=tk.LEFT, padx=(6, 0))

        for w in (self._canvas, self._label):
            w.bind('<Button-1>', self._toggle)

        self._var.trace_add('write', self._on_var_change)
        self._on_var_change()

    def _toggle(self, e=None):
        if self._external_toggle is not None:
            self._external_toggle()
            return
        if str(self._var.get()) != str(self._value):
            self._var.set(str(self._value))
            if self._command:
                self._command()

    def _on_var_change(self, *args):
        if str(self._var.get()) == str(self._value):
            self._canvas.itemconfig(self._outer, outline=theme.BLUE)
            self._canvas.itemconfig(self._inner, state='normal')
        else:
            self._canvas.itemconfig(self._outer, outline=theme.BORDER)
            self._canvas.itemconfig(self._inner, state='hidden')

    def get(self):
        return self._var.get()

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
        self._canvas.itemconfig(self._inner, fill=theme.BLUE)
        self._on_var_change()
