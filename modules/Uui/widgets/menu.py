import tkinter as tk
from typing import Callable, List, Optional, Tuple
from . import theme


class UMenu:
    def __init__(self):
        self._items: List[Tuple] = []

    def add_command(self, label: str, command: Optional[Callable] = None,
                    shortcut: str = ''):
        self._items.append(('command', label, shortcut, command, 'normal'))

    def add_separator(self):
        self._items.append(('separator',))

    def add_checkbutton(self, label: str, variable: Optional[tk.BooleanVar] = None,
                        command: Optional[Callable] = None, shortcut: str = ''):
        self._items.append(('check', label, shortcut, command,
                            variable if variable is not None else tk.BooleanVar()))

    def add_radiobutton(self, label: str, value, variable: Optional[tk.StringVar] = None,
                        command: Optional[Callable] = None, shortcut: str = ''):
        self._items.append(('radio', label, shortcut, command, value,
                            variable if variable is not None else tk.StringVar()))


class _MenuItemRow(tk.Frame):
    _ITEM_HEIGHT = 24
    _SEP_HEIGHT = 9

    def __init__(self, parent, kind: str, *args, dropdown: '_MenuDropdown'):
        super().__init__(parent, bg=theme.BG_PANEL,
                         height=self._SEP_HEIGHT if kind == 'separator' else self._ITEM_HEIGHT)
        self.pack_propagate(False)
        self.pack(fill=tk.X)
        self._dropdown = dropdown
        self._kind = kind

        if kind == 'separator':
            self._sep_line = tk.Frame(self, bg=theme.BORDER, height=1)
            self._sep_line.pack(fill=tk.X, padx=8, pady=4)
            return

        label, shortcut, command = args[0], args[1], args[2]

        self.prefix = tk.Label(self, text='', bg=theme.BG_PANEL,
                               fg=theme.FG_PRIMARY, font=theme.MENU_FONT,
                               width=2, anchor='center')
        self.prefix.pack(side=tk.LEFT, padx=(10, 0))

        self.text = tk.Label(self, text=label, bg=theme.BG_PANEL,
                              fg=theme.FG_PRIMARY, font=theme.MENU_FONT, anchor='w')
        self.text.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(6, 6), pady=3)

        self.sc = tk.Label(self, text=shortcut, bg=theme.BG_PANEL,
                            fg=theme.FG_SECONDARY, font=theme.MENU_FONT, anchor='e')
        self.sc.pack(side=tk.RIGHT, padx=(6, 10))

        state = 'normal'
        var = None
        value = None

        if kind == 'command':
            def on_click(e=None):
                self._dropdown._menu_bar._close_dropdown()
                if command:
                    command()
        elif kind == 'check':
            var = args[3]
            self.prefix.config(text='\u2713' if var.get() else '')
            def on_click(e=None):
                var.set(not var.get())
                self.prefix.config(text='\u2713' if var.get() else '')
                if command:
                    command()
                self._dropdown._menu_bar._close_dropdown()
        elif kind == 'radio':
            var = args[4]
            value = args[3]
            self.prefix.config(text='\u25C9' if str(var.get()) == str(value) else '\u25CC')
            def on_click(e=None):
                var.set(str(value))
                if command:
                    command()
                self._dropdown._menu_bar._close_dropdown()
        else:
            on_click = lambda e=None: None

        for w in (self, self.prefix, self.text, self.sc):
            w.bind('<Button-1>', on_click)
            w.bind('<Enter>', self._on_enter)
            w.bind('<Leave>', self._on_leave)

        self._widgets = (self.prefix, self.text, self.sc)

    def _on_enter(self, e=None):
        for w in self._widgets:
            w.config(bg=theme.BLUE, fg=theme.FG_PRIMARY)
        self.config(bg=theme.BLUE)

    def _on_leave(self, e=None):
        for w in self._widgets:
            if w.cget('text') in ('\u2713', '\u25C9', '\u25CC'):
                w.config(bg=theme.BG_PANEL, fg=theme.FG_PRIMARY)
            else:
                w.config(bg=theme.BG_PANEL, fg=theme.FG_SECONDARY)
        self.config(bg=theme.BG_PANEL)

    def _apply_theme(self):
        if self._kind == 'separator':
            self.config(bg=theme.BG_PANEL)
            self._sep_line.config(bg=theme.BORDER)
            return
        self.config(bg=theme.BG_PANEL)
        self.prefix.config(bg=theme.BG_PANEL, fg=theme.FG_PRIMARY, font=theme.MENU_FONT)
        self.text.config(bg=theme.BG_PANEL, fg=theme.FG_PRIMARY, font=theme.MENU_FONT)
        self.sc.config(bg=theme.BG_PANEL, fg=theme.FG_SECONDARY, font=theme.MENU_FONT)


class _MenuDropdown(tk.Toplevel):
    def __init__(self, menu_bar: 'UMenuBar', owner_button: tk.Widget, items: list):
        top = owner_button.winfo_toplevel()
        super().__init__(top)
        self.overrideredirect(True)
        self.configure(bg=theme.BG_PANEL)

        self._menu_bar = menu_bar
        self._owner = owner_button

        inner = tk.Frame(self, bg=theme.BG_PANEL,
                          highlightthickness=1, highlightbackground=theme.BORDER, bd=0)
        inner.pack(fill=tk.BOTH, expand=True)

        h = 4
        for it in items:
            if it[0] == 'separator':
                h += _MenuItemRow._SEP_HEIGHT
            else:
                h += _MenuItemRow._ITEM_HEIGHT
        h += 4

        x = owner_button.winfo_rootx()
        y = owner_button.winfo_rooty() + owner_button.winfo_height()
        w = max(owner_button.winfo_width() + 60, 180)

        sw = top.winfo_screenwidth()
        sh = top.winfo_screenheight()
        if y + h > sh:
            y = owner_button.winfo_rooty() - h
            if y < 0:
                y = 0
                h = min(h, sh)
        if x + w > sw:
            x = max(0, sw - w)
        if x < 0:
            x = 0

        self.geometry(f'{w}x{h}+{x}+{y}')
        self.update_idletasks()

        for item in items:
            kind = item[0]
            if kind == 'separator':
                _MenuItemRow(inner, 'separator', dropdown=self)
            elif kind == 'command':
                _MenuItemRow(inner, 'command', item[1], item[2], item[3], dropdown=self)
            elif kind == 'check':
                _MenuItemRow(inner, 'check', item[1], item[2], item[3], item[4], dropdown=self)
            elif kind == 'radio':
                _MenuItemRow(inner, 'radio', item[1], item[2], item[3], item[4], item[5], dropdown=self)

    def _apply_theme(self):
        try:
            self.configure(bg=theme.BG_PANEL)
            for child in self.winfo_children():
                apply_fn = getattr(child, '_apply_theme', None)
                if apply_fn is not None:
                    apply_fn()
        except tk.TclError:
            pass


class UMenuBar(tk.Frame):
    def __init__(self, parent, **kwargs):
        bg = kwargs.pop('bg', None)
        if bg is None:
            bg = theme.BG_TITLE
        super().__init__(parent, bg=bg, highlightthickness=0, bd=0, **kwargs)
        self._open_dropdown: Optional[_MenuDropdown] = None
        self._root_bind: Optional[str] = None
        self._buttons: List[Tuple[tk.Label, UMenu]] = []


    def add_cascade(self, label: str) -> UMenu:
        menu = UMenu()
        button = tk.Label(
            self, text=label, bg=self['bg'], fg=theme.FG_PRIMARY,
            font=theme.MENU_FONT, padx=14, pady=6, cursor='hand2',
        )
        button.pack(side=tk.LEFT)
        button.bind('<Button-1>', lambda e: self._toggle(button, menu))
        button.bind('<Enter>', lambda e: self._on_enter(button))
        button.bind('<Leave>', lambda e: self._on_leave(button))
        self._buttons.append((button, menu))
        return menu

    def _on_enter(self, button: tk.Label):
        if self._open_dropdown is not None and self._open_dropdown._owner is button:
            return
        button.config(bg=theme.BG_ACTIVE)

    def _on_leave(self, button: tk.Label):
        if self._open_dropdown is not None and self._open_dropdown._owner is button:
            return
        button.config(bg=self['bg'])

    def _toggle(self, button: tk.Label, menu: UMenu):
        if self._open_dropdown is not None:
            same_button = self._open_dropdown._owner is button
            self._close_dropdown()
            if not same_button:
                self._open(button, menu)
        else:
            self._open(button, menu)

    def _open(self, button: tk.Label, menu: UMenu):
        button.config(bg=theme.BG_ACTIVE)
        self._open_dropdown = _MenuDropdown(self, button, menu._items)
        try:
            top = button.winfo_toplevel()
            self._root_bind = top.bind('<Button-1>', self._on_root_click, add='+')
        except tk.TclError:
            self._root_bind = None

    def _close_dropdown(self):
        if self._open_dropdown is not None:
            try:
                self._open_dropdown.destroy()
            except tk.TclError:
                pass
            self._open_dropdown = None
        if self._root_bind is not None:
            try:
                top = self.winfo_toplevel()
                top.unbind('<Button-1>', self._root_bind)
            except tk.TclError:
                pass
            self._root_bind = None
        for btn, _ in self._buttons:
            try:
                btn.config(bg=self['bg'])
            except tk.TclError:
                pass

    def _on_root_click(self, e: Optional[tk.Event] = None):
        dd = self._open_dropdown
        if dd is None or e is None:
            return
        try:
            if not dd.winfo_exists():
                self._close_dropdown()
                return
            dx, dy = dd.winfo_rootx(), dd.winfo_rooty()
            dw, dh = dd.winfo_width(), dd.winfo_height()
            owner = dd._owner
            bx, by = owner.winfo_rootx(), owner.winfo_rooty()
            bw, bh = owner.winfo_width(), owner.winfo_height()
            xr, yr = e.x_root, e.y_root
        except tk.TclError:
            self._close_dropdown()
            return
        if dx <= xr <= dx + dw and dy <= yr <= dy + dh:
            return
        if bx <= xr <= bx + bw and by <= yr <= by + bh:
            return
        self._close_dropdown()

    def _apply_theme(self):
        for btn, _ in self._buttons:
            try:
                btn.config(bg=theme.BG_TITLE, fg=theme.FG_PRIMARY, font=theme.MENU_FONT)
            except tk.TclError:
                pass
        try:
            self.config(bg=theme.BG_TITLE)
        except tk.TclError:
            pass
