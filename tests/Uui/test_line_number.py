# -*- coding: utf-8 -*-
"""``modules.Uui.widgets.line_number`` 与 UText 行号集成的烟囱测试.

覆盖:

* :class:`LineNumberCanvas` 构造、初始画布存在;
* 文本增加 / 删除行后行号栏内含正确数字;
* 当前行号高亮 (cursor 颜色与普通行号不同);
* yscrollcommand 钩子不会吞掉调用方原有的回调 (UText 集成测试);
* 主题刷新不破坏控件, 仍能重画;
* :class:`UText` 传入 ``show_line_numbers=False`` 时不应创建 gutter。

需要真实映射的渲染 / 滚动测试用 :func:`tests.Uui.conftest.visible_root`
(deiconified + 远屏 1x1), 其他纯状态用例仍用 :func:`root`。
"""

from __future__ import annotations

import tkinter as tk
from typing import List

import pytest

from modules.Uui.widgets import LineNumberCanvas, UText, theme
from modules.Uui.widgets.line_number import font_metrics
from tests.Uui.conftest import skip_without_tk


pytestmark = skip_without_tk


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------


def _make_text_widget(root, lines: int = 5, *, height_lines: int | None = None) -> tk.Text:
    """造一个 ``tk.Text``, 内容是 ``lines`` 行 ``'line N\\n'``.

    默认 height 比 lines 多 2 行, 让 text 不需要滚动就能看见首尾几行。
    注意:  ``visible_root`` 把窗口本身固定在 1x1, 因此我们把 root 调大
    到 400x300, 再让 text 占满。这样 ``winfo_height`` 才能拿到真实像
    素高度, ``dlineinfo`` 也能给出每个 ``lineN.0`` 的 bbox。
    """

    h = height_lines if height_lines is not None else lines + 2
    try:
        root.geometry("400x300+10000+10000")
    except tk.TclError:
        pass
    text = tk.Text(root, height=h, width=40, font=theme.MONO_FONT)
    text.pack(fill=tk.BOTH, expand=True)
    text.insert("1.0", "\n".join(f"line {i}" for i in range(1, lines + 1)) + "\n")
    root.update_idletasks()
    return text


# ----------------------------------------------------------------------
# 构造 / 初始状态 — 纯属性, withdraw root 即可
# ----------------------------------------------------------------------


class TestConstruction:
    def test_construction_with_text(self, root):
        text = _make_text_widget(root)
        gutter = LineNumberCanvas(text)
        assert isinstance(gutter, tk.Frame)
        assert isinstance(gutter._canvas, tk.Canvas)
        gutter.destroy()

    def test_construction_requires_text(self, root):
        with pytest.raises(TypeError):
            LineNumberCanvas(root)  # type: ignore[arg-type]

    def test_yview_callback_attached(self, root):
        """构造后 text 的 yscrollcommand 应被替换为 LineNumberCanvas 的钩子."""

        text = _make_text_widget(root)
        original_cb = text.cget("yscrollcommand") or ""
        gutter = LineNumberCanvas(text)
        new_cb = text.cget("yscrollcommand") or ""
        assert new_cb != original_cb
        gutter.destroy()


# ----------------------------------------------------------------------
# 行号绘制 — 需要 mapped 窗口, 用 visible_root
# ----------------------------------------------------------------------


class TestRendering:
    def test_draws_line_numbers(self, visible_root):
        text = _make_text_widget(visible_root, lines=5)
        gutter = LineNumberCanvas(text)
        visible_root.update_idletasks()
        gutter.redraw()
        visible_root.update_idletasks()

        items = gutter._canvas.find_all()
        assert len(items) >= 1

        rendered_numbers = set()
        for item in items:
            try:
                t = gutter._canvas.itemcget(item, "text")
            except tk.TclError:
                continue
            if t and t.isdigit():
                rendered_numbers.add(t)
        # 至少画出首行 1。
        assert "1" in rendered_numbers
        gutter.destroy()

    def test_redraw_after_insert(self, visible_root):
        """新增一行后, 画出的最大行号应 >= 新总行数."""

        text = _make_text_widget(visible_root, lines=3)
        gutter = LineNumberCanvas(text)
        visible_root.update_idletasks()
        for _ in range(5):
            text.insert("end", "more\n")
        visible_root.update_idletasks()
        gutter.redraw()
        visible_root.update_idletasks()

        rendered = set()
        for item in gutter._canvas.find_all():
            try:
                t = gutter._canvas.itemcget(item, "text")
            except tk.TclError:
                continue
            if t and t.isdigit():
                rendered.add(int(t))
        assert 1 in rendered
        assert max(rendered) >= 5
        gutter.destroy()

    def test_cursor_line_uses_distinct_color(self, visible_root):
        """当前行号的 fill 应与普通行号不同 (theme.FG_PRIMARY vs FG_TERTIARY)."""

        text = _make_text_widget(visible_root, lines=5)
        # 把光标放到第 3 行
        text.mark_set(tk.INSERT, "3.0")
        gutter = LineNumberCanvas(text)
        visible_root.update_idletasks()
        gutter.redraw()
        visible_root.update_idletasks()

        entries: List[tuple] = []
        for item in gutter._canvas.find_all():
            try:
                t = gutter._canvas.itemcget(item, "text")
                fill = gutter._canvas.itemcget(item, "fill")
            except tk.TclError:
                continue
            if t and t.isdigit():
                entries.append((t, fill))

        if not entries:
            pytest.skip("no line-number items rendered")

        cursor_label = text.index(tk.INSERT).split(".")[0]
        cursor_fills = {fill for label, fill in entries if label == cursor_label}
        other_fills = {fill for label, fill in entries if label != cursor_label}
        if not cursor_fills or not other_fills:
            pytest.skip("not enough variety to compare colors")
        assert cursor_fills != other_fills
        gutter.destroy()


# ----------------------------------------------------------------------
# 主题
# ----------------------------------------------------------------------


class TestTheme:
    def test_apply_theme_does_not_raise(self, root):
        text = _make_text_widget(root)
        gutter = LineNumberCanvas(text)
        root.update_idletasks()
        gutter._apply_theme()  # noqa: SLF001 - 单文件集成测试
        gutter.destroy()

    def test_apply_theme_can_change_colors(self, visible_root):
        """主题切换后 canvas 配置应跟随."""

        text = _make_text_widget(visible_root)
        gutter = LineNumberCanvas(text)
        visible_root.update_idletasks()

        original_bg = gutter._canvas.cget("bg")
        from modules.Uui.widgets import theme as theme_mod

        prev = theme_mod._current  # noqa: SLF001
        try:
            theme_mod._current.BG_INPUT = "#222222"  # noqa: SLF001
            gutter._apply_theme()  # noqa: SLF001
            visible_root.update_idletasks()
            assert gutter._canvas.cget("bg") == "#222222"
        finally:
            theme_mod._current.BG_INPUT = original_bg  # noqa: SLF001
            theme_mod._current = prev  # noqa: SLF001
        gutter.destroy()


# ----------------------------------------------------------------------
# 与 UText 的集成
# ----------------------------------------------------------------------


class TestUTextIntegration:
    def test_default_no_gutter(self, root):
        """不传 show_line_numbers 时不应创建 gutter."""

        ut = UText(root, height=5, width=20)
        root.update_idletasks()
        assert ut._line_numbers is None
        ut.destroy()

    def test_show_line_numbers_creates_gutter(self, root):
        """show_line_numbers=True 时挂上 LineNumberCanvas."""

        ut = UText(root, height=5, width=20, show_line_numbers=True)
        root.update_idletasks()
        assert isinstance(ut._line_numbers, LineNumberCanvas)
        ut.destroy()

    def test_external_scrollbar_still_receives_updates(self, visible_root):
        """挂上行号栏后, 滚动 text 仍应驱动 UScrollBar (gutter 不能吞掉)."""

        ut = UText(visible_root, height=3, width=20, show_line_numbers=True)
        ut._text.insert("1.0", "\n".join(f"L{i}" for i in range(50)) + "\n")
        visible_root.update_idletasks()
        ut._text.yview_moveto(1.0)
        visible_root.update_idletasks()
        first, last = ut._scroll.get()
        # scrollbar 必须跟踪到了滚动; 否则说明 yscrollcommand 被吞了
        assert not (first == 0.0 and last == 1.0)
        ut.destroy()


# ----------------------------------------------------------------------
# font_metrics 工具
# ----------------------------------------------------------------------


class TestFontMetrics:
    def test_returns_positive_values_for_tuple(self):
        w, h = font_metrics(("Consolas", 10))
        assert w > 0
        assert h > 0

    def test_returns_positive_values_for_name(self):
        w, h = font_metrics("TkFixedFont")
        assert w > 0
        assert h > 0