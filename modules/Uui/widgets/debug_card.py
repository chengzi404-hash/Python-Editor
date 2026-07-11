"""``modules.Uui.widgets.debug_card`` — 调试卡片.

显示调试信息: 变量、调用栈、断点.
"""

from __future__ import annotations

import tkinter as tk
from typing import Any, Callable, Dict, List, Optional

from . import theme
from .frame import UFrame
from .label import ULabel
from .list_view import UListView


class DebugCard(UFrame):
    """Debug 侧边栏卡片, 显示变量/调用栈/断点."""

    def __init__(
        self,
        parent,
        *,
        title: str = 'DEBUG',
        on_breakpoint_click: Optional[Callable[[str, int], None]] = None,
        **kwargs,
    ) -> None:
        kwargs.setdefault('variant', 'panel')
        super().__init__(parent, **kwargs)

        self._title = title
        self._on_breakpoint_click = on_breakpoint_click
        self._is_running = False
        self._variables: List[Dict[str, str]] = []
        self._call_stack: List[Dict[str, str]] = []
        self._breakpoints: List[Dict[str, Any]] = []

        self._build()

    def _build(self) -> None:
        # 标题头
        header = UFrame(self, variant='title', height=26)
        header.pack(fill=tk.X)
        header.pack_propagate(False)

        self._title_label = ULabel(
            header, text=f'  {self._title}',
            variant='secondary', bg=theme.BG_TITLE,
        )
        self._title_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # 状态标签
        self._status_frame = tk.Frame(self, bg=theme.BG_PANEL, height=24)
        self._status_frame.pack(fill=tk.X, pady=(4, 4))
        self._status_frame.pack_propagate(False)

        self._status_indicator = tk.Frame(self._status_frame, width=8, bg=theme.FG_TERTIARY)
        self._status_indicator.pack(side=tk.LEFT, fill=tk.Y, padx=(8, 4))

        self._status_label = ULabel(
            self._status_frame, text='Not Running',
            variant='secondary', bg=theme.BG_PANEL,
        )
        self._status_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))

        # 调试控制按钮
        control_frame = tk.Frame(self, bg=theme.BG_PANEL, height=32)
        control_frame.pack(fill=tk.X, padx=4, pady=(0, 4))
        control_frame.pack_propagate(False)

        btn_kwargs = {'bg': theme.BG_RAISED, 'fg': theme.FG_PRIMARY,
                     'font': theme.LABEL_FONT_SMALL, 'relief': 'flat',
                     'cursor': 'hand2', 'activebackground': theme.BG_HOVER,
                     'activeforeground': theme.FG_PRIMARY}

        self._btn_continue = tk.Button(control_frame, text='▶ Continue', **btn_kwargs)
        self._btn_continue.pack(side=tk.LEFT, padx=2)
        self._btn_continue.bind('<Button-1>', lambda _: self._on_continue())

        self._btn_step = tk.Button(control_frame, text='⤷ Step', **btn_kwargs)
        self._btn_step.pack(side=tk.LEFT, padx=2)
        self._btn_step.bind('<Button-1>', lambda _: self._on_step())

        self._btn_stop = tk.Button(control_frame, text='⬛ Stop', **btn_kwargs)
        self._btn_stop.pack(side=tk.LEFT, padx=2)
        self._btn_stop.bind('<Button-1>', lambda _: self._on_stop())

        # 变量面板
        self._variables_panel_frame = tk.Frame(self, bg=theme.BG_PANEL)
        self._build_section('VARIABLES', self._variables_panel_frame)
        self._variables_view = UListView(
            self._variables_panel_frame, columns=['Name', 'Value'],
            column_widths={'Name': 120, 'Value': 120},
            show_header=True,
        )
        self._variables_view.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        # 调用栈面板
        self._stack_panel_frame = tk.Frame(self, bg=theme.BG_PANEL)
        self._build_section('CALL STACK', self._stack_panel_frame)
        self._call_stack_view = UListView(
            self._stack_panel_frame, columns=['#', 'Function', 'Location'],
            column_widths={'#': 30, 'Function': 100, 'Location': 100},
            show_header=True,
        )
        self._call_stack_view.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        # 断点面板
        self._breakpoints_panel_frame = tk.Frame(self, bg=theme.BG_PANEL)
        self._build_section('BREAKPOINTS', self._breakpoints_panel_frame)
        self._breakpoints_view = UListView(
            self._breakpoints_panel_frame, columns=['', 'File', 'Line'],
            column_widths={'': 20, 'File': 120, 'Line': 40},
            show_header=True,
        )
        self._breakpoints_view.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

    def _build_section(self, title: str, frame: tk.Frame) -> None:
        section_header = tk.Frame(frame, bg=theme.BG_TITLE, height=22)
        section_header.pack(fill=tk.X)
        section_header.pack_propagate(False)
        tk.Label(
            section_header, text=f'  {title}', bg=theme.BG_TITLE,
            fg=theme.FG_SECONDARY, font=theme.LABEL_FONT_SMALL,
            anchor='w',
        ).pack(side=tk.LEFT, fill=tk.X, expand=True)

    def set_debug_state(self, state: str) -> None:
        """设置调试状态: 'stopped', 'running', 'paused'."""
        self._is_running = state != 'stopped'
        if state == 'running':
            self._status_indicator.config(bg=theme.GREEN)
            self._status_label.config(text='Running')
        elif state == 'paused':
            self._status_indicator.config(bg=theme.YELLOW)
            self._status_label.config(text='Paused')
        else:
            self._status_indicator.config(bg=theme.FG_TERTIARY)
            self._status_label.config(text='Not Running')

    def set_variables(self, variables: List[Dict[str, str]]) -> None:
        self._variables = variables
        self._variables_view.set_data(variables)

    def set_call_stack(self, stack: List[Dict[str, str]]) -> None:
        self._call_stack = stack
        self._call_stack_view.set_data(stack)

    def set_breakpoints(self, breakpoints: List[Dict[str, Any]]) -> None:
        self._breakpoints = breakpoints
        data = []
        for bp in breakpoints:
            data.append({
                '': '●' if bp.get('enabled', True) else '○',
                'File': bp.get('file', ''),
                'Line': str(bp.get('line', '')),
            })
        self._breakpoints_view.set_data(data)

    def _on_continue(self):
        pass  # 调试控制回调,可由外部设置

    def _on_step(self):
        pass

    def _on_stop(self):
        pass

    def _apply_theme(self) -> None:
        try:
            super()._apply_theme()
        except tk.TclError:
            pass
        self._title_label.config(bg=theme.BG_TITLE, fg=theme.FG_SECONDARY)
        self._status_frame.config(bg=theme.BG_PANEL)
        self._status_label.config(bg=theme.BG_PANEL)


__all__ = ['DebugCard']
