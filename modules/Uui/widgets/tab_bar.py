"""``modules.Uui.widgets.tab_bar`` — 多文件标签栏组件。"""

from __future__ import annotations

import tkinter as tk
import tkinter.font as tkfont
from collections.abc import Callable
from dataclasses import dataclass

from . import theme


@dataclass
class Tab:
    """单个标签的数据模型。"""
    id: str
    title: str
    dirty: bool = False
    closeable: bool = True


class TabBar(tk.Frame):
    """标签栏组件。

    使用 Canvas 绘制标签按钮，支持：
    - 活动标签高亮
    - dirty 状态（标题前加 *）
    - 关闭按钮
    - 右键上下文菜单
    - 横向滚动（标签过多时）
    """

    TAB_HEIGHT = 28
    TAB_PADDING = 14
    CLOSE_SIZE = 16
    CLOSE_OFFSET = 6
    TAB_GAP = 4

    def __init__(
        self,
        parent,
        on_select: Callable[[str], None],
        on_close: Callable[[str], None],
        on_context_menu: Callable[[str, int, int], None],
        **kwargs,
    ):
        super().__init__(parent, **kwargs)
        self._on_select = on_select
        self._on_close = on_close
        self._on_context_menu = on_context_menu

        self._scroll_offset = 0
        self._tabs: dict[str, Tab] = {}
        # 布局信息：tab_id -> {x1, x2, width, label_text}
        self._layout: dict[str, dict] = {}
        self._active_id: str | None = None

        self._canvas = tk.Canvas(
            self,
            height=self.TAB_HEIGHT,
            highlightthickness=0,
            bd=0,
        )
        self._canvas.pack(fill=tk.X, side=tk.TOP)
        self._canvas.config(bg=theme.BG_TITLE)

        self._tab_font = tkfont.Font(family='Segoe UI', size=9)

        # 滚动按钮
        self._left_btn = tk.Label(self, text='◀', font=('Segoe UI', 6),
                                   bg=str(theme.BG_TITLE), fg=str(theme.FG_SECONDARY))
        self._right_btn = tk.Label(self, text='▶', font=('Segoe UI', 6),
                                    bg=str(theme.BG_TITLE), fg=str(theme.FG_SECONDARY))
        self._left_btn.pack(side=tk.LEFT, padx=2, pady=0)
        self._right_btn.pack(side=tk.RIGHT, padx=2, pady=0)
        self._left_btn.bind('<Button-1>', lambda e: self._scroll_left())
        self._right_btn.bind('<Button-1>', lambda e: self._scroll_right())

        self._canvas.bind('<Configure>', self._on_resize)
        self._canvas.bind('<Button-1>', self._on_canvas_click)
        self._canvas.bind('<Button-3>', self._on_canvas_right_click)
        self._canvas.bind('<MouseWheel>', self._on_wheel)

    # ------------------------------------------------------------------
    # 公共 API
    # ------------------------------------------------------------------

    def set_tabs(self, tabs: list[Tab], active_id: str | None) -> None:
        """设置所有标签并指定活动标签。"""
        self._tabs = {t.id: t for t in tabs}
        self._active_id = active_id
        self._scroll_offset = 0
        self._redraw()

    def update_tab(self, tab_id: str, title: str, dirty: bool) -> None:
        """更新单个标签的标题或 dirty 状态。"""
        if tab_id in self._tabs:
            self._tabs[tab_id].title = title
            self._tabs[tab_id].dirty = dirty
            self._redraw()

    def set_active(self, tab_id: str) -> None:
        """切换活动标签（不触发回调）。"""
        self._active_id = tab_id
        self._ensure_visible(tab_id)
        self._redraw()

    def remove_tab(self, tab_id: str) -> None:
        """移除标签。"""
        self._tabs.pop(tab_id, None)
        self._layout.pop(tab_id, None)
        if self._active_id == tab_id:
            self._active_id = None
        self._redraw()

    def _redraw(self) -> None:
        """重绘所有标签。"""
        self._canvas.delete('all')

        canvas_w = self._canvas.winfo_width()
        if canvas_w < 2:
            canvas_w = 800

        x = 2 - self._scroll_offset
        self._layout.clear()

        for tab_id, tab in self._tabs.items():
            label_text = f'*{tab.title}' if tab.dirty else tab.title
            text_w = self._tab_font.measure(label_text)
            tab_w = text_w + self.TAB_PADDING * 2 + self.CLOSE_SIZE + self.CLOSE_OFFSET + 4

            # 记录布局信息
            self._layout[tab_id] = {
                'x1': x,
                'x2': x + tab_w,
                'width': tab_w,
                'label': label_text,
            }

            is_active = (tab_id == self._active_id)
            bg = str(theme.BG_ACTIVE) if is_active else str(theme.BG_RAISED)
            fg = str(theme.FG_PRIMARY) if is_active else str(theme.FG_SECONDARY)

            # 标签背景
            self._canvas.create_rectangle(
                x, 2, x + tab_w, self.TAB_HEIGHT - 2,
                fill=bg, outline=str(theme.BORDER),
                tags=('tab', f'bg_{tab_id}'),
            )

            # 文字
            self._canvas.create_text(
                x + self.TAB_PADDING, self.TAB_HEIGHT // 2,
                text=label_text, fill=fg, anchor='w',
                font=self._tab_font,
                tags=('tab', f'label_{tab_id}'),
            )

            # 关闭按钮
            close_x = x + tab_w - self.CLOSE_SIZE - self.CLOSE_OFFSET
            close_y = self.TAB_HEIGHT // 2
            self._canvas.create_text(
                close_x, close_y,
                text='×', fill=str(theme.FG_TERTIARY),
                font=('Segoe UI', 10, 'bold'),
                tags=('tab', f'close_{tab_id}'),
            )

            # 点击热区
            self._canvas.create_rectangle(
                x, 2, x + tab_w, self.TAB_HEIGHT - 2,
                fill='', outline='',
                tags=('tab', f'hit_{tab_id}'),
            )

            x += tab_w + self.TAB_GAP

        total_w = x - 2
        if total_w > canvas_w:
            self._left_btn.pack(side=tk.LEFT, padx=2, pady=0)
            self._right_btn.pack(side=tk.RIGHT, padx=2, pady=0)
        else:
            self._left_btn.pack_forget()
            self._right_btn.pack_forget()

    def _ensure_visible(self, tab_id: str) -> None:
        """确保指定标签在可视区域内。"""
        info = self._layout.get(tab_id)
        if not info:
            return
        canvas_w = self._canvas.winfo_width()
        if canvas_w < 2:
            return
        if info['x1'] < 0:
            self._scroll_offset += abs(info['x1']) + 2
        elif info['x2'] > canvas_w:
            self._scroll_offset -= (info['x2'] - canvas_w) + 2

    # ------------------------------------------------------------------
    # 事件处理
    # ------------------------------------------------------------------

    def _on_resize(self, e=None) -> None:
        self._redraw()

    def _on_canvas_click(self, e) -> None:
        clicked_id = self._hit_test(e.x)
        if clicked_id is None:
            return
        if self._on_close_button(e.x, clicked_id):
            self._on_select(clicked_id)
            self._on_close(clicked_id)
        else:
            self._on_select(clicked_id)

    def _on_canvas_right_click(self, e) -> None:
        tab_id = self._hit_test(e.x)
        if tab_id:
            self._on_context_menu(tab_id, e.x_root, e.y_root)

    def _on_wheel(self, e) -> None:
        delta = int(e.delta / 120)
        canvas_w = self._canvas.winfo_width()
        total_w = sum(info['width'] + self.TAB_GAP for info in self._layout.values())
        if total_w <= canvas_w:
            return
        self._scroll_offset = max(0, min(self._scroll_offset + delta * 30, total_w - canvas_w + 50))
        self._redraw()

    def _scroll_left(self, e=None) -> None:
        self._scroll_offset = max(0, self._scroll_offset - 80)
        self._redraw()

    def _scroll_right(self, e=None) -> None:
        self._scroll_offset += 80
        self._redraw()

    def _hit_test(self, x: float) -> str | None:
        """返回指定 x 坐标处命中的标签 id。"""
        for tab_id, info in self._layout.items():
            if info['x1'] <= x <= info['x2']:
                return tab_id
        return None

    def _on_close_button(self, x: float, tab_id: str) -> bool:
        """检查 x 是否落在 tab_id 的关闭按钮范围内。"""
        info = self._layout.get(tab_id)
        if not info:
            return False
        close_x = info['x2'] - self.CLOSE_SIZE - self.CLOSE_OFFSET
        return close_x <= x <= info['x2']

    # ------------------------------------------------------------------
    # 主题跟随
    # ------------------------------------------------------------------

    def _apply_theme(self) -> None:
        self._canvas.config(bg=str(theme.BG_TITLE))
        self._left_btn.config(bg=str(theme.BG_TITLE), fg=str(theme.FG_SECONDARY))
        self._right_btn.config(bg=str(theme.BG_TITLE), fg=str(theme.FG_SECONDARY))
        self._redraw()
