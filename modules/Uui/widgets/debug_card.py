"""``modules.Uui.widgets.debug_card`` — 调试卡片.

显示调试信息: 变量、调用栈、断点,并支持调试控制.
"""

from __future__ import annotations

import contextlib
import os
import subprocess
import threading
import tkinter as tk
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from . import theme
from .frame import UFrame
from .label import ULabel
from .list_view import UListView


@dataclass
class DebugLocation:
    """调试位置信息."""
    file: str
    line: int
    function: str = ''


@dataclass
class VariableInfo:
    """变量信息."""
    name: str
    value: str
    type: str = ''


class DebugSession:
    """调试会话管理器."""

    def __init__(self, workspace_root: str):
        self._workspace_root = workspace_root
        self._process: subprocess.Popen | None = None
        self._thread: threading.Thread | None = None
        self._running = False
        self._paused = False
        self._stopped = False

        self._variables: list[VariableInfo] = []
        self._call_stack: list[DebugLocation] = []
        self._breakpoints: dict[str, list[int]] = {}  # file -> [lines]

        self._on_state_change: Callable[[str], None] | None = None
        self._on_variables_change: Callable[[list[VariableInfo]], None] | None = None
        self._on_stack_change: Callable[[list[DebugLocation]], None] | None = None
        self._on_output: Callable[[str, str], None] | None = None

    def set_callbacks(
        self,
        on_state_change: Callable[[str], None] | None = None,
        on_variables_change: Callable[[list[VariableInfo]], None] | None = None,
        on_stack_change: Callable[[list[DebugLocation]], None] | None = None,
        on_output: Callable[[str, str], None] | None = None,
    ):
        self._on_state_change = on_state_change
        self._on_variables_change = on_variables_change
        self._on_stack_change = on_stack_change
        self._on_output = on_output

    def add_breakpoint(self, file: str, line: int) -> None:
        if file not in self._breakpoints:
            self._breakpoints[file] = []
        if line not in self._breakpoints[file]:
            self._breakpoints[file].append(line)

    def remove_breakpoint(self, file: str, line: int) -> None:
        if file in self._breakpoints and line in self._breakpoints[file]:
            self._breakpoints[file].remove(line)

    def clear_breakpoints(self) -> None:
        self._breakpoints.clear()

    def get_breakpoints(self) -> dict[str, list[int]]:
        return self._breakpoints.copy()

    def start(self, file: str, args: str = '') -> bool:
        """启动调试会话."""
        if self._running:
            return False

        self._stopped = False
        self._paused = False

        # 构建断点参数
        breakpoint_args = []
        for bp_file, lines in self._breakpoints.items():
            for line in lines:
                breakpoint_args.extend(['-c', f'break {bp_file}:{line}'])

        cmd = ['python', '-u', '-m', 'pdb', *breakpoint_args, file]

        if args:
            cmd.extend(args.split())

        try:
            self._process = subprocess.Popen(
                cmd,
                cwd=self._workspace_root,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=subprocess.PIPE,
                text=True,
                bufsize=1,
            )
            self._running = True
            self._notify_state_change('running')

            self._thread = threading.Thread(target=self._read_output, daemon=True)
            self._thread.start()

            return True
        except Exception:
            return False

    def _read_output(self) -> None:
        """读取调试器输出."""
        if not self._process or not self._process.stdout:
            return

        try:
            for line in self._process.stdout:
                if not line:
                    break

                stripped = line.strip()

                # 检测调试器提示符
                if '(Pdb)' in stripped or '->' in stripped:
                    self._paused = True
                    self._notify_state_change('paused')
                    self._parse_stack()

                # 检测程序结束
                if 'The program finished' in stripped or 'Program exited' in stripped:
                    self._running = False
                    self._paused = False
                    self._notify_state_change('stopped')
                    break

                # 输出
                if self._on_output:
                    self._on_output('stdout', line)

        except Exception:
            pass
        finally:
            self._running = False
            self._paused = False
            self._notify_state_change('stopped')

    def _parse_stack(self) -> None:
        """解析调用栈."""
        if not self._process or not self._running:
            return

        try:
            if self._process and self._process.stdin:
                self._process.stdin.write('w\n')
                self._process.stdin.flush()

                # 读取栈信息(简化处理)
                self._call_stack = []

                # 获取变量
                self._process.stdin.write('locals\n')
                self._process.stdin.flush()
                self._variables = []

        except Exception:
            pass

    def send_command(self, cmd: str) -> None:
        """发送调试命令."""
        if not self._process or not self._running:
            return

        proc_stdin = self._process.stdin
        if not proc_stdin:
            return

        try:
            proc_stdin.write(cmd + '\n')
            proc_stdin.flush()

            if cmd == 'c' or cmd == 'continue':
                self._paused = False
                self._notify_state_change('running')
            elif cmd in ('n', 'next', 's', 'step', 'q', 'quit'):
                self._running = False
                self._paused = False
                self._notify_state_change('stopped')

        except Exception:
            pass

    def step_over(self) -> None:
        """单步跳过."""
        self.send_command('n')

    def step_into(self) -> None:
        """单步进入."""
        self.send_command('s')

    def continue_(self) -> None:
        """继续执行."""
        self.send_command('c')

    def stop(self) -> None:
        """停止调试."""
        self._running = False
        self._stopped = True
        if self._process:
            with contextlib.suppress(Exception):
                self._process.terminate()
        self._notify_state_change('stopped')

    def is_running(self) -> bool:
        return self._running

    def is_paused(self) -> bool:
        return self._paused

    def _notify_state_change(self, state: str) -> None:
        if self._on_state_change:
            self._on_state_change(state)

    def set_variables(self, variables: list[VariableInfo]) -> None:
        self._variables = variables
        if self._on_variables_change:
            self._on_variables_change(variables)

    def set_call_stack(self, stack: list[DebugLocation]) -> None:
        self._call_stack = stack
        if self._on_stack_change:
            self._on_stack_change(stack)


class DebugCard(UFrame):
    """Debug 侧边栏卡片, 显示变量/调用栈/断点."""

    def __init__(
        self,
        parent,
        *,
        title: str = 'DEBUG',
        workspace_root: str | None = None,
        on_breakpoint_click: Callable[[str, int], None] | None = None,
        on_debug_output: Callable[[str, str], None] | None = None,
        **kwargs,
    ) -> None:
        kwargs.setdefault('variant', 'panel')
        super().__init__(parent, **kwargs)

        self._title = title
        self._workspace_root = workspace_root or ''
        self._on_breakpoint_click = on_breakpoint_click
        self._on_debug_output: Callable[[str, str], None] | None = on_debug_output
        self._session: DebugSession | None = None

        self._variables: list[dict[str, str]] = []
        self._call_stack: list[dict[str, str]] = []
        self._breakpoints: list[dict[str, Any]] = []

        self._build()

    def _build(self) -> None:
        # 标题头
        header = UFrame(self, variant='title', height=26)
        header.pack(fill=tk.X)
        header.pack_propagate(False)

        # 左侧 accent 条 —— 与其他卡片保持一致的视觉锚点
        self._title_accent = tk.Frame(
            header, bg=theme.TITLE_ACCENT, width=theme.TITLE_ACCENT_WIDTH,
        )
        self._title_accent.pack(side=tk.LEFT, fill=tk.Y)

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
            self._status_frame, text='Ready',
            variant='secondary', bg=theme.BG_PANEL,
        )
        self._status_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))

        # 调试控制按钮
        control_frame = tk.Frame(self, bg=theme.BG_PANEL, height=32)
        control_frame.pack(fill=tk.X, padx=4, pady=(0, 4))
        control_frame.pack_propagate(False)

        btn_kwargs = {
            'bg': theme.BG_RAISED, 'fg': theme.FG_PRIMARY,
            'font': theme.LABEL_FONT_SMALL, 'relief': 'flat',
            'cursor': 'hand2', 'activebackground': theme.BG_HOVER,
            'activeforeground': theme.FG_PRIMARY,
        }

        self._btn_start = tk.Button(control_frame, text='▶ Start', width=7, **btn_kwargs)
        self._btn_start.pack(side=tk.LEFT, padx=2)
        self._btn_start.bind('<Button-1>', lambda _: self._on_start())

        self._btn_continue = tk.Button(control_frame, text='▶ Continue', width=8, **btn_kwargs)
        self._btn_continue.pack(side=tk.LEFT, padx=2)
        self._btn_continue.bind('<Button-1>', lambda _: self._on_continue())
        self._btn_continue.config(state='disabled')

        self._btn_step_over = tk.Button(control_frame, text='⤷ Over', width=6, **btn_kwargs)
        self._btn_step_over.pack(side=tk.LEFT, padx=2)
        self._btn_step_over.bind('<Button-1>', lambda _: self._on_step_over())
        self._btn_step_over.config(state='disabled')

        self._btn_step_into = tk.Button(control_frame, text='⤵ Into', width=6, **btn_kwargs)
        self._btn_step_into.pack(side=tk.LEFT, padx=2)
        self._btn_step_into.bind('<Button-1>', lambda _: self._on_step_into())
        self._btn_step_into.config(state='disabled')

        self._btn_stop = tk.Button(control_frame, text='⬛ Stop', width=6, **btn_kwargs)
        self._btn_stop.pack(side=tk.LEFT, padx=2)
        self._btn_stop.bind('<Button-1>', lambda _: self._on_stop())
        self._btn_stop.config(state='disabled')

        # 面板容器 (使用 grid 布局管理器)
        panels_frame = tk.Frame(self, bg=theme.BG_PANEL)
        panels_frame.pack(fill=tk.BOTH, expand=True, side=tk.BOTTOM)

        # 变量面板
        self._variables_panel_frame = tk.Frame(panels_frame, bg=theme.BG_PANEL)
        self._variables_panel_frame.grid(row=0, column=0, sticky='nsew')
        self._build_section('VARIABLES', self._variables_panel_frame)
        self._variables_view = UListView(
            self._variables_panel_frame, columns=['Name', 'Value'],
            column_widths={'Name': 120, 'Value': 120},
            show_header=True,
        )
        self._variables_view.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        # 调用栈面板
        self._stack_panel_frame = tk.Frame(panels_frame, bg=theme.BG_PANEL)
        self._stack_panel_frame.grid(row=1, column=0, sticky='nsew')
        self._build_section('CALL STACK', self._stack_panel_frame)
        self._call_stack_view = UListView(
            self._stack_panel_frame, columns=['#', 'Function', 'Location'],
            column_widths={'#': 30, 'Function': 100, 'Location': 100},
            show_header=True,
        )
        self._call_stack_view.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        # 断点面板
        self._breakpoints_panel_frame = tk.Frame(panels_frame, bg=theme.BG_PANEL)
        self._breakpoints_panel_frame.grid(row=2, column=0, sticky='nsew')
        self._build_section('BREAKPOINTS', self._breakpoints_panel_frame)
        self._breakpoints_view = UListView(
            self._breakpoints_panel_frame, columns=['', 'File', 'Line'],
            column_widths={'': 20, 'File': 120, 'Line': 40},
            show_header=True,
        )
        self._breakpoints_view.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        self._breakpoints_view._on_select_cb = self._on_breakpoint_select  # type: ignore

        # Grid weight for equal distribution
        panels_frame.grid_rowconfigure(0, weight=1)
        panels_frame.grid_rowconfigure(1, weight=1)
        panels_frame.grid_rowconfigure(2, weight=1)
        panels_frame.grid_columnconfigure(0, weight=1)

    def _build_section(self, title: str, frame: tk.Frame) -> None:
        section_header = tk.Frame(frame, bg=theme.BG_TITLE, height=22)
        section_header.pack(fill=tk.X)
        section_header.pack_propagate(False)
        tk.Label(
            section_header, text=f'  {title}', bg=theme.BG_TITLE,
            fg=theme.FG_SECONDARY, font=theme.LABEL_FONT_SMALL,
            anchor='w',
        ).pack(side=tk.LEFT, fill=tk.X, expand=True)

    def set_workspace_root(self, path: str) -> None:
        """设置工作区根目录."""
        self._workspace_root = path
        if self._session:
            self._session._workspace_root = path

    def set_debug_state(self, state: str) -> None:
        """设置调试状态: 'stopped', 'running', 'paused'."""
        if state == 'running':
            self._status_indicator.config(bg=theme.GREEN)
            self._status_label.config(text='Running')
            self._enable_running_controls()
        elif state == 'paused':
            self._status_indicator.config(bg=theme.YELLOW)
            self._status_label.config(text='Paused')
            self._enable_paused_controls()
        else:
            self._status_indicator.config(bg=theme.FG_TERTIARY)
            self._status_label.config(text='Ready')
            self._enable_stopped_controls()

    def _enable_stopped_controls(self) -> None:
        self._btn_start.config(state='normal')
        self._btn_continue.config(state='disabled')
        self._btn_step_over.config(state='disabled')
        self._btn_step_into.config(state='disabled')
        self._btn_stop.config(state='disabled')

    def _enable_running_controls(self) -> None:
        self._btn_start.config(state='disabled')
        self._btn_continue.config(state='normal')
        self._btn_step_over.config(state='normal')
        self._btn_step_into.config(state='normal')
        self._btn_stop.config(state='normal')

    def _enable_paused_controls(self) -> None:
        self._btn_start.config(state='disabled')
        self._btn_continue.config(state='normal')
        self._btn_step_over.config(state='normal')
        self._btn_step_into.config(state='normal')
        self._btn_stop.config(state='normal')

    def set_variables(self, variables: list[dict[str, str]]) -> None:
        self._variables = variables
        self._variables_view.set_data(variables)

    def set_call_stack(self, stack: list[dict[str, str]]) -> None:
        self._call_stack = stack
        self._call_stack_view.set_data(stack)

    def set_breakpoints(self, breakpoints: list[dict[str, Any]]) -> None:
        self._breakpoints = breakpoints
        data = []
        for bp in breakpoints:
            data.append({
                '': '●' if bp.get('enabled', True) else '○',
                'File': bp.get('file', ''),
                'Line': str(bp.get('line', '')),
            })
        self._breakpoints_view.set_data(data)

    def add_breakpoint(self, file: str, line: int) -> None:
        """添加断点."""
        if not self._session:
            self._session = DebugSession(self._workspace_root)
        self._session.add_breakpoint(file, line)
        self._refresh_breakpoints()

    def remove_breakpoint(self, file: str, line: int) -> None:
        """移除断点."""
        if self._session:
            self._session.remove_breakpoint(file, line)
            self._refresh_breakpoints()

    def clear_breakpoints(self) -> None:
        """清除所有断点."""
        if self._session:
            self._session.clear_breakpoints()
            self._refresh_breakpoints()

    def _refresh_breakpoints(self) -> None:
        if not self._session:
            return
        bp_dict = self._session.get_breakpoints()
        bp_list = []
        for file_path, lines in bp_dict.items():
            file_name = os.path.basename(file_path)
            for line in lines:
                bp_list.append({'file': file_name, 'line': line, 'enabled': True})
        self.set_breakpoints(bp_list)

    def _on_breakpoint_select(
        self,
        index: int,  # pyright: ignore[reportUnusedParameter]
        row: dict,
    ) -> None:  # type: ignore[assignment]
        if self._on_breakpoint_click and row.get('File') and row.get('Line'):
            self._on_breakpoint_click(row['File'], int(row['Line']))

    def _on_start(self) -> None:
        """开始调试当前文件."""
        if not self._workspace_root:
            return

        # 获取当前打开的文件
        if hasattr(self, '_current_file') and self._current_file:
            file_to_debug = self._current_file
        else:
            # 查找 Python 文件
            file_to_debug = None
            for f in os.listdir(self._workspace_root):
                if f.endswith('.py'):
                    file_to_debug = os.path.join(self._workspace_root, f)
                    break

        if not file_to_debug:
            return

        self._start_debug_session(file_to_debug)

    def _start_debug_session(self, file: str) -> None:
        """启动调试会话."""
        if not self._session:
            self._session = DebugSession(self._workspace_root)
            self._session.set_callbacks(
                on_state_change=self._on_session_state_change,
                on_variables_change=self._on_variables_changed,
                on_stack_change=self._on_stack_changed,
                on_output=self._handle_debug_output,
            )

        if self._session.start(file):
            self.set_debug_state('running')

    def _on_session_state_change(self, state: str) -> None:
        self.after(0, lambda: self.set_debug_state(state))

    def _on_variables_changed(self, variables: list[VariableInfo]) -> None:
        data = [{'Name': v.name, 'Value': v.value} for v in variables]
        self.after(0, lambda: self.set_variables(data))

    def _on_stack_changed(self, stack: list[DebugLocation]) -> None:
        data = []
        for i, loc in enumerate(stack):
            data.append({
                '#': str(i),
                'Function': loc.function or '?',
                'Location': f'{os.path.basename(loc.file)}:{loc.line}',
            })
        self.after(0, lambda: self.set_call_stack(data))

    def _handle_debug_output(self, stream: str, line: str) -> None:
        callback = self._on_debug_output
        if callback:
            self.after(0, lambda: callback(stream, line))

    def _on_continue(self) -> None:
        if self._session:
            self._session.continue_()

    def _on_step_over(self) -> None:
        if self._session:
            self._session.step_over()

    def _on_step_into(self) -> None:
        if self._session:
            self._session.step_into()

    def _on_stop(self) -> None:
        if self._session:
            self._session.stop()
        self.set_debug_state('stopped')

    def set_current_file(self, file: str) -> None:
        """设置当前调试的文件."""
        self._current_file = file

    def _apply_theme(self) -> None:
        with contextlib.suppress(tk.TclError):
            super()._apply_theme()
        self._title_label.config(bg=theme.BG_TITLE, fg=theme.FG_SECONDARY)
        if hasattr(self, '_title_accent'):
            self._title_accent.config(bg=theme.TITLE_ACCENT)
        self._status_frame.config(bg=theme.BG_PANEL)
        self._status_label.config(bg=theme.BG_PANEL)


__all__ = ['DebugCard', 'DebugLocation', 'DebugSession', 'VariableInfo']
