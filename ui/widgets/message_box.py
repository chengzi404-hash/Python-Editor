from __future__ import annotations

import tkinter as tk

from core.settings.i18n import t

from . import theme
from .button import UButton
from .frame import UFrame
from .label import ULabel


class _UDialogBase(tk.Toplevel):
    def __init__(self, parent, title: str = "", width: int = 400, height: int = 180):
        super().__init__(parent)
        self._parent = parent

        self.title(title)
        self.transient(parent)
        self.grab_set()
        self.resizable(False, False)

        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x = max(0, (sw - width) // 2)
        y = max(0, (sh - height) // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")

        outer = UFrame(self, variant="panel")
        outer.pack(fill=tk.BOTH, expand=True)

        self._body = UFrame(outer, variant="panel")
        self._body.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        self._btn_area = UFrame(outer, variant="panel")
        self._btn_area.pack(fill=tk.X, padx=20, pady=(0, 15))

        self.protocol("WM_DELETE_WINDOW", self.destroy)

    @property
    def body(self) -> UFrame:
        return self._body

    @property
    def btn_area(self) -> UFrame:
        return self._btn_area


def askstring(parent, title: str, prompt: str, initialvalue: str = "", **kwargs) -> str | None:
    import tkinter.simpledialog as sd

    return sd.askstring(title, prompt, initialvalue=initialvalue, parent=parent, **kwargs)


def showinfo(title: str, message: str, parent=None, **kwargs):
    if parent is None:
        import tkinter.messagebox as mb

        return mb.showinfo(title, message, **kwargs)

    dlg = _UDialogBase(parent, title=title, width=400, height=150)
    ULabel(dlg.body, text=message, variant="primary", font=theme.LABEL_FONT).pack(pady=20)

    def close():
        dlg.destroy()

    UButton(dlg.btn_area, text=t("dialog.btn.ok"), variant="primary", command=close, width=80).pack(
        side=tk.RIGHT
    )
    dlg.wait_window()


def showerror(title: str, message: str, parent=None, **kwargs):
    if parent is None:
        import tkinter.messagebox as mb

        return mb.showerror(title, message, **kwargs)

    dlg = _UDialogBase(parent, title=title, width=420, height=150)
    ULabel(dlg.body, text=message, variant="red", font=theme.LABEL_FONT).pack(pady=20)

    def close():
        dlg.destroy()

    UButton(dlg.btn_area, text=t("dialog.btn.ok"), variant="danger", command=close, width=80).pack(
        side=tk.RIGHT
    )
    dlg.wait_window()


def showwarning(title: str, message: str, parent=None, **kwargs):
    if parent is None:
        import tkinter.messagebox as mb

        return mb.showwarning(title, message, **kwargs)

    dlg = _UDialogBase(parent, title=title, width=420, height=150)
    ULabel(dlg.body, text=message, variant="yellow", font=theme.LABEL_FONT).pack(pady=20)

    def close():
        dlg.destroy()

    UButton(dlg.btn_area, text=t("dialog.btn.ok"), variant="warning", command=close, width=80).pack(
        side=tk.RIGHT
    )
    dlg.wait_window()


def askyesno(title: str, message: str, parent=None, **kwargs) -> bool:
    if parent is None:
        import tkinter.messagebox as mb

        return mb.askyesno(title, message, **kwargs)

    result = False

    dlg = _UDialogBase(parent, title=title, width=400, height=150)
    ULabel(dlg.body, text=message, variant="primary", font=theme.LABEL_FONT).pack(pady=20)

    def on_yes():
        nonlocal result
        result = True
        dlg.destroy()

    def on_no():
        nonlocal result
        result = False
        dlg.destroy()

    btn_frame = UFrame(dlg.btn_area, variant="panel")
    btn_frame.pack(side=tk.RIGHT)
    UButton(btn_frame, text=t("dialog.btn.yes"), variant="primary", command=on_yes, width=70).pack(
        side=tk.LEFT, padx=5
    )
    UButton(btn_frame, text=t("dialog.btn.no"), variant="ghost", command=on_no, width=70).pack(
        side=tk.LEFT
    )

    dlg.wait_window()
    return result


def askstring_custom(parent, title: str, prompt: str, initialvalue: str = "") -> str | None:
    from .entry import UEntry

    result: str | None = None

    dlg = _UDialogBase(parent, title=title, width=420, height=180)
    ULabel(dlg.body, text=prompt, variant="secondary", font=theme.LABEL_FONT).pack(anchor="w")

    var = tk.StringVar(value=initialvalue)
    entry = UEntry(dlg.body, textvariable=var, width=40)
    entry.pack(fill=tk.X, pady=(8, 0))

    def on_ok():
        nonlocal result
        result = entry.get() or var.get()
        dlg.destroy()

    def on_cancel():
        nonlocal result
        result = None
        dlg.destroy()

    def on_key(e):
        if e.keysym == "Return":
            on_ok()
        elif e.keysym == "Escape":
            on_cancel()

    dlg.bind("<Key>", on_key)
    entry.focus_set()

    btn_frame = UFrame(dlg.btn_area, variant="panel")
    btn_frame.pack(side=tk.RIGHT)
    UButton(btn_frame, text=t("dialog.btn.ok"), variant="primary", command=on_ok, width=70).pack(
        side=tk.LEFT, padx=5
    )
    UButton(
        btn_frame, text=t("dialog.btn.cancel"), variant="ghost", command=on_cancel, width=70
    ).pack(side=tk.LEFT)

    dlg.wait_window()
    return result
