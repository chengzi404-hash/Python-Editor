"""``modules.Uui.widgets.line_number`` — 基于 :class:`tk.Canvas` 的代码行号栏.

设计动机
========

Tk 自带的 :class:`tk.Text` 不带行号; 在编辑器侧栏画行号常见做法有
两条路:

1. 用另一个 :class:`tk.Text` 当 gutter, 把行号当普通文本插入 — 实现
   简单, 但行高 / 字体跟随、性能、滚动同步都靠 :class:`tk.Text` 的
   既有逻辑, 难以微调 (例如改行号颜色 / 高亮当前行 / 改间距);
2. 用 :class:`tk.Canvas` 自己画 — 控制粒度更细, 主题切换 / 行高 /
   当前行高亮都自己说了算, 性能也稳。

本模块走第 2 条路。提供 :class:`LineNumberCanvas` 控件, 由
:class:`UText` 在 ``show_line_numbers=True`` 时挂到 text widget 左
侧, 并通过 ``yscrollcommand`` 与 ``<<Modified>>`` 事件双向同步。

与 :class:`UText` 的协议
-----------------------

:class:`LineNumberCanvas` 在构造时拿到被观察的 :class:`tk.Text`,
然后:

* 把自己的 :meth:`redraw` 挂到 text 的 ``yscrollcommand`` 钩子上 —
  text 一滚动就重画;
* 监听 ``<<Modified>>`` 事件, 每次文本变更后清掉 modified flag 并
  触发重画;
* 监听 ``<ButtonRelease-1>`` / ``<KeyRelease>`` — 这两类事件不会改
  ``modified`` flag 但会影响当前行 / 可见区;
* 监听 ``<Configure>`` — text 宽高变化时 (例如切语言 / 调字号) 重算
  行高与可视行号范围。

行号宽度按当前最大行号位数自动留白, 多 1 位留 2 位的策略 (10 行只
画 1 位时仍按 2 位宽度画) 避免"再加 1 行后 gutter 突然变宽、把光标
左右推动"。

主题
----

行号颜色取 ``theme.FG_TERTIARY``, 当前行号颜色取 ``theme.FG_PRIMARY``,
gutter 背景取 ``theme.BG_INPUT`` (与 text 一致, 视觉上像同一片区域)。
主题刷新时 :meth:`_apply_theme` 重画一次。
"""

from __future__ import annotations

import contextlib
import tkinter as tk

from . import theme


class LineNumberCanvas(tk.Frame):
    """基于 Canvas 的代码行号栏.

    必须传入一个已创建好的 :class:`tk.Text` 控件, 本控件会自动跟随其
    滚动、文本变化与光标位置。

    参数
    ----

    text
        被观察的 :class:`tk.Text` 控件 (一般是 :class:`UText._text`)。
    pad_x
        行号文字与右侧分隔线的水平内边距 (像素)。
    min_width
        gutter 最小宽度 (像素), 防止文件为空时宽度缩成 0。
    """

    # 行号位数 → 像素宽度的经验值 (按 Consolas 10pt 估算);
    # 实际宽度由 Canvas 根据当前字体度量自动调整, 这里只是下限保护。
    _CHARS_PER_LEVEL = 1

    def __init__(
        self,
        text: tk.Text,
        *,
        pad_x: int = 6,
        min_width: int = 28,
        **kwargs,
    ) -> None:
        bg = kwargs.pop("bg", theme.BG_INPUT)
        super().__init__(text.master, bg=bg, highlightthickness=0, bd=0, **kwargs)

        if not isinstance(text, tk.Text):
            raise TypeError(
                f"LineNumberCanvas requires a tk.Text, got {type(text).__name__}"
            )
        self._text = text
        self._pad_x = pad_x
        self._min_width = min_width

        self._canvas = tk.Canvas(
            self,
            bg=theme.BG_INPUT,
            highlightthickness=0,
            bd=0,
        )
        self._canvas.pack(side=tk.LEFT, fill=tk.Y, expand=False)
        # 把 Canvas 撑成与 text 等高; 真实可用高度在 _redraw 里通过
        # winfo_height 读出, 这里只是让 pack 不去收缩。
        self._canvas.configure(height=1)

        # 防抖: <Configure> 在窗口拖动时会高频触发, 用一个 flag + after
        # 把多次重排合并成一次 _redraw。
        self._redraw_pending = False

        # 缓存: 当前最大行号; 文本行数变化才重算宽度, 避免每次重画都
        # 重新布局。
        self._last_total_lines = -1
        self._last_digit_count = -1

        # 记下 text 原有的 yscrollcommand, 在我们的钩子里转发, 这样
        # 调用方之前挂的 scrollbar 不会被吞掉。挂不到时降级成空回调。
        self._external_scroll_cb = text.cget("yscrollcommand") or ""
        self._text.configure(
            yscrollcommand=self._on_text_yview,
        )

        # --- 事件订阅 ---
        # <<Modified>> 在 set / delete / insert 后置 flag; 我们读完后
        # 立刻 reset 让 Tk 继续在下次变更时再次置 flag。
        self._text.bind("<<Modified>>", self._on_text_modified, add="+")
        self._text.bind("<KeyRelease>", self._on_cursor_change, add="+")
        self._text.bind("<ButtonRelease-1>", self._on_cursor_change, add="+")
        self._text.bind("<ButtonRelease-2>", self._on_cursor_change, add="+")
        self._text.bind("<Configure>", self._on_text_configure, add="+")

        # 鼠标滚轮: 直接转发到 text widget, 让用户即使把鼠标移到
        # gutter 上也能滚动编辑区。
        self._canvas.bind("<MouseWheel>", self._on_mousewheel, add="+")
        self._canvas.bind(
            "<Button-4>",
            lambda e: self._text.yview_scroll(-1, "units"),
            add="+",
        )
        self._canvas.bind(
            "<Button-5>",
            lambda e: self._text.yview_scroll(1, "units"),
            add="+",
        )

        # 第一次 layout 完成后再画 — 此时 text 已有 winfo_width / height。
        self.after_idle(self._redraw)

    # ==================================================================
    # 公开 API
    # ==================================================================

    def redraw(self) -> None:
        """强制重画一次行号. 等价于内部 :meth:`_redraw`, 但放在公开
        API 让外部 (例如 UText 在切换主题后) 显式调用。
        """

        self._redraw()

    # ==================================================================
    # 事件回调
    # ==================================================================

    def _on_text_yview(self, *args) -> None:
        """text 的 yscrollcommand 钩子: 同时驱动滚动条 + 行号栏重画."""

        # 转发给原 yscrollcommand (例如 UText 里的 UScrollBar)
        if self._external_scroll_cb:
            try:
                # args 是 (first, last); Tk 协议就是直接 set(*args)
                if callable(self._external_scroll_cb):
                    self._external_scroll_cb(*args)
                else:
                    self._text.tk.call(
                        (self._external_scroll_cb, *args)
                    )
            except Exception:
                # 协议外调用方不应让行号栏把整个 UI 拖崩, 异常吞掉。
                pass
        self._schedule_redraw()

    def _on_text_modified(self, _event: tk.Event) -> None:
        # 必须立即 reset flag, 否则 Tk 不会在下次变更时再次触发。
        with contextlib.suppress(tk.TclError):
            self._text.edit_modified(False)
        self._schedule_redraw()

    def _on_cursor_change(self, _event: tk.Event) -> None:
        # 光标移动不一定会动 <<Modified>>, 单独触发一次重画以更新
        # 当前行高亮。
        self._schedule_redraw()

    def _on_text_configure(self, _event: tk.Event) -> None:
        # 窗口 / 字号变化都会导致行高变化, 需要重算可见行号范围。
        self._schedule_redraw()

    def _on_mousewheel(self, event: tk.Event) -> str | None:
        """把滚轮事件转发给 text widget, 行为与在 text 上滚一致."""

        if not hasattr(event, "delta") or event.delta == 0:
            return None
        # Tk 标准协议: delta > 0 向上滚. 在 Text 上滚动是 "scroll -1 units"
        # 表示向上滚一行 (内容向下移动); 这里保持一致。
        delta = -1 if event.delta > 0 else 1
        try:
            self._text.yview_scroll(delta, "units")
        except tk.TclError:
            return None
        # "break" 让 Tk 停止继续把事件冒泡到外层 (例如 PanedWindow
        # 的滚轮 handler), 否则会出现 "滚一行又被滚回来" 的抖动。
        return "break"

    # ==================================================================
    # 重画
    # ==================================================================

    def _schedule_redraw(self) -> None:
        if self._redraw_pending:
            return
        self._redraw_pending = True
        try:
            self.after_idle(self._flush_redraw)
        except tk.TclError:
            self._redraw_pending = False

    def _flush_redraw(self) -> None:
        self._redraw_pending = False
        self._redraw()

    def _redraw(self) -> None:
        try:
            self._do_redraw()
        except tk.TclError:
            # 控件已销毁; 常见于窗口关闭过程中事件残留。
            pass

    def _do_redraw(self) -> None:
        text = self._text
        canvas = self._canvas

        # 文本尚未布局好 (winfo_* = 1) 时跳过, 等 idle 后再画。
        text_h = text.winfo_height()
        text_w = text.winfo_width()
        if text_h <= 1 or text_w <= 1:
            return

        # 总行数 (含末尾的空行; Tk 的 end 是 "下一行 0 列")
        try:
            total_lines = int(text.index("end-1c").split(".")[0])
        except tk.TclError:
            return
        if total_lines < 1:
            total_lines = 1

        # 当前行号
        try:
            cursor_line = int(text.index(tk.INSERT).split(".")[0])
        except tk.TclError:
            cursor_line = 1

        # 1. 自适应宽度: 按"最大行号的位数"决定 gutter 宽,
        #    但每多 1 位给 2 位的宽度 (避免加 1 行后 gutter 突然变宽
        #    把光标左右推动一格)。
        if total_lines != self._last_total_lines:
            digits = len(str(total_lines))
            # "2 位 → 留 3 位宽" 这种规则用 max(1, ceil(digits * 1.5)) 近似。
            self._last_digit_count = max(2, digits + (1 if digits >= 2 else 0))
            self._last_total_lines = total_lines

        digit_count = self._last_digit_count
        font = text.cget("font")
        try:
            char_w = font_metrics(font)[0]
        except Exception:
            char_w = 8
        target_width = max(
            self._min_width,
            int(digit_count * char_w + self._pad_x * 2 + 1),
        )
        # 把 Canvas 撑到目标宽度, 让分隔线落在右边沿。
        if canvas.winfo_width() != target_width:
            canvas.configure(width=target_width)

        # 2. 可见行号范围: 用 @0,0 / @0,H 拿当前屏上可见的 index。
        try:
            top_idx = text.index("@0,0")
            bot_idx = text.index(f"@0,{text_h}")
        except tk.TclError:
            return
        top_line = int(top_idx.split(".")[0])
        bot_line = int(bot_idx.split(".")[0])
        # bot_idx 可能落在最后一行"之后", 至少显示到 total_lines。
        bot_line = max(bot_line, min(total_lines, top_line))

        # 3. 清画布, 重画
        canvas.delete("all")
        fg_normal = theme.FG_TERTIARY
        fg_cursor = theme.FG_PRIMARY
        bg = theme.BG_INPUT
        border = theme.BORDER
        canvas.configure(bg=bg)

        # 行高 (像素) - 从 text 取首行 bbox。
        line_height = self._line_height(text)
        if line_height <= 0:
            line_height = max(14, int(font_metrics(font)[1]) + 2)

        # 当前 text 滚动的"首行 Y 偏移" (像素, 0 表示内容顶部对齐)。
        self._y_of_line(text, top_line)

        width = target_width
        right = width - self._pad_x

        # 画分隔线 (gutter 与 text 之间的细线)
        canvas.create_line(
            width - 1, 0, width - 1, text_h,
            fill=border, width=1,
        )

        # 画每一行行号
        for line_no in range(top_line, bot_line + 1):
            if line_no > total_lines:
                break
            dline = text.dlineinfo(f"{line_no}.0")
            if not dline:
                continue
            # dlineinfo 返回 (x, y, width, height, baseline)
            _, line_y, _, dh, _ = dline
            # dlineinfo 给的是 text widget 内部坐标, 加上 text padx/pady
            # 等偏移后就是"画到 gutter canvas 上"的 y。
            # gutter 与 text 共享同一滚动, 所以 text 滚动不影响 gutter
            # 的可见位置 — 屏幕坐标一致, 直接用 line_y 即可。
            screen_y = line_y
            if screen_y + dh < 0 or screen_y > text_h:
                continue
            color = fg_cursor if line_no == cursor_line else fg_normal
            canvas.create_text(
                right,
                screen_y + dh / 2,
                text=str(line_no),
                anchor="e",
                fill=color,
                font=font,
            )

    @staticmethod
    def _line_height(text: tk.Text) -> int:
        bbox = text.dlineinfo("1.0")
        if not bbox:
            return 0
        return int(bbox[3])

    @staticmethod
    def _y_of_line(text: tk.Text, line_no: int) -> int:
        bbox = text.dlineinfo(f"{line_no}.0")
        if not bbox:
            return 0
        return int(bbox[1])

    # ==================================================================
    # 主题
    # ==================================================================

    def _apply_theme(self) -> None:
        """主题切换回调: 刷 canvas 颜色 + 触发一次重画."""

        with contextlib.suppress(tk.TclError):
            self.configure(bg=theme.BG_INPUT)
        with contextlib.suppress(tk.TclError):
            self._canvas.configure(bg=theme.BG_INPUT)
        self._redraw()


def font_metrics(font) -> tuple:
    """返回 ``(char_pixel_width, line_pixel_height)`` 的近似值.

    Tk 不暴露字体度量 API (除了 ``measure`` 一个具体字符串); 这里用
    "0" 作为代表字符测量宽度, 高度则用 ``tk.font.Font.metrics``. 后
    者依赖可选的 ``tkinter.font``, 在某些最小 Tk 构建上可能不可用,
    我们在异常分支退回到固定估算值。
    """

    char_w = 8
    line_h = 16
    try:
        # tk.font 在 Tk 8.6+ 默认可用, 但我们不强制依赖。
        from tkinter import font as tkfont

        if isinstance(font, str):
            fnt = tkfont.nametofont(font)
        elif isinstance(font, tuple):
            fnt = tkfont.Font(font=font)
        else:
            fnt = font
        char_w = max(4, int(fnt.measure("0")))
        line_h = max(10, int(fnt.metrics("linespace")))
    except Exception:
        # 兜底: 假定 10pt monospace ≈ 6 × 13 像素
        try:
            size = int(font[1]) if isinstance(font, tuple) and len(font) >= 2 else 10
        except Exception:
            size = 10
        char_w = max(4, int(size * 0.6))
        line_h = max(10, int(size * 1.4))
    return char_w, line_h


__all__ = ["LineNumberCanvas", "font_metrics"]
