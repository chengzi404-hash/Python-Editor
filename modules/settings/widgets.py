"""``modules.settings.widgets`` — 设置模块的可视化 UI 封装。

依赖本仓库内的 :mod:`modules.Uui.widgets` 组件, 提供:

* :class:`USettingPanel` — 单作用域的设置面板（适用于"全局设置"或"项目设置"）。
* :class:`UProjectSettingsWindow` — 同时管理项目与全局设置的窗口,
  在底部提供 :guilabel:`应用` / :guilabel:`保存` / :guilabel:`关闭` / :guilabel:`恢复默认` 按钮。

> 这些 UI 类**只是便捷封装**, 内部仍通过 :class:`SettingsManager` /
> :class:`Settings` 抽象读写, 业务代码完全不必感知 UI 的存在。
"""

from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, messagebox
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional

from .base import (
    Settings,
    SettingsChangeEvent,
    SettingsListener,
    SettingsScope,
    SettingSpec,
    SettingValueType,
)
from .manager import SettingsManager
from modules.i18n import t

if TYPE_CHECKING:
    # 类型检查器看到的类型 - 用于静态分析
    from modules.Uui.widgets import (
        UButton,
        UCheckButton,
        UComboBox,
        UEntry,
        UFrame,
        ULabel,
        USettingsNavBar,
        NavSelection,
        theme,
    )
else:
    # 运行时变量 - 实际从 UUI 包导入; 失败时退化为 None
    UButton: Any = None  # type: ignore[assignment,misc]
    UCheckButton: Any = None  # type: ignore[assignment,misc]
    UComboBox: Any = None  # type: ignore[assignment,misc]
    UEntry: Any = None  # type: ignore[assignment,misc]
    UFrame: Any = None  # type: ignore[assignment,misc]
    ULabel: Any = None  # type: ignore[assignment,misc]
    USettingsNavBar: Any = None  # type: ignore[assignment,misc]
    NavSelection: Any = None  # type: ignore[assignment,misc]
    theme: Any = None  # type: ignore[assignment,misc]

try:
    from modules.Uui.widgets import (  # type: ignore[assignment]
        UButton,
        UCheckButton,
        UComboBox,
        UEntry,
        UFrame,
        ULabel,
        USettingsNavBar,
        NavSelection,
        theme,
    )
    _UUI_AVAILABLE = True
except Exception:  # pragma: no cover - 允许在无 tk 环境下被 import
    _UUI_AVAILABLE = False




def _group_key(spec: SettingSpec) -> str:
    """按 ``key`` 前缀自动归类, 例如 ``editor.tab_size`` → ``editor``."""

    if "." in spec.key:
        return spec.key.split(".", 1)[0]
    return "_"




class USettingPanel(UFrame if _UUI_AVAILABLE else object):  # type: ignore[misc]
    """为某一作用域渲染一组 :class:`SettingSpec` 的可视化面板.

    每个 spec 显示为一个 ``标签 + 控件 + 说明`` 的三段行; 按 ``key`` 前缀自动分组.
    用户编辑控件时只会修改 *本地副本*, 需要调用 :meth:`apply` 或 :meth:`revert`
    才真正写回底层 :class:`Settings` 或丢弃改动.

    参数:
        parent —— 父容器.
        settings —— 底层 :class:`Settings` 实例(全局或项目).
        on_change —— 当用户改动某个控件时的回调(可选).
        show_only_keys —— 若指定则只渲染这些 key; 默认渲染 schema 中全部.
        filter_group_keys —— 若指定则只渲染 key 属于这些分组的.
    """

    def __init__(
        self,
        parent,
        settings: Settings,
        *,
        on_change: Optional[Callable[[str, Any], None]] = None,
        show_only_keys: Optional[List[str]] = None,
        filter_group_keys: Optional[List[str]] = None,
        **kwargs,
    ) -> None:
        if not _UUI_AVAILABLE:
            raise RuntimeError(
                "USettingPanel requires modules.Uui.widgets; "
                "tkinter is not available in this environment."
            )
        super().__init__(parent, variant='base', **kwargs)
        self._settings = settings
        self._on_change = on_change
        self._working: Dict[str, Any] = dict(settings.defined())
        self._widgets: Dict[str, Any] = {}
        self._vars: Dict[str, tk.Variable] = {}
        self._listener: Optional[SettingsListener] = None

        specs = list(settings.schema)
        if show_only_keys is not None:
            only = set(show_only_keys)
            specs = [s for s in specs if s.key in only]
        if filter_group_keys is not None:
            groups = set(filter_group_keys)
            specs = [s for s in specs if _group_key(s) in groups]

        self._specs: List[SettingSpec] = specs
        self._build()
        self._listener = self._on_settings_event
        settings.add_listener(self._listener)


    def _build(self) -> None:
        grouped: Dict[str, List[SettingSpec]] = {}
        order: List[str] = []
        for spec in self._specs:
            g = _group_key(spec)
            if g not in grouped:
                grouped[g] = []
                order.append(g)
            grouped[g].append(spec)

        row = 0
        for group_key in order:
            ULabel(
                self, text=group_key, variant='secondary',
                font=theme.LABEL_FONT_BOLD,
            ).grid(row=row, column=0, columnspan=3, sticky='w',
                   padx=8, pady=(8 if row > 0 else 4, 2))
            row += 1
            for spec in grouped[group_key]:
                self._build_row(row, spec)
                row += 1

        # 列宽策略:列 1(输入控件)承载剩余空间且有最小宽度,保证输入框
        # 不会被描述文本挤掉;列 0/2 设置最小宽度,避免标签或说明被裁切到不可读。
        self.columnconfigure(0, minsize=110)
        self.columnconfigure(1, weight=1, minsize=160)
        self.columnconfigure(2, minsize=180)

    def _build_row(self, row: int, spec: SettingSpec) -> None:
        label = ULabel(self, text=spec.label or spec.key, variant='primary')
        label.grid(row=row, column=0, sticky='w', padx=(12, 6), pady=4)

        widget = self._make_widget(spec)
        widget.grid(row=row, column=1, sticky='ew', padx=4, pady=4)
        self._widgets[spec.key] = widget

        # 关键修复:为说明列设置明确的字符宽度上限 + 像素级 wraplength,
        # 这样长说明会按 240px 自动换行,而不会按"最长一行"的像素宽度
        # 把整列撑开、把输入框挤没。``anchor='w'`` + ``justify='left'`` 保证
        # 多行文本左上对齐;``sticky='nw'`` 让单元格纵向也顶格。
        desc = ULabel(
            self,
            text=spec.description or '',
            variant='tertiary',
            font=theme.LABEL_FONT_SMALL,
            width=30,
            wraplength=240,
            anchor='w',
            justify='left',
        )
        desc.grid(row=row, column=2, sticky='nw', padx=(4, 12), pady=4)

    def _make_widget(self, spec: SettingSpec):
        """根据 spec.type 实例化对应控件."""

        current = self._current_value(spec)

        if spec.type is SettingValueType.BOOLEAN:
            var = tk.BooleanVar(value=bool(current))
            widget = UCheckButton(self, text='', variable=var)
            widget._command = lambda v=var, k=spec.key: self._user_changed(k, v.get())  # type: ignore[attr-defined]
            self._vars[spec.key] = var
            return widget

        if spec.type is SettingValueType.CHOICE:
            widget = UComboBox(self, values=list(spec.choices))
            widget.set(str(current))
            widget._command = lambda v, k=spec.key: self._user_changed(k, v)  # type: ignore[attr-defined]
            return widget

        var = tk.StringVar(value=self._stringify(current))
        widget = UEntry(self, textvariable=var, width=24)
        var.trace_add('write', lambda *a, k=spec.key, v=var: self._user_changed(k, v.get()))
        self._vars[spec.key] = var
        return widget

    def _current_value(self, spec: SettingSpec) -> Any:
        """读取当前生效值(优先本地 working, 再底层 settings)."""

        if spec.key in self._working:
            return self._working[spec.key]
        return self._settings.get(spec.key)

    @staticmethod
    def _stringify(value: Any) -> str:
        if isinstance(value, list):
            return ", ".join(str(x) for x in value)
        return "" if value is None else str(value)

    def _user_changed(self, key: str, value: Any) -> None:
        try:
            coerced = self._coerce(key, value)
        except ValueError as exc:
            self._last_error = exc
            return
        self._working[key] = coerced
        if self._on_change is not None:
            try:
                self._on_change(key, coerced)
            except Exception:
                pass

    def _coerce(self, key: str, value: Any) -> Any:
        spec = self._settings.spec(key)
        if spec is None:
            return value
        if spec.type is SettingValueType.INTEGER:
            if value == "" or value is None:
                return spec.default
            return spec.validate(int(value))
        if spec.type is SettingValueType.FLOAT:
            if value == "" or value is None:
                return spec.default
            return spec.validate(float(value))
        if spec.type is SettingValueType.LIST:
            if isinstance(value, list):
                return spec.validate(value)
            text = str(value)
            items = [s.strip() for s in text.split(",") if s.strip()]
            return spec.validate(items)
        return spec.validate(value)


    def apply(self) -> int:
        """把 working 副本同步到底层 :class:`Settings`. 返回写入条数."""

        count = 0
        for key, value in self._working.items():
            try:
                self._settings.set(key, value)
                count += 1
            except (ValueError, KeyError):
                continue
        return count

    def revert(self) -> None:
        """丢弃 working 副本并按底层值刷新所有控件."""

        self._working = dict(self._settings.defined())
        self._refresh_widgets()

    def last_error(self) -> Optional[Exception]:
        return getattr(self, "_last_error", None)

    def _refresh_widgets(self) -> None:
        for spec in self._specs:
            self._refresh_single_widget(spec.key)

    def _refresh_single_widget(self, key: str) -> None:
        spec = self._settings.spec(key)
        widget = self._widgets.get(key)
        if spec is None or widget is None:
            return
        value = self._current_value(spec)
        if spec.type is SettingValueType.BOOLEAN:
            widget.set(bool(value))
        elif spec.type is SettingValueType.CHOICE:
            widget.set(str(value))
        else:
            var = self._vars.get(key)
            if var is not None:
                var.set(self._stringify(value))

    def _on_settings_event(self, event: SettingsChangeEvent) -> None:
        if event.scope is not self._settings.scope:
            return
        if event.key is not None:
            self._working.pop(event.key, None)
            self._refresh_single_widget(event.key)
        else:
            self._working.clear()
            self._refresh_widgets()

    def destroy(self) -> None:  # type: ignore[override]
        if self._listener is not None:
            try:
                self._settings.remove_listener(self._listener)
            except Exception:
                pass
        super().destroy()  # type: ignore[misc]




class UProjectSettingsWindow:
    """同时呈现"全局 / 项目"两份设置的窗口.

    使用::

        manager = SettingsManager()
        win = UProjectSettingsWindow(manager)
        win.show()

    行为:

    * 顶部两个 Tab 切换 **全局** 与 **项目**(若未挂载项目则禁用项目 Tab).
    * 切换 Tab 时丢弃当前未保存的修改并重新载入.
    * 点击 :guilabel:`应用` 把当前 Tab 的改动写回 :class:`Settings`.
    * 点击 :guilabel:`保存` 写回并调用 :meth:`SettingsManager.save_all` 落盘.
    * 点击 :guilabel:`关闭` 不写回任何未应用改动.
    """

    def __init__(
        self,
        manager: SettingsManager,
        *,
        title: str = "Settings",
        parent: Optional[tk.Misc] = None,
        geometry: str = "640x520",
    ) -> None:
        if not _UUI_AVAILABLE:
            raise RuntimeError(
                "UProjectSettingsWindow requires modules.Uui.widgets."
            )
        self._manager = manager
        self._parent = parent
        self._geometry = geometry
        self._title = title

        self._root = tk.Toplevel(parent) if parent is not None else tk.Tk()
        self._root.title(title)
        self._root.geometry(geometry)
        self._root.configure(bg=theme.BG_BASE)

        self._build()


    def _build(self) -> None:
        header = UFrame(self._root, variant='title')
        header.pack(fill=tk.X)
        ULabel(header, text=self._title, variant='primary',
               font=theme.LABEL_FONT_BOLD).pack(side=tk.LEFT, padx=12, pady=8)

        # 中部: 左侧导航树 + 右侧设置面板, 用水平 PanedWindow 分隔。
        # sashrelief / sashwidth 让分隔条可见可拖动; 与主窗口里的项目
        # 文件树 PanedWindow 完全同构。
        self._paned = tk.PanedWindow(
            self._root, orient=tk.HORIZONTAL,
            sashwidth=4, sashrelief='flat',
            bg=theme.BORDER, bd=0, showhandle=False,
        )
        self._paned.pack(fill=tk.BOTH, expand=True)
        self._paned.bind('<Map>', self._init_paned_position, add='+')

        self._nav: Any = USettingsNavBar(
            self._paned,
            title=t('settings.navbar.title'),
            on_select=self._on_nav_select,
        )
        self._paned.add(self._nav, minsize=160, stretch='never')

        self._body = UFrame(self._paned, variant='base')
        self._paned.add(self._body, minsize=200, stretch='always')

        footer = UFrame(self._root, variant='title')
        footer.pack(fill=tk.X)
        UButton(
            footer, text=t('settings.btn.reset'), variant='warning',
            command=self._on_reset_defaults, width=96, height=28,
        ).pack(side=tk.RIGHT, padx=4, pady=6)
        UButton(
            footer, text=t('settings.btn.close'), variant='default',
            command=self._on_close, width=80, height=28,
        ).pack(side=tk.RIGHT, padx=4, pady=6)
        UButton(
            footer, text=t('settings.btn.save'), variant='success',
            command=self._on_save, width=80, height=28,
        ).pack(side=tk.RIGHT, padx=4, pady=6)
        UButton(
            footer, text=t('settings.btn.apply'), variant='primary',
            command=self._on_apply, width=80, height=28,
        ).pack(side=tk.RIGHT, padx=4, pady=6)

        self._current_scope: SettingsScope = SettingsScope.GLOBAL
        self._panel: Optional[USettingPanel] = None
        # 先把树按当前 manager 状态建好; set_roots 会自动选中第一片
        # 叶子并触发 on_select, 顺势完成首屏的右侧面板渲染。
        self._load_nav()

    def _init_paned_position(self, event=None) -> None:
        """首次显示后, 把分隔条放到 220px 处, 与项目里其它 PanedWindow 同构."""

        try:
            total = self._paned.winfo_width()
            if total <= 1:
                # 还未真正布局完成, 推迟一帧
                self._root.after(10, self._init_paned_position)
                return
            self._paned.sash_place(0, max(220, 160), 0)
            self._paned.unbind('<Map>')
        except tk.TclError:
            pass

    def _load_nav(self) -> None:
        """根据当前 ``SettingsManager`` 状态重新构建导航树.

        项目未挂载时不传 project_schema, 树里就不出现"项目"分支;
        后续 ``_switch(PROJECT)`` 若检测到未挂项目会引导用户选择目录,
        选完后由 :meth:`_switch` 再次调用本方法刷新树。
        """

        project = self._manager.project_settings
        self._nav.set_roots(
            global_schema=self._manager.global_settings.schema,
            project_schema=project.schema if project is not None else None,
        )


    def _switch(self, scope: SettingsScope) -> None:
        """导航到指定 scope 根节点 (兼容 :meth:`CodeEditor._open_global_settings`
        / :meth:`CodeEditor._open_project_settings` 的旧调用形式).

        行为:
            * 若切到 PROJECT 但未挂项目, 弹提示让用户选目录, 选完后刷新
              导航树使"项目"分支出现。
            * 否则仅让左侧导航树跟随到对应 scope 根, 真正渲染交由
              :meth:`_on_nav_select` 处理 (它会重建右侧面板)。
        """

        if scope is SettingsScope.PROJECT and self._manager.project_settings is None:
            if not messagebox.askyesno(
                t('settings.msg.project.no_attach.title'),
                t('settings.msg.project.no_attach.body'),
                parent=self._root,
            ):
                return
            chosen = filedialog.askdirectory(
                title=t('settings.msg.project.pick_dir.title'), parent=self._root,
            )
            if not chosen:
                return
            try:
                self._manager.attach_project(chosen)
            except Exception as exc:
                messagebox.showerror(
                    t('settings.msg.project.no_attach.title'),
                    t('settings.msg.project.mount_failed', exc=exc),
                    parent=self._root,
                )
                return
            # 挂载成功后重新构建树 (让"项目"分支出现)。
            self._load_nav()

        self._current_scope = scope
        if self._nav is not None:
            self._nav.set_selected(scope)

    def _on_nav_select(self, selection: Any) -> None:
        """导航树节点被选中: 用 selection 的范围重建右侧 :class:`USettingPanel`.

        * selection.group_key 为 ``None`` 且 keys 为空 → scope 根, 显示全部
        * selection.keys 非空 → 叶子节点, ``show_only_keys=keys`` 精确过滤
        * 其它情况 (group 节点) → ``filter_group_keys=[group_key]`` 保留
          :class:`USettingPanel` 自带的"分组标题"渲染
        """

        if selection is None:
            return
        self._current_scope = selection.scope
        self._rebuild_panel(selection)

    def _rebuild_panel(self, selection: Any) -> None:
        """根据 selection 重建右侧 ``USettingPanel``."""

        if self._panel is not None:
            try:
                self._panel.destroy()
            except Exception:
                pass
            self._panel = None

        scope = selection.scope
        if scope is SettingsScope.GLOBAL:
            settings = self._manager.global_settings
        elif scope is SettingsScope.PROJECT:
            settings = self._manager.project_settings
        else:
            return
        if settings is None:
            return

        if selection.keys:
            # 叶子节点: 精确到单个 key
            panel = USettingPanel(
                self._body, settings=settings,
                show_only_keys=list(selection.keys),
            )
        elif selection.group_key is not None:
            # 分组节点: 走 filter_group_keys, 保留 USettingPanel 的
            # "分组标题 + 多个设置行"渲染风格
            panel = USettingPanel(
                self._body, settings=settings,
                filter_group_keys=[selection.group_key],
            )
        else:
            # scope 根: 渲染该 scope 全部
            panel = USettingPanel(self._body, settings=settings)

        panel.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        self._panel = panel


    def _on_apply(self) -> None:
        if self._panel is None:
            return
        try:
            count = self._panel.apply()
        except Exception as exc:
            messagebox.showerror(t('settings.msg.apply.failed'), str(exc), parent=self._root)
            return
        messagebox.showinfo(t('settings.msg.apply.success.title'), t('settings.msg.apply.success.body', count=count), parent=self._root)

    def _on_save(self) -> None:
        if self._panel is not None:
            try:
                self._panel.apply()
            except Exception as exc:
                messagebox.showerror(t('settings.msg.save.failed'), str(exc), parent=self._root)
                return
        try:
            self._manager.save_all()
        except Exception as exc:
            messagebox.showerror(t('settings.msg.save.failed'), str(exc), parent=self._root)
            return
        messagebox.showinfo(t('settings.msg.save.success.title'), t('settings.msg.save.success.body'), parent=self._root)

    def _on_close(self) -> None:
        try:
            self._root.destroy()
        except tk.TclError:
            pass

    def _on_reset_defaults(self) -> None:
        if self._panel is None:
            return
        if not messagebox.askyesno(
            t('settings.msg.reset.confirm.title'),
            t('settings.msg.reset.confirm.body'),
            parent=self._root,
        ):
            return
        self._manager.reset(self._current_scope)
        # 保留用户当前所在节点, 仅重建面板让默认值显示出来;
        # 若导航树还未建好(异常路径)再回退到 _switch。
        sel = self._nav.get_selected() if self._nav is not None else None
        if sel is not None:
            self._rebuild_panel(sel)
        else:
            self._switch(self._current_scope)


    def show(self) -> None:
        """进入 mainloop."""

        self._root.mainloop()

    @property
    def root(self) -> tk.Misc:
        return self._root


__all__ = ["USettingPanel", "UProjectSettingsWindow"]