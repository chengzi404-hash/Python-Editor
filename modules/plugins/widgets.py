"""``modules.plugins.widgets`` — 插件管理窗口。

这是给用户用的可视化插件管理界面:

* 已加载插件列表 (启用/禁用 toggle)
* 磁盘上发现但未启用的插件列表
* 每个插件可"启用 / 禁用 / 重新加载 / 查看详情"
* 显示插件目录位置, 方便用户写新插件
"""

from __future__ import annotations

import os
import tkinter as tk
from tkinter import messagebox
from typing import TYPE_CHECKING, Any, Dict, List, Optional

try:
    from modules.Uui.widgets import (
        UButton,
        UCheckButton,
        UFrame,
        ULabel,
        UText,
        theme,
    )
    _UUI_AVAILABLE = True
except Exception:  # pragma: no cover
    _UUI_AVAILABLE = False

from .hooks import HOOK_SPECS

from modules.i18n import t


__all__ = ["UPluginManagerWindow"]


class UPluginManagerWindow:
    """插件管理窗口 (单例风格, 但允许多开 — 每次新建一个窗口)。

    构造时立刻创建 Toplevel; 用户关闭后该实例可丢弃。
    """

    def __init__(self, editor: Any, manager: Any) -> None:
        self._editor = editor
        self._manager = manager
        self._tk_vars: Dict[str, tk.BooleanVar] = {}

        self._win = tk.Toplevel(editor.window)
        self._win.title(t('plugin.manager.title'))
        self._win.configure(bg=theme.BG_BASE)
        self._win.geometry('720x520+300+150')
        self._win.transient(editor.window)
        self._win.resizable(True, True)

        self._build()

    # ------------------------------------------------------------------
    # 布局
    # ------------------------------------------------------------------

    def _build(self) -> None:
        # 顶部: 目录信息
        top = UFrame(self._win, variant='title')
        top.pack(fill=tk.X)
        global_dir = self._manager._global_plugins_dir
        ULabel(
            top,
            text=(
                f"  {t('plugin.manager.from_label')} {global_dir}"
                f"    <project>/plugins/"
            ),
            variant='secondary', bg=theme.BG_TITLE,
        ).pack(side=tk.LEFT, padx=10, pady=4)

        # 中部: 左右两栏
        body = UFrame(self._win, variant='base')
        body.pack(fill=tk.BOTH, expand=True)

        body.columnconfigure(0, weight=1, uniform='col')
        body.columnconfigure(1, weight=1, uniform='col')
        body.rowconfigure(0, weight=1)

        # 左栏: 已加载插件
        left = UFrame(body, variant='panel')
        left.grid(row=0, column=0, sticky='nsew', padx=(4, 2), pady=4)
        ULabel(left, text=t('plugin.manager.loaded'), variant='primary', bg=theme.BG_PANEL).pack(
            anchor='w', padx=8, pady=4,
        )
        self._loaded_text = UText(left, width=40, height=18)
        self._loaded_text.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        self._loaded_text._text.config(state='disabled', wrap='word')

        # 右栏: 发现但未启用
        right = UFrame(body, variant='panel')
        right.grid(row=0, column=1, sticky='nsew', padx=(2, 4), pady=4)
        ULabel(right, text=t('plugin.manager.discovered'), variant='primary', bg=theme.BG_PANEL).pack(
            anchor='w', padx=8, pady=4,
        )
        self._discovered_text = UText(right, width=40, height=18)
        self._discovered_text.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        self._discovered_text._text.config(state='disabled', wrap='word')

        # 底部: 按钮行 + 钩子列表
        bottom = UFrame(self._win, variant='title')
        bottom.pack(fill=tk.X)
        UButton(
            bottom, text=t('plugin.manager.btn.enable'), width=70, height=24,
            command=self._on_enable,
        ).pack(side=tk.LEFT, padx=4, pady=4)
        UButton(
            bottom, text=t('plugin.manager.btn.disable'), width=70, height=24,
            command=self._on_disable,
        ).pack(side=tk.LEFT, padx=4, pady=4)
        UButton(
            bottom, text=t('plugin.manager.btn.reload'), width=80, height=24,
            command=self._on_reload,
        ).pack(side=tk.LEFT, padx=4, pady=4)
        UButton(
            bottom, text=t('plugin.manager.btn.details'), width=80, height=24,
            command=self._on_info,
        ).pack(side=tk.LEFT, padx=4, pady=4)
        UButton(
            bottom, text=t('plugin.manager.btn.close'), width=70, height=24, variant='default',
            command=self._win.destroy,
        ).pack(side=tk.RIGHT, padx=4, pady=4)

        # 钩子事件参考
        hooks_frame = UFrame(self._win, variant='panel', height=80)
        hooks_frame.pack(fill=tk.X, padx=4, pady=4)
        hooks_frame.pack_propagate(False)
        ULabel(
            hooks_frame, text=t('plugin.manager.hooks_label'), variant='primary',
            bg=theme.BG_PANEL,
        ).pack(anchor='w', padx=8, pady=2)
        hooks_text = UText(hooks_frame, height=3)
        hooks_text.pack(fill=tk.BOTH, expand=True, padx=4, pady=2)
        hooks_text._text.config(state='disabled', wrap='word')
        for spec in HOOK_SPECS:
            params = ', '.join(spec.params) if spec.params else ''
            hook_key = f'hook.{spec.name}'
            hook_desc = t(hook_key, default=spec.description)
            hooks_text._text.insert(
                'end' if hooks_text._text.index('end-1c') == '1.0' else 'end',
                f"  {spec.name}({params})  — {hook_desc}\n",
            )

        self._refresh()

    # ------------------------------------------------------------------
    # 列表渲染
    # ------------------------------------------------------------------

    def _refresh(self) -> None:
        """重渲染两侧列表。"""

        loaded = self._manager.list_loaded()
        discovered = [
            d for d in self._manager.list_discovered()
            if d.manifest.id not in {r.manifest.id for r in loaded}
        ]

        on_mark = t('plugin.manager.on')
        off_mark = t('plugin.manager.off')
        warn = t('plugin.manager.warning')
        from_label = t('plugin.manager.from_label')

        loaded_lines: List[str] = []
        self._tk_vars = {}
        for i, rec in enumerate(loaded, 1):
            mark = on_mark if rec.enabled else off_mark
            err = f"  {warn} {rec.error}" if rec.error else ''
            loaded_lines.append(
                f"{i:2}. {mark} {rec.manifest.name}  ({rec.manifest.id}){err}\n"
                f"      {from_label} {rec.location}\n"
            )
        if not loaded_lines:
            loaded_lines = [f"{t('plugin.manager.loaded_empty')}\n"]
        self._loaded_text._text.config(state='normal')
        self._loaded_text._text.delete('1.0', 'end')
        self._loaded_text._text.insert('1.0', ''.join(loaded_lines))
        self._loaded_text._text.config(state='disabled')

        discovered_lines: List[str] = []
        no_desc = t('plugin.manager.no_desc')
        for i, d in enumerate(discovered, 1):
            desc = d.manifest.description or no_desc
            discovered_lines.append(
                f"{i:2}. {d.manifest.name}  ({d.manifest.id})\n"
                f"      {desc}\n"
                f"      {from_label} {d.location}\n"
            )
        if not discovered_lines:
            discovered_lines = [f"{t('plugin.manager.discovered_empty')}\n"]
        self._discovered_text._text.config(state='normal')
        self._discovered_text._text.delete('1.0', 'end')
        self._discovered_text._text.insert('1.0', ''.join(discovered_lines))
        self._discovered_text._text.config(state='disabled')

    def _selected_loaded_index(self) -> Optional[int]:
        """从已加载列表里读取当前选中行对应的索引 (1-based)。"""

        try:
            sel = self._loaded_text._text.tag_ranges('sel')
            if not sel:
                return None
            line = int(str(sel[0]).split('.')[0])
        except Exception:
            return None
        loaded = self._manager.list_loaded()
        if 1 <= line <= len(loaded):
            # 已加载列表的"序号"行号在 1, 3, 5, ... (每项两行)
            return (line - 1) // 2
        return None

    def _selected_discovered_index(self) -> Optional[int]:
        try:
            sel = self._discovered_text._text.tag_ranges('sel')
            if not sel:
                return None
            line = int(str(sel[0]).split('.')[0])
        except Exception:
            return None
        loaded_ids = {r.manifest.id for r in self._manager.list_loaded()}
        discovered = [
            d for d in self._manager.list_discovered()
            if d.manifest.id not in loaded_ids
        ]
        if 1 <= line <= len(discovered):
            return (line - 1) // 3  # 每项 3 行 (标题/描述/路径)
        return None

    # ------------------------------------------------------------------
    # 按钮回调
    # ------------------------------------------------------------------

    def _on_enable(self) -> None:
        idx = self._selected_discovered_index()
        if idx is None:
            messagebox.showinfo(
                t('plugin.manager.msg.enable_title'),
                t('plugin.manager.msg.enable_select_discovered'),
                parent=self._win,
            )
            return
        loaded_ids = {r.manifest.id for r in self._manager.list_loaded()}
        discovered = [
            d for d in self._manager.list_discovered()
            if d.manifest.id not in loaded_ids
        ]
        target = discovered[idx]
        try:
            self._manager.enable(target.manifest.id)
        except Exception as exc:
            messagebox.showerror(
                t('plugin.manager.msg.enable_title'),
                t('plugin.manager.msg.enable_failed') + f': {exc}',
                parent=self._win,
            )
            return
        self._editor._refresh_plugin_menu()
        self._editor._refresh_plugin_languages()
        self._refresh()

    def _on_disable(self) -> None:
        idx = self._selected_loaded_index()
        if idx is None:
            messagebox.showinfo(
                t('plugin.manager.msg.disable_title'),
                t('plugin.manager.msg.disable_select_loaded'),
                parent=self._win,
            )
            return
        loaded = self._manager.list_loaded()
        target = loaded[idx]
        try:
            self._manager.disable(target.manifest.id)
        except Exception as exc:
            messagebox.showerror(
                t('plugin.manager.msg.disable_title'),
                t('plugin.manager.msg.disable_failed') + f': {exc}',
                parent=self._win,
            )
            return
        self._editor._refresh_plugin_menu()
        self._editor._refresh_plugin_languages()
        self._refresh()

    def _on_reload(self) -> None:
        idx = self._selected_loaded_index()
        if idx is None:
            messagebox.showinfo(
                t('plugin.manager.msg.reload_title'),
                t('plugin.manager.msg.reload_select_loaded'),
                parent=self._win,
            )
            return
        loaded = self._manager.list_loaded()
        target = loaded[idx]
        try:
            self._manager.reload(target.manifest.id)
        except Exception as exc:
            messagebox.showerror(
                t('plugin.manager.msg.reload_title'),
                t('plugin.manager.msg.reload_failed') + f': {exc}',
                parent=self._win,
            )
            return
        self._editor._refresh_plugin_menu()
        self._editor._refresh_plugin_languages()
        self._refresh()

    def _on_info(self) -> None:
        idx = self._selected_loaded_index()
        if idx is not None:
            loaded = self._manager.list_loaded()
            self._editor._show_plugin_info(loaded[idx])
            return
        idx = self._selected_discovered_index()
        if idx is not None:
            loaded_ids = {r.manifest.id for r in self._manager.list_loaded()}
            discovered = [
                d for d in self._manager.list_discovered()
                if d.manifest.id not in loaded_ids
            ]
            d = discovered[idx]
            m = d.manifest
            text = (
                f"名称: {m.name}\n"
                f"ID: {m.id}\n"
                f"版本: {m.version}\n"
                f"作者: {m.author or '(未提供)'}\n"
                f"作用域: {m.scope}\n"
                f"来源: {d.location}\n"
                f"状态: 未启用"
            )
            if m.description:
                text += f"\n\n{m.description}"
            messagebox.showinfo(f'插件: {m.name}', text, parent=self._win)
            return
        messagebox.showinfo(
            t('plugin.manager.msg.details_title'),
            t('plugin.manager.msg.details_select'),
            parent=self._win,
        )
