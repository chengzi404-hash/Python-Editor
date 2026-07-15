"""``modules.Uui.widgets.git_card`` — Git 源代码管理卡片.

显示当前分支(含 ahead/behind 远程跟踪)、变更文件、内联提交编辑器,
并支持 Commit / Push / Pull / Refresh 操作.

Public API
----------
* ``set_workspace_root(path)`` —— 设置工作区根目录并刷新
* ``set_on_file_click(callback)`` —— 设置文件点击回调 ``(filepath, status)``
* ``refresh()`` —— 重新拉取 Git 状态
* ``get_branch()`` / ``has_staged_changes()`` / ``get_staged_count()`` /
  ``get_unstaged_count()`` —— 只读访问器
"""

from __future__ import annotations

import contextlib
import subprocess
import tkinter as tk
from collections.abc import Callable

from . import theme
from .button import UButton
from .frame import UFrame
from .label import ULabel
from .list_view import UListView
from .message_box import showerror, showinfo

# 视觉常量
_TITLE_HEIGHT = 28
_COMPOSER_HEIGHT = 3     # Text widget 行数
_STATUS_HEIGHT = 22
_SECTION_HEADER_HEIGHT = 26
_PANEL_PADDING_X = 10


class GitCard(UFrame):
    """Git 侧边栏卡片.

    自上而下的视觉层次:

    1. 标题栏(带左侧蓝色 accent)
    2. 分支信息行 + 远程跟踪 chip
    3. 操作工具栏(主提交按钮 + 推送 / 拉取 / 刷新)
    4. 内联提交编辑器(多行 + Amend + Ctrl+Enter 提交)
    5. 状态条(状态点 + 计数摘要)
    6. 已暂存列表(weight=2)
    7. 变更列表(weight=3)
    """

    def __init__(
        self,
        parent,
        *,
        title: str = 'SOURCE CONTROL',
        workspace_root: str | None = None,
        on_file_click: Callable[[str, str], None] | None = None,
        on_refresh: Callable[[], None] | None = None,
        **kwargs,
    ) -> None:
        kwargs.setdefault('variant', 'panel')
        super().__init__(parent, **kwargs)

        self._title = title
        self._workspace_root = workspace_root or ''
        self._on_file_click = on_file_click
        self._on_refresh = on_refresh

        self._branch = ''
        self._has_remote = False
        self._ahead = 0
        self._behind = 0
        self._last_commit_subject = ''

        self._staged: list[dict] = []
        self._unstaged: list[dict] = []

        # 提交编辑器状态
        self._msg_placeholder = 'Message  (Ctrl+Enter to commit)'
        self._has_placeholder = True

        self._build()

    # ─────────────────────────── build ───────────────────────────

    def _build(self) -> None:
        self._build_title_bar()
        self._build_branch_row()
        self._build_toolbar()
        self._build_commit_composer()
        self._build_status_row()
        self._build_lists()

    # —— 标题栏 —— #

    def _build_title_bar(self) -> None:
        header = tk.Frame(self, bg=theme.BG_TITLE, height=_TITLE_HEIGHT)
        header.pack(fill=tk.X)
        header.pack_propagate(False)

        # 左侧 accent 条 —— 视觉锚点(颜色/宽度在 theme.TITLE_ACCENT*)
        self._title_accent = tk.Frame(
            header, bg=theme.TITLE_ACCENT, width=theme.TITLE_ACCENT_WIDTH,
        )
        self._title_accent.pack(side=tk.LEFT, fill=tk.Y)

        self._title_label = ULabel(
            header, text=f'  {self._title}',
            variant='secondary', bg=theme.BG_TITLE,
            font=theme.LABEL_FONT_BOLD,
        )
        self._title_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

    # —— 分支信息行 —— #

    def _build_branch_row(self) -> None:
        row = tk.Frame(self, bg=theme.BG_PANEL)
        row.pack(fill=tk.X, padx=_PANEL_PADDING_X, pady=(10, 6))

        # 分支图标(绘制)
        self._branch_icon_canvas = tk.Canvas(
            row, width=16, height=16,
            bg=theme.BG_PANEL, highlightthickness=0, bd=0,
        )
        self._branch_icon_canvas.pack(side=tk.LEFT, padx=(0, 6))
        self._draw_branch_icon()

        # 分支名(mono 字体,体现"代码/标识符"语义)
        self._branch_label = ULabel(
            row, text='No repository',
            variant='primary', bg=theme.BG_PANEL,
            font=theme.MONO_FONT,
        )
        self._branch_label.pack(side=tk.LEFT)

        # 右侧 tracking chip(ahead/behind)
        self._ahead_chip = self._make_chip(row, color=theme.GREEN)
        self._ahead_chip.pack(side=tk.RIGHT, padx=(4, 0))
        self._ahead_chip.pack_forget()

        self._behind_chip = self._make_chip(row, color=theme.YELLOW)
        self._behind_chip.pack(side=tk.RIGHT, padx=(4, 0))
        self._behind_chip.pack_forget()

    # —— 操作工具栏 —— #

    def _build_toolbar(self) -> None:
        bar = tk.Frame(self, bg=theme.BG_PANEL)
        bar.pack(fill=tk.X, padx=_PANEL_PADDING_X, pady=(0, 6))

        # 主操作:Commit(蓝色填充,variant='primary')
        self._btn_commit = UButton(
            bar, text='✓ Commit',
            command=self._on_commit,
            variant='primary', width=88, height=26, radius=4,
        )
        self._btn_commit.pack(side=tk.LEFT)
        self._btn_commit.config(state='disabled')

        # 远端:刷新(右侧)
        self._btn_refresh = UButton(
            bar, text='↻',
            command=self.refresh,
            variant='ghost', width=30, height=26, radius=4,
        )
        self._btn_refresh.pack(side=tk.RIGHT)

        # 次要组:Pull / Push(右对齐,从右向左)
        self._btn_pull = UButton(
            bar, text='↓ Pull',
            command=self._on_pull,
            variant='default', width=64, height=26, radius=4,
        )
        self._btn_pull.pack(side=tk.RIGHT, padx=(6, 0))

        self._btn_push = UButton(
            bar, text='↑ Push',
            command=self._on_push,
            variant='default', width=64, height=26, radius=4,
        )
        self._btn_push.pack(side=tk.RIGHT, padx=(6, 0))

    # —— 内联提交编辑器 —— #

    def _build_commit_composer(self) -> None:
        wrap = tk.Frame(self, bg=theme.BG_PANEL)
        wrap.pack(fill=tk.X, padx=_PANEL_PADDING_X, pady=(0, 6))

        # 边框层(用 tk.Frame 模拟 focus ring,grid 包裹真正的 Text)
        composer_frame = tk.Frame(
            wrap, bg=theme.BORDER, bd=0, highlightthickness=0,
        )
        composer_frame.pack(fill=tk.X)

        self._msg_var = tk.StringVar()
        self._msg_text = tk.Text(
            composer_frame,
            height=_COMPOSER_HEIGHT,
            bg=theme.BG_INPUT, fg=theme.FG_TERTIARY,
            insertbackground=theme.FG_PRIMARY,
            selectbackground=theme.BLUE,
            selectforeground=theme.FG_PRIMARY,
            relief='flat', highlightthickness=0, bd=0,
            font=theme.LABEL_FONT, wrap='word',
            padx=8, pady=6,
            undo=True,
        )
        self._msg_text.pack(fill=tk.X, expand=True, padx=1, pady=1)
        self._msg_text.insert('1.0', self._msg_placeholder)

        # placeholder 行为
        self._msg_text.bind('<FocusIn>', self._on_msg_focus_in)
        self._msg_text.bind('<FocusOut>', self._on_msg_focus_out)
        self._msg_text.bind('<Key>', self._on_msg_key)
        self._msg_text.bind('<Control-Return>', lambda _: self._on_commit())
        self._msg_text.bind('<Button-1>', self._on_msg_focus_in, add='+')

        # 底部行:Amend + 快捷键提示
        footer = tk.Frame(wrap, bg=theme.BG_PANEL)
        footer.pack(fill=tk.X, pady=(4, 0))

        self._amend_var = tk.BooleanVar(value=False)
        self._amend_check = tk.Checkbutton(
            footer, text='Amend last commit',
            variable=self._amend_var,
            bg=theme.BG_PANEL, fg=theme.FG_SECONDARY,
            selectcolor=theme.BG_PANEL,
            activebackground=theme.BG_PANEL,
            activeforeground=theme.FG_PRIMARY,
            font=theme.LABEL_FONT_SMALL,
            relief='flat', bd=0, highlightthickness=0,
            cursor='hand2',
        )
        self._amend_check.pack(side=tk.LEFT)

        hint = ULabel(
            footer, text='Ctrl+↵ commit',
            variant='tertiary', bg=theme.BG_PANEL,
            font=theme.LABEL_FONT_SMALL,
        )
        hint.pack(side=tk.RIGHT)

    # —— 状态条 —— #

    def _build_status_row(self) -> None:
        row = tk.Frame(self, bg=theme.BG_PANEL, height=_STATUS_HEIGHT)
        row.pack(fill=tk.X, padx=_PANEL_PADDING_X, pady=(2, 4))
        row.pack_propagate(False)

        self._status_dot = tk.Frame(
            row, bg=theme.FG_TERTIARY, width=8, height=8,
            highlightthickness=0, bd=0,
        )
        self._status_dot.pack_propagate(False)
        self._status_dot.pack(side=tk.LEFT, padx=(0, 6), pady=7)

        self._stats_label = ULabel(
            row, text='—',
            variant='secondary', bg=theme.BG_PANEL,
            font=theme.LABEL_FONT_SMALL,
        )
        self._stats_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

    # —— 两个列表(STAGED / CHANGES) —— #

    def _build_lists(self) -> None:
        panels = tk.Frame(self, bg=theme.BG_PANEL)
        panels.pack(fill=tk.BOTH, expand=True, padx=4, pady=(0, 6))

        # Staged panel
        self._staged_frame = tk.Frame(panels, bg=theme.BG_PANEL)
        self._staged_frame.grid(row=0, column=0, sticky='nsew')
        self._build_section_header(
            self._staged_frame,
            title='STAGED CHANGES',
            empty_hint='No staged files',
        )
        self._staged_view = UListView(
            self._staged_frame,
            columns=['Status', 'File'],
            column_widths={'Status': 36, 'File': 200},
            show_header=False,
        )
        self._staged_view.pack(fill=tk.BOTH, expand=True, padx=4, pady=(2, 4))
        self._staged_view._on_select_cb = self._on_staged_select  # type: ignore

        # Changes panel
        self._unstaged_frame = tk.Frame(panels, bg=theme.BG_PANEL)
        self._unstaged_frame.grid(row=1, column=0, sticky='nsew')
        self._build_section_header(
            self._unstaged_frame,
            title='CHANGES',
            empty_hint='Working tree clean',
        )
        self._unstaged_view = UListView(
            self._unstaged_frame,
            columns=['Status', 'File'],
            column_widths={'Status': 36, 'File': 200},
            show_header=False,
        )
        self._unstaged_view.pack(fill=tk.BOTH, expand=True, padx=4, pady=(2, 4))
        self._unstaged_view._on_select_cb = self._on_unstaged_select  # type: ignore

        # 已暂存区域略小、变更区域略大
        panels.grid_rowconfigure(0, weight=2, uniform='git_rows')
        panels.grid_rowconfigure(1, weight=3, uniform='git_rows')
        panels.grid_columnconfigure(0, weight=1)

    # ─────────────────────────── helpers ───────────────────────────

    def _make_chip(self, parent: tk.Misc, *, color: str) -> tk.Frame:
        """右侧 ahead/behind chip —— 圆角小徽章."""
        outer = tk.Frame(
            parent, bg=theme.BG_RAISED,
            highlightthickness=0, bd=0,
        )
        inner = tk.Frame(
            outer, bg=theme.BG_RAISED,
            highlightthickness=1, highlightbackground=color,
            bd=0,
        )
        inner.pack(padx=0, pady=0)

        lbl = tk.Label(
            inner, text='0', bg=theme.BG_RAISED, fg=color,
            font=theme.LABEL_FONT_SMALL, padx=6, pady=0,
        )
        lbl.pack()
        outer._label = lbl   # type: ignore[attr-defined]
        outer._color = color  # type: ignore[attr-defined]
        return outer

    def _set_chip(self, chip: tk.Frame, value: int) -> None:
        chip._label.config(text=str(value), fg=chip._color)  # type: ignore[attr-defined]

    def _draw_branch_icon(self) -> None:
        """绘制类似 VSCode 的三分支图标."""
        c = self._branch_icon_canvas
        c.delete('all')
        # 主干
        c.create_line(5, 2, 5, 14, fill=theme.FG_PRIMARY, width=1)
        # 一条分支
        c.create_line(5, 5, 11, 5, fill=theme.FG_PRIMARY, width=1)
        c.create_line(11, 5, 11, 11, fill=theme.FG_PRIMARY, width=1)
        # 节点
        c.create_oval(3, 3, 7, 7, fill=theme.FG_PRIMARY, outline=theme.FG_PRIMARY)
        c.create_oval(9, 3, 13, 7, fill=theme.FG_PRIMARY, outline=theme.FG_PRIMARY)
        c.create_oval(9, 9, 13, 13, fill=theme.FG_PRIMARY, outline=theme.FG_PRIMARY)
        c.create_oval(3, 12, 7, 16, fill=theme.FG_PRIMARY, outline=theme.FG_PRIMARY)

    def _build_section_header(
        self,
        parent: tk.Frame,
        *,
        title: str,
        empty_hint: str,
    ) -> None:
        """生成一个带 chevron、标题、计数、空态提示的 section header."""
        header = tk.Frame(parent, bg=theme.BG_TITLE, height=_SECTION_HEADER_HEIGHT)
        header.pack(fill=tk.X)
        header.pack_propagate(False)

        chevron = tk.Label(
            header, text='▾', bg=theme.BG_TITLE,
            fg=theme.FG_TERTIARY, font=('Arial', 9),
            padx=8,
        )
        chevron.pack(side=tk.LEFT)

        title_lbl = tk.Label(
            header, text=title, bg=theme.BG_TITLE,
            fg=theme.FG_SECONDARY, font=('Arial', 9, 'bold'),
            anchor='w',
        )
        title_lbl.pack(side=tk.LEFT)

        # 计数(可选, 0 时不显示避免噪声)
        count_lbl = tk.Label(
            header, text='', bg=theme.BG_TITLE,
            fg=theme.FG_TERTIARY, font=('Arial', 9),
            padx=6,
        )
        count_lbl.pack(side=tk.LEFT)

        # 提示文本(右侧,item 为空时显示)
        hint_lbl = ULabel(
            header, text=empty_hint, variant='disabled',
            bg=theme.BG_TITLE, font=theme.LABEL_FONT_SMALL,
        )
        hint_lbl.pack(side=tk.RIGHT, padx=8)

        if title.startswith('STAGED'):
            self._staged_count_label = count_lbl
            self._staged_hint_label = hint_lbl
        else:
            self._unstaged_count_label = count_lbl
            self._unstaged_hint_label = hint_lbl

    # —— placeholder —— #

    def _on_msg_focus_in(self, _=None) -> None:
        if self._has_placeholder:
            self._msg_text.delete('1.0', 'end')
            self._msg_text.config(fg=theme.FG_PRIMARY)
            self._has_placeholder = False

    def _on_msg_focus_out(self, _=None) -> None:
        if not self._msg_text.get('1.0', 'end-1c').strip():
            self._has_placeholder = True
            self._msg_text.delete('1.0', 'end')
            self._msg_text.insert('1.0', self._msg_placeholder)
            self._msg_text.config(fg=theme.FG_TERTIARY)

    def _on_msg_key(self, _=None) -> None:
        if self._has_placeholder:
            self._msg_text.delete('1.0', 'end')
            self._msg_text.config(fg=theme.FG_PRIMARY)
            self._has_placeholder = False

    def _get_msg(self) -> str:
        if self._has_placeholder:
            return ''
        return self._msg_text.get('1.0', 'end-1c').strip()

    def _set_placeholder(self) -> None:
        self._msg_text.delete('1.0', 'end')
        self._msg_text.insert('1.0', self._msg_placeholder)
        self._msg_text.config(fg=theme.FG_TERTIARY)
        self._has_placeholder = True

    # ─────────────────────────── lifecycle ───────────────────────────

    def set_workspace_root(self, path: str) -> None:
        self._workspace_root = path
        self.refresh()

    def set_on_file_click(self, callback: Callable[[str, str], None]) -> None:
        """设置文件点击回调,签名为 ``(filepath: str, status: str)``."""
        self._on_file_click = callback

    def refresh(self) -> None:
        """重新拉取 Git 状态."""
        if not self._workspace_root:
            self._set_idle('No repository')
            return

        try:
            self._run_git_checks()
            if self._on_refresh:
                self._on_refresh()
        except FileNotFoundError:
            self._set_idle('Git not found')
        except Exception:
            self._set_idle('Error')

    def _run_git_checks(self) -> None:
        ws = self._workspace_root

        # 当前分支
        r = subprocess.run(
            ['git', 'branch', '--show-current'],
            cwd=ws, capture_output=True, text=True, timeout=5,
        )
        self._branch = r.stdout.strip()
        if self._branch:
            self._branch_label.config(text=self._branch)
        else:
            self._branch_label.config(text='(detached)')

        # 远程
        r = subprocess.run(
            ['git', 'remote'],
            cwd=ws, capture_output=True, text=True, timeout=5,
        )
        self._has_remote = bool(r.stdout.strip())

        # 状态
        r = subprocess.run(
            ['git', 'status', '--porcelain=v1'],
            cwd=ws, capture_output=True, text=True, timeout=5,
        )
        self._parse_git_status(r.stdout)

        # 远程跟踪(ahead/behind),仅当有 upstream 时有结果
        self._ahead, self._behind = self._compute_tracking(ws)

        # 上次提交 subject(为 Amend 提供后备提交信息)
        r = subprocess.run(
            ['git', 'log', '-1', '--pretty=%s'],
            cwd=ws, capture_output=True, text=True, timeout=5,
        )
        self._last_commit_subject = r.stdout.strip()

        self._refresh_views()

    def _compute_tracking(self, ws: str) -> tuple[int, int]:
        try:
            r = subprocess.run(
                ['git', 'rev-list', '--left-right', '--count', 'HEAD...@{u}'],
                cwd=ws, capture_output=True, text=True, timeout=5,
            )
            if r.returncode != 0 or '\t' not in r.stdout:
                return 0, 0
            left, right = r.stdout.strip().split('\t')
            return int(left), int(right)
        except Exception:
            return 0, 0

    def _parse_git_status(self, output: str) -> None:
        staged: list[dict] = []
        unstaged: list[dict] = []
        for line in output.splitlines():
            if len(line) < 3:
                continue
            status = line[:2]
            filepath = line[3:]
            icon = self._status_icon(status)
            entry = {'Status': icon, 'File': filepath}

            if status[0] in 'MADRC':
                staged.append(entry)
            if status[1] in 'MAD' or status[0] in '??':
                unstaged.append(entry)

        self._staged = staged
        self._unstaged = unstaged

    def _status_icon(self, status: str) -> str:
        s = status.strip()
        if not s:
            return '·'
        if s == '??':
            return 'U'
        first = s[0]
        marker = {'M': 'M', 'A': 'A', 'D': 'D', 'R': 'R', 'C': 'C'}.get(first, '?')
        second = s[1] if len(s) > 1 else ' '
        if second in 'MAD' and first != second:
            return f'{marker}!'   # 暂存 + 又有未暂存修改
        return marker

    def _refresh_views(self) -> None:
        staged = len(self._staged)
        unstaged = len(self._unstaged)

        # 列表
        self._staged_view.set_data(self._staged)
        self._unstaged_view.set_data(self._unstaged)

        # section 计数 + 空态提示
        self._staged_count_label.config(text=f'· {staged}' if staged else '')
        self._unstaged_count_label.config(text=f'· {unstaged}' if unstaged else '')
        self._staged_hint_label.config(text='' if staged else 'No staged files')
        self._unstaged_hint_label.config(text='' if unstaged else 'Working tree clean')

        # 底部状态条:状态点 + 文本
        if staged or unstaged:
            self._status_dot.config(bg=theme.YELLOW)
            parts = []
            if staged:
                parts.append(f'{staged} staged')
            if unstaged:
                parts.append(f'{unstaged} changed')
            self._stats_label.config(text='  ·  '.join(parts))
        else:
            self._status_dot.config(bg=theme.GREEN)
            self._stats_label.config(text='Working tree clean')

        # ahead/behind chip
        if self._ahead > 0:
            self._set_chip(self._ahead_chip, self._ahead)
            self._ahead_chip.pack(side=tk.RIGHT, padx=(4, 0))
        else:
            self._ahead_chip.pack_forget()
        if self._behind > 0:
            self._set_chip(self._behind_chip, self._behind)
            self._behind_chip.pack(side=tk.RIGHT, padx=(4, 0))
        else:
            self._behind_chip.pack_forget()

        # 按钮可用态
        self._update_button_states()

    def _set_idle(self, msg: str) -> None:
        self._branch_label.config(text=msg)
        self._stats_label.config(text='—')
        self._staged_view.set_data([])
        self._unstaged_view.set_data([])
        try:
            self._staged_count_label.config(text='')
            self._unstaged_count_label.config(text='')
            self._staged_hint_label.config(text='No staged files')
            self._unstaged_hint_label.config(text='Working tree clean')
        except tk.TclError:
            pass
        self._status_dot.config(bg=theme.FG_TERTIARY)
        if hasattr(self, '_ahead_chip'):
            self._ahead_chip.pack_forget()
        if hasattr(self, '_behind_chip'):
            self._behind_chip.pack_forget()
        self._btn_commit.config(state='disabled')
        self._btn_push.config(state='disabled')
        self._btn_pull.config(state='disabled')

    def _update_button_states(self) -> None:
        # Amend 时允许空提交,否则必须有 staged
        if self._amend_var.get():
            commit_state = 'normal'
        else:
            commit_state = 'normal' if self._staged else 'disabled'
        self._btn_commit.config(state=commit_state)
        self._btn_push.config(state='normal' if self._has_remote else 'disabled')
        self._btn_pull.config(state='normal' if self._has_remote else 'disabled')

    # ─────────────────────────── actions ───────────────────────────

    def _on_staged_select(
        self,
        index: int,  # pyright: ignore[reportUnusedParameter]
        row: dict,
    ) -> None:
        if self._on_file_click and row.get('File'):
            self._on_file_click(row['File'], 'staged')

    def _on_unstaged_select(
        self,
        index: int,  # pyright: ignore[reportUnusedParameter]
        row: dict,
    ) -> None:
        if self._on_file_click and row.get('File'):
            self._on_file_click(row['File'], 'unstaged')

    def _on_commit(self) -> None:
        """使用内联编辑器中的消息执行 ``git commit``(可 Amend)."""
        msg = self._get_msg()
        amend = self._amend_var.get()

        if not msg and not amend:
            showinfo('Commit', 'Type a commit message or check Amend.')
            return

        # Amend 但未填消息时,沿用上次提交 subject
        effective_msg = msg
        if amend and not msg:
            effective_msg = self._last_commit_subject
            if not effective_msg:
                showerror('Amend', 'No previous commit message to amend.')
                return

        try:
            cmd = ['git', 'commit']
            if amend:
                cmd.append('--amend')
                if msg:
                    cmd.extend(['-m', msg])
            else:
                cmd.extend(['-m', msg])

            r = subprocess.run(
                cmd, cwd=self._workspace_root,
                capture_output=True, text=True, timeout=30,
            )
            if r.returncode == 0:
                self._set_placeholder()
                self.refresh()
            else:
                showerror('Commit Error', r.stderr or 'Unknown error')
        except Exception as e:
            showerror('Commit Error', str(e))

    def _on_push(self) -> None:
        if not self._has_remote:
            showinfo('Push', 'No remote repository configured.')
            return
        try:
            r = subprocess.run(
                ['git', 'push'],
                cwd=self._workspace_root,
                capture_output=True, text=True, timeout=60,
            )
            if r.returncode == 0:
                self.refresh()
            else:
                showerror('Push Error', r.stderr or 'Unknown error')
        except Exception as e:
            showerror('Push Error', str(e))

    def _on_pull(self) -> None:
        if not self._has_remote:
            showinfo('Pull', 'No remote repository configured.')
            return
        try:
            r = subprocess.run(
                ['git', 'pull'],
                cwd=self._workspace_root,
                capture_output=True, text=True, timeout=60,
            )
            if r.returncode == 0:
                self.refresh()
            else:
                showerror('Pull Error', r.stderr or 'Unknown error')
        except Exception as e:
            showerror('Pull Error', str(e))

    # ─────────────────────────── public read API ───────────────────────────

    def get_branch(self) -> str:
        return self._branch

    def has_staged_changes(self) -> bool:
        return len(self._staged) > 0

    def get_staged_count(self) -> int:
        return len(self._staged)

    def get_unstaged_count(self) -> int:
        return len(self._unstaged)

    # ─────────────────────────── theming ───────────────────────────

    def _apply_theme(self) -> None:
        with contextlib.suppress(tk.TclError):
            super()._apply_theme()

        try:
            self._title_label.config(bg=theme.BG_TITLE, fg=theme.FG_SECONDARY)
            self._title_accent.config(bg=theme.TITLE_ACCENT)
            self._branch_label.config(bg=theme.BG_PANEL)
            self._branch_icon_canvas.config(bg=theme.BG_PANEL)
            self._draw_branch_icon()
            self._stats_label.config(bg=theme.BG_PANEL)
            self._msg_text.config(
                bg=theme.BG_INPUT,
                insertbackground=theme.FG_PRIMARY,
                selectbackground=theme.BLUE,
            )
            if self._has_placeholder:
                self._msg_text.config(fg=theme.FG_TERTIARY)
            else:
                self._msg_text.config(fg=theme.FG_PRIMARY)
        except tk.TclError:
            pass


__all__ = ['GitCard']
