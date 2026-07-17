import tkinter as tk

from . import theme


def _round_rect(canvas: tk.Canvas, x1, y1, x2, y2, r, **kwargs):
    return canvas.create_polygon(
        x1 + r,
        y1,
        x2 - r,
        y1,
        x2,
        y1,
        x2,
        y1 + r,
        x2,
        y2 - r,
        x2,
        y2,
        x2 - r,
        y2,
        x1 + r,
        y2,
        x1,
        y2,
        x1,
        y2 - r,
        x1,
        y1 + r,
        x1,
        y1,
        smooth=True,
        **kwargs,
    )


def _variant_colors(variant: str):
    return {
        "default": (theme.BG_RAISED, theme.BG_HOVER, theme.BG_ACTIVE, theme.FG_PRIMARY),
        "primary": (theme.BLUE, theme.BLUE_HOVER, theme.BLUE_DARK, theme.FG_PRIMARY),
        "success": (theme.GREEN, theme.GREEN_HOVER, theme.GREEN_DARK, "#000000"),
        "danger": (theme.RED, theme.RED_HOVER, theme.RED_DARK, theme.FG_PRIMARY),
        "warning": (theme.YELLOW, theme.YELLOW_HOVER, theme.YELLOW_DARK, "#000000"),
        "ghost": (theme.BG_BASE, theme.BG_RAISED, theme.BG_HOVER, theme.FG_PRIMARY),
    }.get(variant, (theme.BG_RAISED, theme.BG_HOVER, theme.BG_ACTIVE, theme.FG_PRIMARY))


class UButton(tk.Frame):
    def __init__(
        self,
        parent,
        text: str = "",
        command=None,
        variant: str = "default",
        width: int = 96,
        height: int = 28,
        radius: int = 6,
        font=None,
        state: str = "normal",
        **kwargs,
    ):
        self._variant = variant
        self._command = command
        self._radius = radius
        self._state = state
        self._width = width
        self._height = height

        bg = kwargs.pop("bg", theme.BG_BASE)
        super().__init__(parent, bg=bg, highlightthickness=0, bd=0, **kwargs)

        self._normal, self._hover, self._active, self._fg = _variant_colors(variant)

        self._canvas = tk.Canvas(
            self, width=width, height=height, bg=bg, highlightthickness=0, bd=0
        )
        self._canvas.pack()

        self._rect = _round_rect(
            self._canvas, 0, 0, width, height, radius, fill=self._normal, outline=""
        )
        self._text = self._canvas.create_text(
            width // 2,
            height // 2,
            text=text,
            fill=self._fg,
            font=font or theme.BUTTON_FONT,
        )

        self._canvas.bind("<Enter>", self._on_enter)
        self._canvas.bind("<Leave>", self._on_leave)
        self._canvas.bind("<Button-1>", self._on_press)
        self._canvas.bind("<ButtonRelease-1>", self._on_release)

        if state != "normal":
            self._set_state(state)

    def _on_enter(self, e=None):
        if self._state == "normal":
            self._canvas.itemconfig(self._rect, fill=self._hover)

    def _on_leave(self, e=None):
        if self._state == "normal":
            self._canvas.itemconfig(self._rect, fill=self._normal)

    def _on_press(self, e=None):
        if self._state == "normal":
            self._canvas.itemconfig(self._rect, fill=self._active)

    def _on_release(self, e=None):
        if self._state == "normal":
            self._canvas.itemconfig(self._rect, fill=self._hover)
            if self._command:
                self._command()

    def config(self, **kwargs):  # type: ignore[override]
        cnf = dict(kwargs)
        text = cnf.pop("text", None)
        if text is not None:
            self._canvas.itemconfig(self._text, text=text)
        command = cnf.pop("command", None)
        if command is not None:
            self._command = command
        state = cnf.pop("state", None)
        if state is not None:
            self._set_state(state)
        bg = cnf.pop("bg", None)
        if bg is not None:
            self._canvas.config(bg=bg)
        super().config(**cnf)

    def _set_state(self, state: str):
        self._state = state
        if state == "disabled":
            self._canvas.itemconfig(self._rect, fill=theme.BG_RAISED)
            self._canvas.itemconfig(self._text, fill=theme.FG_DISABLED)
        else:
            self._canvas.itemconfig(self._rect, fill=self._normal)
            self._canvas.itemconfig(self._text, fill=self._fg)

    def _apply_theme(self):
        self._normal, self._hover, self._active, self._fg = _variant_colors(self._variant)
        bg = self._parent_bg()
        self.config(bg=bg)
        self._canvas.config(bg=bg)
        self._set_state(self._state)

    def _parent_bg(self) -> str:
        try:
            v = self.master.cget("bg")
            if v:
                return str(v)
        except Exception:
            pass
        return theme.BG_BASE

    configure = config  # type: ignore[assignment]
