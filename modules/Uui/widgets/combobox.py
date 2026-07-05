import tkinter as tk
from typing import Optional
from . import theme


class UComboBox(tk.Frame):
    def __init__(self, parent, values=(), textvariable=None, command=None,
                 select_first: bool = True, **kwargs):
        bg = kwargs.pop('bg', theme.BG_BASE)
        super().__init__(parent, bg=bg, highlightthickness=0, bd=0, **kwargs)

        self._values = list(values)
        self._command = command
        self._var = textvariable if textvariable is not None else tk.StringVar()
        self._select_first = select_first

        self._button = tk.Frame(
            self, bg=theme.BG_INPUT,
            highlightthickness=1,
            highlightcolor=theme.BORDER_FOCUS,
            highlightbackground=theme.BORDER,
            bd=0,
        )
        self._button.pack(fill=tk.X)

        self._text_label = tk.Label(
            self._button, textvariable=self._var,
            bg=theme.BG_INPUT, fg=theme.FG_PRIMARY,
            font=theme.LABEL_FONT, anchor='w',
        )
        self._text_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10, pady=6)

        self._arrow = tk.Label(
            self._button, text='\u25BE', bg=theme.BG_INPUT,
            fg=theme.FG_SECONDARY, font=theme.LABEL_FONT,
        )
        self._arrow.pack(side=tk.RIGHT, padx=10)

        for w in (self._button, self._text_label, self._arrow):
            w.bind('<Button-1>', self._toggle)
            w.bind('<Enter>', self._on_enter)
            w.bind('<Leave>', self._on_leave)

        self._dropdown = None
        self._root_bind = None

        if select_first and self._values and not self._var.get():
            self._var.set(self._values[0])

    def _on_enter(self, e=None):
        if self._dropdown is not None:
            return
        self._button.config(bg=theme.BG_HOVER)
        self._text_label.config(bg=theme.BG_HOVER)
        self._arrow.config(bg=theme.BG_HOVER)

    def _on_leave(self, e=None):
        if self._dropdown is not None:
            return
        self._button.config(bg=theme.BG_INPUT)
        self._text_label.config(bg=theme.BG_INPUT)
        self._arrow.config(bg=theme.BG_INPUT)

    def _toggle(self, e=None):
        if self._dropdown is not None:
            self._close_dropdown()
        else:
            self._show_dropdown()

    def _show_dropdown(self):
        top = self.winfo_toplevel()
        self._dropdown = tk.Toplevel(top)
        self._dropdown.overrideredirect(True)
        self._dropdown.configure(bg=theme.BG_PANEL)

        x = self.winfo_rootx()
        y = self.winfo_rooty() + self.winfo_height()
        w = max(self.winfo_width(), 160)

        frame = tk.Frame(
            self._dropdown, bg=theme.BG_PANEL,
            highlightthickness=1, highlightbackground=theme.BORDER, bd=0,
        )
        frame.pack(fill=tk.BOTH, expand=True)

        item_height = 26
        h = item_height * len(self._values) + 4

        sw = top.winfo_screenwidth()
        sh = top.winfo_screenheight()
        if y + h > sh:
            y = self.winfo_rooty() - h
            if y < 0:
                y = 0
                h = min(h, sh)
        if x + w > sw:
            x = max(0, sw - w)
        if x < 0:
            x = 0

        self._dropdown.geometry(f'{w}x{h}+{x}+{y}')

        for value in self._values:
            item = tk.Label(
                frame, text='  ' + str(value), bg=theme.BG_PANEL,
                fg=theme.FG_PRIMARY, font=theme.LABEL_FONT,
                anchor='w', cursor='hand2',
                height=1, padx=8, pady=4,
            )
            item.pack(fill=tk.X)
            item.bind('<Button-1>', lambda e, v=value: self._select(v))
            item.bind('<Enter>', lambda e, w=item: w.config(bg=theme.BLUE))
            item.bind('<Leave>', lambda e, w=item: w.config(bg=theme.BG_PANEL))

        self._root_bind = top.bind('<Button-1>', self._on_root_click, add='+')

    def _on_root_click(self, e: Optional[tk.Event] = None):
        dd = self._dropdown
        if dd is None or e is None:
            return
        try:
            if not dd.winfo_exists():
                self._close_dropdown()
                return
            dx, dy = dd.winfo_rootx(), dd.winfo_rooty()
            dw, dh = dd.winfo_width(), dd.winfo_height()
            bx, by = self.winfo_rootx(), self.winfo_rooty()
            bw, bh = self.winfo_width(), self.winfo_height()
            xr, yr = e.x_root, e.y_root
        except tk.TclError:
            self._close_dropdown()
            return
        if dx <= xr <= dx + dw and dy <= yr <= dy + dh:
            return
        if bx <= xr <= bx + bw and by <= yr <= by + bh:
            return
        self._close_dropdown()

    def _select(self, value):
        self._var.set(value)
        self._close_dropdown()
        if self._command:
            self._command(value)

    def _close_dropdown(self):
        if self._dropdown is not None:
            try:
                self._dropdown.destroy()
            except tk.TclError:
                pass
            self._dropdown = None
        if self._root_bind is not None:
            try:
                self.winfo_toplevel().unbind('<Button-1>', self._root_bind)
            except tk.TclError:
                pass
            self._root_bind = None
        self._button.config(bg=theme.BG_INPUT)
        self._text_label.config(bg=theme.BG_INPUT)
        self._arrow.config(bg=theme.BG_INPUT)

    def get(self) -> str:
        return self._var.get()

    def set(self, value):
        self._var.set(value)

    def set_values(self, values):
        self._values = list(values)
        if self._select_first and self._values and self._var.get() not in self._values:
            self._var.set(self._values[0])

    def _apply_theme(self):
        try:
            outer_bg = self.master.cget('bg')
            if outer_bg:
                self.config(bg=outer_bg)
        except Exception:
            self.config(bg=theme.BG_BASE)
        self._button.config(
            bg=theme.BG_INPUT,
            highlightcolor=theme.BORDER_FOCUS,
            highlightbackground=theme.BORDER,
        )
        self._text_label.config(bg=theme.BG_INPUT, fg=theme.FG_PRIMARY, font=theme.LABEL_FONT)
        self._arrow.config(bg=theme.BG_INPUT, fg=theme.FG_SECONDARY, font=theme.LABEL_FONT)
        if self._dropdown is not None:
            self._close_dropdown()
