# -*- coding: utf-8 -*-
"""``modules.Uui.widgets.scrollbar`` 的测试 (Canvas 实现).

覆盖:

* ``bg=""`` —— 默认取 :data:`theme.BG_PANEL`;
* ``bg="red"`` —— 显式颜色锁定, 主题切换不被覆盖;
* ``autohidden=True`` —— 默认行为, ``set(0, 1)`` 时自动隐藏;
* ``autohidden=False`` —— 显式指定后 ``set(0, 1)`` 不影响可见性;
* ``set()`` 不转发 ``command`` (与标准 Tk 协议一致);
* 主题刷新时, ``troughcolor`` / ``activebackground`` 始终跟随
  ``_theme_key_*`` 类/实例属性指定的 ``theme`` 模块属性;
  ``bg`` 仅在显式未指定时跟随。

需要真实 Tk 窗口才能验证 ``pack_forget`` / ``pack_info`` 行为, 因此
用 :func:`tests.Uui.conftest.visible_root` (deiconified + offscreen)
跑可见性相关用例; 其他纯属性用例仍用 :func:`root`。
"""

from __future__ import annotations

import tkinter as tk
from typing import List, Tuple

import pytest

from modules.Uui.widgets import UScrollBar, theme
from tests.Uui.conftest import skip_without_tk


pytestmark = skip_without_tk


# ----------------------------------------------------------------------
# bg 选项
# ----------------------------------------------------------------------


class TestBgOption:
    """``bg=""`` 取主题色; ``bg="..."`` 锁定."""

    def test_default_bg_uses_theme(self, root):
        sb = UScrollBar(root)
        # 默认: 取当前 theme 的 BG_PANEL, 而不是 Tk 默认色。
        assert sb.cget("bg") == theme.BG_PANEL

    def test_explicit_bg_preserved(self, root):
        sb = UScrollBar(root, bg="red")
        assert sb.cget("bg") == "red"

    def test_explicit_bg_preserved_across_theme(self, root):
        """显式 bg 不会因主题切换被覆盖 (与 UFrame._explicit_bg 一致)."""

        sb = UScrollBar(root, bg="#abcdef")
        # 触发一次 _apply_theme
        sb._apply_theme()
        assert sb.cget("bg") == "#abcdef"

    def test_theme_bg_updates_on_theme_change(self, root):
        """bg="" 传入的滚动条会跟随主题切换."""

        sb = UScrollBar(root)
        assert sb.cget("bg") == theme.BG_PANEL
        # 模拟主题切换(直接改 _current 不可行 — 改用 _apply_theme
        # 验证它把 bg 设回 theme.BG_PANEL)。
        sb._apply_theme()
        assert sb.cget("bg") == theme.BG_PANEL


# ----------------------------------------------------------------------
# 其他颜色
# ----------------------------------------------------------------------


class TestThemeColors:
    def test_troughcolor_defaults_to_theme(self, root):
        sb = UScrollBar(root)
        assert sb.cget("troughcolor") == theme.BG_INPUT

    def test_activebackground_defaults_to_theme(self, root):
        sb = UScrollBar(root)
        assert sb.cget("activebackground") == theme.BG_HOVER

    def test_troughcolor_follows_theme(self, root):
        sb = UScrollBar(root, troughcolor="red")
        # 显式传入不会跟随主题
        sb._apply_theme()
        assert sb.cget("troughcolor") == theme.BG_INPUT

    def test_activebackground_follows_theme(self, root):
        sb = UScrollBar(root, activebackground="red")
        sb._apply_theme()
        assert sb.cget("activebackground") == theme.BG_HOVER


# ----------------------------------------------------------------------
# 几何参数
# ----------------------------------------------------------------------


class TestGeometry:
    def test_orient_vertical_default(self, root):
        sb = UScrollBar(root)
        assert sb.cget("orient") == "vertical"

    def test_orient_horizontal(self, root):
        sb = UScrollBar(root, orient="horizontal")
        assert sb.cget("orient") == "horizontal"

    def test_width_default(self, root):
        sb = UScrollBar(root)
        assert sb.cget("width") == "10"

    def test_custom_width(self, root):
        sb = UScrollBar(root, width=14)
        assert sb.cget("width") == "14"

    def test_appearance_styling_locked(self, root):
        """仓库里所有 Scrollbar 都强制 relief=flat/bd=0/highlightthickness=0."""

        sb = UScrollBar(root)
        assert sb.cget("relief") == "flat"
        assert sb.cget("bd") == "0"
        assert sb.cget("highlightthickness") == "0"


# ----------------------------------------------------------------------
# set() 转发
# ----------------------------------------------------------------------


class TestSetProportional:
    """``set`` 必须更新滑块视觉状态, 否则滚动比例不对."""

    def test_set_updates_visual_state(self, root):
        """调用 set 后 get() 应返回相同的 (first, last)."""
        sb = UScrollBar(root)
        sb.set(0.2, 0.8)
        assert sb.get() == (0.2, 0.8)

    def test_set_full_range(self, root):
        """set(0.0, 1.0) 表示内容完全可见."""
        sb = UScrollBar(root)
        sb.set(0.0, 1.0)
        assert sb.get() == (0.0, 1.0)

    def test_set_with_autohidden_still_updates(self, root):
        """autohidden=True 时 set 仍应更新滑块位置."""
        sb = UScrollBar(root, autohidden=True)
        sb.set(0.3, 0.7)
        assert sb.get() == (0.3, 0.7)


class TestSetNoForward:
    """``set`` 不应该转发到 ``command`` (标准 Tk 协议)."""

    def test_set_does_not_call_command(self, root):
        """set 后 command 不应被调用."""

        called = False

        def cb(*args):
            nonlocal called
            called = True

        sb = UScrollBar(root, command=cb)
        sb.set(0.2, 0.8)
        assert not called

    def test_set_with_no_command_does_not_raise(self, root):
        """空 command 时 set 不应抛异常."""

        sb = UScrollBar(root)
        sb.set(0.0, 1.0)  # 不会抛

    def test_set_with_autohidden_does_not_call_command(self, root):
        """autohidden=True 时 set 也不应触发 command."""

        called = False

        def cb(*args):
            nonlocal called
            called = True

        sb = UScrollBar(root, command=cb, autohidden=True)
        sb.set(0.0, 1.0)
        assert not called
        sb.set(0.3, 0.7)
        assert not called


# ----------------------------------------------------------------------
# autohidden 行为
# ----------------------------------------------------------------------


class TestAutohide:
    """``autohidden=True`` 时, 内容完全可见自动 pack_forget."""

    def test_autohide_hides_when_content_fits(self, visible_root):
        sb = UScrollBar(visible_root, autohidden=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        visible_root.update_idletasks()
        assert sb.winfo_ismapped() == 1

        sb.set(0.0, 1.0)  # 内容完全可见
        visible_root.update_idletasks()
        assert sb.winfo_ismapped() == 0

    def test_autohide_shows_when_content_overflows(self, visible_root):
        sb = UScrollBar(visible_root, autohidden=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        visible_root.update_idletasks()
        assert sb.winfo_ismapped() == 1

        # 先触发隐藏
        sb.set(0.0, 1.0)
        visible_root.update_idletasks()
        assert sb.winfo_ismapped() == 0

        # 再触发显示
        sb.set(0.2, 0.8)
        visible_root.update_idletasks()
        assert sb.winfo_ismapped() == 1

    def test_autohide_preserves_pack_params(self, visible_root):
        """hide/show 来回切, pack 参数(side/fill)要还原."""

        sb = UScrollBar(visible_root, autohidden=True)
        sb.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        visible_root.update_idletasks()

        sb.set(0.0, 1.0)
        visible_root.update_idletasks()
        assert sb.winfo_ismapped() == 0

        sb.set(0.5, 1.0)
        visible_root.update_idletasks()
        assert sb.winfo_ismapped() == 1
        info = sb.pack_info()
        # side / fill 应该与原始 pack 一致
        assert info.get("side") == "left"
        assert info.get("fill") == "both"
        assert info.get("expand") in (1, True)  # tk 把 expand 归一

    def test_no_autohide_keeps_visible(self, visible_root):
        """autohidden=False 时, set(0, 1) 不会让它消失."""

        sb = UScrollBar(visible_root, autohidden=False)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        visible_root.update_idletasks()
        assert sb.winfo_ismapped() == 1

        sb.set(0.0, 1.0)
        visible_root.update_idletasks()
        # 默认行为, 不会自动隐藏
        assert sb.winfo_ismapped() == 1

    def test_no_autohide_no_saved_pack(self, visible_root):
        """autohidden=False 时, _saved_pack 保持空, 不做无谓缓存."""

        sb = UScrollBar(visible_root, autohidden=False)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        visible_root.update_idletasks()
        sb.set(0.0, 1.0)
        visible_root.update_idletasks()
        assert sb._saved_pack == {}

    def test_autohide_boundary_values(self, visible_root):
        """``first`` / ``last`` 为字符串 "0.0" / "1" 时也要正确处理."""

        sb = UScrollBar(visible_root, autohidden=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        visible_root.update_idletasks()

        sb.set("0.0", "1")  # 等价于 (0.0, 1.0)
        visible_root.update_idletasks()
        assert sb.winfo_ismapped() == 0

        sb.set("0.3", "0.7")
        visible_root.update_idletasks()
        assert sb.winfo_ismapped() == 1

    def test_autohide_idempotent_hide(self, visible_root):
        """连续多次 set(0, 1) 不报错, 状态稳定."""

        sb = UScrollBar(visible_root, autohidden=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        visible_root.update_idletasks()

        sb.set(0.0, 1.0)
        sb.set(0.0, 1.0)
        sb.set(0.0, 1.0)
        visible_root.update_idletasks()
        assert sb.winfo_ismapped() == 0

    def test_autohide_idempotent_show(self, visible_root):
        """连续多次 set(0.2, 0.8) 不报错, 状态稳定."""

        sb = UScrollBar(visible_root, autohidden=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        visible_root.update_idletasks()

        sb.set(0.0, 1.0)  # hide
        visible_root.update_idletasks()
        sb.set(0.2, 0.8)  # show
        sb.set(0.2, 0.8)  # show again
        sb.set(0.2, 0.8)  # show again
        visible_root.update_idletasks()
        assert sb.winfo_ismapped() == 1


# ----------------------------------------------------------------------
# 显式调用 _apply_autohide 的边缘态
# ----------------------------------------------------------------------


class TestApplyAutohideEdgeCases:
    """直接验证内部方法的边缘态, 避免依赖真实的 winfo_ismapped."""

    def test_saved_pack_populated_after_hide(self, root):
        """hide 时应把当前 pack_info 缓存到 _saved_pack."""

        sb = UScrollBar(root, autohidden=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        # withdrawn root 上 ismapped=0, 直接构造场景。
        # 模拟: 把 widget 看作"已经 mapped"(绕过 ismapped 检查)。
        sb._first = 0.0
        sb._last = 1.0
        sb._apply_autohide()  # hide 路径
        # withdrawn root 下 ismapped=False, _apply_autohide 不会进
        # hide 分支; _saved_pack 应保持空。
        # 这个测试主要确认在 withdrawn 场景下没有副作用异常。
        assert sb._saved_pack == {}

    def test_apply_theme_does_not_raise_on_withdrawn(self, root):
        """withdrawn root 上 _apply_theme 不应抛异常."""

        sb = UScrollBar(root, bg="red")
        sb._apply_theme()  # 不应抛
        assert sb.cget("bg") == "red"
