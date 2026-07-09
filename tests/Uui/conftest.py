"""``modules.Uui`` 共享测试 fixtures 与 skip 条件。"""
from __future__ import annotations

import tkinter as tk

import pytest


def _has_display() -> bool:
    """Tk 在无 DISPLAY (Linux headless) / 无窗口系统时会失败.

    Windows / macOS 一般总能起一个 Tk root; 真正的失败是 import 或
    第一次 ``Tk()`` 抛 TclError, 我们用 try/except 在 fixture 里
    探测, 探测失败时 skip 整套测试。
    """

    try:
        root = tk.Tk()
    except tk.TclError:
        return False
    try:
        root.withdraw()
        return True
    finally:
        try:
            root.destroy()
        except tk.TclError:
            pass


# 提前探测一次; 如果无 GUI, 整个模块 skip, 不让单测因
# 反复 try/except Tk() 拖慢。
_skip_reason: str = ""
if not _has_display():
    _skip_reason = "no Tk display available in this environment"


skip_without_tk = pytest.mark.skipif(
    bool(_skip_reason), reason=_skip_reason or "Tk unavailable",
)


@pytest.fixture
def root():
    """每个用例一个 Tk root, withdraw 避免抢焦点; 用例结束自动销毁.

    withdrawn 状态下子 widget 的 ``winfo_ismapped()`` 永远返回 0,
    所以测几何属性 (mapped/visible) 时请用 :func:`visible_root`。
    """

    r = tk.Tk()
    r.withdraw()
    try:
        yield r
    finally:
        try:
            r.destroy()
        except tk.TclError:
            pass


@pytest.fixture
def visible_root():
    """deiconified + offscreen 的 Tk root, 子 widget 报告 ``ismapped=True``.

    用 1x1 像素 + 远屏坐标 + ``overrideredirect`` 让窗口不抢用户焦点
    也不出现在任务栏, 但 Tk 端仍把子 widget 当作"已映射" — 适合需要
    测 ``pack_forget`` / 真实可见性的场景, 例如 :class:`UScrollBar`
    的 autohide 行为。
    """

    r = tk.Tk()
    r.geometry("1x1+10000+10000")
    try:
        r.overrideredirect(True)
    except tk.TclError:
        pass
    r.update_idletasks()
    try:
        yield r
    finally:
        try:
            r.destroy()
        except tk.TclError:
            pass
