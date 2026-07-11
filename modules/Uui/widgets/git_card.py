"""``modules.Uui.widgets.git_card`` — Git 源代码管理卡片.

显示当前分支、变更文件、暂存区状态.
"""

from __future__ import annotations

import subprocess
import tkinter as tk
from typing import Callable, List, Optional

from . import theme
from .frame import UFrame
from .label import ULabel
from .list_view import UListView


class GitCard(UFrame):
    """Git 侧边栏卡片, 显示分支和变更文件."""

    def __init__(
        self,
        parent,
        *,
        title: str = 'SOURCE CONTROL',
        workspace_root: Optional[str] = None,
        on_file_click: Optional[Callable[[str], None]] = None,
        **kwargs,
    ) -> None:
        kwargs.setdefault('variant', 'panel')
        super().__init__(parent, **kwargs)

        self._title = title
        self._workspace_root = workspace_root or ''
        self._on_file_click = on_file_click
        self._branch = ''
        self._staged: List[dict] = []
        self._unstaged: List[dict] = []

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

        # 分支信息
        branch_frame = tk.Frame(self, bg=theme.BG_PANEL, height=28)
        branch_frame.pack(fill=tk.X, padx=8, pady=(4, 4))
        branch_frame.pack_propagate(False)

        self._branch_icon = tk.Label(
            branch_frame, text='🔀', font=('', 10),
            bg=theme.BG_PANEL, fg=theme.FG_PRIMARY,
        )
        self._branch_icon.pack(side=tk.LEFT, padx=(0, 4))

        self._branch_label = ULabel(
            branch_frame, text='No repository',
            variant='primary', bg=theme.BG_PANEL,
        )
        self._branch_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # 操作按钮
        action_frame = tk.Frame(self, bg=theme.BG_PANEL, height=28)
        action_frame.pack(fill=tk.X, padx=4, pady=(0, 4))
        action_frame.pack_propagate(False)

        btn_kwargs = {
            'bg': theme.BG_RAISED, 'fg': theme.FG_PRIMARY,
            'font': theme.LABEL_FONT_SMALL, 'relief': 'flat',
            'cursor': 'hand2', 'activebackground': theme.BG_HOVER,
            'activeforeground': theme.FG_PRIMARY,
        }

        self._btn_commit = tk.Button(action_frame, text='✓ Commit', **btn_kwargs)
        self._btn_commit.pack(side=tk.LEFT, padx=2)
        self._btn_commit.bind('<Button-1>', lambda _: self._on_commit())

        self._btn_refresh = tk.Button(action_frame, text='↻', width=3, **btn_kwargs)
        self._btn_refresh.pack(side=tk.LEFT, padx=2)
        self._btn_refresh.bind('<Button-1>', lambda _: self.refresh())

        # 暂存区面板
        self._staged_frame = tk.Frame(self, bg=theme.BG_PANEL)
        self._build_section('STAGED CHANGES', self._staged_frame)
        self._staged_view = UListView(
            self._staged_frame, columns=['', 'File'],
            column_widths={'': 16, 'File': 200},
            show_header=False,
        )
        self._staged_view.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        # 未暂存面板
        self._unstaged_frame = tk.Frame(self, bg=theme.BG_PANEL)
        self._build_section('CHANGES', self._unstaged_frame)
        self._unstaged_view = UListView(
            self._unstaged_frame, columns=['', 'File'],
            column_widths={'': 16, 'File': 200},
            show_header=False,
        )
        self._unstaged_view.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

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
        self._workspace_root = path
        self.refresh()

    def refresh(self) -> None:
        """刷新 Git 状态."""
        if not self._workspace_root:
            return

        try:
            # 获取当前分支
            result = subprocess.run(
                ['git', 'branch', '--show-current'],
                cwd=self._workspace_root,
                capture_output=True, text=True, timeout=5,
            )
            self._branch = result.stdout.strip()
            if self._branch:
                self._branch_label.config(text=self._branch)
            else:
                self._branch_label.config(text='( detached )')

            # 获取变更状态
            result = subprocess.run(
                ['git', 'status', '--porcelain=v1'],
                cwd=self._workspace_root,
                capture_output=True, text=True, timeout=5,
            )
            self._parse_git_status(result.stdout)
        except Exception:
            self._branch_label.config(text='No repository')
            self._staged_view.set_data([])
            self._unstaged_view.set_data([])

    def _parse_git_status(self, output: str) -> None:
        staged = []
        unstaged = []

        for line in output.splitlines():
            if len(line) < 3:
                continue
            status = line[:2]
            filepath = line[3:]

            entry = {'': self._status_icon(status), 'File': filepath}

            if status[0] in 'MADRC':  # Staged changes
                staged.append(entry)
            # Both staged and unstaged for some statuses
            if status[1] in 'MADRC':
                unstaged.append(entry)
            elif status[0] in '??':  # Untracked
                unstaged.append(entry)

        self._staged = staged
        self._unstaged = unstaged
        self._staged_view.set_data(staged)
        self._unstaged_view.set_data(unstaged)

    def _status_icon(self, status: str) -> str:
        """获取状态图标."""
        s = status.strip()
        if not s:
            return ' '
        first = s[0]
        icons = {
            'M': '📝', 'A': '➕', 'D': '➖', 'R': '📛', 'C': '📋',
        }
        if first in icons:
            return icons[first]
        if s == '??':
            return '❓'
        return '✏️'

    def _on_commit(self):
        # 简单的 commit 回调,实际实现需要弹窗输入 commit message
        pass

    def get_branch(self) -> str:
        return self._branch

    def _apply_theme(self) -> None:
        try:
            super()._apply_theme()
        except tk.TclError:
            pass
        self._title_label.config(bg=theme.BG_TITLE, fg=theme.FG_SECONDARY)
        self._branch_label.config(bg=theme.BG_PANEL)
        self._branch_icon.config(bg=theme.BG_PANEL)


__all__ = ['GitCard']
