# -*- coding: utf-8 -*-
"""``modules.Uui.widgets.tree_canvas`` 的烟囱测试。

本测试在真实 Tk root 上构造一个 :class:`TreeCanvas`, 验证:

* ``add_node`` / ``clear`` / ``set_selected`` / ``set_open`` 的状态机
* ``on_select`` / ``on_activate`` / ``on_toggle`` 三个回调的触发
* 选中节点在 :meth:`clear` 后被清空
* :meth:`see` 不抛异常
* 主题刷新不破坏状态

如果环境没有 Tk, 整模块会被 :func:`skip_without_tk` 跳过 (CI headless)。
"""

from __future__ import annotations

import tkinter as tk
from typing import List, Tuple

import pytest

from modules.Uui.widgets.tree_canvas import TreeCanvas
from tests.Uui.conftest import skip_without_tk


pytestmark = skip_without_tk


# ----------------------------------------------------------------------
# Fixtures
# ----------------------------------------------------------------------


@pytest.fixture
def hooks() -> dict:
    """空的事件收集 dict — 多个 fixture 共享同一份 hooks 时合并用."""

    return {"selects": [], "activates": [], "toggles": []}


@pytest.fixture
def tree(root, hooks) -> TreeCanvas:
    """构造一个简单的 3 节点树: root -> {a, b}, a -> {a1}.

    回调写入 :func:`hooks` fixture 共享的 dict; 单独要 tree 时只取
    ``tree``, 单独要事件记录时只取 ``hooks``。
    """

    def on_select(iid):
        hooks["selects"].append(iid)

    def on_activate(iid):
        hooks["activates"].append(iid)

    def on_toggle(iid, is_open):
        hooks["toggles"].append((iid, is_open))

    labels = {"root": "Root", "a": "A", "b": "B", "a1": "A1"}
    tree = TreeCanvas(
        root,
        row_text=lambda iid: labels[iid],
        on_select=on_select,
        on_activate=on_activate,
        on_toggle=on_toggle,
    )
    tree.pack(fill=tk.BOTH, expand=True)
    tree.add_node("root", None, is_open=True)
    tree.add_node("a", "root")
    tree.add_node("b", "root")
    tree.add_node("a1", "a")

    # 让 Tk 完成一次 layout, 否则 winfo_width 之类的可能是 1.
    root.update_idletasks()
    return tree


# ----------------------------------------------------------------------
# 状态机
# ----------------------------------------------------------------------


class TestNodeModel:
    """``add_node`` / ``clear`` / ``exists`` / ``is_open`` 的纯状态测试."""

    def test_add_root(self, root):
        tree = TreeCanvas(root, row_text=lambda iid: iid)
        tree.add_node("r", None)
        assert tree.exists("r")
        assert tree.is_open("r") is False

    def test_add_with_is_open(self, root):
        tree = TreeCanvas(root, row_text=lambda iid: iid)
        tree.add_node("r", None, is_open=True)
        assert tree.is_open("r") is True

    def test_add_nested(self, root):
        tree = TreeCanvas(root, row_text=lambda iid: iid)
        tree.add_node("r", None, is_open=True)
        tree.add_node("c", "r")
        assert tree.exists("c")
        assert tree.is_open("r") is True

    def test_add_duplicate_is_noop(self, root):
        tree = TreeCanvas(root, row_text=lambda iid: iid)
        tree.add_node("r", None, is_open=True)
        tree.add_node("c", "r")
        # 重复添加 c 不应改变状态, 也不应抛异常
        tree.add_node("c", "r")
        assert tree.exists("c")

    def test_add_orphan_raises(self, root):
        tree = TreeCanvas(root, row_text=lambda iid: iid)
        # 父节点不存在时必须报错, 否则会形成永远不可见的孤儿节点。
        with pytest.raises(ValueError):
            tree.add_node("orphan", "ghost")

    def test_clear_removes_all(self, root):
        tree = TreeCanvas(root, row_text=lambda iid: iid)
        tree.add_node("r", None, is_open=True)
        tree.add_node("c", "r")
        tree.set_selected("c")
        tree.clear()
        assert tree.exists("r") is False
        assert tree.exists("c") is False
        assert tree.get_selected() is None

    def test_remove_node_removes_descendants(self, root):
        tree = TreeCanvas(root, row_text=lambda iid: iid)
        tree.add_node("r", None, is_open=True)
        tree.add_node("a", "r")
        tree.add_node("a1", "a")
        tree.add_node("a2", "a")
        tree.add_node("b", "r")
        tree.remove_node("a")
        assert tree.exists("a") is False
        assert tree.exists("a1") is False
        assert tree.exists("a2") is False
        assert tree.exists("b") is True
        assert tree.exists("r") is True


# ----------------------------------------------------------------------
# set_open / toggle
# ----------------------------------------------------------------------


class TestOpenClose:
    def test_set_open_true(self, tree, hooks):
        tree.set_open("a", True)
        assert tree.is_open("a") is True
        assert ("a", True) in hooks["toggles"]

    def test_set_open_false_fires_toggle(self, tree, hooks):
        tree.set_open("a", True)
        tree.set_open("a", False)
        assert tree.is_open("a") is False
        toggles_for_a = [t for t in hooks["toggles"] if t[0] == "a"]
        assert (True,) in [t[1:] for t in toggles_for_a]
        assert False in [t[1] for t in toggles_for_a]

    def test_set_open_idempotent(self, tree, hooks):
        tree.set_open("a", True)
        hooks["toggles"].clear()
        tree.set_open("a", True)  # 已经是 True
        assert hooks["toggles"] == []  # 不应再触发

    def test_set_open_can_fire_toggle_off(self, tree):
        # 关键交互: 关闭一个父节点后, 其下的选中节点应被取消选中
        # (避免"看不见的选中"导致 on_select 错乱)。
        tree.set_open("a", True)
        tree.set_selected("a1")
        assert tree.get_selected() == "a1"
        tree.set_open("a", False)
        assert tree.get_selected() is None


# ----------------------------------------------------------------------
# 选中
# ----------------------------------------------------------------------


class TestSelection:
    def test_set_selected_basic(self, tree, hooks):
        tree.set_selected("a")
        assert tree.get_selected() == "a"
        assert "a" in hooks["selects"]

    def test_set_selected_hidden_blocked(self, tree, hooks):
        # 'a1' 在 'a' 关闭时不可见, 不应能被选中。
        assert tree.is_open("a") is False
        tree.set_selected("a1")
        assert tree.get_selected() is None
        assert hooks["selects"] == []

    def test_set_selected_after_open_succeeds(self, tree, hooks):
        tree.set_open("a", True)
        tree.set_selected("a1")
        assert tree.get_selected() == "a1"
        assert "a1" in hooks["selects"]

    def test_set_selected_none_clears(self, tree):
        tree.set_selected("a")
        tree.set_selected(None)
        assert tree.get_selected() is None

    def test_set_selected_fire_off(self, tree, hooks):
        tree.set_selected("a", fire=False)
        assert tree.get_selected() == "a"
        assert hooks["selects"] == []  # fire=False 抑制回调


# ----------------------------------------------------------------------
# identify_row / see
# ----------------------------------------------------------------------


class TestGeometry:
    def test_identify_row_finds_visible(self, tree):
        # 'root' 位于 y=0 (它在最上面), 'a' 在 y=row_height, 'b' 在之后。
        assert tree.identify_row(0) == "root"
        assert tree.identify_row(tree._row_height) == "a"
        # row 区间是 [y, y+row_height), 所以 y+row_height-1 仍是该行。
        assert tree.identify_row(2 * tree._row_height - 1) == "a"

    def test_identify_row_returns_none_below(self, tree):
        # 越界返回 None, 不抛异常。
        assert tree.identify_row(10_000) is None
        assert tree.identify_row(-1) is None

    def test_see_does_not_raise(self, tree):
        # see 不可见节点应安全跳过。
        tree.see("ghost")
        tree.see("a1")  # 'a' 关闭, a1 不可见
        # 可见节点也不应抛
        tree.see("a")


# ----------------------------------------------------------------------
# 主题刷新
# ----------------------------------------------------------------------


class TestTheme:
    def test_apply_theme_preserves_state(self, tree, hooks):
        tree.set_open("a", True)
        tree.set_selected("a1")
        sel_before = tree.get_selected()
        open_before = dict(
            (iid, tree.is_open(iid)) for iid in ("root", "a", "b", "a1")
        )
        # 主题刷新不应破坏状态。
        tree._apply_theme()
        assert tree.get_selected() == sel_before
        for iid, was_open in open_before.items():
            assert tree.is_open(iid) == was_open


# ----------------------------------------------------------------------
# 数据载荷 (iid -> 业务对象的反向查表)
# ----------------------------------------------------------------------


class TestNodeData:
    def test_data_roundtrip(self, root):
        tree = TreeCanvas(root, row_text=lambda iid: iid)
        payload = {"path": "/tmp/foo", "kind": "file"}
        tree.add_node("f", None, data=payload)
        assert tree.node_data("f") is payload

    def test_data_none_default(self, root):
        tree = TreeCanvas(root, row_text=lambda iid: iid)
        tree.add_node("f", None)
        assert tree.node_data("f") is None

    def test_data_unknown_iid_returns_none(self, root):
        tree = TreeCanvas(root, row_text=lambda iid: iid)
        assert tree.node_data("ghost") is None
