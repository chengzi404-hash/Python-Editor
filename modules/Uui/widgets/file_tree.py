"""``modules.Uui.widgets.file_tree`` — VS 风格的目录树组件.

基于 :class:`TreeCanvas` (Canvas 渲染层) 实现, 自身只负责:

* 维护 ``iid -> 绝对路径`` 的映射, 把 TreeCanvas 的 iid 与文件系统
  路径解耦;
* 扫描目录、把节点喂给 TreeCanvas; **首层立即展开, 深层按需懒加载**
  —— 第一次 ``<<TreeviewOpen>>`` 等价事件 (即 :meth:`TreeCanvas.toggle`)
  触发时再 ``scandir`` 该目录;
* 在 :meth:`on_activate` 回调里区分"目录"和"文件" — 双击目录等价
  于点三角 (展开/折叠), 双击文件才真正回调用户的 ``on_activate``。

API 与 ttk.Treeview 时代完全一致:

* :meth:`set_root` / :meth:`refresh` —— 切换或重建项目根;
* :meth:`set_on_activate` / :meth:`set_title` —— 运行时改回调/标题;
* :meth:`selected_path` —— 当前选中节点的绝对路径;
* :meth:`_apply_theme` —— 主题切换, 由
  :func:`modules.Uui.widgets.theme.apply_theme_recursive` 递归触发。
"""

from __future__ import annotations

import os
import tkinter as tk
from typing import Callable, Dict, Iterable, Optional

from . import theme
from .frame import UFrame
from .label import ULabel
from .tree_canvas import TreeCanvas


# 这些目录在任何项目里都不该出现在文件树中,显式隐藏掉能避免节点爆炸。
_DEFAULT_IGNORE_DIRS = frozenset({
    "__pycache__", ".git", ".venv", "venv", "node_modules",
    ".idea", ".vscode", "build", "dist", ".mypy_cache", ".pytest_cache",
})


# iid 编码: ``FILE:\\\\绝对路径``; 用 ``FILE:`` 前缀避免与未来可能
# 引入的非文件节点冲突 (例如设置项节点)。
_IID_PREFIX = "FILE:"


def _path_to_iid(path: str) -> str:
    return _IID_PREFIX + os.path.abspath(path)


def _iid_to_path(iid: str) -> Optional[str]:
    if not iid.startswith(_IID_PREFIX):
        return None
    return iid[len(_IID_PREFIX):]


class UFileTree(UFrame):
    """文件树: 头部标题 + Canvas 树 + 纵向 Scrollbar."""

    def __init__(
        self,
        parent,
        *,
        title: str = "Project",
        ignore_dirs: Optional[Iterable[str]] = None,
        width: int = 240,
        on_activate: Optional[Callable[[str], None]] = None,
        **kwargs,
    ) -> None:
        # 自身作为外层 panel,与 output_panel 同构 (``variant='panel'``)。
        kwargs.setdefault("variant", "panel")
        super().__init__(parent, **kwargs)

        self._title_text = title
        self._on_activate = on_activate
        self._ignore_dirs = (
            set(ignore_dirs) if ignore_dirs is not None
            else set(_DEFAULT_IGNORE_DIRS)
        )
        self._root_path: Optional[str] = None
        # iid -> 绝对路径 (TreeCanvas 不关心业务, 我们自己维护反查表)。
        self._iid_to_path: Dict[str, str] = {}

        self._build()

    # ------------------------------------------------------------------
    # 构造
    # ------------------------------------------------------------------

    def _build(self) -> None:
        # 标题头: 与 _build_output_panel 同构: UFrame(title) + ULabel(secondary).
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
            on_select=self._on_select,
            on_activate=self._on_activate_dispatch,
            on_toggle=self._on_toggle,
        )
        self._tree.pack(fill=tk.BOTH, expand=True)

    def _row_label(self, iid: str) -> str:
        """TreeCanvas 用此回调拿每行的显示文本."""

        path = self._iid_to_path.get(iid)
        if path is None:
            return ""
        return os.path.basename(path) or path

    # ------------------------------------------------------------------
    # 公共 API
    # ------------------------------------------------------------------

    def set_on_activate(
        self, callback: Optional[Callable[[str], None]],
    ) -> None:
        self._on_activate = callback

    def set_title(self, text: str) -> None:
        self._title_text = text
        self._title_label.config(text=f"  {text}")

    def set_root(self, path: Optional[str]) -> None:
        """设置根目录, ``None`` 表示清空树."""

        self._root_path = os.path.abspath(path) if path else None
        # 头部只显示项目名;无根目录时回到默认标题。
        if self._root_path:
            display = os.path.basename(self._root_path) or self._root_path
        else:
            display = self._title_text
        self._title_label.config(text=f"  {display}")
        self._rebuild()

    def refresh(self) -> None:
        """外部触发重建(例如刚 attach 了项目)."""
        self._rebuild()

    def selected_path(self) -> Optional[str]:
        iid = self._tree.get_selected()
        if iid is None:
            return None
        return self._iid_to_path.get(iid)

    # ------------------------------------------------------------------
    # 内部: 重建树
    # ------------------------------------------------------------------

    def _rebuild(self) -> None:
        self._tree.clear()
        self._iid_to_path.clear()

        if not self._root_path or not os.path.isdir(self._root_path):
            return

        root_iid = _path_to_iid(self._root_path)
        self._iid_to_path[root_iid] = self._root_path
        # 根节点始终展开; TreeCanvas 的 add_node 一旦 is_open=True 就
        # 会立即在 _relayout 中渲染其下的子节点, 这正是首层扫描的
        # 切入点。
        self._tree.add_node(root_iid, None, is_open=True)
        try:
            self._populate(root_iid, self._root_path)
        except OSError:
            # 权限不足等情况: 在根下挂一个错误节点提示用户。
            err_iid = root_iid + "::err"
            self._iid_to_path[err_iid] = ""
            self._tree.add_node(err_iid, root_iid)

    def _populate(self, parent_iid: str, dir_path: str) -> None:
        """递归填充 ``dir_path`` 下的一级子节点到 ``parent_iid`` 之下.

        同层按"目录优先、字母序"排序, 这样浏览体验稳定。
        """

        try:
            entries = list(os.scandir(dir_path))
        except OSError:
            return

        dirs = []
        files = []
        for e in entries:
            name = e.name
            if name.startswith(".") and name not in (".gitignore", ".env"):
                if e.is_dir():
                    continue
            try:
                is_dir = e.is_dir(follow_symlinks=False)
            except OSError:
                continue
            if is_dir:
                if name in self._ignore_dirs:
                    continue
                dirs.append(e)
            else:
                try:
                    is_file = e.is_file(follow_symlinks=False)
                except OSError:
                    is_file = False
                if is_file:
                    files.append(e)

        dirs.sort(key=lambda d: d.name.lower())
        files.sort(key=lambda f: f.name.lower())

        for d in dirs:
            self._add_dir(d, parent_iid)
        for f in files:
            self._add_file(f, parent_iid)

    def _add_dir(self, entry: os.DirEntry, parent_iid: str) -> None:
        """添加一个目录节点;默认折叠, 首次展开时再 scandir."""

        iid = _path_to_iid(entry.path)
        self._iid_to_path[iid] = entry.path
        # is_open=False: 不立即填充子节点, 等 on_toggle 触发时再懒加载。
        self._tree.add_node(iid, parent_iid, is_open=False, data=entry.path)

    def _add_file(self, entry: os.DirEntry, parent_iid: str) -> None:
        iid = _path_to_iid(entry.path)
        self._iid_to_path[iid] = entry.path
        # 叶子节点不需要三角; is_open 在 TreeCanvas 里被忽略。
        self._tree.add_node(iid, parent_iid, data=entry.path)

    # ------------------------------------------------------------------
    # 内部: 事件
    # ------------------------------------------------------------------

    def _on_select(self, iid: str) -> None:
        # TreeCanvas 已经把高亮切到 iid; 我们这里不需要做额外的事,
        # 选中仅供 :meth:`selected_path` 反查。
        return

    def _on_activate_dispatch(self, iid: str) -> None:
        """TreeCanvas 的双击/Enter 入口;区分文件 vs 目录."""

        path = self._iid_to_path.get(iid)
        if path is None or not path:
            return
        if os.path.isdir(path):
            # 双击目录 = 展开/折叠, 与原 Treeview 行为一致。
            self._tree.toggle(iid)
            return
        if self._on_activate is not None:
            try:
                self._on_activate(path)
            except Exception:
                pass

    def _on_toggle(self, iid: str, is_open: bool) -> None:
        """目录首次展开时, 懒加载其下的子节点。

        通过 :attr:`_iid_to_path` 反查该目录对应的真实路径, 然后
        :meth:`_populate` 一次。后续再展开/折叠只是状态切换, 不会
        重复 scandir (TreeCanvas 已经知道该节点当前是开/合, 不会
        重复触发 on_toggle)。
        """

        if not is_open:
            return
        path = self._iid_to_path.get(iid)
        if path is None or not path or not os.path.isdir(path):
            return
        # 检查该 iid 下是否已经有真实子节点; 防止"先关再开"时被
        # 误判为"首次展开"造成重复插入。
        # TreeCanvas 暂时不暴露 children 列表 — 走数据层:
        # 在 _iid_to_path 里, 子节点的 iid 都以 "<this path>" 作为
        # 前缀 (abspath 后); 用 iid_to_path 反查, 看是否已有 child。
        prefix = _path_to_iid(path) + os.sep
        already = any(
            k != iid and k.startswith(prefix)
            for k in self._iid_to_path
        )
        if already:
            return
        try:
            self._populate(iid, path)
        except OSError:
            err_iid = iid + "::err"
            self._iid_to_path[err_iid] = ""
            self._tree.add_node(err_iid, iid)

    # ------------------------------------------------------------------
    # 主题刷新
    # ------------------------------------------------------------------

    def _apply_theme(self) -> None:
        """供上层在切换主题时调用, 刷新所有颜色.

        UFrame._apply_theme 只更新自身 bg;这里递归刷新子控件, 保证
        标题 / body / TreeCanvas 全部跟随 theme 切换。
        """

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
        # TreeCanvas 自己实现了 _apply_theme, 通过 super()._apply_theme
        # 的递归(在 UFrame 中)已经会被命中, 但 _apply_theme 实际只在
        # 收到 _apply_theme 调用时刷新。UFrame._apply_theme 不递归,
        # 这里显式触发 TreeCanvas 的主题刷新。
        if hasattr(self._tree, "_apply_theme"):
            try:
                self._tree._apply_theme()
            except tk.TclError:
                pass


__all__ = ["UFileTree"]
