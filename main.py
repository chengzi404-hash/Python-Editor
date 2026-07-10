import sys
import os
import queue
import subprocess
import tempfile
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from modules.logging import configure_logging, get_logger
from modules.Uui.widgets import UFrame, ULabel, UButton, UText, UComboBox, UMenuBar, UMenu, theme, UFileTree, TabBar, Tab
from modules.Uui.widgets.window import Window
from modules.Uui.widgets.editor_suggestion import UEditorSuggestion, CompletionItem
from modules.highlighter import PythonHighlighterExpert, CcppHighlighterExpert, HighlightBlock
from modules.suggestion import PythonSuggestionExpert, CSuggestionExpert, CppSuggestionExpert, SuggestionBlock
from modules.checker import Flake8Checker, PyrightChecker, CPythonChecker
from modules.runner import RunResult, run_blocking, stream_command
from modules.settings import SettingsManager, SettingsScope, SettingsChangeEvent
from modules.plugins import (
    PluginManager,
    LanguageContribution,
    HookEvents,
)
from modules.i18n import AVAILABLE_LANGUAGES, get_translator, t


@dataclass
class Document:
    """单个文档的数据模型，对应一个打开的文件（或 Untitled）。"""
    path: Optional[str]          # None 表示未保存的 Untitled 文档
    content: str = ''
    dirty: bool = False
    lang: str = 'Python'          # 代码语言
    seq: int = 0                 # Untitled 序号（0 表示非 untitled）


class _Debouncer:
    """轻量级防抖调度器,可在多次 ``schedule`` 时只保留最后一次的回调。

    与具体 GUI 框架解耦:构造时注入 ``after(ms, cb)`` 与 ``cancel(id)`` 两个钩子。
    ``delay_ms`` 在每次 ``schedule`` 时读取,因此支持运行时动态修改延迟值。
    任何 ``schedule`` 都会取消前一个未触发的任务,确保**只有最后一次按键的
    回调**会在停顿 ``delay_ms`` 毫秒后真正执行。
    """

    def __init__(self, after, cancel):
        self._after = after
        self._cancel = cancel
        self._after_id = None

    def schedule(self, callback, delay_ms: int) -> None:
        if self._after_id is not None:
            try:
                self._cancel(self._after_id)
            except Exception:
                pass
            self._after_id = None
        delay = max(0, int(delay_ms))
        try:
            self._after_id = self._after(delay, callback)
        except Exception:
            self._after_id = None

    def cancel(self) -> None:
        if self._after_id is None:
            return
        try:
            self._cancel(self._after_id)
        except Exception:
            pass
        self._after_id = None

    @property
    def pending_id(self):
        return self._after_id


HIGHLIGHT_TOKENS = {
    'keyword': {'foreground': '#569cd6'},
    'builtin': {'foreground': '#dcdcaa'},
    'string': {'foreground': '#ce9178'},
    'number': {'foreground': '#b5cea8'},
    'comment': {'foreground': '#6a9955'},
    'identifier': {'foreground': '#9cdcfe'},
    'operator': {'foreground': '#d4d4d4'},
    'punctuation': {'foreground': '#d4d4d4'},
    'function': {'foreground': '#dcdcaa'},
    'class': {'foreground': '#4ec9b0'},
    'struct': {'foreground': '#4ec9b0'},
    'preprocessor': {'foreground': '#9b9b9b'},
    'decorator': {'foreground': '#dcdcaa'},
    'self': {'foreground': '#569cd6'},
    'type': {'foreground': '#4ec9b0'},
}

LANG_CONFIG = {
    'Python': {
        'ext': '.py',
        'highlighter': PythonHighlighterExpert,
        'suggestion': PythonSuggestionExpert,
        'suggestion_factory': lambda: PythonSuggestionExpert(),
        'sample': 'def hello():\n    print("Hello, world!")\n\nhello()\n',
    },
    'C': {
        'ext': '.c',
        'highlighter': CcppHighlighterExpert,
        'suggestion': CSuggestionExpert,
        'suggestion_factory': lambda: CSuggestionExpert(),
        'sample': '#include <stdio.h>\n\nint main() {\n    printf("Hello, world!\\n");\n    return 0;\n}\n',
    },
    'C++': {
        'ext': '.cpp',
        'highlighter': CcppHighlighterExpert,
        'suggestion': CppSuggestionExpert,
        'suggestion_factory': lambda: CppSuggestionExpert(),
        'sample': '#include <iostream>\n\nint main() {\n    std::cout << "Hello, world!" << std::endl;\n    return 0;\n}\n',
    },
}

THEME_NAMES = ['Dark', 'Light', 'Solarized Dark']
FONT_FAMILIES = ['Consolas', 'Courier New', 'Menlo', 'Monaco']
FONT_SIZES = [9, 10, 11, 12, 14, 16]
TAB_WIDTHS = [2, 4, 8]

_log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
configure_logging(
    level="INFO",
    file_enabled=True,
    console_enabled=True,
    log_dir=_log_dir,
    max_bytes=5 * 1024 * 1024,
    backup_count=5,
)
app_logger = get_logger("app")
app_logger.info("Application starting...")


class CodeEditor:
    def __init__(self):
        custom_titlebar = '--custom-titlebar' in sys.argv
        self.window = Window(title=t('window.title'), custom_titlebar=custom_titlebar)
        self.window.geometry('960x680+200+100')
        self.window.configure(bg=theme.BG_BASE)
        self.window.resizable(width=True, height=True)

        self._settings = SettingsManager()
        self._suppress_settings_listener = False

        # 国际化: 先把 translator 切到 settings 里持久化的语言, 再开始构建 UI。
        # 这样 _build_menubar / _build_status_bar 等内部 t() 调用就能拿到正确的文本。
        self._translator = get_translator()
        initial_lang = self._settings.effective('i18n.language', 'zh_CN')
        if initial_lang in AVAILABLE_LANGUAGES:
            self._translator.set_language(initial_lang)
        self._translator.add_listener(self._on_language_changed)

        self._lang = 'Python'
        self._current_file: Optional[str] = None
        self._current_project_root: Optional[str] = None
        self._suggestion_popup: Optional[UEditorSuggestion] = None
        self._dirty = False

        # ── 多文档状态 ──────────────────────────────────────────────────
        self._documents: Dict[str, Document] = {}
        self._active_id: Optional[str] = None
        self._next_untitled_seq: int = 1
        self._tab_bar: Optional[TabBar] = None

        gs = self._settings.global_settings
        self._highlighting_enabled = gs.get('completion.enabled', True)
        self._suggestions_enabled = gs.get('completion.enabled', True)
        self._autosave_enabled = gs.get('editor.auto_save', False)

        self._font_family = gs.get('ui.font_family', 'Consolas')
        self._font_size = int(gs.get('ui.font_size', 10))
        self._tab_width = int(gs.get('editor.tab_size', 4))
        self._highlight_delay_ms = int(
            gs.get('editor.highlight_delay_ms', 300)
        )
        self._suggest_delay_ms = int(
            gs.get('editor.suggestion_delay_ms', 200)
        )

        self._highlight_debouncer = _Debouncer(
            self.window.after, self.window.after_cancel,
        )
        self._suggest_debouncer = _Debouncer(
            self.window.after, self.window.after_cancel,
        )

        self._find_dialog: Optional[tk.Toplevel] = None
        self._find_query = ''
        self._find_last_index: Optional[str] = None

        # 大文件模式: 打开超过 ``editor.large_file_threshold_bytes`` 的文件时
        # 置 True, _apply_highlight / _show_suggestions 会提前返回。
        # 用户切到小文件/新建文件/切语言时会被重置回 False。
        self._large_file_mode: bool = False
        # 流式加载 epoch 计数器: 每次新加载(打开/新建/切语言)都 +1,
        # 让 in-flight 的 after() 回调可以判断自己是否已过期,
        # 避免"切换文件时被旧回调把内容覆盖回去"。
        self._stream_epoch: int = 0

        self._build_menubar()
        self._build_toolbar()
        self._build_editor()
        # 多文档状态依赖 _tab_bar，所以要在 _build_editor 之后
        self._init_first_document()
        self._build_output_panel()
        self._build_status_bar()

        # 插件系统: 先建 manager, 在菜单/编辑器建好之后 attach,
        # 这样插件注册的命令 / 语言可以立刻渲染到菜单和下拉框。
        # Project 级插件在 _attach_project 时按需加载。
        self._plugin_manager = PluginManager()
        self._plugin_menus: Dict[str, Any] = {}
        self._plugin_lang_combo_added: List[str] = []
        self._plugin_manager.attach_editor(self)
        try:
            self._plugin_manager.load_global_plugins()
        except Exception:
            pass
        self._refresh_plugin_menu()
        self._refresh_plugin_languages()

        # 在所有控件都已构造后再注册 listener, 避免启动期触发未初始化控件。
        self._settings.add_listener(self._on_settings_changed)

        self._apply_loaded_theme()
        self._apply_editor_font()
        self._set_tab_width(self._tab_width)
        self._switch_language('Python')

        self._bind_shortcuts()
        self.window.protocol('WM_DELETE_WINDOW', self._on_close_request)
        app_logger.info(
            f"CodeEditor initialized: theme={theme.current().name}, "
            f"font={self._font_family} {self._font_size}pt, "
            f"tab_width={self._tab_width}"
        )

    # ------------------------------------------------------------------
    # 多文档管理
    # ------------------------------------------------------------------

    def _init_first_document(self) -> None:
        """初始化第一个 Untitled 文档。"""
        doc_id = self._new_doc_id()
        self._documents[doc_id] = Document(
            path=None, content='', dirty=False, lang=self._lang, seq=1,
        )
        self._active_id = doc_id
        self._next_untitled_seq = 2
        self._update_tab_bar()

    def _new_doc_id(self) -> str:
        """生成新的未命名文档 ID。"""
        return f'__untitled_{self._next_untitled_seq}__'

    def _tab_title(self, doc: Document) -> str:
        """返回文档的显示标题。"""
        if doc.path:
            return os.path.basename(doc.path)
        return f'Untitled-{doc.seq}'

    def _update_tab_bar(self) -> None:
        """刷新标签栏以反映当前文档状态。"""
        if self._tab_bar is None:
            return
        tabs = []
        for doc_id, doc in self._documents.items():
            title = self._tab_title(doc)
            closeable = len(self._documents) > 1
            tabs.append(Tab(id=doc_id, title=title, dirty=doc.dirty, closeable=closeable))
        self._tab_bar.set_tabs(tabs, self._active_id)

    def _switch_document(self, doc_id: str) -> None:
        """切换到指定文档（保存当前文档状态，加载目标文档到编辑器）。"""
        if doc_id not in self._documents:
            return
        if self._active_id and self._active_id in self._documents:
            curr = self._documents[self._active_id]
            try:
                curr.content = self._editor.get('1.0', 'end-1c')
            except tk.TclError:
                curr.content = ''
            curr.lang = self._lang

        self._active_id = doc_id
        doc = self._documents[doc_id]
        self._editor._text.config(state='normal')
        self._editor._text.delete('1.0', tk.END)
        if doc.content:
            self._editor._text.insert('1.0', doc.content)
        self._dirty = doc.dirty
        self._lang = doc.lang
        self._switch_language(doc.lang, from_doc_switch=True)
        self._tab_bar.set_active(doc_id)
        self._apply_highlight()
        self._update_status()

    def _tab_select(self, doc_id: str) -> None:
        """标签点击回调。"""
        if doc_id == self._active_id:
            return
        self._switch_document(doc_id)

    def _tab_close(self, doc_id: str) -> None:
        """关闭标签。"""
        if doc_id not in self._documents:
            return
        doc = self._documents[doc_id]
        if doc.dirty:
            result = messagebox.askyesno(
                t('dialog.title.unsaved_discard'),
                t('dialog.unsaved_discard.message'),
            )
            if not result:
                return

        del self._documents[doc_id]
        self._tab_bar.remove_tab(doc_id)

        if not self._documents:
            self._init_first_document()
        elif self._active_id == doc_id:
            other_id = next(iter(self._documents.keys()))
            self._active_id = other_id
            doc = self._documents[other_id]
            self._editor._text.config(state='normal')
            self._editor._text.delete('1.0', tk.END)
            if doc.content:
                self._editor._text.insert('1.0', doc.content)
            self._dirty = doc.dirty
            self._lang = doc.lang
            self._switch_language(doc.lang, from_doc_switch=True)
            self._apply_highlight()
            self._update_status()
        self._update_tab_bar()

    def _tab_context_menu(self, doc_id: str, x_root: int, y_root: int) -> None:
        """标签右键菜单。"""
        menu = tk.Menu(self.window, tearoff=0)
        menu.add_command(label='Close', command=lambda: self._tab_close(doc_id))
        menu.add_command(label='Close Others', command=lambda: self._close_other_tabs(doc_id))
        menu.add_command(label='Close All', command=self._close_all_tabs)
        try:
            menu.tk_popup(x_root, y_root)
        finally:
            menu.grab_release()

    def _close_other_tabs(self, keep_id: str) -> None:
        """关闭除指定标签外的所有标签。"""
        for did in [d for d in self._documents if d != keep_id]:
            self._tab_close(did)

    def _close_all_tabs(self) -> None:
        """关闭所有标签（只剩一个时退化为普通新建）。"""
        if len(self._documents) <= 1:
            self._new_file()
            return
        for did in list(self._documents.keys()):
            self._tab_close(did)

    def _mark_dirty(self) -> None:
        """标记当前文档为脏（已修改）。"""
        if self._active_id and self._active_id in self._documents:
            self._documents[self._active_id].dirty = True
            self._dirty = True
            self._update_tab_bar()

    def _next_tab(self) -> None:
        """切换到下一个标签。"""
        if not self._documents:
            return
        ids = list(self._documents.keys())
        if self._active_id in ids:
            idx = ids.index(self._active_id)
            self._switch_document(ids[(idx + 1) % len(ids)])

    def _prev_tab(self) -> None:
        """切换到上一个标签。"""
        if not self._documents:
            return
        ids = list(self._documents.keys())
        if self._active_id in ids:
            idx = ids.index(self._active_id)
            self._switch_document(ids[(idx - 1) % len(ids)])

    def _close_active_tab(self) -> None:
        """关闭当前标签。"""
        if self._active_id:
            self._tab_close(self._active_id)

    # ------------------------------------------------------------------
    # SettingsManager 桥接层
    # ------------------------------------------------------------------
    #
    # 写入方向(用户操作 UI 控件):
    #     _set_theme / _set_font_family / _set_font_size / _set_tab_width
    #     _toggle_highlighting / _toggle_suggestions / _toggle_autosave
    #     这些方法在更新 Tk 状态后,主动调用 SettingsManager.set(...)
    #     来持久化到 JSON 文件。``persist=False`` 用于避免循环触发。
    #
    # 读取方向(settings 面板改动 → UI 同步):
    #     :meth:`_on_settings_changed` 监听 SettingsChangeEvent,
    #     把 GLOBAL 作用域的变更同步到 Tk 控件变量。
    #

    def _on_settings_changed(self, event: SettingsChangeEvent) -> None:
        """settings 变更后回调: 同步 UI 状态(由设置面板触发)。"""

        if self._suppress_settings_listener:
            return
        if event.scope is not SettingsScope.GLOBAL:
            return
        if event.key is None:
            self._refresh_all_from_settings()
            return
        key = event.key
        if key == 'ui.theme':
            try:
                self._set_theme(event.new, persist=False)
            except Exception:
                pass
        elif key == 'ui.font_family':
            self._font_family = event.new
            if hasattr(self, '_font_family_tk_var'):
                self._font_family_tk_var.set(event.new)
            self._apply_editor_font()
        elif key == 'ui.font_size':
            self._font_size = int(event.new)
            if hasattr(self, '_font_size_tk_var'):
                self._font_size_tk_var.set(int(event.new))
            self._apply_editor_font()
        elif key == 'editor.tab_size':
            self._set_tab_width(int(event.new), persist=False)
        elif key == 'completion.enabled':
            val = bool(event.new)
            self._highlighting_enabled = val
            self._suggestions_enabled = val
            for tk_var in (
                getattr(self, '_highlight_tk_var', None),
                getattr(self, '_suggestion_tk_var', None),
            ):
                if tk_var is not None:
                    tk_var.set(val)
            if val:
                self._apply_highlight()
            else:
                text = self._editor._text
                for tag in text.tag_names():
                    text.tag_delete(tag)
                self._hide_suggestions()
        elif key == 'editor.auto_save':
            self._autosave_enabled = bool(event.new)
            if hasattr(self, '_autosave_tk_var'):
                self._autosave_tk_var.set(bool(event.new))
        elif key == 'editor.highlight_delay_ms':
            try:
                self._highlight_delay_ms = max(0, int(event.new))
            except (TypeError, ValueError):
                self._highlight_delay_ms = 300
        elif key == 'editor.suggestion_delay_ms':
            try:
                self._suggest_delay_ms = max(0, int(event.new))
            except (TypeError, ValueError):
                self._suggest_delay_ms = 200
        elif key == 'i18n.language':
            new_lang = event.new if event.new in AVAILABLE_LANGUAGES else 'zh_CN'
            if self._translator.current_language != new_lang:
                self._translator.set_language(new_lang)
                # _on_language_changed (translator listener) 会重建 UI,
                # 这里不需要再做任何事。
            if hasattr(self, '_lang_locale_tk_var') and self._lang_locale_tk_var is not None:
                self._lang_locale_tk_var.set(new_lang)

    def _refresh_all_from_settings(self) -> None:
        """设置面板整体保存后,把全局值同步回 UI。"""

        try:
            self._set_theme(self._settings.effective('ui.theme'), persist=False)
        except Exception:
            pass
        gs = self._settings.global_settings
        self._font_family = gs.get('ui.font_family', self._font_family)
        self._font_size = int(gs.get('ui.font_size', self._font_size))
        self._tab_width = int(gs.get('editor.tab_size', self._tab_width))
        self._highlight_delay_ms = int(
            gs.get('editor.highlight_delay_ms', self._highlight_delay_ms)
        )
        self._suggest_delay_ms = int(
            gs.get('editor.suggestion_delay_ms', self._suggest_delay_ms)
        )
        if hasattr(self, '_font_family_tk_var'):
            self._font_family_tk_var.set(self._font_family)
        if hasattr(self, '_font_size_tk_var'):
            self._font_size_tk_var.set(int(self._font_size))
        if hasattr(self, '_tab_width_tk_var'):
            self._tab_width_tk_var.set(int(self._tab_width))
        self._apply_editor_font()
        self._set_tab_width(self._tab_width, persist=False)

    def _apply_loaded_theme(self) -> None:
        """启动时根据全局设置应用主题(忽略变更事件)。"""

        try:
            target = self._settings.effective('ui.theme', 'Dark')
            self._set_theme(target, persist=False)
        except Exception:
            pass

    def _on_language_changed(self, lang: str) -> None:
        """translator listener: 语言切换后重建需要本地化的 UI 部分。

        重建范围:
            * 菜单栏: _build_menubar 内部会用 t() 重新生成 label
            * 状态栏: 状态字符串、pos 标签等需要立即刷新
            * 关闭当前打开的 find/replace dialog 与 settings 窗口,
              它们的 label 是构建时固化的, 不重建就会停留在旧语言。

        不重建: 编辑器文本、文件树、主题颜色 — 这些与语言无关。
        """

        if hasattr(self, '_lang_changing') and self._lang_changing:
            return
        self._lang_changing = True
        try:
            # 先关掉可能停留在旧语言的 dialog, 避免用户看到半中半英
            for attr in ('_find_dialog', '_settings_window', '_plugin_manager_window'):
                win = getattr(self, attr, None)
                if win is not None and win.winfo_exists():
                    try:
                        win.destroy()
                    except tk.TclError:
                        pass
                if attr == '_find_dialog':
                    self._find_dialog = None

            # 重建菜单栏: 先清空旧按钮, 再走完整 _build_menubar。
            self._clear_menubar()
            self._build_menubar()

            # 重建插件菜单 / 语言下拉框: 它们依赖 LANG_CONFIG, 不随 i18n 变
            # (代码语言与界面语言是两回事), 但插件菜单的 label 是动态拼出来的,
            # 需要刷新一下, 否则会停留在旧文案。
            try:
                self._refresh_plugin_menu()
            except Exception:
                pass

            # 刷新状态栏与 pos 标签
            try:
                self._refresh_status_for_language()
            except Exception:
                pass
        finally:
            self._lang_changing = False

    def _clear_menubar(self) -> None:
        """销毁 UMenuBar 上已渲染的 cascade 按钮,准备 _build_menubar 重建。

        之所以不直接 destroy UMenuBar 自身: 它已经被 pack 到窗口里,
        销毁并重新创建会改变布局管理器的状态, 容易留下空白。
        这里直接销毁每个 cascade 按钮 + 清空 _buttons 列表,
        _build_menubar 调用时只是重新 pack, 行为与首次构造一致。
        """

        bar = getattr(self, '_menubar', None)
        if bar is None:
            return
        try:
            # _buttons 是 [(tk.Label, UMenu), ...], 销毁 Label 即可
            for btn, _ in list(getattr(bar, '_buttons', [])):
                try:
                    btn.destroy()
                except tk.TclError:
                    pass
            bar._buttons = []
        except Exception:
            pass

    def _refresh_status_for_language(self) -> None:
        """语言切换后,把状态栏里以 t() 渲染的 label 全部刷新。"""

        if not hasattr(self, '_status_label'):
            return
        try:
            self._status_label.config(text=t('status.ready'))
        except tk.TclError:
            pass
        # pos 标签: 走 _update_status 重算 (里面没有硬编码文案,
        # 但 status.pos 的 key 是新的, 这里确保 _pos_label 存在)
        if hasattr(self, '_pos_label'):
            try:
                self._update_status()
            except Exception:
                pass

    def _write_setting(self, scope: SettingsScope, key: str, value) -> None:
        """写入 setting(抑制 listener,避免用户操作 UI 后回到原值的无效回弹)。"""

        self._suppress_settings_listener = True
        try:
            self._settings.set(scope, key, value)
        except (KeyError, ValueError):
            pass
        finally:
            self._suppress_settings_listener = False

    # ------------------------------------------------------------------
    # 关闭 / 持久化
    # ------------------------------------------------------------------

    def _on_close_request(self) -> None:
        """窗口关闭时: 检查所有文档脏状态 + 落盘。"""

        # 检查所有文档是否有未保存更改
        dirty_docs = [doc for doc in self._documents.values() if doc.dirty]
        if dirty_docs:
            if not messagebox.askyesno(
                t('dialog.title.unsaved_exit'),
                t('dialog.unsaved_exit.message'),
            ):
                return

        self._cancel_pending_highlight()
        self._cancel_pending_suggestions()
        app_logger.info("Editor closing...")
        self._emit(HookEvents.EDITOR_CLOSING)
        try:
            self._plugin_manager.unload_all()
        except Exception:
            pass
        self._plugin_manager.detach_editor()
        self._settings.detach_project()
        try:
            self._settings.save_all()
        except Exception as exc:
            messagebox.showerror(t('dialog.title.save_settings_failed'), str(exc))
        app_logger.info("Editor closed. Exiting.")
        self.window.destroy()

    # ------------------------------------------------------------------
    # 文件系统小工具
    # ------------------------------------------------------------------

    @staticmethod
    def _is_within(path: str, root: str) -> bool:
        """判断 ``path`` 是否在 ``root`` 目录内(或等于 root).

        跨平台处理大小写(Windows 不区分大小写),避免 ``/foo/bar``
        误判为 ``/foo/barbaz`` 的祖先。
        """
        if not path or not root:
            return False
        try:
            p = os.path.normcase(os.path.abspath(path))
            r = os.path.normcase(os.path.abspath(root))
        except (OSError, ValueError):
            return False
        if p == r:
            return True
        return p.startswith(r + os.sep)

    def _should_reattach_for_path(self, path: str) -> Optional[str]:
        """根据当前已挂载项目,决定打开 ``path`` 后是否需要切换项目根.

        规则:
        * 当前没挂载项目 -> 切到 ``path`` 的父目录;
        * ``path`` 不在当前项目内 -> 切到 ``path`` 的父目录;
        * 否则返回 ``None``(保持当前项目根不变,避免把项目视图
          切碎成只剩某个子目录)。

        这个函数是修"侧边栏打开深层文件时,其它文件全消失"的根因:
        旧实现无条件把 ``os.path.dirname(path)`` 设成项目根,导致
        双击 ``src/lib/utils.py`` 后,文件树变成 ``src/lib/`` 的内容,
        外层的 ``src/``、``tests/`` 等全部消失。
        """
        abs_path = os.path.abspath(path)
        file_dir = os.path.dirname(abs_path)
        current_root = self._current_project_root
        if not current_root:
            return file_dir or None
        if not file_dir:
            return None
        if self._is_within(file_dir, current_root):
            # 文件在当前项目内,保留视图
            return None
        return file_dir


    def _build_menubar(self):
        self._menubar = UMenuBar(self.window)
        self._menubar.pack(fill=tk.X, padx=0, pady=0)

        file_menu = self._menubar.add_cascade(t('menu.file'))
        file_menu.add_command(t('menu.file.new'), self._new_file, 'Ctrl+N')
        file_menu.add_command(t('menu.file.open'), self._open_file, 'Ctrl+O')
        file_menu.add_command(t('menu.file.open_project'), self._open_project, 'Ctrl+Shift+O')
        file_menu.add_separator()
        file_menu.add_command(t('menu.file.save'), self._save_file, 'Ctrl+S')
        file_menu.add_command(t('menu.file.save_as'), self._save_file_as, 'Ctrl+Shift+S')
        file_menu.add_separator()
        file_menu.add_command(t('menu.file.close_tab'), self._close_active_tab, 'Ctrl+W')
        file_menu.add_separator()
        file_menu.add_command(t('menu.file.run'), self._run_code, 'F5')
        file_menu.add_command(t('menu.file.check'), self._run_check, 'Ctrl+R')
        file_menu.add_command(t('menu.file.clear_output'), self._clear_output, 'Ctrl+L')
        file_menu.add_separator()
        file_menu.add_command(t('menu.file.exit'), self.window.destroy, 'Alt+F4')

        edit_menu = self._menubar.add_cascade(t('menu.edit'))
        edit_menu.add_command(t('menu.edit.undo'), self._undo, 'Ctrl+Z')
        edit_menu.add_command(t('menu.edit.redo'), self._redo, 'Ctrl+Y')
        edit_menu.add_separator()
        edit_menu.add_command(t('menu.edit.cut'), self._cut, 'Ctrl+X')
        edit_menu.add_command(t('menu.edit.copy'), self._copy, 'Ctrl+C')
        edit_menu.add_command(t('menu.edit.paste'), self._paste, 'Ctrl+V')
        edit_menu.add_separator()
        edit_menu.add_command(t('menu.edit.select_all'), self._select_all, 'Ctrl+A')
        edit_menu.add_separator()
        edit_menu.add_command(t('menu.edit.find'), self._open_find, 'Ctrl+F')
        edit_menu.add_command(t('menu.edit.replace'), self._open_replace, 'Ctrl+H')
        edit_menu.add_command(t('menu.edit.goto_line'), self._goto_line, 'Ctrl+G')
        edit_menu.add_separator()
        edit_menu.add_command(t('menu.edit.indent'), self._indent, 'Tab')
        edit_menu.add_command(t('menu.edit.outdent'), self._outdent, 'Shift+Tab')
        edit_menu.add_command(t('menu.edit.toggle_comment'), self._toggle_comment, 'Ctrl+/')
        lang_sub = edit_menu.add_cascade(t('menu.edit.switch_language'))
        for name in LANG_CONFIG:
            lang_sub.add_radiobutton(name, value=name, variable=self._lang_var(),
                                     command=lambda n=name: self._switch_language(n))

        query_menu = self._menubar.add_cascade(t('menu.query'))
        query_menu.add_command(t('menu.query.goto_definition'), self._goto_definition, 'F12')
        query_menu.add_command(t('menu.query.find_references'), self._find_references, 'Shift+F12')
        query_menu.add_command(t('menu.query.find_documentation'), self._find_documentation, 'Ctrl+Shift+F1')
        query_menu.add_separator()
        query_menu.add_command(t('menu.query.reparse'), self._reparse, 'F6')
        query_menu.add_command(t('menu.query.refresh_highlight'), self._apply_highlight, 'F7')
        query_menu.add_separator()
        query_menu.add_command(t('menu.query.trigger_suggestions'), self._show_suggestions, 'Ctrl+Space')
        query_menu.add_command(t('menu.query.hide_suggestions'), self._hide_suggestions, 'Esc')

        settings_menu = self._menubar.add_cascade(t('menu.settings'))
        theme_sub = settings_menu.add_cascade(t('menu.settings.theme'))
        for name in THEME_NAMES:
            theme_sub.add_radiobutton(name, value=name,
                                       variable=self._theme_var(),
                                       command=lambda n=name: self._set_theme(n))
        font_sub = settings_menu.add_cascade(t('menu.settings.font'))
        for fnt in FONT_FAMILIES:
            font_sub.add_radiobutton(fnt, value=fnt,
                                      variable=self._font_family_var(),
                                      command=lambda f=fnt: self._set_font_family(f))
        size_sub = settings_menu.add_cascade(t('menu.settings.font_size'))
        for sz in FONT_SIZES:
            size_sub.add_radiobutton(str(sz), value=sz,
                                      variable=self._font_size_var(),
                                      command=lambda s=sz: self._set_font_size(s))
        tab_sub = settings_menu.add_cascade(t('menu.settings.tab_width'))
        for tw in TAB_WIDTHS:
            tab_sub.add_radiobutton(str(tw), value=tw,
                                     variable=self._tab_width_var(),
                                     command=lambda t=tw: self._set_tab_width(t))
        settings_menu.add_separator()
        settings_menu.add_checkbutton(t('menu.settings.enable_highlight'), variable=self._highlight_var(),
                                       command=self._toggle_highlighting)
        settings_menu.add_checkbutton(t('menu.settings.enable_suggestions'), variable=self._suggestion_var(),
                                       command=self._toggle_suggestions)
        settings_menu.add_checkbutton(t('menu.settings.auto_save'), variable=self._autosave_var(),
                                       command=self._toggle_autosave)
        settings_menu.add_separator()
        # 语言子菜单: 每种语言一个 radio, 写回 settings 触发全局 i18n 切换
        lang_locale_sub = settings_menu.add_cascade(t('menu.settings.language'))
        for lang in AVAILABLE_LANGUAGES:
            lang_locale_sub.add_radiobutton(
                t(f'menu.language.{lang}'),
                value=lang,
                variable=self._lang_locale_var(),
                command=lambda l=lang: self._set_language_locale(l),
            )
        settings_menu.add_separator()
        settings_menu.add_command(t('menu.settings.global_settings'), self._open_global_settings)
        settings_menu.add_command(t('menu.settings.project_settings'), self._open_project_settings)
        settings_menu.add_command(t('menu.settings.reset'), self._reset_settings)

        help_menu = self._menubar.add_cascade(t('menu.help'))
        help_menu.add_command(t('menu.help.docs'), self._show_documentation, 'F1')
        help_menu.add_command(t('menu.help.shortcuts'), self._show_shortcuts, 'Ctrl+K')
        help_menu.add_separator()
        help_menu.add_command(t('menu.help.about'), self._show_about)
        help_menu.add_command(t('menu.help.check_updates'), self._check_updates)
        help_menu.add_command(t('menu.help.report_issue'), self._report_issue)

        # 插件菜单: 插件命令按 menu 分组作为子菜单挂在这里, 同时有
        # "管理插件..." 进入插件管理窗口。该菜单在 _refresh_plugin_menu 里
        # 重建, 这里只占位。
        self._plugin_menu = self._menubar.add_cascade(t('menu.plugins'))
        self._plugin_menu.add_command(t('menu.plugins.manage'), self._open_plugin_manager)

    def _bind_shortcuts(self):
        self.window.bind('<Control-n>', lambda e: self._new_file())
        self.window.bind('<Control-o>', lambda e: self._open_file())
        self.window.bind('<Control-Shift-O>', lambda e: self._open_project())
        self.window.bind('<Control-s>', lambda e: self._save_file())
        self.window.bind('<Control-Shift-S>', lambda e: self._save_file_as())
        self.window.bind('<Control-r>', lambda e: self._run_check())
        self.window.bind('<F5>', lambda e: self._run_code())
        self.window.bind('<Control-l>', lambda e: self._clear_output())
        self.window.bind('<Control-z>', lambda e: self._undo())
        self.window.bind('<Control-y>', lambda e: self._redo())
        self.window.bind('<Control-f>', lambda e: self._open_find())
        self.window.bind('<Control-h>', lambda e: self._open_replace())
        self.window.bind('<Control-g>', lambda e: self._goto_line())
        self.window.bind('<F12>', lambda e: self._goto_definition())
        self.window.bind('<Shift-F12>', lambda e: self._find_references())
        self.window.bind('<F6>', lambda e: self._reparse())
        self.window.bind('<F7>', lambda e: self._apply_highlight())
        self.window.bind('<Control-space>', lambda e: self._show_suggestions())
        self.window.bind('<F1>', lambda e: self._show_documentation())
        self.window.bind('<Control-slash>', lambda e: self._toggle_comment())
        # 多文档标签快捷键
        self.window.bind('<Control-w>', lambda e: self._close_active_tab())
        self.window.bind('<Control-Tab>', lambda e: self._next_tab())
        self.window.bind('<Control-Shift-Tab>', lambda e: self._prev_tab())

    def _lang_var(self) -> tk.StringVar:
        if not hasattr(self, '_lang_tk_var') or self._lang_tk_var is None:
            self._lang_tk_var = tk.StringVar(value=self._lang)
        return self._lang_tk_var

    def _lang_locale_var(self) -> tk.StringVar:
        """界面语言(独立于代码语言)对应的 tk 变量。

        之所以和 ``_lang_var`` 分开: 编辑器的 "切换语言" 子菜单是改
        代码高亮/补全的 Python/C/C++, 而 settings 菜单的 "语言"
        子菜单改的是 UI 文案 i18n.language。两者很容易混淆。
        """

        if not hasattr(self, '_lang_locale_tk_var') or self._lang_locale_tk_var is None:
            current = self._settings.effective('i18n.language', 'zh_CN')
            if current not in AVAILABLE_LANGUAGES:
                current = 'zh_CN'
            self._lang_locale_tk_var = tk.StringVar(value=current)
        return self._lang_locale_tk_var

    def _set_language_locale(self, lang: str) -> None:
        """菜单点击 → 写 settings → settings listener 会切 translator + 重建 UI。

        不在这里直接调 ``translator.set_language``: settings 是单一信息源,
        所有路径(菜单 / 插件 / 设置面板)都通过它同步, 避免循环触发。
        """

        if lang not in AVAILABLE_LANGUAGES:
            return
        if hasattr(self, '_lang_locale_tk_var') and self._lang_locale_tk_var is not None:
            self._lang_locale_tk_var.set(lang)
        self._write_setting(SettingsScope.GLOBAL, 'i18n.language', lang)

    def _theme_var(self) -> tk.StringVar:
        if not hasattr(self, '_theme_tk_var') or self._theme_tk_var is None:
            self._theme_tk_var = tk.StringVar(value=theme.current().name)
        return self._theme_tk_var

    def _font_family_var(self) -> tk.StringVar:
        if not hasattr(self, '_font_family_tk_var') or self._font_family_tk_var is None:
            self._font_family_tk_var = tk.StringVar(value=self._font_family)
        return self._font_family_tk_var

    def _font_size_var(self) -> tk.IntVar:
        if not hasattr(self, '_font_size_tk_var') or self._font_size_tk_var is None:
            self._font_size_tk_var = tk.IntVar(value=self._font_size)
        return self._font_size_tk_var

    def _tab_width_var(self) -> tk.IntVar:
        if not hasattr(self, '_tab_width_tk_var') or self._tab_width_tk_var is None:
            self._tab_width_tk_var = tk.IntVar(value=self._tab_width)
        return self._tab_width_tk_var

    def _highlight_var(self) -> tk.BooleanVar:
        if not hasattr(self, '_highlight_tk_var') or self._highlight_tk_var is None:
            self._highlight_tk_var = tk.BooleanVar(value=self._highlighting_enabled)
        return self._highlight_tk_var

    def _suggestion_var(self) -> tk.BooleanVar:
        if not hasattr(self, '_suggestion_tk_var') or self._suggestion_tk_var is None:
            self._suggestion_tk_var = tk.BooleanVar(value=self._suggestions_enabled)
        return self._suggestion_tk_var

    def _autosave_var(self) -> tk.BooleanVar:
        if not hasattr(self, '_autosave_tk_var') or self._autosave_tk_var is None:
            self._autosave_tk_var = tk.BooleanVar(value=self._autosave_enabled)
        return self._autosave_tk_var

    def _build_toolbar(self):
        bar = UFrame(self.window, variant='title')
        bar.pack(fill=tk.X, padx=0, pady=0)

        self._lang_combo = UComboBox(
            bar, values=list(LANG_CONFIG.keys()),
            command=self._on_lang_changed,
        )
        self._lang_combo.pack(side=tk.LEFT, padx=10, pady=6)

    def _build_editor(self):
        body = UFrame(self.window, variant='base')
        body.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)

        # 标签栏（多文档）
        self._tab_bar = TabBar(
            body,
            on_select=self._tab_select,
            on_close=self._tab_close,
            on_context_menu=self._tab_context_menu,
        )
        self._tab_bar.pack(fill=tk.X, padx=0, pady=0)

        # 水平 PanedWindow: 左 = 编辑器, 右 = Solution Explorer 风格的文件树。
        # sashrelief / sashwidth 让分隔条可见可拖动。
        self._paned = tk.PanedWindow(
            body, orient=tk.HORIZONTAL,
            sashwidth=4, sashrelief='flat',
            bg=theme.BORDER, bd=0,
            showhandle=False,
        )
        self._paned.pack(fill=tk.BOTH, expand=True)

        self._editor = UText(self._paned, width=80, height=20, show_line_numbers=True)
        self._paned.add(self._editor, minsize=200, stretch='always')

        self._file_tree = UFileTree(
            self._paned,
            title='Project',
            on_activate=self._open_path_from_tree,
            width=260,
        )
        self._paned.add(self._file_tree, minsize=160, stretch='never')
        # 默认把分隔条放到窗口右侧 260px 处。
        self._paned.bind('<Map>', self._init_paned_position, add='+')

        self._editor._text.bind('<KeyRelease>', self._on_key_release)
        self._editor._text.bind('<KeyPress>', self._on_key_press)
        self._editor._text.bind('<ButtonRelease-1>', self._on_click)
        self._editor._text.bind('<FocusIn>', self._on_focus_in)
        self._editor._text.config(undo=True)

    def _init_paned_position(self, event=None) -> None:
        """在 PanedWindow 首次显示后,把分隔条放到合适位置(右 260px)."""
        try:
            total = self._paned.winfo_width()
            if total <= 1:
                # 还未真正布局完成,推迟一帧
                self.window.after(10, self._init_paned_position)
                return
            self._paned.sash_place(0, max(total - 260, 200), 0)
            self._paned.unbind('<Map>')
        except tk.TclError:
            pass

    def _open_path_from_tree(self, path: str) -> None:
        """文件树双击回调: 复用 ``_load_file_into_editor`` 加载文件."""
        self._load_file_into_editor(path)

    def _load_file_into_editor(self, path: str) -> None:
        """文件树双击回调: 先确认脏状态, 再走统一加载路径.

        主体逻辑在 :meth:`_load_path_into_editor`,这里只做"未保存"确认,
        避免双击树时绕开"未保存提示"。
        """
        if self._dirty and not messagebox.askyesno(
            t('dialog.title.unsaved_discard'),
            t('dialog.unsaved_discard.message'),
        ):
            return
        self._load_path_into_editor(path)

    def _load_path_into_editor(self, path: str) -> None:
        """把 ``path`` 读进编辑器,统一处理"小文件快路径 / 大文件流式路径".

        多文档模式下为打开的文件创建一个新 Document 并切换到该文档。
        """
        threshold_raw = self._settings.global_settings.get(
            'editor.large_file_threshold_bytes', 5 * 1024 * 1024,
        )
        try:
            threshold = max(0, int(threshold_raw))
        except (TypeError, ValueError):
            threshold = 5 * 1024 * 1024

        try:
            size = os.path.getsize(path)
        except OSError as e:
            messagebox.showerror(t('dialog.title.open_failed'), str(e), parent=self.window)
            return

        is_large = threshold > 0 and size >= threshold

        if is_large:
            messagebox.showwarning(
                t('dialog.title.large_file'),
                t('dialog.large_file.message',
                  size=self._human_size(size),
                  threshold=self._human_size(threshold)),
                parent=self.window,
            )

        # 在做任何破坏性操作前, 先让可能 in-flight 的旧 after() 回调失效,
        # 防止"切换文件时旧 callback 把旧内容覆盖到新清空的编辑器"。
        self._stream_epoch += 1
        self._editor._text.config(state='normal')
        self._large_file_mode = False

        # 创建新文档（用路径作为 doc_id，便于重新打开同一文件时复用）
        doc_id = path
        doc = Document(path=path, content='', dirty=False, lang=self._lang, seq=0)
        self._documents[doc_id] = doc
        self._active_id = doc_id

        self._editor._text.delete('1.0', tk.END)
        self._current_file = path
        self._dirty = False

        if is_large:
            self._status_label.config(
                text=t('status.loading', name=os.path.basename(path), size=self._human_size(size)),
            )
            self._stream_insert_into_editor(path, size, doc_id)
        else:
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    code = f.read()
            except OSError as e:
                # 读失败时回滚状态
                self._active_id = None
                self._documents.pop(doc_id, None)
                self._current_file = None
                self._editor._text.delete('1.0', tk.END)
                messagebox.showerror(t('dialog.title.open_failed'), str(e), parent=self.window)
                return
            except UnicodeDecodeError as e:
                self._active_id = None
                self._documents.pop(doc_id, None)
                self._current_file = None
                self._editor._text.delete('1.0', tk.END)
                messagebox.showerror(t('dialog.title.open_failed'), str(e), parent=self.window)
                return
            doc.content = code
            self._editor._text.insert('1.0', code)
            self._status_label.config(text=t('status.opened', name=os.path.basename(path)))

        self._update_tab_bar()

        # 关键修复: 打开文件时**只在文件不在当前项目内**时才更新项目根
        new_root = self._should_reattach_for_path(path)
        if new_root:
            self._attach_project(new_root)

        # 大文件不触发高亮
        if not is_large:
            self._apply_highlight()
        if is_large:
            self._last_emit_code = None
        else:
            self._last_emit_code = self._editor.get('1.0', 'end-1c')
        self._emit(HookEvents.EDITOR_FILE_OPENED, path)

    def _stream_insert_into_editor(self, path: str, total_size: int, doc_id: str) -> None:
        """分块读取 ``path`` 并插入编辑器; 通过 ``after(1)`` 让 Tk 事件循环
        有空隙处理其他事件(窗口移动、滚动、重绘)。
        """
        chunk_size = 64 * 1024  # 64 KiB
        try:
            f = open(path, 'r', encoding='utf-8', errors='replace')
        except OSError as e:
            messagebox.showerror(t('dialog.title.open_failed'), str(e), parent=self.window)
            self._large_file_mode = False
            self._editor._text.config(state='normal')
            self._status_label.config(text=t('status.open_failed'))
            return

        self._stream_epoch += 1
        my_epoch = self._stream_epoch
        self._large_file_mode = True
        self._editor._text.config(state='disabled')
        accumulated: List[str] = []

        def insert_chunk() -> None:
            if my_epoch != self._stream_epoch:
                try:
                    f.close()
                except Exception:
                    pass
                return
            try:
                chunk = f.read(chunk_size)
            except OSError as e:
                try:
                    f.close()
                except Exception:
                    pass
                self._editor._text.config(state='normal')
                self._large_file_mode = False
                messagebox.showerror(t('dialog.title.read_failed'), str(e), parent=self.window)
                self._status_label.config(text=t('status.read_failed'))
                return

            if not chunk:
                try:
                    f.close()
                except Exception:
                    pass
                self._editor._text.config(state='normal')
                self._large_file_mode = False
                self._status_label.config(
                    text=t('status.opened', name=os.path.basename(path))
                )
                # 更新文档内容
                if doc_id in self._documents:
                    self._documents[doc_id].content = ''.join(accumulated)
                try:
                    self._last_emit_code = self._editor.get('1.0', 'end-1c')
                except tk.TclError:
                    pass
                self._emit(HookEvents.EDITOR_FILE_OPENED, path)
                return

            accumulated.append(chunk)
            self._editor._text.insert(self._editor._text.index('end-1c'), chunk)
            self.window.after(1, insert_chunk)

        self.window.after(1, insert_chunk)

    @staticmethod
    def _human_size(nbytes: int) -> str:
        """把字节数格式化成易读字符串(用于警告 / 状态栏)。"""
        try:
            n = float(max(0, int(nbytes)))
        except (TypeError, ValueError):
            return f'{nbytes} B'
        for unit in ('B', 'KB', 'MB', 'GB'):
            if n < 1024.0 or unit == 'GB':
                if unit == 'B':
                    return f'{int(n)} {unit}'
                return f'{n:.1f} {unit}'
            n /= 1024.0
        return f'{nbytes} B'

    def _build_output_panel(self):
        self._output_frame = UFrame(self.window, variant='panel', height=120)
        self._output_frame.pack(fill=tk.X, padx=0, pady=0)
        self._output_frame.pack_propagate(False)

        header = UFrame(self._output_frame, variant='title')
        header.pack(fill=tk.X)
        ULabel(header, text=t('panel.output'), variant='secondary', bg=theme.BG_TITLE).pack(side=tk.LEFT, padx=4, pady=2)

        self._output = UText(self._output_frame, width=80, height=5)
        self._output.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)
        self._output._text.config(state='disabled')

    def _build_status_bar(self):
        status = UFrame(self.window, variant='title', height=24)
        status.pack(fill=tk.X, padx=0, pady=0)
        status.pack_propagate(False)

        self._status_label = ULabel(status, text=t('status.ready'), variant='secondary',
                                     bg=theme.BG_TITLE)
        self._status_label.pack(side=tk.LEFT, padx=10, pady=2)

        self._lang_label = ULabel(status, text='Python', variant='secondary',
                                   bg=theme.BG_TITLE)
        self._lang_label.pack(side=tk.RIGHT, padx=10, pady=2)

        self._pos_label = ULabel(status, text='Ln 1, Col 1', variant='secondary',
                                  bg=theme.BG_TITLE)
        self._pos_label.pack(side=tk.RIGHT, padx=10, pady=2)

    def _switch_language(self, lang, *, from_doc_switch: bool = False):
        if lang not in LANG_CONFIG:
            return
        self._lang = lang
        if hasattr(self, '_lang_tk_var') and self._lang_tk_var is not None:
            self._lang_tk_var.set(lang)
        config = LANG_CONFIG[lang]
        # 插件注册的语言存的是 factory, 而不是已实例化的类 — 这里统一
        # 优先用 factory (动态), 没有再退回类构造 (内置)。
        if 'highlighter_factory' in config:
            self._highlighter = config['highlighter_factory']()
            self._suggestion_expert = config['suggestion_factory']()
        else:
            self._highlighter = config['highlighter']()
            self._suggestion_expert = config['suggestion']()
        self._lang_label.config(text=lang)
        # 切语言相当于"打开新的示例文本", 同样需要取消可能的 in-flight 大文件流
        # 并退出大文件模式(示例文本永远是小文件)。
        self._stream_epoch += 1
        self._editor._text.config(state='normal')
        self._large_file_mode = False
        # 从文档切换来时不清空编辑器（内容已由 _switch_document 加载）
        if not from_doc_switch:
            self._editor._text.delete('1.0', tk.END)
            self._editor._text.insert('1.0', config['sample'])
            # 更新当前文档的语言
            if self._active_id and self._active_id in self._documents:
                self._documents[self._active_id].lang = lang
            self._apply_highlight()
        self._update_status()
        self._status_label.config(text=t('status.editor_lang_changed', lang=lang))
        app_logger.info(f"Language switched to: {lang}")
        self._emit(HookEvents.EDITOR_LANGUAGE_CHANGED, lang)

    def _on_lang_changed(self, value):
        self._switch_language(value)

    def _on_key_release(self, event=None):
        self._update_status()
        self._schedule_highlight()
        if self._suggestions_enabled:
            self._schedule_suggestions()
        self._mark_dirty()
        self._emit_content_changed()

    def _schedule_highlight(self) -> None:
        """按 ``editor.highlight_delay_ms`` 防抖地触发高亮刷新。

        每次调用都会取消上一次尚未执行的 ``after`` 任务并重新调度,
        这样快速连续按键时,只有最后一次按键在停顿 ``delay`` 毫秒后
        才会真正执行高亮。``delay`` 为 0 时退化为 ``after(0, ...)``,
        仍会在当前事件循环 tick 之后立即执行。
        """

        if not self._highlighting_enabled:
            self._highlight_debouncer.cancel()
            return
        self._highlight_debouncer.schedule(
            self._run_scheduled_highlight, self._highlight_delay_ms,
        )

    def _cancel_pending_highlight(self) -> None:
        self._highlight_debouncer.cancel()

    def _run_scheduled_highlight(self) -> None:
        """``after`` 回调入口:执行实际高亮。"""

        self._apply_highlight()

    def _schedule_suggestions(self) -> None:
        """输入或光标主动移动后,按 ``editor.suggestion_delay_ms`` 延迟触发建议。

        输入(字符键)与光标主动移动(方向键/Home/End/PageUp/PageDown/鼠标点击)
        共享同一条 debounce 通道,因此连续触发时只保留最后一次的事件,
        停顿 ``_suggest_delay_ms`` 毫秒后才真正执行建议刷新。
        """

        if not self._suggestions_enabled:
            self._suggest_debouncer.cancel()
            return
        self._suggest_debouncer.schedule(
            self._run_scheduled_suggestions, self._suggest_delay_ms,
        )

    def _cancel_pending_suggestions(self) -> None:
        self._suggest_debouncer.cancel()

    def _run_scheduled_suggestions(self) -> None:
        self._show_suggestions()

    def _on_key_press(self, event=None):
        if self._suggestion_popup and self._suggestion_popup.winfo_exists():
            if event and event.keysym in ('Escape',):
                self._suggestion_popup.hide()
            elif event and event.keysym in ('Down', 'Up', 'Return', 'Tab'):
                return

    def _on_click(self, event=None):
        self._update_status()
        # 鼠标点击属于"光标主动移动",与键入共用同一条建议 debounce 通道,
        # 保证停顿 _suggest_delay_ms 毫秒后才真正触发,避免连续点击时抖动。
        if self._suggestions_enabled:
            self._schedule_suggestions()
        self._emit_cursor_moved()

    def _on_focus_in(self, event=None):
        self._update_status()
        self._emit_cursor_moved()

    def _emit_cursor_moved(self) -> None:
        """发出光标位置变化事件, 但只在线号或列号真正变化时触发。"""

        try:
            cursor = self._editor._text.index(tk.INSERT)
            line, col = cursor.split('.')
            line_i, col_i = int(line), int(col)
        except Exception:
            return
        last = getattr(self, '_last_cursor', None)
        if last == (line_i, col_i):
            return
        self._last_cursor = (line_i, col_i)
        self._emit(HookEvents.EDITOR_CURSOR_MOVED, line_i, col_i)

    def _apply_highlight(self):
        if self._large_file_mode:
            # 大文件模式: 跳过整套高亮(对几十 MB 文本跑正则/tokenize 会卡死)。
            return
        if not self._highlighting_enabled:
            return
        code = self._editor.get('1.0', 'end-1c')
        if not code.strip():
            return
        block = HighlightBlock(code=code, tokens=None)
        result = self._highlighter.highlight(block)
        if result.tokens is None:
            return

        text = self._editor._text
        for tag in text.tag_names():
            text.tag_delete(tag)

        for token_type, style in HIGHLIGHT_TOKENS.items():
            text.tag_configure(token_type, **style)

        for token in result.tokens:
            start = self._index_from_pos(token.start)
            end = self._index_from_pos(token.end)
            tag = token.type if token.type in HIGHLIGHT_TOKENS else 'identifier'
            text.tag_add(tag, start, end)

    def _show_suggestions(self):
        if self._large_file_mode:
            # 大文件模式: 把全文本喂给 highlighter/suggester 会非常慢且
            # 没必要(用户也看不到结果), 直接跳过。
            return
        if not self._suggestions_enabled:
            return
        code = self._editor.get('1.0', 'end-1c')
        cursor = self._editor._text.index(tk.INSERT)
        line, col = map(int, cursor.split('.'))
        position = sum(len(l) + 1 for l in code.split('\n')[:line - 1]) + col
        block = SuggestionBlock(code=code, position=position)
        suggestions = self._suggestion_expert.suggest(block)

        if not suggestions:
            if self._suggestion_popup:
                self._suggestion_popup.hide()
            return

        items = [CompletionItem(label=s.label, priority=s.priority, kind=s.kind) for s in suggestions[:20]]
        if self._suggestion_popup and self._suggestion_popup.winfo_exists():
            self._suggestion_popup.set_items(items)
            self._suggestion_popup.show(
                attach_to=self._editor._text,
                index=tk.INSERT,
            )
        else:
            self._suggestion_popup = UEditorSuggestion(
                self._editor,
                items=items,
                on_select=self._on_suggestion_select,
                max_visible=8,
                show_detail=False,
                show_description=False,
            )
            self._suggestion_popup.show(
                attach_to=self._editor._text,
                index=tk.INSERT,
            )

    def _hide_suggestions(self):
        if self._suggestion_popup and self._suggestion_popup.winfo_exists():
            self._suggestion_popup.hide()

    def _on_suggestion_select(self, item):
        text = self._editor._text
        cursor = text.index(tk.INSERT)
        line, col = map(int, cursor.split('.'))

        line_start = f'{line}.0'
        line_text = text.get(line_start, cursor)
        word_start = col
        while word_start > 0 and (line_text[word_start - 1].isalnum() or line_text[word_start - 1] == '_'):
            word_start -= 1

        text.delete(f'{line}.{word_start}', cursor)
        text.insert(f'{line}.{word_start}', item.insert)
        self._apply_highlight()

    def _index_from_pos(self, pos):
        code = self._editor.get('1.0', 'end-1c')
        line = 1
        col = 0
        for i, ch in enumerate(code):
            if i >= pos:
                break
            if ch == '\n':
                line += 1
                col = 0
            else:
                col += 1
        return f'{line}.{col}'

    def _update_status(self):
        cursor = self._editor._text.index(tk.INSERT)
        line, col = cursor.split('.')
        self._pos_label.config(text=t('status.pos', line=line, col=int(col) + 1))

    def _new_file(self):
        # 检查当前文档是否有未保存更改
        if self._active_id and self._documents.get(self._active_id):
            curr = self._documents[self._active_id]
            if curr.dirty:
                result = messagebox.askyesno(
                    t('dialog.title.unsaved_discard'),
                    t('dialog.unsaved_discard.message'),
                )
                if not result:
                    return

        # 创建新文档
        seq = self._next_untitled_seq
        doc_id = self._new_doc_id()
        self._documents[doc_id] = Document(
            path=None,
            content='',
            dirty=False,
            lang=self._lang,
            seq=seq,
        )
        self._next_untitled_seq += 1
        self._active_id = doc_id

        # 切换到新文档
        self._stream_epoch += 1
        self._editor._text.config(state='normal')
        self._large_file_mode = False
        self._editor._text.delete('1.0', tk.END)
        self._current_file = None
        self._dirty = False
        self._last_emit_code = ''
        self._status_label.config(text=t('status.new_file'))
        self._update_tab_bar()
        self._emit(HookEvents.EDITOR_FILE_CREATED)
        app_logger.info(f"New file created: {doc_id}")

    def _open_file(self):
        # 检查当前文档是否有未保存更改
        if self._active_id and self._documents.get(self._active_id):
            curr = self._documents[self._active_id]
            if curr.dirty:
                result = messagebox.askyesno(
                    t('dialog.title.unsaved_discard'),
                    t('dialog.unsaved_discard.message'),
                )
                if not result:
                    return

        ext = LANG_CONFIG[self._lang]['ext']
        lang_label = t('file_dialog.lang_filter', lang=self._lang)
        filetypes = [(lang_label, f'*{ext}'), (t('file_dialog.all_files'), '*.*')]
        path = filedialog.askopenfilename(filetypes=filetypes)
        if not path:
            return

        # 检查是否已在打开的文档中
        for doc_id, doc in self._documents.items():
            if doc.path == path:
                # 已打开，切换到该文档
                self._switch_document(doc_id)
                return

        # 大小判断/分块流式/禁用高亮建议等都在 :meth:`_load_path_into_editor` 里,
        # 这里不再重复 open() + insert() 的逻辑。
        self._load_path_into_editor(path)
        app_logger.info(f"File opened: {path}")

    def _open_project(self):
        """仅打开/切换项目目录, 不动编辑器内容.

        与 :meth:`_open_file` 的区别: 本方法只把目录挂到
        :class:`SettingsManager` 并刷新右侧文件树, 编辑器里的代码
        不会被替换,适合"先选项目再写代码"或"切换到另一个项目"的场景。
        若当前有未保存修改, 仍会先弹确认以免误操作。
        """
        if self._dirty and not messagebox.askyesno(
            t('dialog.title.unsaved_discard'),
            t('dialog.unsaved_discard.message'),
        ):
            return
        # 默认定位到当前项目根(若有), 方便连续切换。
        initial = self._current_project_root or os.getcwd()
        chosen = filedialog.askdirectory(
            title=t('dialog.title.choose_project'),
            initialdir=initial if os.path.isdir(initial) else None,
            parent=self.window,
        )
        if not chosen:
            return
        self._attach_project(chosen)
        if os.path.isdir(chosen):
            self._status_label.config(
                text=t('status.project', name=os.path.basename(chosen) or chosen),
            )

    def _save_file(self):
        if self._active_id and self._documents.get(self._active_id):
            doc = self._documents[self._active_id]
            if doc.path:
                self._save_to_path(doc.path)
            else:
                self._save_file_as()
        else:
            self._save_file_as()

    def _save_file_as(self):
        ext = LANG_CONFIG[self._lang]['ext']
        lang_label = t('file_dialog.lang_filter', lang=self._lang)
        filetypes = [(lang_label, f'*{ext}'), (t('file_dialog.all_files'), '*.*')]
        path = filedialog.asksaveasfilename(defaultextension=ext, filetypes=filetypes)
        if path:
            self._save_to_path(path)
            # 同时更新文档的 path
            if self._active_id and self._active_id in self._documents:
                self._documents[self._active_id].path = path
            self._current_file = path
            new_root = self._should_reattach_for_path(path)
            if new_root:
                self._attach_project(new_root)

    def _save_to_path(self, path: str):
        code = self._editor.get('1.0', 'end-1c')
        try:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(code)
        except OSError as e:
            app_logger.error(f"Failed to save file {path}: {e}")
            messagebox.showerror(t('dialog.title.save_failed'), str(e))
            return
        self._dirty = False
        if self._active_id and self._active_id in self._documents:
            self._documents[self._active_id].dirty = False
            self._documents[self._active_id].content = code
        self._update_tab_bar()
        app_logger.info(f"File saved: {path}")
        self._status_label.config(text=t('status.saved', name=os.path.basename(path)))
        self._emit(HookEvents.EDITOR_FILE_SAVED, path)

    def _undo(self):
        try:
            self._editor._text.edit_undo()
        except tk.TclError:
            pass
        self._apply_highlight()

    def _redo(self):
        try:
            self._editor._text.edit_redo()
        except tk.TclError:
            pass
        self._apply_highlight()

    def _cut(self):
        widget = self.window.focus_get()
        if widget is not None:
            widget.event_generate('<<Cut>>')
        self._apply_highlight()

    def _copy(self):
        widget = self.window.focus_get()
        if widget is not None:
            widget.event_generate('<<Copy>>')

    def _paste(self):
        widget = self.window.focus_get()
        if widget is not None:
            widget.event_generate('<<Paste>>')
        self._apply_highlight()

    def _select_all(self):
        self._editor._text.tag_add('sel', '1.0', 'end')
        self._editor._text.mark_set(tk.INSERT, '1.0')
        self._editor._text.see(tk.INSERT)

    def _open_find(self):
        self._show_find_dialog(replace=False)

    def _open_replace(self):
        self._show_find_dialog(replace=True)

    def _show_find_dialog(self, replace: bool):
        if self._find_dialog and self._find_dialog.winfo_exists():
            self._find_dialog.destroy()
        dlg = tk.Toplevel(self.window)
        dlg.title(t('dialog.title.replace') if replace else t('dialog.title.find'))
        dlg.configure(bg=theme.BG_PANEL)
        dlg.transient(self.window)
        dlg.resizable(False, False)

        ULabel(dlg, text=t('find.find_label'), bg=theme.BG_PANEL).grid(row=0, column=0, sticky='e', padx=6, pady=6)
        find_var = tk.StringVar(value=self._find_query)
        find_entry = tk.Entry(dlg, textvariable=find_var, width=30,
                              bg=theme.BG_INPUT, fg=theme.FG_PRIMARY,
                              insertbackground=theme.FG_PRIMARY)
        find_entry.grid(row=0, column=1, columnspan=2, sticky='ew', padx=6, pady=6)

        replace_var = None
        replace_entry = None
        if replace:
            ULabel(dlg, text=t('find.replace_label'), bg=theme.BG_PANEL).grid(row=1, column=0, sticky='e', padx=6, pady=6)
            replace_var = tk.StringVar()
            replace_entry = tk.Entry(dlg, textvariable=replace_var, width=30,
                                      bg=theme.BG_INPUT, fg=theme.FG_PRIMARY,
                                      insertbackground=theme.FG_PRIMARY)
            replace_entry.grid(row=1, column=1, columnspan=2, sticky='ew', padx=6, pady=6)

        case_var = tk.BooleanVar(value=False)
        tk.Checkbutton(dlg, text=t('find.case_sensitive'), variable=case_var,
                       bg=theme.BG_PANEL, fg=theme.FG_PRIMARY,
                       selectcolor=theme.BG_RAISED,
                       activebackground=theme.BG_PANEL).grid(row=2, column=0, columnspan=3, sticky='w', padx=6)

        def do_find(*_):
            query = find_var.get()
            if not query:
                return
            self._find_query = query
            text = self._editor._text
            start = text.index(tk.INSERT)
            if self._find_last_index:
                start = self._find_last_index
            nocase = not case_var.get()
            pos = text.search(query, start, stopindex='end', nocase=nocase)
            if not pos:
                pos = text.search(query, '1.0', stopindex=start, nocase=nocase)
                if not pos:
                    messagebox.showinfo(t('dialog.title.find_not_found'), t('dialog.find.not_found'), parent=dlg)
                    return
            end = f'{pos}+{len(query)}c'
            text.tag_remove('sel', '1.0', 'end')
            text.tag_add('sel', pos, end)
            text.mark_set(tk.INSERT, end)
            text.see(pos)
            self._find_last_index = str(end)

        def do_replace():
            do_find()
            replace_text = replace_var.get() if replace_var else ''
            sel = self._editor._text.tag_ranges('sel')
            if sel:
                self._editor._text.delete(sel[0], sel[1])
                self._editor._text.insert(sel[0], replace_text)
                self._find_last_index = str(sel[0])
                self._apply_highlight()

        def do_replace_all():
            query = find_var.get()
            if not query:
                return
            replace_text = replace_var.get() if replace_var else ''
            self._find_query = query
            text = self._editor._text
            nocase = not case_var.get()
            count = 0
            pos = text.search(query, '1.0', stopindex='end', nocase=nocase)
            while pos:
                end = f'{pos}+{len(query)}c'
                text.delete(pos, end)
                text.insert(pos, replace_text)
                count += 1
                pos = text.search(query, f'{pos}+{len(replace_text)}c',
                                   stopindex='end', nocase=nocase)
            self._apply_highlight()
            messagebox.showinfo(t('dialog.title.replace_done'), t('dialog.replace.done', count=count), parent=dlg)

        def close():
            self._find_dialog = None
            dlg.destroy()

        btn_row = 3 if replace else 2
        UButton(dlg, text=t('find.find_next'), command=do_find, variant='primary', width=80, height=24
                 ).grid(row=btn_row, column=0, padx=4, pady=6)
        if replace:
            UButton(dlg, text=t('find.replace'), command=do_replace, variant='default', width=60, height=24
                     ).grid(row=btn_row, column=1, padx=4, pady=6)
            UButton(dlg, text=t('find.replace_all'), command=do_replace_all, variant='warning', width=80, height=24
                     ).grid(row=btn_row, column=2, padx=4, pady=6)
        else:
            UButton(dlg, text=t('find.close'), command=close, variant='default', width=60, height=24
                     ).grid(row=btn_row, column=1, columnspan=2, padx=4, pady=6, sticky='ew')

        dlg.protocol('WM_DELETE_WINDOW', close)
        find_entry.focus_set()
        self._find_dialog = dlg

    def _goto_line(self):
        line_no = simpledialog.askinteger(
            t('dialog.title.goto_line'),
            t('dialog.goto_line.prompt'),
            parent=self.window, minvalue=1,
            maxvalue=self._line_count(),
        )
        if not line_no:
            return
        self._editor._text.mark_set(tk.INSERT, f'{line_no}.0')
        self._editor._text.see(f'{line_no}.0')
        self._update_status()

    def _line_count(self) -> int:
        return int(self._editor._text.index('end-1c').split('.')[0])

    def _indent(self):
        text = self._editor._text
        sel = text.tag_ranges('sel')
        if sel:
            start = sel[0]
            end = sel[1]
        else:
            start = text.index(tk.INSERT)
            end = start
        start = str(start)
        end = str(end)
        start_line = int(start.split('.')[0])
        end_line = int(end.split('.')[0])
        indent = ' ' * self._tab_width
        for ln in range(start_line, end_line + 1):
            line_start = f'{ln}.0'
            text.insert(line_start, indent)
        new_start = f'{start_line}.0'
        new_end = f'{end_line}.{len(text.get(f"{end_line}.0", f"{end_line}.end"))}'
        text.tag_remove('sel', '1.0', 'end')
        text.tag_add('sel', new_start, new_end)

    def _outdent(self):
        text = self._editor._text
        sel = text.tag_ranges('sel')
        if sel:
            start = sel[0]
            end = sel[1]
        else:
            start = text.index(tk.INSERT)
            end = start
        start = str(start)
        end = str(end)
        start_line = int(start.split('.')[0])
        end_line = int(end.split('.')[0])
        for ln in range(start_line, end_line + 1):
            line_start = f'{ln}.0'
            line_text = text.get(line_start, f'{ln}.end')
            stripped = line_text.lstrip()
            removed = len(line_text) - len(stripped)
            for i in range(min(self._tab_width, removed)):
                if line_text[i] == ' ':
                    text.delete(f'{ln}.{i}')
                else:
                    break

    def _toggle_comment(self):
        if self._lang != 'Python':
            messagebox.showinfo(
                t('dialog.title.toggle_comment'),
                t('dialog.toggle_comment.unsupported', lang=self._lang),
                parent=self.window,
            )
            return
        text = self._editor._text
        sel = text.tag_ranges('sel')
        if sel:
            start = sel[0]
            end = sel[1]
        else:
            start = text.index(tk.INSERT)
            end = start
        start = str(start)
        end = str(end)
        start_line = int(start.split('.')[0])
        end_line = int(end.split('.')[0])
        for ln in range(start_line, end_line + 1):
            line_start = f'{ln}.0'
            line_text = text.get(line_start, f'{ln}.end')
            if line_text.lstrip().startswith('#'):
                stripped = line_text.lstrip()
                prefix = line_text[:len(line_text) - len(stripped)]
                text.delete(line_start, f'{ln}.{len(prefix)+1}')
            else:
                text.insert(line_start, '# ')

    def _goto_definition(self):
        messagebox.showinfo(t('dialog.title.goto_definition'),
                           t('dialog.goto_definition.not_implemented'), parent=self.window)

    def _find_references(self):
        messagebox.showinfo(t('dialog.title.find_references'),
                           t('dialog.find_references.not_implemented'), parent=self.window)

    def _find_documentation(self):
        messagebox.showinfo(t('dialog.title.find_documentation'),
                           t('dialog.find_documentation.not_implemented'), parent=self.window)

    def _reparse(self):
        self._apply_highlight()
        self._status_label.config(text=t('status.reparsed'))

    def _set_theme(self, name: str, *, persist: bool = True):
        try:
            target = theme.by_name(name)
            if target is None:
                return
            theme.set_theme(target, refresh_root=self.window)
            if hasattr(self, '_theme_tk_var') and self._theme_tk_var is not None:
                self._theme_tk_var.set(name)
            self._status_label.config(text=t('status.theme', name=name))
            self._force_redraw()
            app_logger.info(f"Theme changed to: {name}")
        except Exception as e:
            app_logger.error(f"Failed to set theme {name}: {e}")
            self._status_label.config(text=t('status.theme_error', err=str(e)))
            return
        if persist:
            self._write_setting(SettingsScope.GLOBAL, 'ui.theme', name)

    def _force_redraw(self):
        """Force complete window redraw - workaround for Tk rendering quirks on some systems."""
        try:
            self.window.update_idletasks()
            self.window.update()
            geom = self.window.geometry()
            self.window.geometry(geom)
            self.window.update_idletasks()
            self.window.update()
            self.window.tk.eval('update')
            if getattr(self.window, '_custom_titlebar', True):
                self.window.overrideredirect(False)
                self.window.update_idletasks()
                self.window.overrideredirect(True)
                self.window.update_idletasks()
                self.window.update()
        except Exception:
            pass

    def _set_font_family(self, family: str):
        self._font_family = family
        if hasattr(self, '_font_family_tk_var') and self._font_family_tk_var is not None:
            self._font_family_tk_var.set(family)
        self._apply_editor_font()
        self._status_label.config(text=t('status.font', name=family))
        self._write_setting(SettingsScope.GLOBAL, 'ui.font_family', family)

    def _set_font_size(self, size: int):
        self._font_size = size
        if hasattr(self, '_font_size_tk_var') and self._font_size_tk_var is not None:
            self._font_size_tk_var.set(size)
        self._apply_editor_font()
        self._status_label.config(text=t('status.font_size', n=size))
        self._write_setting(SettingsScope.GLOBAL, 'ui.font_size', int(size))

    def _apply_editor_font(self):
        font = (self._font_family, self._font_size)
        self._editor._text.config(font=font)

    def _set_tab_width(self, tw: int, *, persist: bool = True):
        self._tab_width = tw
        if hasattr(self, '_tab_width_tk_var') and self._tab_width_tk_var is not None:
            self._tab_width_tk_var.set(tw)
        self._editor._text.config(tabs=(tw * self._font_size,))
        if persist:
            self._write_setting(SettingsScope.GLOBAL, 'editor.tab_size', int(tw))

    def _toggle_highlighting(self):
        self._highlighting_enabled = bool(self._highlight_tk_var.get())
        if not self._highlighting_enabled:
            self._cancel_pending_highlight()
            text = self._editor._text
            for tag in text.tag_names():
                text.tag_delete(tag)
        else:
            self._cancel_pending_highlight()
            self._apply_highlight()
        self._write_setting(
            SettingsScope.GLOBAL, 'completion.enabled', self._highlighting_enabled,
        )

    def _toggle_suggestions(self):
        self._suggestions_enabled = bool(self._suggestion_tk_var.get())
        if not self._suggestions_enabled:
            self._hide_suggestions()
        self._write_setting(
            SettingsScope.GLOBAL, 'completion.enabled', self._suggestions_enabled,
        )

    def _toggle_autosave(self):
        self._autosave_enabled = bool(self._autosave_tk_var.get())
        self._write_setting(
            SettingsScope.GLOBAL, 'editor.auto_save', self._autosave_enabled,
        )

    def _open_global_settings(self):
        """打开可视化的全局+项目设置窗口(默认在"全局"Tab)。"""
        from modules.settings.widgets import UProjectSettingsWindow
        try:
            win = UProjectSettingsWindow(
                self._settings, parent=self.window, title=t('dialog.title.settings'),
            )
            self._settings_window = win
            win._switch(SettingsScope.GLOBAL)  # noqa: SLF001 - 单文件集成
        except Exception as exc:
            messagebox.showerror(t('dialog.title.settings_load_failed'),
                               t('dialog.settings.load_failed', err=exc), parent=self.window)

    def _open_project_settings(self):
        """打开设置窗口并跳到"项目"Tab;无项目时自动提示。"""
        if self._settings.project_settings is None:
            if not messagebox.askyesno(
                t('dialog.title.project_load_failed'),
                t('dialog.project_settings.no_project'),
                parent=self.window,
            ):
                return
            chosen = filedialog.askdirectory(
                title=t('dialog.title.choose_project'),
                parent=self.window,
            )
            if not chosen:
                return
            self._attach_project(chosen)
        from modules.settings.widgets import UProjectSettingsWindow
        try:
            win = UProjectSettingsWindow(
                self._settings, parent=self.window, title=t('dialog.title.project_settings'),
            )
            # 切到项目 Tab
            try:
                win._switch(SettingsScope.PROJECT)  # noqa: SLF001 - 单文件集成
            except Exception:
                pass
            self._settings_window = win
        except Exception as exc:
            messagebox.showerror(t('dialog.title.project_load_failed'),
                               t('dialog.project_settings.load_failed', err=exc), parent=self.window)

    def _attach_project(self, root: str) -> None:
        """附加项目目录到 SettingsManager,记录当前根,并刷新文件树。"""

        root = os.path.abspath(root)
        if self._current_project_root == root:
            return
        # 切项目: 先卸载旧项目的项目级插件, 再 attach 新项目, 再加载新插件。
        # 顺序避免"加载新插件时还在用旧项目 settings"的混淆。
        try:
            self._plugin_manager.unload_project_plugins()
        except Exception:
            pass
        self._settings.detach_project()
        try:
            self._settings.attach_project(root)
            self._current_project_root = root
            app_logger.info(f"Project attached: {root}")
        except Exception as exc:
            app_logger.error(f"Failed to attach project {root}: {exc}")
            messagebox.showerror(
                t('dialog.title.project_attach_failed'),
                t('dialog.project_settings.attach_failed', root=root, err=exc),
                parent=self.window,
            )
            return
        # 同步刷新右侧文件树。
        tree = getattr(self, '_file_tree', None)
        if tree is not None:
            tree.set_root(root)
        # 加载项目级插件 (<root>/plugins/)
        try:
            self._plugin_manager.load_project_plugins(root)
        except Exception:
            pass
        self._refresh_plugin_menu()
        self._refresh_plugin_languages()

    def _reset_settings(self):
        if not messagebox.askyesno(
            t('dialog.title.reset_settings'),
            t('dialog.reset_settings.confirm'),
            parent=self.window,
        ):
            return
        try:
            self._settings.reset(SettingsScope.GLOBAL)
        except Exception:
            pass
        self._refresh_all_from_settings()
        try:
            self._settings.save_all()
        except Exception as exc:
            messagebox.showerror(t('dialog.title.reset_failed'), str(exc), parent=self.window)
            return
        self._status_label.config(text=t('status.settings_reset'))

    # ------------------------------------------------------------------
    # 插件系统集成
    # ------------------------------------------------------------------
    #
    # 以下方法给 :class:`PluginManager` 调用, 编辑器对外暴露一组受限接口:
    #
    # * :meth:`_add_plugin_command` —— 把插件命令挂到菜单。
    # * :meth:`_add_plugin_language` —— 把插件声明的语言加入 LANG_CONFIG + 下拉框。
    # * :meth:`_refresh_plugin_menu` —— 重建"插件"主菜单的子菜单 (命令分组)。
    # * :meth:`_refresh_plugin_languages` —— 把插件语言重新同步到下拉框。
    #
    # 钩子事件通过 :meth:`_emit` 在编辑器关键节点发出 (打开/保存/内容变更等)。
    #

    def _emit(self, hook: str, *args: Any, **kwargs: Any) -> None:
        """发出一个钩子事件给所有已订阅插件。

        出错被吞掉, 单个坏插件不影响编辑器主流程。
        """

        manager = getattr(self, '_plugin_manager', None)
        if manager is None:
            return
        try:
            manager.emit(hook, *args, **kwargs)
        except Exception:
            pass

    def _emit_content_changed(self) -> None:
        """按当前编辑器内容是否真的发生变化来决定是否 emit content_changed。

        简单的"最近一次 emit 的内容快照"对比 — 不依赖 Tk 的 edit_modified,
        因为后者会因为 undo 之后还触发而误报。
        """

        if not hasattr(self, '_last_emit_code'):
            self._last_emit_code = None
        try:
            code = self._editor.get('1.0', 'end-1c')
        except tk.TclError:
            return
        if code == self._last_emit_code:
            return
        self._last_emit_code = code
        try:
            cursor = int(self._editor._text.index(tk.INSERT).split('.')[1])
        except Exception:
            cursor = 0
        self._emit(HookEvents.EDITOR_CONTENT_CHANGED, code, cursor)

    def _add_plugin_command(self, record: Any, cmd: Any) -> None:
        """插件命令注册入口: 添加到 _plugin_menus 字典里, 由 ``_refresh_plugin_menu`` 渲染。"""

        groups = self._plugin_menus.setdefault(cmd.menu, [])
        # 同一个 (plugin_id, label) 已存在则跳过 (manager 已做防御, 这里双保险)
        for existing in groups:
            if existing['plugin_id'] == cmd.plugin_id and existing['label'] == cmd.label:
                return
        groups.append({
            'plugin_id': cmd.plugin_id,
            'label': cmd.label,
            'callback': cmd.callback,
            'shortcut': cmd.shortcut,
        })

    def _add_plugin_language(self, plugin_id: str, contrib: LanguageContribution) -> None:
        """插件声明新语言: 加进 LANG_CONFIG + 下拉框。"""

        if contrib.name in LANG_CONFIG:
            # 已有同名语言 (内置或别的插件) → 拒绝
            return
        LANG_CONFIG[contrib.name] = {
            'ext': contrib.ext,
            'highlighter': type(contrib.highlighter_factory()),
            'suggestion': type(contrib.suggestion_factory()),
            'highlighter_factory': contrib.highlighter_factory,
            'suggestion_factory': contrib.suggestion_factory,
            'sample': contrib.sample,
            'plugin_id': plugin_id,
        }
        if contrib.name not in self._plugin_lang_combo_added:
            self._plugin_lang_combo_added.append(contrib.name)
        self._lang_combo.set_values(list(LANG_CONFIG.keys()))

    def _refresh_plugin_menu(self) -> None:
        """重建插件主菜单: 按 ``menu`` 分组的子菜单 + 每条命令 + 末尾的"管理插件"。"""

        menu = getattr(self, '_plugin_menu', None)
        if menu is None:
            return
        menu._items.clear()
        loaded = self._plugin_manager.list_loaded()
        if not loaded:
            menu.add_command(t('menu.plugins.none'), lambda: None)
        else:
            for rec in loaded:
                status = t('plugin.info.status.enabled') if rec.enabled else t('plugin.info.status.disabled')
                err = t('plugin.menu.errors_prefix', err=rec.error) if rec.error else ''
                menu.add_command(
                    t('plugin.menu.item', name=rec.manifest.name, status=status, error=err),
                    lambda r=rec: self._show_plugin_info(r),
                )
        menu.add_separator()
        # 命令按 menu 分组
        for group_name, items in self._plugin_menus.items():
            sub = menu.add_cascade(group_name)
            sub._items.clear()
            if not items:
                sub.add_command(t('menu.plugins.empty'), lambda: None)
                continue
            for item in items:
                label = item['label']
                if item['shortcut']:
                    label = f"{label}\t{item['shortcut']}"
                sub.add_command(
                    label,
                    lambda cb=item['callback']: self._safe_run_plugin_command(cb),
                )
        menu.add_separator()
        menu.add_command(t('menu.plugins.manage'), self._open_plugin_manager)
        menu.add_command(t('menu.plugins.rescan'), self._reload_all_plugins)

    def _refresh_plugin_languages(self) -> None:
        """同步下拉框: 把插件新增的语言值塞进去。"""

        if not hasattr(self, '_lang_combo'):
            return
        self._lang_combo.set_values(list(LANG_CONFIG.keys()))

    def _safe_run_plugin_command(self, callback: Any) -> None:
        """包装一层 try/except, 避免插件崩溃搞坏编辑器。"""

        try:
            callback()
        except Exception as exc:
            self._append_output(f'[ERROR] {t("dialog.plugin.error", err=exc)}\n')
            try:
                messagebox.showerror(t('dialog.title.plugin_error'), str(exc), parent=self.window)
            except Exception:
                pass

    def _show_plugin_info(self, record: Any) -> None:
        """弹窗显示单个插件的元信息 + 来源路径 + 错误。"""

        m = record.manifest
        author = m.author if m.author else t('plugin.info.author_unknown')
        status = t('plugin.info.status.enabled') if record.enabled else t('plugin.info.status.disabled')
        text = t(
            'plugin.info.template',
            name=m.name,
            id=m.id,
            version=m.version,
            author=author,
            scope=m.scope,
            location=record.location,
            status=status,
        )
        if record.error:
            text += f"\n{t('plugin.info.errors_header')}\n{record.error}"
        if m.description:
            text += f"\n\n{m.description}"
        messagebox.showinfo(t('dialog.title.plugin', name=m.name), text, parent=self.window)

    def _open_plugin_manager(self) -> None:
        """打开插件管理窗口。"""

        try:
            from modules.plugins.widgets import UPluginManagerWindow
        except Exception as exc:
            messagebox.showerror(
                t('dialog.title.plugin_manager'),
                t('dialog.plugin_manager.load_failed', err=exc),
                parent=self.window,
            )
            return
        try:
            win = UPluginManagerWindow(self, self._plugin_manager)
            self._plugin_manager_window = win
        except Exception as exc:
            messagebox.showerror(
                t('dialog.title.plugin_manager'),
                t('dialog.plugin_manager.open_failed', err=exc),
                parent=self.window,
            )

    def _reload_all_plugins(self) -> None:
        """手动触发完整 reload: 卸载 + 重新扫描 + 加载。"""

        try:
            self._plugin_manager.unload_all()
        except Exception:
            pass
        # 清菜单缓存
        self._plugin_menus = {}
        for name in list(LANG_CONFIG.keys()):
            if LANG_CONFIG[name].get('plugin_id'):
                LANG_CONFIG.pop(name, None)
        self._plugin_lang_combo_added = []
        try:
            self._plugin_manager.load_global_plugins()
        except Exception:
            pass
        if self._current_project_root:
            try:
                self._plugin_manager.load_project_plugins(self._current_project_root)
            except Exception:
                pass
        self._refresh_plugin_menu()
        self._refresh_plugin_languages()
        self._status_label.config(text=t('status.plugins_reloaded'))

    # ------------------------------------------------------------------
    # 钩子触发点 (各业务方法内部调用 self._emit)
    # ------------------------------------------------------------------

    def _show_documentation(self):
        messagebox.showinfo(t('dialog.title.docs'),
                          t('dialog.docs.message'),
                          parent=self.window)

    def _show_shortcuts(self):
        messagebox.showinfo(t('dialog.title.shortcuts'), t('shortcuts.text'), parent=self.window)

    def _show_about(self):
        messagebox.showinfo(t('dialog.title.about'), t('dialog.about.message'), parent=self.window)

    def _check_updates(self):
        messagebox.showinfo(t('dialog.title.check_updates'), t('dialog.updates.message'), parent=self.window)

    def _report_issue(self):
        messagebox.showinfo(t('dialog.title.report_issue'), t('dialog.report_issue.message'), parent=self.window)

    def _run_check(self):
        code = self._editor.get('1.0', 'end-1c')
        if not code.strip():
            self._append_output('No code to check.\n')
            return

        app_logger.info(f"Check started: lang={self._lang}")
        self._status_label.config(text=t('status.checking'))
        self.window.update_idletasks()

        with tempfile.NamedTemporaryFile(mode='w', suffix=LANG_CONFIG[self._lang]['ext'],
                                          delete=False, encoding='utf-8') as f:
            f.write(code)
            temp_path = f.name

        try:
            results = []
            for checker_cls in (Flake8Checker, PyrightChecker, CPythonChecker):
                try:
                    checker = checker_cls()
                    output = checker.check(temp_path)
                    if output and output.row:
                        results.extend(output.row)
                except Exception:
                    pass

            self._output._text.config(state='normal')
            self._output.clear()
            if results:
                for row in results:
                    level = getattr(row, 'level', 'info')
                    message = getattr(row, 'message', str(row))
                    line_no = getattr(row, 'line', '')
                    col_no = getattr(row, 'col', '')
                    prefix = f'[{level.upper()}]'
                    loc = f'  Ln {line_no}' if line_no else ''
                    if col_no:
                        loc += f', Col {col_no}'
                    self._append_output(f'{prefix}{loc}: {message}\n')
            else:
                self._append_output('No issues found.\n')
            self._output._text.config(state='disabled')
            self._status_label.config(text=t('status.check_complete'))
            app_logger.info(f"Check complete: {len(results)} issue(s) found")
            self._emit(HookEvents.EDITOR_CHECK_FINISHED, self._lang, results)
        except Exception as e:
            app_logger.error(f"Check failed: {e}")
            self._output._text.config(state='normal')
            self._append_output(f'Check error: {e}\n')
            self._output._text.config(state='disabled')
            self._status_label.config(text=t('status.check_failed'))
            self._emit(HookEvents.EDITOR_CHECK_FINISHED, self._lang, [])
        finally:
            try:
                os.unlink(temp_path)
            except OSError:
                pass

    def _run_code(self):
        code = self._editor.get('1.0', 'end-1c')
        if not code.strip():
            return

        app_logger.info(f"Run started: lang={self._lang}")
        self._status_label.config(text=t('status.running'))
        self.window.update_idletasks()

        ext = LANG_CONFIG[self._lang]['ext']
        with tempfile.NamedTemporaryFile(mode='w', suffix=ext, delete=False, encoding='utf-8') as f:
            f.write(code)
            temp_path = f.name

        try:
            if self._lang == 'Python':
                cmd: List[str] = [sys.executable, temp_path]
            elif self._lang in ('C', 'C++'):
                ok, artifact = self._compile_c_cpp(temp_path)
                if not ok:
                    # 编译失败 / 编译器找不到: 错误已写到 output, 这里
                    # 只负责把临时源文件清掉。
                    try:
                        os.unlink(temp_path)
                    except OSError:
                        pass
                    return
                cmd = [artifact]
            else:
                try:
                    os.unlink(temp_path)
                except OSError:
                    pass
                return

            # 取 runner 相关设置; 默认值与 schema 中保持一致, 即使在
            # 旧的 (无该字段的) global settings.json 下也不会 KeyError。
            clear_first = bool(
                self._settings.effective('runner.clear_output_before_run', True)
            )
            streaming = bool(
                self._settings.effective('runner.stream_output', True)
            )
            timeout_ms = int(
                self._settings.effective('runner.timeout_ms', 30000)
            )
            timeout_s = max(0.5, timeout_ms / 1000.0)

            self._emit(HookEvents.EDITOR_RUN_STARTED, self._lang, temp_path)

            if streaming:
                # 流式: temp_path 由 _run_streaming_path 在 done 回调里
                # unlink, 这里不立即删除, 否则子进程打开文件可能失败。
                self._run_streaming_path(
                    cmd, temp_path, clear_first, timeout_s,
                )
            else:
                # 阻塞: temp_path 在 _run_blocking_path 的 finally 里
                # unlink, 行为与改造前一致。
                self._run_blocking_path(
                    cmd, temp_path, clear_first, timeout_s,
                )
        except FileNotFoundError:
            # 理论上不会到这里 (Python 走 sys.executable, C/C++ 的
            # FileNotFoundError 已被 _compile_c_cpp 消化), 兜底以防
            # 未来新增语言的 cmd 找不到解释器。
            try:
                os.unlink(temp_path)
            except OSError:
                pass
            self._output._text.config(state='normal')
            self._output.clear()
            self._append_output(
                'Compiler not found. Please install GCC/G++ for C/C++ support.\n'
            )
            self._output._text.config(state='disabled')
            self._status_label.config(text=t('status.compiler_not_found'))
        except Exception as e:
            try:
                os.unlink(temp_path)
            except OSError:
                pass
            self._output._text.config(state='normal')
            self._output.clear()
            self._append_output(f'Run error: {e}\n')
            self._output._text.config(state='disabled')
            self._status_label.config(text=t('status.run_failed'))

    def _compile_c_cpp(self, temp_path: str) -> tuple:
        """编译 C / C++ 源文件; 返回 ``(ok, binary_path_or_stderr)``.

        失败时 ``ok=False`` 且错误信息已写到 output widget; 成功时
        ``ok=True`` 且第二项是产物可执行文件路径。

        与原 ``_run_code`` 内的内联代码不同点: 错误处理抽到这里集中,
        让 :meth:`_run_code` 主路径只剩"准备 cmd + 选 blocking/streaming
        两条路"两件事, 便于在流式 / 阻塞之间切换时不会让编译错误
        漏到其中一条路径上。
        """

        binary_ext = '.exe' if sys.platform == 'win32' else ''
        binary = temp_path.rsplit('.', 1)[0] + binary_ext
        compiler = 'g++' if self._lang == 'C++' else 'gcc'
        try:
            compile_result = subprocess.run(
                [compiler, temp_path, '-o', binary],
                capture_output=True, text=True, timeout=30,
            )
        except FileNotFoundError:
            self._output._text.config(state='normal')
            self._output.clear()
            self._append_output(
                'Compiler not found. Please install GCC/G++ for C/C++ support.\n'
            )
            self._output._text.config(state='disabled')
            self._status_label.config(text=t('status.compiler_not_found'))
            return False, 'compiler not found'
        if compile_result.returncode != 0:
            self._output._text.config(state='normal')
            self._output.clear()
            self._append_output(f'Compile error:\n{compile_result.stderr}\n')
            self._output._text.config(state='disabled')
            self._status_label.config(text=t('status.compile_failed'))
            return False, compile_result.stderr
        return True, binary

    def _run_blocking_path(
        self,
        cmd: List[str],
        temp_path: str,
        clear_first: bool,
        timeout_s: float,
    ) -> None:
        """``runner.stream_output`` 关闭时的回退路径.

        行为与改造前 ``subprocess.run(...)`` 等价; 临时文件在 finally
        中清理, 与原实现保持一致。
        """

        try:
            result = run_blocking(cmd, timeout_s=timeout_s)
            self._output._text.config(state='normal')
            if clear_first:
                self._output.clear()
            if result.stdout:
                self._append_output(result.stdout)
            if result.stderr:
                self._append_output(result.stderr)
            if result.returncode != 0:
                self._append_output(f'\n[Exit code: {result.returncode}]\n')
            self._output._text.config(state='disabled')
            self._status_label.config(text=t('status.run_complete'))
            app_logger.info(f"Run complete: lang={self._lang}, exit_code={result.returncode}")
            self._emit(
                HookEvents.EDITOR_RUN_FINISHED,
                self._lang,
                result.returncode,
                result.stdout or '',
                result.stderr or '',
            )
        except subprocess.TimeoutExpired:
            app_logger.warning(f"Run timed out: lang={self._lang}")
            self._output._text.config(state='normal')
            if clear_first:
                self._output.clear()
            self._append_output('Execution timed out.\n')
            self._output._text.config(state='disabled')
            self._status_label.config(text=t('status.timeout'))
            self._emit(
                HookEvents.EDITOR_RUN_FINISHED,
                self._lang, -1, '', 'Execution timed out',
            )
        except Exception as e:
            app_logger.error(f"Run error: lang={self._lang}, err={e}")
            self._output._text.config(state='normal')
            if clear_first:
                self._output.clear()
            self._append_output(f'Run error: {e}\n')
            self._output._text.config(state='disabled')
            self._status_label.config(text=t('status.run_failed'))
            self._emit(
                HookEvents.EDITOR_RUN_FINISHED,
                self._lang, -1, '', str(e),
            )
        finally:
            try:
                os.unlink(temp_path)
            except OSError:
                pass

    def _run_streaming_path(
        self,
        cmd: List[str],
        temp_path: str,
        clear_first: bool,
        timeout_s: float,
    ) -> None:
        """流式执行: 后台线程把行塞进 ``queue.Queue``, Tk 主线程用
        :meth:`tk.Misc.after` 周期排空.

        Tk widget 只能在主线程操作 — 这是所有 GUI 框架的硬约束, 因此
        不能在 ``line_callback`` / ``done_callback`` 里直接 ``config``
        文本框。后台线程只负责把数据 push 到线程安全的 ``Queue``, 由
        ``drain`` 在主线程里把行渲染到 output。这是 Tk + subprocess
        实时输出的标准桥接模式。
        """

        # 清屏
        self._output._text.config(state='normal')
        if clear_first:
            self._output.clear()
        self._output._text.config(state='disabled')

        # 取消上一次未结束的 drain, 避免旧 drain 往新 run 的 output
        # 里灌陈旧的行 (用户连续点 Run 时常见)。
        prev_after = getattr(self, '_stream_drain_after_id', None)
        if prev_after is not None:
            try:
                self.window.after_cancel(prev_after)
            except tk.TclError:
                pass

        line_q: queue.Queue = queue.Queue()
        self._stream_drain_after_id: Any = None
        # 流式输出收集: 用于在结束时给插件回调传完整 stdout/stderr。
        # 字符串拼接为简单实现, 因为运行输出一般 KB 量级。
        captured_stdout: List[str] = []
        captured_stderr: List[str] = []

        def on_line(stream_name: str, line: str) -> None:
            try:
                line_q.put((stream_name, line))
            except Exception:
                pass

        def on_done(result: RunResult) -> None:
            try:
                line_q.put(('__done__', result))
            except Exception:
                pass

        def drain() -> None:
            try:
                while True:
                    item = line_q.get_nowait()
                    if item[0] == '__done__':
                        result: RunResult = item[1]
                        app_logger.info(f"Run stream finished: lang={self._lang}, timed_out={result.timed_out}, exit_code={result.returncode}")
                        self._output._text.config(state='normal')
                        if result.timed_out:
                            self._append_output('\n[Execution timed out]\n')
                        elif result.returncode != 0:
                            self._append_output(
                                f'\n[Exit code: {result.returncode}]\n'
                            )
                        self._output._text.config(state='disabled')
                        self._status_label.config(
                            text=t('status.timeout') if result.timed_out else t('status.run_complete'),
                        )
                        try:
                            os.unlink(temp_path)
                        except OSError:
                            pass
                        self._stream_drain_after_id = None
                        # 通知插件: 流式运行结束
                        self._emit(
                            HookEvents.EDITOR_RUN_FINISHED,
                            self._lang,
                            result.returncode,
                            ''.join(captured_stdout),
                            ''.join(captured_stderr),
                        )
                        return
                    stream_name, line = item
                    if stream_name == 'stdout':
                        captured_stdout.append(line)
                    elif stream_name == 'stderr':
                        captured_stderr.append(line)
                    self._output._text.config(state='normal')
                    self._append_output(line)
                    self._output._text.config(state='disabled')
            except queue.Empty:
                pass
            except tk.TclError:
                # 窗口被销毁; 后续 after 也会失败, 直接退出即可
                self._stream_drain_after_id = None
                return
            try:
                self._stream_drain_after_id = self.window.after(50, drain)
            except tk.TclError:
                self._stream_drain_after_id = None

        stream_command(
            cmd,
            timeout_s=timeout_s,
            line_callback=on_line,
            done_callback=on_done,
        )
        drain()

    def _append_output(self, text):
        self._output._text.config(state='normal')
        self._output._text.insert(tk.END, text)
        self._output._text.see(tk.END)
        self._output._text.config(state='disabled')

    def _clear_output(self):
        self._output._text.config(state='normal')
        self._output.clear()
        self._output._text.config(state='disabled')
        self._status_label.config(text=t('status.ready'))

    def run(self):
        self.window.mainloop()


if __name__ == '__main__':
    editor = CodeEditor()
    editor.run()
