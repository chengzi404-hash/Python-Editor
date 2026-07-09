"""``modules.Uui.widgets.settings_nav`` — 设置导航树组件.

基于 :class:`TreeCanvas` 渲染; 自身只负责"把 SettingsSchema 拆成
``scope -> group -> leaf`` 三层并喂给 TreeCanvas", 以及把
TreeCanvas 的 iid 反查成 :class:`NavSelection` 给上层消费。

公开 API 与 ttk.Treeview 时代完全一致:

* :meth:`set_roots` —— 用两个 schema 重建整棵树;
* :meth:`set_selected` —— 程序式跳到指定 scope/group/leaf;
* :meth:`get_selected` —— 当前选中的 :class:`NavSelection`;
* :meth:`set_on_select` / :meth:`set_title` —— 运行时改回调/标题;
* :meth:`_apply_theme` —— 主题切换时由
  :func:`modules.Uui.widgets.theme.apply_theme_recursive` 递归触发。

模块级纯函数 (:func:`group_key` / :func:`node_id` /
:func:`parse_node_id` / :func:`group_keys_for_schema`) 故意不依赖
Tk, 以便在无 GUI 环境下单元测试 (见 ``tests/settings/test_settings_nav.py``)。
"""

from __future__ import annotations

import tkinter as tk
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Tuple

from . import theme
from .frame import UFrame
from .label import ULabel
from .tree_canvas import TreeCanvas


if TYPE_CHECKING:
    from modules.settings.base import SettingsScope, SettingsSchema, SettingSpec


# --------------------------------------------------------------------------
# 纯数据层 (无 Tk 依赖, 可独立测试)
# --------------------------------------------------------------------------


def group_key(spec_key: str) -> str:
    """按 ``key`` 前缀自动归类。

    ``"editor.tab_size"`` -> ``"editor"``; 无前缀 (``"foo"``) -> ``"_"``.
    与 :mod:`modules.settings.widgets` 中 ``_group_key`` 行为保持一致。
    """

    if "." in spec_key:
        return spec_key.split(".", 1)[0]
    return "_"


def node_id(scope_value: str, group_key: Optional[str] = None,
            key: Optional[str] = None) -> str:
    """生成稳定的 iid.

    * ``node_id("global")`` -> ``"global"``  (scope 根)
    * ``node_id("global", "ui")`` -> ``"global:ui"``  (分组)
    * ``node_id("global", "ui", "ui.theme")`` -> ``"global:ui:ui.theme"``  (叶子)
    """

    if key is not None:
        return f"{scope_value}:{group_key}:{key}"
    if group_key is not None:
        return f"{scope_value}:{group_key}"
    return scope_value


def parse_node_id(iid: str) -> Tuple[str, Optional[str], Optional[str]]:
    """逆向解析 :func:`node_id` 生成的结果。

    返回 ``(scope_value, group_key, key)``; 任意中间段为 ``None`` 表示
    对应层级不存在 (例如 scope 根没有 group/key)。
    """

    head, sep, rest = iid.partition(":")
    if not sep:
        return (head, None, None)
    group, sep2, key = rest.partition(":")
    if not sep2:
        return (head, group, None)
    return (head, group, key)


def group_keys_for_schema(schema: "SettingsSchema") -> "OrderedDict[str, List[Tuple[str, str]]]":
    """把一个 schema 拆成 ``{group_key: [(key, label), ...]}``。

    * 分组与组内 spec 都按 schema 的声明顺序保留 (使用 ``OrderedDict``),
      这样树渲染出来的视觉顺序与 schema 文件中的顺序一致, 不会因字典
      重新 hash 而跳动。
    * 无 group 前缀的 spec 会归到 ``"_"`` 桶。
    """

    groups: "OrderedDict[str, List[Tuple[str, str]]]" = OrderedDict()
    for spec in schema:
        g = group_key(spec.key)
        groups.setdefault(g, []).append((spec.key, spec.label or spec.key))
    return groups


# --------------------------------------------------------------------------
# 选中事件载荷
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class NavSelection:
    """导航树节点被选中时回传给监听者的载荷。

    字段:
        * ``scope`` —— 所在作用域 (GLOBAL / PROJECT)。
        * ``group_key`` —— 节点所在分组, ``None`` 表示点中了 scope 根。
        * ``keys`` —— 节点关联的设置 key 列表; scope 根为空, group 节点
          为空 (由上层用 ``filter_group_keys`` 过滤), 叶子节点为单元素。
        * ``label`` —— 节点显示文本, 便于日志/调试。
    """

    scope: Any  # modules.settings.base.SettingsScope (懒加载)
    group_key: Optional[str] = None
    keys: Tuple[str, ...] = field(default_factory=tuple)
    label: str = ""


# --------------------------------------------------------------------------
# 组件主体
# --------------------------------------------------------------------------


class USettingsNavBar(UFrame):
    """设置导航树: 标题头 + Canvas 树 + 纵向 Scrollbar.

    典型用法 (与 :class:`UProjectSettingsWindow` 配合)::

        nav = USettingsNavBar(
            parent,
            on_select=lambda sel: window.show_panel_for(sel),
        )
        nav.pack(side=tk.LEFT, fill=tk.Y)
        nav.set_roots(
            global_schema=settings_manager.global_settings.schema,
            project_schema=(
                settings_manager.project_settings.schema
                if settings_manager.project_settings else None
            ),
        )

    参数:
        parent —— 父容器.
        title —— 顶部标题文本, 默认 ``"Settings"``.
        on_select —— 节点被点击 / 键盘 Enter 触发时的回调, 接收一个
            :class:`NavSelection`. 可选.
    """

    def __init__(
        self,
        parent,
        *,
        title: str = "Settings",
        on_select: Optional[Callable[[NavSelection], None]] = None,
        scope_label_global: str = "全球",
        scope_label_project: str = "项目",
        **kwargs,
    ) -> None:
        # 视觉与 file_tree 一致: 自身是 'panel' 容器。
        kwargs.setdefault("variant", "panel")
        super().__init__(parent, **kwargs)

        self._on_select = on_select
        self._title_text = title
        self._scope_label_global = scope_label_global
        self._scope_label_project = scope_label_project

        # iid -> NavSelection, 由 set_roots 重置。
        self._node_data: Dict[str, NavSelection] = {}

        # 懒加载 SettingsScope 枚举; 失败时用字符串兜底以保证组件仍可
        # 构造 (例如在脱离 settings 子系统的演示场景)。
        try:
            from modules.settings.base import SettingsScope  # noqa: WPS433
            self._SettingsScope = SettingsScope
        except Exception:  # pragma: no cover - 防御性兜底
            self._SettingsScope = None

        self._build()

    # ------------------------------------------------------------------
    # 构造
    # ------------------------------------------------------------------

    def _build(self) -> None:
        # 标题头: 与 UFileTree 完全同构 (variant='title' + 26px 高).
        header = UFrame(self, variant="title", height=26)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        self._title_label = ULabel(
            header, text=f"  {self._title_text}",
            variant="secondary", bg=theme.BG_TITLE,
        )
        self._title_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self._tree = TreeCanvas(
            self,
            row_text=self._row_label,
            on_select=self._on_tree_select,
            on_activate=self._on_tree_activate,
        )
        self._tree.pack(fill=tk.BOTH, expand=True)

    def _row_label(self, iid: str) -> str:
        sel = self._node_data.get(iid)
        return sel.label if sel is not None else ""

    # ------------------------------------------------------------------
    # 公共 API
    # ------------------------------------------------------------------

    def set_on_select(
        self, callback: Optional[Callable[[NavSelection], None]],
    ) -> None:
        self._on_select = callback

    def set_title(self, text: str) -> None:
        self._title_text = text
        self._title_label.config(text=f"  {text}")

    def set_roots(
        self,
        global_schema: Optional["SettingsSchema"],
        project_schema: Optional["SettingsSchema"],
    ) -> Optional[NavSelection]:
        """按两个 schema 重建整棵树并自动选中第一片叶子.

        返回被自动选中的 :class:`NavSelection`; 若两侧 schema 都为空
        则返回 ``None``。
        """

        self._tree.clear()
        self._node_data.clear()

        first_leaf_iid: Optional[str] = None

        if global_schema is not None:
            leaf_iid = self._populate_scope(
                self._SettingsScope.GLOBAL if self._SettingsScope else "global",
                global_schema,
                label=self._scope_label_global,
            )
            if first_leaf_iid is None:
                first_leaf_iid = leaf_iid

        if project_schema is not None:
            leaf_iid = self._populate_scope(
                self._SettingsScope.PROJECT if self._SettingsScope else "project",
                project_schema,
                label=self._scope_label_project,
            )
            if first_leaf_iid is None:
                first_leaf_iid = leaf_iid

        if first_leaf_iid is not None:
            self._tree.set_selected(first_leaf_iid, fire=False)
        return self._node_data.get(first_leaf_iid) if first_leaf_iid else None

    def set_selected(
        self,
        scope: Any,
        group_key: Optional[str] = None,
        key: Optional[str] = None,
    ) -> None:
        """编程式选中: scope 根 / group / leaf 三种深度皆可."""

        scope_value = getattr(scope, "value", str(scope))
        iid = node_id(scope_value, group_key, key)
        if self._tree.exists(iid):
            self._tree.set_selected(iid, fire=False)

    def get_selected(self) -> Optional[NavSelection]:
        iid = self._tree.get_selected()
        if iid is None:
            return None
        return self._node_data.get(iid)

    # ------------------------------------------------------------------
    # 内部: 填充树
    # ------------------------------------------------------------------

    def _populate_scope(
        self,
        scope: Any,
        schema: "SettingsSchema",
        *,
        label: str,
    ) -> Optional[str]:
        """插入 ``scope -> group -> leaf`` 三层, 返回第一片叶子的 iid."""

        scope_value = getattr(scope, "value", str(scope))
        scope_iid = node_id(scope_value)

        sel = NavSelection(
            scope=scope, group_key=None, keys=(), label=label,
        )
        self._node_data[scope_iid] = sel
        # scope 根展开; TreeCanvas 的 add_node 看到 is_open=True 会
        # 在 _relayout 时立刻渲染其下子节点。
        self._tree.add_node(scope_iid, None, is_open=True, data=sel)

        first_leaf_iid: Optional[str] = None
        for g, items in group_keys_for_schema(schema).items():
            group_iid = node_id(scope_value, g)
            g_sel = NavSelection(
                scope=scope, group_key=g, keys=(), label=g,
            )
            self._node_data[group_iid] = g_sel
            # group 节点也展开: 用户点 group 就能直接看到里面的叶子。
            self._tree.add_node(group_iid, scope_iid, is_open=True, data=g_sel)
            for spec_key, spec_label in items:
                leaf_iid = node_id(scope_value, g, spec_key)
                leaf_sel = NavSelection(
                    scope=scope, group_key=g,
                    keys=(spec_key,), label=spec_label,
                )
                self._node_data[leaf_iid] = leaf_sel
                self._tree.add_node(leaf_iid, group_iid, data=leaf_sel)
                if first_leaf_iid is None:
                    first_leaf_iid = leaf_iid
        return first_leaf_iid

    # ------------------------------------------------------------------
    # 内部: 事件
    # ------------------------------------------------------------------

    def _on_tree_select(self, iid: str) -> None:
        sel = self._node_data.get(iid)
        if sel is None or self._on_select is None:
            return
        try:
            self._on_select(sel)
        except Exception:
            pass

    def _on_tree_activate(self, iid: str) -> None:
        # 与原 ttk.Treeview 版本一致: Enter / 双击 都触发 on_select,
        # 让面板切到对应分组或叶子。
        self._on_tree_select(iid)

    # ------------------------------------------------------------------
    # 主题
    # ------------------------------------------------------------------

    def _apply_theme(self) -> None:
        """被 :func:`theme.apply_theme_recursive` 调用, 刷新所有颜色."""

        try:
            super()._apply_theme()
        except tk.TclError:
            pass
        try:
            self._title_label.config(
                bg=theme.BG_TITLE, fg=theme.FG_SECONDARY,
            )
        except (tk.TclError, AttributeError):
            pass
        if hasattr(self._tree, "_apply_theme"):
            try:
                self._tree._apply_theme()
            except tk.TclError:
                pass


__all__ = [
    "USettingsNavBar",
    "NavSelection",
    "group_key",
    "node_id",
    "parse_node_id",
    "group_keys_for_schema",
]
