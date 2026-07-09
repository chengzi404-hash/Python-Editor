"""``modules.Uui.widgets.tree_canvas`` — 基于 ``tk.Canvas`` 的通用树控件.

设计动机:

* 仓库里目前两个树形控件 (:class:`UFileTree` /
  :class:`USettingsNavBar`) 都基于 ``tkinter.ttk.Treeview`` + ``clam``
  主题, 用 :class:`ttk.Style` 一项一项 ``configure`` 才能贴齐当前
  :data:`theme`, 维护成本高且与 Tk 主题系统耦合。
* :class:`TreeCanvas` 提供一个最小、可复用的树形渲染层, 业务侧只
  负责: 把"iid + 父 iid + 显示文本"喂进来, 再监听 ``on_select`` /
  ``on_activate`` / ``on_toggle`` 三个回调即可。颜色完全由
  :data:`theme` 决定, :meth:`_apply_theme` 一行就能全树刷色。

API 概览::

    tree = TreeCanvas(
        parent,
        row_text=lambda iid: my_label_for(iid),
        on_select=lambda iid: ...,
        on_activate=lambda iid: ...,
        on_toggle=lambda iid, is_open: ...,
    )
    tree.add_node("root", None, is_open=True)
    tree.add_node("child", "root")
    tree.set_selected("child")
    tree.see("child")
    tree.clear()

设计要点:

* 每个可见节点用 :class:`tk.Frame` 嵌入到 :class:`tk.Canvas` (``create_window``),
  这样 hover / selected 的高亮直接改 Frame 的 ``bg`` 即可, 不需要
  走 ttk style 体系。
* 节点的展开/折叠通过在每行左侧画一个 ``▼ / ▶`` 三角实现; 整棵
  树扁平化为一个 ``iid -> row_y`` 字典, 滚动只关心行序。
* 主题刷新只需重画所有行 Frame 的 ``bg / fg``; 不重建 widget,
  因此选择状态、hover 状态、滚动位置都不会丢。
"""

from __future__ import annotations

import tkinter as tk
from typing import Any, Callable, Dict, List, Optional, Tuple

from . import theme
from .frame import UFrame
from .scrollbar import UScrollBar


# 三角字符 — 用 ASCII 回退兼容所有字体; 视觉上比 ▼/▶ 更稳。
_TRI_OPEN = "v"   # "已展开" 的占位
_TRI_CLOSED = ">"  # "已折叠" 的占位
_TRI_BLANK = " "   # 叶子节点 (无子) 的占位


class _Node:
    """树节点的纯数据层; 不持有任何 Tk 引用, 方便测试与重建."""

    __slots__ = ("iid", "parent_iid", "children", "is_open", "data")

    def __init__(self, iid: str, parent_iid: Optional[str], data: Any) -> None:
        self.iid = iid
        self.parent_iid = parent_iid
        self.children: List[str] = []
        self.is_open = False
        self.data = data


class TreeCanvas(UFrame):
    """基于 Canvas 的可复用树控件.

    业务侧只需要提供"iid -> 显示文本"的回调以及三个事件回调, 即可
    构建一棵可点击、可展开/折叠、可滚动、跟随主题的树。具体的"iid
    背后是什么业务对象"完全交给调用方 — 通常调用方会维护一个
    ``iid -> 业务对象`` 的字典, 在回调里反向查表。
    """

    def __init__(
        self,
        parent,
        *,
        row_text: Callable[[str], str],
        on_select: Optional[Callable[[str], None]] = None,
        on_activate: Optional[Callable[[str], None]] = None,
        on_toggle: Optional[Callable[[str, bool], None]] = None,
        row_height: int = 22,
        row_indent: int = 18,
        show_disclosure: bool = True,
        **kwargs,
    ) -> None:
        # 视觉与 UFileTree 同构: 自身是 'panel' 容器。
        kwargs.setdefault("variant", "panel")
        super().__init__(parent, **kwargs)

        self._row_text = row_text
        self._on_select = on_select
        self._on_activate = on_activate
        self._on_toggle = on_toggle
        self._row_height = row_height
        self._row_indent = row_indent
        self._show_disclosure = show_disclosure

        # 树模型 (纯数据, 不依赖 Tk)
        self._nodes: Dict[str, _Node] = {}
        self._root_iids: List[str] = []
        self._selected_iid: Optional[str] = None
        self._hover_iid: Optional[str] = None

        # 渲染层
        self._row_frames: Dict[str, tk.Frame] = {}  # iid -> 行 Frame
        self._row_y: Dict[str, int] = {}            # iid -> canvas y
        self._row_window_id: Dict[str, int] = {}    # iid -> canvas window item id
        self._pending_width_sync = False            # 防抖: 多次 resize 只刷一次

        self._build_canvas()

    # ------------------------------------------------------------------
    # 构造
    # ------------------------------------------------------------------

    def _build_canvas(self) -> None:
        self._canvas = tk.Canvas(
            self,
            bg=theme.BG_INPUT,
            highlightthickness=0,
            bd=0,
        )
        # 收口到 :class:`UScrollBar` — 主题色、autohide 行为都集中维护;
        # 旧版手写 6 个 kwargs 的 Scrollbar 已经散落在 4 个文件里, 改
        # 一次样式要改 4 处, 这里统一收口。
        self._vsb = UScrollBar(
            self,
            orient="vertical",
            command=self._canvas.yview,
        )
        self._canvas.configure(yscrollcommand=self._vsb.set)

        self._vsb.pack(side=tk.RIGHT, fill=tk.Y)
        self._canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 事件
        self._canvas.bind("<Button-1>", self._on_canvas_press)
        self._canvas.bind("<Double-Button-1>", self._on_canvas_double)
        self._canvas.bind("<Return>", self._on_canvas_return)
        self._canvas.bind("<Configure>", self._on_canvas_configure)
        # 鼠标滚轮 (Windows / macOS 用 delta; Linux 用 Button-4/5)
        self._canvas.bind("<MouseWheel>", self._on_mousewheel)
        self._canvas.bind("<Button-4>", lambda e: self._canvas.yview_scroll(-1, "units"))
        self._canvas.bind("<Button-5>", lambda e: self._canvas.yview_scroll(1, "units"))

    # ------------------------------------------------------------------
    # 公共 API: 增 / 删 / 改节点
    # ------------------------------------------------------------------

    def add_node(
        self,
        iid: str,
        parent_iid: Optional[str],
        *,
        is_open: bool = False,
        data: Any = None,
    ) -> None:
        """注册一个节点. 父节点必须已存在 (除了 ``parent_iid=None`` 的根).

        重复 iid 静默忽略, 避免上游重复构造时把已有的子节点清空;
        如需"重建"语义, 先调用 :meth:`clear`。
        """

        if iid in self._nodes:
            return
        node = _Node(iid=iid, parent_iid=parent_iid, data=data)
        node.is_open = is_open
        self._nodes[iid] = node
        if parent_iid is None:
            self._root_iids.append(iid)
        else:
            parent = self._nodes.get(parent_iid)
            if parent is None:
                # 防御: 父节点缺失, 不允许建立孤儿节点, 否则永远不会
                # 被 _relayout 命中, 形成"看上去加进去了但看不见"的 bug。
                del self._nodes[iid]
                raise ValueError(
                    f"TreeCanvas.add_node: parent {parent_iid!r} not found"
                )
            parent.children.append(iid)
        self._relayout()

    def remove_node(self, iid: str) -> None:
        """删除一个节点及其全部后代."""

        node = self._nodes.get(iid)
        if node is None:
            return
        to_remove: List[str] = []
        self._collect_descendants(iid, to_remove)
        # 从根列表中清掉被删的根节点。
        for rid in to_remove:
            if rid in self._root_iids:
                self._root_iids.remove(rid)
        # 关键: 还要从父节点的 children 列表里把自己摘掉, 否则下次
        # _relayout 走 DFS 时仍会撞上已删的 iid, 触发 KeyError。
        if node.parent_iid is not None:
            parent = self._nodes.get(node.parent_iid)
            if parent is not None and iid in parent.children:
                parent.children.remove(iid)
        # 释放 Tk 资源 + 清空数据层。
        for rid in to_remove:
            self._nodes.pop(rid, None)
            self._row_frames.pop(rid, None)
            self._row_y.pop(rid, None)
            self._row_window_id.pop(rid, None)
        if self._selected_iid in to_remove:
            self._selected_iid = None
        if self._hover_iid in to_remove:
            self._hover_iid = None
        self._relayout()

    def clear(self) -> None:
        """清空整棵树, 回到初始状态."""

        for frame in self._row_frames.values():
            try:
                frame.destroy()
            except tk.TclError:
                pass
        self._row_frames.clear()
        self._row_y.clear()
        self._row_window_id.clear()
        self._canvas.delete("all")
        self._nodes.clear()
        self._root_iids.clear()
        self._selected_iid = None
        self._hover_iid = None
        self._update_scroll_region()

    def set_open(self, iid: str, is_open: bool, *, fire_toggle: bool = True) -> None:
        """程序式打开 / 关闭一个节点. 关闭时若当前选中项被隐藏, 取消选中."""

        node = self._nodes.get(iid)
        if node is None or node.is_open == is_open:
            return
        node.is_open = is_open
        if (
            not is_open
            and self._selected_iid is not None
            and not self._is_visible(self._selected_iid)
        ):
            self._apply_selection(None)
        self._relayout()
        if fire_toggle and self._on_toggle is not None:
            try:
                self._on_toggle(iid, is_open)
            except Exception:
                pass

    def toggle(self, iid: str) -> None:
        node = self._nodes.get(iid)
        if node is None:
            return
        self.set_open(iid, not node.is_open)

    # ------------------------------------------------------------------
    # 公共 API: 选中 / 滚动 / 查找
    # ------------------------------------------------------------------

    def set_selected(
        self, iid: Optional[str], *, fire: bool = True, scroll: bool = True,
    ) -> None:
        """程序式选中一个节点. 隐藏节点不可被选中 (保护 UX 一致性)."""

        if iid is not None:
            if iid not in self._nodes:
                return
            if not self._is_visible(iid):
                return
        self._apply_selection(iid)
        if iid is not None and scroll:
            self.see(iid)
        if fire and iid is not None and self._on_select is not None:
            try:
                self._on_select(iid)
            except Exception:
                pass

    def get_selected(self) -> Optional[str]:
        return self._selected_iid

    def exists(self, iid: str) -> bool:
        return iid in self._nodes

    def is_open(self, iid: str) -> bool:
        node = self._nodes.get(iid)
        return node.is_open if node is not None else False

    def node_data(self, iid: str) -> Any:
        """返回 :meth:`add_node` 时塞进来的 ``data`` (供业务侧反查)."""

        node = self._nodes.get(iid)
        return node.data if node is not None else None

    def see(self, iid: str) -> None:
        """滚动到让 ``iid`` 进入可见区. 不可见节点直接忽略."""

        if iid not in self._nodes or not self._is_visible(iid):
            return
        y = self._row_y.get(iid)
        if y is None:
            return
        bbox = self._canvas.bbox("all")
        if not bbox:
            return
        total_h = bbox[3]
        canvas_h = self._canvas.winfo_height()
        if total_h <= canvas_h or canvas_h <= 1:
            return
        first, _ = self._canvas.yview()
        top_y = first * total_h
        if y < top_y:
            self._canvas.yview_moveto(y / total_h)
        elif y + self._row_height > top_y + canvas_h:
            self._canvas.yview_moveto(
                (y + self._row_height - canvas_h) / total_h
            )

    def identify_row(self, y: int) -> Optional[str]:
        """把 canvas y 坐标反查到 iid; 不在行上则返回 ``None``."""

        for iid, row_y in self._row_y.items():
            if row_y <= y < row_y + self._row_height:
                return iid
        return None

    # ------------------------------------------------------------------
    # 内部: 可见性 / 深度
    # ------------------------------------------------------------------

    def _is_visible(self, iid: str) -> bool:
        node = self._nodes.get(iid)
        if node is None:
            return False
        cur = node.parent_iid
        while cur is not None:
            parent = self._nodes.get(cur)
            if parent is None or not parent.is_open:
                return False
            cur = parent.parent_iid
        return True

    def _depth(self, iid: str) -> int:
        depth = 0
        cur = self._nodes.get(iid)
        while cur is not None and cur.parent_iid is not None:
            depth += 1
            cur = self._nodes.get(cur.parent_iid)
        return depth

    def _collect_descendants(self, iid: str, out: List[str]) -> None:
        node = self._nodes.get(iid)
        if node is None:
            return
        out.append(iid)
        for c in node.children:
            self._collect_descendants(c, out)

    # ------------------------------------------------------------------
    # 内部: 重布局
    # ------------------------------------------------------------------

    def _relayout(self) -> None:
        """按当前可见性扁平化整棵树, 重建所有行 widget."""

        for frame in self._row_frames.values():
            try:
                frame.destroy()
            except tk.TclError:
                pass
        self._row_frames.clear()
        self._row_y.clear()
        self._row_window_id.clear()
        self._canvas.delete("all")

        # DFS 收集可见 (iid, depth) 序列。
        visible: List[Tuple[str, int]] = []

        def walk(iid: str, depth: int) -> None:
            visible.append((iid, depth))
            node = self._nodes.get(iid)
            if node is None:
                return
            if node.is_open:
                for c in node.children:
                    walk(c, depth + 1)

        for r in self._root_iids:
            walk(r, 0)

        canvas_w = max(1, self._canvas.winfo_width())
        y = 0
        for iid, depth in visible:
            y = self._build_row(iid, depth, y, canvas_w)

        self._update_scroll_region()

    def _build_row(self, iid: str, depth: int, y: int, canvas_w: int) -> int:
        """构造一行 (三角 + 文本), 嵌入到 canvas. 返回下一行的 y."""

        node = self._nodes[iid]
        text = self._row_text(iid)
        is_selected = (iid == self._selected_iid)
        indent = depth * self._row_indent

        # 整行 Frame — 接受 click 事件, 背景色根据 state 决定。
        frame = tk.Frame(
            self._canvas,
            bg=theme.BG_INPUT,
            highlightthickness=0,
            bd=0,
            height=self._row_height,
        )
        frame.pack_propagate(False)

        # 左侧三角: 内部节点画 v/>; 叶子画空白占位让文本对齐。
        if self._show_disclosure:
            tri_text = (
                _TRI_OPEN if node.is_open else
                _TRI_CLOSED if node.children else
                _TRI_BLANK
            )
            tri = tk.Label(
                frame, text=tri_text,
                bg=theme.BG_INPUT,
                fg=theme.FG_TERTIARY,
                width=2,
                anchor="center",
                font=theme.LABEL_FONT_SMALL,
                cursor="hand2" if node.children else "arrow",
            )
            tri.pack(side=tk.LEFT, padx=(0, 2))
            if node.children:
                tri.bind(
                    "<Button-1>",
                    lambda e, i=iid: self._on_triangle_click(i),
                )

        # 文本标签。
        label = tk.Label(
            frame, text=text,
            bg=theme.BG_INPUT, fg=theme.FG_PRIMARY,
            anchor="w",
            font=theme.LABEL_FONT,
            cursor="hand2",
        )
        label.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(2, 4))

        # 事件绑到 label + frame (双保险: 点击文字或文字旁的留白都生效)。
        for w in (label, frame):
            w.bind("<Button-1>", lambda e, i=iid: self._on_row_press(i))
            w.bind(
                "<Double-Button-1>",
                lambda e, i=iid: self._on_row_double(i),
            )
            w.bind("<Enter>", lambda e, i=iid: self._on_row_enter(i))
            w.bind("<Leave>", lambda e, i=iid: self._on_row_leave(i))

        # 嵌入到 canvas。
        win_w = max(50, canvas_w - indent - 16)
        window_id = self._canvas.create_window(
            indent, y, window=frame, anchor="nw", width=win_w,
        )
        self._row_frames[iid] = frame
        self._row_y[iid] = y
        self._row_window_id[iid] = window_id

        self._paint_row(frame, iid, is_selected=is_selected, is_hover=False)
        return y + self._row_height

    def _update_scroll_region(self) -> None:
        if self._row_y:
            max_y = max(self._row_y.values()) + self._row_height
        else:
            max_y = 0
        canvas_w = self._canvas.winfo_width() or 200
        self._canvas.configure(scrollregion=(0, 0, canvas_w, max_y))

    def _resync_widths(self) -> None:
        """canvas 宽度变化时, 调整已有行的嵌入宽度, 不重建 widget."""

        canvas_w = max(1, self._canvas.winfo_width())
        for iid, window_id in self._row_window_id.items():
            depth = self._depth(iid)
            indent = depth * self._row_indent
            try:
                self._canvas.itemconfigure(
                    window_id, width=max(50, canvas_w - indent - 16),
                )
            except tk.TclError:
                pass

    # ------------------------------------------------------------------
    # 内部: 绘制 (hover / selected)
    # ------------------------------------------------------------------

    def _paint_row(
        self,
        frame: tk.Frame,
        iid: str,
        *,
        is_selected: bool,
        is_hover: bool,
    ) -> None:
        if is_selected:
            bg, fg = theme.BG_ACTIVE, theme.FG_PRIMARY
        elif is_hover:
            bg, fg = theme.BG_HOVER, theme.FG_PRIMARY
        else:
            bg, fg = theme.BG_INPUT, theme.FG_PRIMARY
        self._safe_config(frame, bg=bg)
        for child in frame.winfo_children():
            # isinstance 缩窄类型, 让类型检查器认得 .config(bg=, fg=)。
            if not isinstance(child, (tk.Frame, tk.Label)):
                continue
            if isinstance(child, tk.Label) and child.cget("text") in (
                _TRI_OPEN, _TRI_CLOSED, _TRI_BLANK,
            ):
                self._safe_config(child, bg=bg, fg=theme.FG_TERTIARY)
            else:
                self._safe_config(child, bg=bg, fg=fg)

    @staticmethod
    def _safe_config(widget: tk.Misc, **kwargs: Any) -> None:
        """包一层 ``widget.config``; 主题刷新时可能 widget 已被销毁, 异常吞掉.

        通过 ``isinstance`` 缩窄到 ``tk.Frame`` / ``tk.Label`` 后再调
        ``.config`` — 这两个具体类的 ``config`` 接受 ``bg`` / ``fg``,
        静态检查器能看到; 比起 ``**kwargs`` 直接调 base class 的
        ``tk.Misc.config`` (签名太宽) 更类型安全。
        """

        if not isinstance(widget, (tk.Frame, tk.Label)):
            return
        try:
            widget.config(**kwargs)
        except tk.TclError:
            pass

    def _apply_selection(self, iid: Optional[str]) -> None:
        """更新选中状态并重绘相关行; 不触发回调也不滚动."""

        self._selected_iid = iid
        for rid, frame in self._row_frames.items():
            self._paint_row(
                frame, rid,
                is_selected=(rid == iid),
                is_hover=(rid == self._hover_iid),
            )

    # ------------------------------------------------------------------
    # 内部: 事件
    # ------------------------------------------------------------------

    def _on_canvas_press(self, event: tk.Event) -> None:
        iid = self.identify_row(event.y)
        if iid is None:
            return
        # 点击若落在"三角区" (缩进后的最左侧 16 像素), 切换展开。
        node = self._nodes.get(iid)
        if node and node.children and self._show_disclosure:
            depth = self._depth(iid)
            indent = depth * self._row_indent
            if event.x < indent + 16:
                self.toggle(iid)
                return
        self.set_selected(iid)

    def _on_canvas_double(self, event: tk.Event) -> None:
        iid = self.identify_row(event.y)
        if iid is None:
            return
        if self._on_activate is not None:
            try:
                self._on_activate(iid)
            except Exception:
                pass

    def _on_canvas_return(self, _event: tk.Event) -> None:
        iid = self._selected_iid
        if iid is None or self._on_activate is None:
            return
        try:
            self._on_activate(iid)
        except Exception:
            pass

    def _on_canvas_configure(self, _event: tk.Event) -> None:
        # 防抖: 拖窗口时一连串 <Configure>, 50ms 内只刷一次。
        if self._pending_width_sync:
            return
        self._pending_width_sync = True
        try:
            self._canvas.after(50, self._do_width_sync)
        except tk.TclError:
            self._pending_width_sync = False

    def _do_width_sync(self) -> None:
        self._pending_width_sync = False
        self._resync_widths()
        self._update_scroll_region()

    def _on_mousewheel(self, event: tk.Event) -> None:
        if not hasattr(event, "delta") or event.delta == 0:
            return
        # Windows / macOS: delta 是 ±120 的倍数; 一行一滚。
        delta = -1 if event.delta > 0 else 1
        self._canvas.yview_scroll(delta, "units")

    def _on_row_press(self, iid: str) -> None:
        self.set_selected(iid)

    def _on_row_double(self, iid: str) -> None:
        if self._on_activate is None:
            return
        try:
            self._on_activate(iid)
        except Exception:
            pass

    def _on_triangle_click(self, iid: str) -> None:
        self.toggle(iid)

    def _on_row_enter(self, iid: str) -> None:
        if self._hover_iid == iid:
            return
        self._hover_iid = iid
        frame = self._row_frames.get(iid)
        if frame is not None:
            self._paint_row(
                frame, iid,
                is_selected=(iid == self._selected_iid),
                is_hover=True,
            )

    def _on_row_leave(self, iid: str) -> None:
        if self._hover_iid != iid:
            return
        self._hover_iid = None
        frame = self._row_frames.get(iid)
        if frame is not None:
            self._paint_row(
                frame, iid,
                is_selected=(iid == self._selected_iid),
                is_hover=False,
            )

    # ------------------------------------------------------------------
    # 主题
    # ------------------------------------------------------------------

    def _apply_theme(self) -> None:
        try:
            super()._apply_theme()
        except tk.TclError:
            pass
        try:
            self._canvas.config(bg=theme.BG_INPUT)
        except tk.TclError:
            pass
        # UScrollBar 自己实现 _apply_theme, 直接转发即可。
        if hasattr(self._vsb, "_apply_theme"):
            try:
                self._vsb._apply_theme()
            except tk.TclError:
                pass
        # 重画所有行 — 不重建 widget, 保留选择/hover/滚动位置。
        for iid, frame in self._row_frames.items():
            self._paint_row(
                frame, iid,
                is_selected=(iid == self._selected_iid),
                is_hover=(iid == self._hover_iid),
            )


__all__ = ["TreeCanvas"]
