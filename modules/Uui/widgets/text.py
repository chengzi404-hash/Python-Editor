import tkinter as tk
from . import theme


class UText(tk.Frame):
    def __init__(self, parent, width: int = 40, height: int = 10,
                 wrap: str = 'word', font=None, **kwargs):
        bg = kwargs.pop('bg', theme.BG_BASE)
        super().__init__(parent, bg=bg, highlightthickness=0, bd=0, **kwargs)

        self._text = tk.Text(
            self, width=width, height=height,
            bg=theme.BG_INPUT, fg=theme.FG_PRIMARY,
            insertbackground=theme.FG_PRIMARY,
            selectbackground=theme.BLUE,
            selectforeground=theme.FG_PRIMARY,
            relief='flat', highlightthickness=1,
            highlightcolor=theme.BORDER_FOCUS,
            highlightbackground=theme.BORDER,
            bd=0, font=font or theme.MONO_FONT,
            wrap=wrap,
            undo=True,
            padx=8, pady=8,
        )
        self._scroll = tk.Scrollbar(
            self, orient='vertical', command=self._text.yview,
            bg=theme.BG_PANEL, troughcolor=theme.BG_INPUT,
            activebackground=theme.BG_HOVER,
            relief='flat', bd=0, width=10,
            highlightthickness=0,
        )
        self._text.config(yscrollcommand=self._scroll.set)

        self._scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self._text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    def get(self, *args):
        return self._text.get(*args)

    def insert(self, *args):
        self._text.insert(*args)

    def delete(self, *args):
        self._text.delete(*args)

    def clear(self):
        self._text.delete('1.0', tk.END)

    def see(self, index):
        self._text.see(index)

    def config(self, **kwargs):
        cnf = dict(kwargs)
        if 'state' in cnf:
            self._text.config(state=cnf.pop('state'))
        super().config(**cnf)

    def _apply_theme(self):
        try:
            bg = self.master.cget('bg')
            if bg:
                self.config(bg=bg)
        except Exception:
            self.config(bg=theme.BG_BASE)
        self._text.config(
            bg=theme.BG_INPUT, fg=theme.FG_PRIMARY,
            insertbackground=theme.FG_PRIMARY,
            selectbackground=theme.BLUE,
            selectforeground=theme.FG_PRIMARY,
            highlightcolor=theme.BORDER_FOCUS,
            highlightbackground=theme.BORDER,
        )
        self._scroll.config(
            bg=theme.BG_PANEL, troughcolor=theme.BG_INPUT,
            activebackground=theme.BG_HOVER,
        )

    configure = config
