"""``modules.Uui.widgets.scrollbar`` — Canvas 绘制的主题感知 ScrollBar.

用 :class:`tk.Frame` + 内部 :class:`tk.Canvas` 完全替代
:class:`tk.Scrollbar`, 因为 Windows 下 ``tk.Scrollbar`` 的系统主题
(BG/troughcolor) 无法被自定义颜色可靠覆盖。

支持:

* ``bg=""`` —— 滑块颜色, 空字符串默认取 :data:`theme.BG_PANEL`;
  主题切换时会跟随刷新; 若调用方显式传了非空颜色则不覆盖。
* ``autohidden`` —— ``True`` 时, ``set(first, last)`` 收到 (0.0, 1.0)
  自动 ``pack_forget``; 收到非满区间时用缓存 ``pack_info()`` 还原布局。
* ``command`` / ``orient`` / ``troughcolor`` / ``activebackground`` /
  ``width`` —— 与 :class:`tk.Scrollbar` 一致的接口。
* 鼠标: 拖拽滑块 → ``command("moveto", first)``; 点击滑道 → page scroll;
  滚轮 → unit scroll。
"""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from typing import Any, Literal

from . import theme


class UScrollBar(tk.Frame):
    """Canvas 绘制的主题感知 ScrollBar.

    主题切换时 :meth:`_apply_theme` 通过 ``_theme_key_*`` 属性决定各颜色
    从 ``theme`` 模块取哪个属性:

    * ``_theme_key_bg = 'BG_PANEL'``
    * ``_theme_key_trough = 'BG_INPUT'``
    * ``_theme_key_active = 'BG_HOVER'``
    """

    # 主题键 —— 子类可覆盖, 或在实例上直接赋值来改变主题刷新来源。
    _theme_key_bg: str = 'BG_PANEL'
    _theme_key_trough: str = 'BG_INPUT'
    _theme_key_active: str = 'BG_HOVER'

    # 滑块最小像素, 保证始终可拖拽
    _MIN_SLIDER_PX = 20

    def __init__(
        self,
        parent: tk.Widget,
        *,
        orient: Literal["horizontal", "vertical"] = "vertical",
        command: Callable[..., Any] | str = "",
        bg: str = "",
        autohidden: bool = True,
        troughcolor: str | None = None,
        activebackground: str | None = None,
        width: int = 10,
        **kwargs: Any,
    ) -> None:
        self._orient = orient
        # command: 空串或无 callable 时设 None, 其余存 callable
        self._command: Callable[..., Any] | None = (
            command if callable(command) else None
        )
        self._autohidden = autohidden
        self._explicit_bg = bool(bg)
        self._width = width

        # --- 颜色 ---
        self._slider_color = bg or getattr(theme, self._theme_key_bg)
        self._trough_color = (
            troughcolor if troughcolor is not None
            else getattr(theme, self._theme_key_trough)
        )
        self._active_color = (
            activebackground if activebackground is not None
            else getattr(theme, self._theme_key_active)
        )

        # --- 滚动状态 ---
        self._first = 0.0
        self._last = 1.0
        self._widget_size = 100          # 当前可滚动方向像素 (垂直=高, 水平=宽)
        self._slider_pos = 0             # 滑块在 _widget_size 中的像素偏移
        self._slider_sz = self._MIN_SLIDER_PX  # 滑块像素大小

        # --- 拖拽状态 ---
        self._dragging = False
        self._drag_offset = 0

        # --- autohide 缓存 ---
        self._saved_pack: dict[str, Any] = {}

        # ---------- 构建 Frame ----------
        frame_kw: dict[str, Any] = {
            'highlightthickness': 0,
            'bd': 0,
            'relief': 'flat',
        }
        # 垂直: 固定 width, 水平: 固定 height
        if orient == 'vertical':
            frame_kw['width'] = width
        else:
            frame_kw['height'] = width
        super().__init__(parent, **frame_kw)
        # 固定 Frame 尺寸: 避免包传播 (pack_propagate 默认 True) 让 Canvas
        # 默认 1×1 的请求尺寸撑开 Frame, 导致 width/height 被忽略。
        self.pack_propagate(False)

        # --- 内部 Canvas (绘制区域) ---
        self._canvas = tk.Canvas(self, highlightthickness=0, bd=0)
        self._canvas.pack(fill=tk.BOTH, expand=True)

        # --- 事件 ---
        self._canvas.bind('<Configure>', self._on_configure)
        self._canvas.bind('<Button-1>', self._on_press)
        self._canvas.bind('<B1-Motion>', self._on_drag)
        self._canvas.bind('<ButtonRelease-1>', self._on_release)
        self._canvas.bind('<MouseWheel>', self._on_wheel)

        # 初绘
        self._draw()

    # ==================================================================
    # 公开 API
    # ==================================================================

    def set(self, first: float | str, last: float | str) -> None:
        """被控制 widget 在视图变化时调用 (例如 via yscrollcommand).

        更新滑块位置/大小, 不转发 command (与标准 :class:`tk.Scrollbar`
        协议一致)。
        """
        f_first = float(first)
        f_last = float(last)
        self._first = f_first
        self._last = f_last
        self._draw()
        if self._autohidden:
            self._apply_autohide()

    def get(self) -> tuple[float, float]:
        """返回当前 (first, last)."""
        return (self._first, self._last)

    # ==================================================================
    # config / cget (拦截自定义选项)
    # ==================================================================

    def config(self, **kwargs: Any) -> Any:  # type: ignore[override]
        scrollbar_opts: dict[str, Any] = {}
        for key in (
            'command', 'bg', 'troughcolor', 'activebackground',
            'orient', 'autohidden', 'width',
        ):
            if key in kwargs:
                scrollbar_opts[key] = kwargs.pop(key)
        if scrollbar_opts:
            self._apply_config(scrollbar_opts)
        if kwargs:
            super().config(**kwargs)

    configure = config  # type: ignore[assignment]

    def cget(self, key: str) -> Any:  # type: ignore[override]
        custom: dict[str, Any] = {
            'command': self._command if self._command else '',
            'bg': self._slider_color,
            'troughcolor': self._trough_color,
            'activebackground': self._active_color,
            'orient': self._orient,
            'autohidden': self._autohidden,
            'width': str(self._width),
            'relief': 'flat',
            'bd': '0',
            'highlightthickness': '0',
        }
        if key in custom:
            return custom[key]
        return super().cget(key)

    # ==================================================================
    # 绘制
    # ==================================================================

    def _on_configure(self, event: tk.Event) -> None:
        sz = event.height if self._orient == 'vertical' else event.width
        self._widget_size = sz
        self._draw()

    def _draw(self) -> None:
        cw = self._canvas.winfo_width()
        ch = self._canvas.winfo_height()
        if cw < 2 or ch < 2:
            return

        size = ch if self._orient == 'vertical' else cw
        self._widget_size = size
        visible = self._last - self._first
        slider_sz = max(self._MIN_SLIDER_PX, int(size * visible))
        # first 可能略小于 0（浮点边界），clamp 处理
        slider_pos = max(0, int(size * self._first))
        # 超界保护
        if slider_pos + slider_sz > size:
            slider_pos = max(0, size - slider_sz)

        self._slider_pos = slider_pos
        self._slider_sz = slider_sz

        self._canvas.delete('all')

        if self._orient == 'vertical':
            # 滑道
            self._canvas.create_rectangle(
                0, 0, cw, ch, fill=self._trough_color, outline='',
            )
            # 滑块
            self._canvas.create_rectangle(
                1, slider_pos, cw - 1, slider_pos + slider_sz,
                fill=self._slider_color, outline='',
                tags=('slider',),
            )
        else:
            self._canvas.create_rectangle(
                0, 0, cw, ch, fill=self._trough_color, outline='',
            )
            self._canvas.create_rectangle(
                slider_pos, 1, slider_pos + slider_sz, ch - 1,
                fill=self._slider_color, outline='',
                tags=('slider',),
            )

    # ==================================================================
    # 鼠标事件
    # ==================================================================

    def _get_pos(self, event: tk.Event) -> int:
        return event.y if self._orient == 'vertical' else event.x

    def _on_press(self, event: tk.Event) -> None:
        pos = self._get_pos(event)
        if self._slider_pos <= pos <= self._slider_pos + self._slider_sz:
            # 开始拖拽
            self._dragging = True
            self._drag_offset = pos - self._slider_pos
        else:
            # 滑道点击 → 翻页
            direction = -1 if pos < self._slider_pos else 1
            if self._command is not None:
                try:
                    self._command("scroll", direction, "pages")
                except Exception:
                    pass

    def _on_drag(self, event: tk.Event) -> None:
        if not self._dragging:
            return
        pos = self._get_pos(event)
        new_start = pos - self._drag_offset
        visible = self._last - self._first
        # 归一化到 [0, 1-visible]
        new_first = new_start / max(1, self._widget_size)
        new_first = max(0.0, min(1.0 - max(visible, 0.01), new_first))
        if self._command is not None:
            try:
                self._command("moveto", str(new_first))
            except Exception:
                pass

    def _on_release(self, event: tk.Event) -> None:
        self._dragging = False

    def _on_wheel(self, event: tk.Event) -> None:
        if self._command is not None:
            delta = -1 if event.delta > 0 else 1
            try:
                self._command("scroll", delta, "units")
            except Exception:
                pass

    # ==================================================================
    # 自动隐藏
    # ==================================================================

    def _apply_autohide(self) -> None:
        try:
            is_mapped = bool(self.winfo_ismapped())
        except tk.TclError:
            return
        needs_scroll = not (self._first <= 0.0 and self._last >= 1.0)

        if needs_scroll and not is_mapped:
            if self._saved_pack:
                try:
                    self.pack(**self._saved_pack)
                except tk.TclError:
                    pass
        elif not needs_scroll and is_mapped:
            try:
                info = self.pack_info()
            except tk.TclError:
                return
            self._saved_pack = {k: v for k, v in info.items() if k != "in"}
            try:
                self.pack_forget()
            except tk.TclError:
                pass

    # ==================================================================
    # 主题刷新
    # ==================================================================

    def _apply_theme(self) -> None:
        if not self._explicit_bg:
            self._slider_color = getattr(theme, self._theme_key_bg)
        self._trough_color = getattr(theme, self._theme_key_trough)
        self._active_color = getattr(theme, self._theme_key_active)
        self._draw()

    # ==================================================================
    # 内部 option 设置
    # ==================================================================

    def _apply_config(self, opts: dict[str, Any]) -> None:
        if 'command' in opts:
            cmd = opts.pop('command')
            self._command = cmd if callable(cmd) else None
        if 'bg' in opts:
            self._slider_color = opts.pop('bg')
            self._explicit_bg = True
        if 'troughcolor' in opts:
            self._trough_color = opts.pop('troughcolor')
        if 'activebackground' in opts:
            self._active_color = opts.pop('activebackground')
        if 'orient' in opts:
            self._orient = opts.pop('orient')
        if 'autohidden' in opts:
            self._autohidden = opts.pop('autohidden')
        if 'width' in opts:
            w = opts.pop('width')
            self._width = w
            if self._orient == 'vertical':
                super().config(width=w)
            else:
                super().config(height=w)
        self._draw()


__all__ = ["UScrollBar"]
