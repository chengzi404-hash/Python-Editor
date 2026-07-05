import ctypes
import sys
import tkinter as tk
from . import theme


GWL_EXSTYLE = -20
WS_EX_APPWINDOW = 0x00040000
SW_SHOWNORMAL = 1
SW_SHOWMAXIMIZED = 3
SW_MINIMIZE = 6


class WindowPlacement(ctypes.Structure):
    _fields_ = [
        ("length", ctypes.c_uint),
        ("flags", ctypes.c_uint),
        ("showCmd", ctypes.c_uint),
        ("ptMinPosition_x", ctypes.c_long),
        ("ptMinPosition_y", ctypes.c_long),
        ("ptMaxPosition_x", ctypes.c_long),
        ("ptMaxPosition_y", ctypes.c_long),
        ("rcNormalPosition_left", ctypes.c_long),
        ("rcNormalPosition_top", ctypes.c_long),
        ("rcNormalPosition_right", ctypes.c_long),
        ("rcNormalPosition_bottom", ctypes.c_long),
    ]


class Window(tk.Tk):
    def __init__(self, screenName: str | None = None, baseName: str | None = None,
                 className: str = "Tk", useTk: bool = True, sync: bool = False, use: str | None = None,
                 title: str = "Uui Sample Window", title_font=None, debug: bool = False) -> None:
        super().__init__(screenName, baseName, className, useTk, sync, use)

        super().title(title)

        self.withdraw()
        self.update_idletasks()

        self._remove_title_bar()
        if sys.platform.startswith('win'):
            self._ensure_taskbar_button()
        self.tk_setPalette(theme.BG_TITLE)

        self.drag_offset_x = 0
        self.drag_offset_y = 0

        if debug:
            self.bind("<Escape>", lambda e: self.destroy())

        self._title_frame = tk.Frame(self, bg=theme.BG_TITLE)
        self._title_frame.pack(anchor=tk.N, fill=tk.X)

        self._title_frame.bind('<Button-1>', self.start_move)
        self._title_frame.bind('<B1-Motion>', self.set_position)

        dot_size = 14
        gap = 8
        pad = 6
        self._dot_canvas = tk.Canvas(self._title_frame, bg=theme.BG_TITLE,
                                      highlightthickness=0, bd=0)
        self._dot_canvas.pack(side=tk.RIGHT)

        self._dots: list = []

        def _create_dot(x, color, hover_char, command):
            y = pad
            oval = self._dot_canvas.create_oval(x, y, x + dot_size, y + dot_size,
                                                 fill=color, outline='')
            htext = self._dot_canvas.create_text(x + dot_size // 2, y + dot_size // 2,
                                                  text=hover_char, fill=theme.FG_PRIMARY,
                                                  font=theme.ICON_FONT, state='hidden')
            group = self._dot_canvas.create_rectangle(x - 1, y - 1, x + dot_size + 1, y + dot_size + 1,
                                                       outline='', fill='', tags=('dot_hit',))
            def on_enter(e):
                self._dot_canvas.itemconfig(oval, fill=theme.BG_TITLE, outline='')
                self._dot_canvas.itemconfig(htext, state='normal')
            def on_leave(e):
                self._dot_canvas.itemconfig(oval, fill=color, outline='')
                self._dot_canvas.itemconfig(htext, state='hidden')
            for item in (oval, htext, group):
                self._dot_canvas.tag_bind(item, '<Button-1>', lambda e: command())
                self._dot_canvas.tag_bind(item, '<Enter>', on_enter)
                self._dot_canvas.tag_bind(item, '<Leave>', on_leave)
            self._dots.append((oval, htext, color))

        x0 = pad
        _create_dot(x0, theme.GREEN, '=', self.maximize)
        _create_dot(x0 + dot_size + gap, theme.YELLOW, '-', self.minimize)
        _create_dot(x0 + 2 * (dot_size + gap), theme.RED, '\u00D7', self.destroy)

        self._dot_canvas.config(width=pad * 2 + 3 * dot_size + 2 * gap,
                                  height=dot_size + pad * 2)

        self.title_label = tk.Label(self._title_frame, text=title,
                                    font=title_font or theme.TITLE_FONT,
                                    bg=theme.BG_TITLE, fg=theme.FG_PRIMARY)
        self.title_label.pack(anchor=tk.W, pady=10, padx=20)

        self.title_label.bind('<Button-1>', self.start_move)
        self.title_label.bind('<B1-Motion>', self.set_position)

        self._title_font = title_font

        self.after(0, self._show_window)

    def _remove_title_bar(self):
        self.overrideredirect(True)

    def _ensure_taskbar_button(self):
        hwnd = self.winfo_id()
        if not hwnd:
            return
        ex_style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        ex_style |= WS_EX_APPWINDOW
        ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, ex_style)

    def _show_window(self):
        self._remove_title_bar()
        self.deiconify()
        self._remove_title_bar()

    def start_move(self, event):
        self.drag_offset_x = event.x_root - self.winfo_x()
        self.drag_offset_y = event.y_root - self.winfo_y()

    def set_position(self, event):
        x = event.x_root - self.drag_offset_x
        y = event.y_root - self.drag_offset_y
        self.geometry(f'+{x}+{y}')

    def maximize(self):
        if not sys.platform.startswith('win'):
            if self.state() == 'zoomed':
                self.state('normal')
            else:
                self.state('zoomed')
            return
        hwnd = self.winfo_id()
        if not hwnd:
            return
        wp = WindowPlacement()
        wp.length = ctypes.sizeof(wp)
        ctypes.windll.user32.GetWindowPlacement(hwnd, ctypes.byref(wp))
        if wp.showCmd == SW_SHOWMAXIMIZED:
            ctypes.windll.user32.ShowWindow(hwnd, SW_SHOWNORMAL)
        else:
            ctypes.windll.user32.ShowWindow(hwnd, SW_SHOWMAXIMIZED)

    def minimize(self):
        if not sys.platform.startswith('win'):
            self.state('iconic')
            return
        hwnd = self.winfo_id()
        if not hwnd:
            return
        ctypes.windll.user32.ShowWindow(hwnd, SW_MINIMIZE)

    def title(self, *args):
        if args:
            super().title(args[0])
            if hasattr(self, 'title_label'):
                self.title_label.config(text=args[0])
            return args[0]
        return super().title()

    def _apply_theme(self):
        try:
            self.tk_setPalette(theme.BG_TITLE)
            self.config(bg=theme.BG_BASE)
            self._title_frame.config(bg=theme.BG_TITLE)
            self._dot_canvas.config(bg=theme.BG_TITLE)
            for oval, htext, color in self._dots:
                self._dot_canvas.itemconfig(oval, fill=color)
                self._dot_canvas.itemconfig(htext, fill=theme.FG_PRIMARY)
            self.title_label.config(
                bg=theme.BG_TITLE, fg=theme.FG_PRIMARY,
                font=self._title_font or theme.TITLE_FONT,
            )
        except tk.TclError:
            pass


if __name__ == "__main__":
    window = Window()

    window.geometry('500x550+50+50')
    window.configure(bg=theme.BG_BASE)
    window.resizable(width=True, height=True)

    window.mainloop()