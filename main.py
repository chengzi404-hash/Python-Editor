import sys
import os
import subprocess
import tempfile
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from modules.Uui.widgets import UFrame, ULabel, UButton, UText, UComboBox, UMenuBar, UMenu, theme
from modules.Uui.widgets.window import Window
from modules.Uui.widgets.editor_suggestion import UEditorSuggestion, CompletionItem
from modules.highlighter import PythonHighlighterExpert, CcppHighlighterExpert, HighlightBlock
from modules.suggestion import PythonSuggestionExpert, CSuggestionExpert, CppSuggestionExpert, SuggestionBlock
from modules.checker import Flake8Checker, PyrightChecker, CPythonChecker
from modules.settings import SettingsManager, SettingsScope, SettingsChangeEvent

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
        'sample': 'def hello():\n    print("Hello, world!")\n\nhello()\n',
    },
    'C': {
        'ext': '.c',
        'highlighter': CcppHighlighterExpert,
        'suggestion': CSuggestionExpert,
        'sample': '#include <stdio.h>\n\nint main() {\n    printf("Hello, world!\\n");\n    return 0;\n}\n',
    },
    'C++': {
        'ext': '.cpp',
        'highlighter': CcppHighlighterExpert,
        'suggestion': CppSuggestionExpert,
        'sample': '#include <iostream>\n\nint main() {\n    std::cout << "Hello, world!" << std::endl;\n    return 0;\n}\n',
    },
}

THEME_NAMES = ['Dark', 'Light', 'Solarized Dark']
FONT_FAMILIES = ['Consolas', 'Courier New', 'Menlo', 'Monaco']
FONT_SIZES = [9, 10, 11, 12, 14, 16]
TAB_WIDTHS = [2, 4, 8]


class CodeEditor:
    def __init__(self):
        custom_titlebar = '--custom-titlebar' in sys.argv
        self.window = Window(title='Python Editor', custom_titlebar=custom_titlebar)
        self.window.geometry('960x680+200+100')
        self.window.configure(bg=theme.BG_BASE)
        self.window.resizable(width=True, height=True)

        self._settings = SettingsManager()
        self._suppress_settings_listener = False

        self._lang = 'Python'
        self._current_file: Optional[str] = None
        self._current_project_root: Optional[str] = None
        self._suggestion_popup: Optional[UEditorSuggestion] = None
        self._dirty = False

        gs = self._settings.global_settings
        self._highlighting_enabled = gs.get('completion.enabled', True)
        self._suggestions_enabled = gs.get('completion.enabled', True)
        self._autosave_enabled = gs.get('editor.auto_save', False)

        self._font_family = gs.get('ui.font_family', 'Consolas')
        self._font_size = int(gs.get('ui.font_size', 10))
        self._tab_width = int(gs.get('editor.tab_size', 4))

        self._find_dialog: Optional[tk.Toplevel] = None
        self._find_query = ''
        self._find_last_index: Optional[str] = None

        self._build_menubar()
        self._build_toolbar()
        self._build_editor()
        self._build_output_panel()
        self._build_status_bar()

        # 在所有控件都已构造后再注册 listener, 避免启动期触发未初始化控件。
        self._settings.add_listener(self._on_settings_changed)

        self._apply_loaded_theme()
        self._apply_editor_font()
        self._set_tab_width(self._tab_width)
        self._switch_language('Python')

        self._bind_shortcuts()
        self.window.protocol('WM_DELETE_WINDOW', self._on_close_request)

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
        """窗口关闭时: 询问 + 落盘。"""

        if self._dirty and not messagebox.askyesno('未保存', '有未保存的修改,确认退出?'):
            return
        self._settings.detach_project()
        try:
            self._settings.save_all()
        except Exception as exc:
            messagebox.showerror('保存设置失败', str(exc))
        self.window.destroy()


    def _build_menubar(self):
        self._menubar = UMenuBar(self.window)
        self._menubar.pack(fill=tk.X, padx=0, pady=0)

        file_menu = self._menubar.add_cascade('文件(F)')
        file_menu.add_command('新建', self._new_file, 'Ctrl+N')
        file_menu.add_command('打开...', self._open_file, 'Ctrl+O')
        file_menu.add_separator()
        file_menu.add_command('保存', self._save_file, 'Ctrl+S')
        file_menu.add_command('另存为...', self._save_file_as, 'Ctrl+Shift+S')
        file_menu.add_separator()
        file_menu.add_command('运行', self._run_code, 'F5')
        file_menu.add_command('检查', self._run_check, 'Ctrl+R')
        file_menu.add_command('清除输出', self._clear_output, 'Ctrl+L')
        file_menu.add_separator()
        file_menu.add_command('退出', self.window.destroy, 'Alt+F4')

        edit_menu = self._menubar.add_cascade('编辑(E)')
        edit_menu.add_command('撤销', self._undo, 'Ctrl+Z')
        edit_menu.add_command('重做', self._redo, 'Ctrl+Y')
        edit_menu.add_separator()
        edit_menu.add_command('剪切', self._cut, 'Ctrl+X')
        edit_menu.add_command('复制', self._copy, 'Ctrl+C')
        edit_menu.add_command('粘贴', self._paste, 'Ctrl+V')
        edit_menu.add_separator()
        edit_menu.add_command('全选', self._select_all, 'Ctrl+A')
        edit_menu.add_separator()
        edit_menu.add_command('查找...', self._open_find, 'Ctrl+F')
        edit_menu.add_command('替换...', self._open_replace, 'Ctrl+H')
        edit_menu.add_command('转到行...', self._goto_line, 'Ctrl+G')
        edit_menu.add_separator()
        edit_menu.add_command('缩进', self._indent, 'Tab')
        edit_menu.add_command('取消缩进', self._outdent, 'Shift+Tab')
        edit_menu.add_command('切换注释', self._toggle_comment, 'Ctrl+/')
        lang_sub = edit_menu.add_cascade('切换语言')
        for name in LANG_CONFIG:
            lang_sub.add_radiobutton(name, value=name, variable=self._lang_var(),
                                     command=lambda n=name: self._switch_language(n))

        query_menu = self._menubar.add_cascade('查询(Q)')
        query_menu.add_command('跳转到定义', self._goto_definition, 'F12')
        query_menu.add_command('查找引用', self._find_references, 'Shift+F12')
        query_menu.add_command('查找文档', self._find_documentation, 'Ctrl+Shift+F1')
        query_menu.add_separator()
        query_menu.add_command('重新解析代码', self._reparse, 'F6')
        query_menu.add_command('刷新高亮', self._apply_highlight, 'F7')
        query_menu.add_separator()
        query_menu.add_command('触发建议', self._show_suggestions, 'Ctrl+Space')
        query_menu.add_command('隐藏建议', self._hide_suggestions, 'Esc')

        settings_menu = self._menubar.add_cascade('设置(S)')
        theme_sub = settings_menu.add_cascade('主题')
        for name in THEME_NAMES:
            theme_sub.add_radiobutton(name, value=name,
                                       variable=self._theme_var(),
                                       command=lambda n=name: self._set_theme(n))
        font_sub = settings_menu.add_cascade('字体')
        for fnt in FONT_FAMILIES:
            font_sub.add_radiobutton(fnt, value=fnt,
                                      variable=self._font_family_var(),
                                      command=lambda f=fnt: self._set_font_family(f))
        size_sub = settings_menu.add_cascade('字号')
        for sz in FONT_SIZES:
            size_sub.add_radiobutton(str(sz), value=sz,
                                      variable=self._font_size_var(),
                                      command=lambda s=sz: self._set_font_size(s))
        tab_sub = settings_menu.add_cascade('Tab 宽度')
        for tw in TAB_WIDTHS:
            tab_sub.add_radiobutton(str(tw), value=tw,
                                     variable=self._tab_width_var(),
                                     command=lambda t=tw: self._set_tab_width(t))
        settings_menu.add_separator()
        settings_menu.add_checkbutton('启用高亮', variable=self._highlight_var(),
                                       command=self._toggle_highlighting)
        settings_menu.add_checkbutton('启用建议', variable=self._suggestion_var(),
                                       command=self._toggle_suggestions)
        settings_menu.add_checkbutton('自动保存', variable=self._autosave_var(),
                                       command=self._toggle_autosave)
        settings_menu.add_separator()
        settings_menu.add_command('全局设置...', self._open_global_settings)
        settings_menu.add_command('项目设置...', self._open_project_settings)
        settings_menu.add_command('重置设置', self._reset_settings)

        help_menu = self._menubar.add_cascade('帮助(H)')
        help_menu.add_command('文档', self._show_documentation, 'F1')
        help_menu.add_command('快捷键', self._show_shortcuts, 'Ctrl+K')
        help_menu.add_separator()
        help_menu.add_command('关于', self._show_about)
        help_menu.add_command('检查更新...', self._check_updates)
        help_menu.add_command('报告问题...', self._report_issue)

    def _bind_shortcuts(self):
        self.window.bind('<Control-n>', lambda e: self._new_file())
        self.window.bind('<Control-o>', lambda e: self._open_file())
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

    def _lang_var(self) -> tk.StringVar:
        if not hasattr(self, '_lang_tk_var') or self._lang_tk_var is None:
            self._lang_tk_var = tk.StringVar(value=self._lang)
        return self._lang_tk_var

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

        self._editor = UText(body, width=80, height=20)
        self._editor.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)

        self._editor._text.bind('<KeyRelease>', self._on_key_release)
        self._editor._text.bind('<KeyPress>', self._on_key_press)
        self._editor._text.bind('<ButtonRelease-1>', self._on_click)
        self._editor._text.bind('<FocusIn>', self._on_focus_in)
        self._editor._text.config(undo=True)

    def _build_output_panel(self):
        self._output_frame = UFrame(self.window, variant='panel', height=120)
        self._output_frame.pack(fill=tk.X, padx=0, pady=0)
        self._output_frame.pack_propagate(False)

        header = UFrame(self._output_frame, variant='title')
        header.pack(fill=tk.X)
        ULabel(header, text='  Output', variant='secondary', bg=theme.BG_TITLE).pack(side=tk.LEFT, padx=4, pady=2)

        self._output = UText(self._output_frame, width=80, height=5)
        self._output.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)
        self._output._text.config(state='disabled')

    def _build_status_bar(self):
        status = UFrame(self.window, variant='title', height=24)
        status.pack(fill=tk.X, padx=0, pady=0)
        status.pack_propagate(False)

        self._status_label = ULabel(status, text='Ready', variant='secondary',
                                     bg=theme.BG_TITLE)
        self._status_label.pack(side=tk.LEFT, padx=10, pady=2)

        self._lang_label = ULabel(status, text='Python', variant='secondary',
                                   bg=theme.BG_TITLE)
        self._lang_label.pack(side=tk.RIGHT, padx=10, pady=2)

        self._pos_label = ULabel(status, text='Ln 1, Col 1', variant='secondary',
                                  bg=theme.BG_TITLE)
        self._pos_label.pack(side=tk.RIGHT, padx=10, pady=2)

    def _switch_language(self, lang):
        if lang not in LANG_CONFIG:
            return
        self._lang = lang
        if hasattr(self, '_lang_tk_var') and self._lang_tk_var is not None:
            self._lang_tk_var.set(lang)
        config = LANG_CONFIG[lang]
        self._highlighter = config['highlighter']()
        self._suggestion_expert = config['suggestion']()
        self._lang_label.config(text=lang)
        self._editor._text.delete('1.0', tk.END)
        self._editor._text.insert('1.0', config['sample'])
        self._apply_highlight()
        self._update_status()

    def _on_lang_changed(self, value):
        self._switch_language(value)

    def _on_key_release(self, event=None):
        self._apply_highlight()
        self._update_status()
        if self._suggestions_enabled:
            self._show_suggestions()

    def _on_key_press(self, event=None):
        if self._suggestion_popup and self._suggestion_popup.winfo_exists():
            if event and event.keysym in ('Escape',):
                self._suggestion_popup.hide()
            elif event and event.keysym in ('Down', 'Up', 'Return', 'Tab'):
                return

    def _on_click(self, event=None):
        self._update_status()
        if self._suggestions_enabled:
            self.window.after(100, self._show_suggestions)

    def _on_focus_in(self, event=None):
        self._update_status()

    def _apply_highlight(self):
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

        items = [CompletionItem(label=s) for s in suggestions[:20]]
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
        self._pos_label.config(text=f'Ln {line}, Col {int(col) + 1}')

    def _new_file(self):
        if self._dirty and not messagebox.askyesno('未保存', '丢弃当前修改？'):
            return
        self._editor._text.delete('1.0', tk.END)
        self._current_file = None
        self._dirty = False
        self._status_label.config(text='New file')

    def _open_file(self):
        if self._dirty and not messagebox.askyesno('未保存', '丢弃当前修改？'):
            return
        ext = LANG_CONFIG[self._lang]['ext']
        filetypes = [(f'{self._lang} files', f'*{ext}'), ('All files', '*.*')]
        path = filedialog.askopenfilename(filetypes=filetypes)
        if not path:
            return
        try:
            with open(path, 'r', encoding='utf-8') as f:
                code = f.read()
        except OSError as e:
            messagebox.showerror('打开失败', str(e))
            return
        self._editor._text.delete('1.0', tk.END)
        self._editor._text.insert('1.0', code)
        self._current_file = path
        self._dirty = False
        self._status_label.config(text=f'Opened: {os.path.basename(path)}')
        # 打开文件时自动挂载该项目目录,以便加载 .pyeditor/settings.json。
        project_root = os.path.dirname(os.path.abspath(path))
        if project_root:
            self._attach_project(project_root)
        self._apply_highlight()

    def _save_file(self):
        if self._current_file:
            self._save_to_path(self._current_file)
        else:
            self._save_file_as()

    def _save_file_as(self):
        ext = LANG_CONFIG[self._lang]['ext']
        filetypes = [(f'{self._lang} files', f'*{ext}'), ('All files', '*.*')]
        path = filedialog.asksaveasfilename(defaultextension=ext, filetypes=filetypes)
        if path:
            self._save_to_path(path)
            self._current_file = path
            project_root = os.path.dirname(os.path.abspath(path))
            if project_root:
                self._attach_project(project_root)

    def _save_to_path(self, path: str):
        code = self._editor.get('1.0', 'end-1c')
        try:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(code)
        except OSError as e:
            messagebox.showerror('保存失败', str(e))
            return
        self._dirty = False
        self._status_label.config(text=f'Saved: {os.path.basename(path)}')

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
        dlg.title('替换' if replace else '查找')
        dlg.configure(bg=theme.BG_PANEL)
        dlg.transient(self.window)
        dlg.resizable(False, False)

        ULabel(dlg, text='查找内容:', bg=theme.BG_PANEL).grid(row=0, column=0, sticky='e', padx=6, pady=6)
        find_var = tk.StringVar(value=self._find_query)
        find_entry = tk.Entry(dlg, textvariable=find_var, width=30,
                              bg=theme.BG_INPUT, fg=theme.FG_PRIMARY,
                              insertbackground=theme.FG_PRIMARY)
        find_entry.grid(row=0, column=1, columnspan=2, sticky='ew', padx=6, pady=6)

        replace_var = None
        replace_entry = None
        if replace:
            ULabel(dlg, text='替换为:', bg=theme.BG_PANEL).grid(row=1, column=0, sticky='e', padx=6, pady=6)
            replace_var = tk.StringVar()
            replace_entry = tk.Entry(dlg, textvariable=replace_var, width=30,
                                      bg=theme.BG_INPUT, fg=theme.FG_PRIMARY,
                                      insertbackground=theme.FG_PRIMARY)
            replace_entry.grid(row=1, column=1, columnspan=2, sticky='ew', padx=6, pady=6)

        case_var = tk.BooleanVar(value=False)
        tk.Checkbutton(dlg, text='区分大小写', variable=case_var,
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
                    messagebox.showinfo('查找', '未找到', parent=dlg)
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
            messagebox.showinfo('替换', f'已替换 {count} 处', parent=dlg)

        def close():
            self._find_dialog = None
            dlg.destroy()

        btn_row = 3 if replace else 2
        UButton(dlg, text='查找下一个', command=do_find, variant='primary', width=80, height=24
                 ).grid(row=btn_row, column=0, padx=4, pady=6)
        if replace:
            UButton(dlg, text='替换', command=do_replace, variant='default', width=60, height=24
                     ).grid(row=btn_row, column=1, padx=4, pady=6)
            UButton(dlg, text='全部替换', command=do_replace_all, variant='warning', width=80, height=24
                     ).grid(row=btn_row, column=2, padx=4, pady=6)
        else:
            UButton(dlg, text='关闭', command=close, variant='default', width=60, height=24
                     ).grid(row=btn_row, column=1, columnspan=2, padx=4, pady=6, sticky='ew')

        dlg.protocol('WM_DELETE_WINDOW', close)
        find_entry.focus_set()
        self._find_dialog = dlg

    def _goto_line(self):
        line_no = simpledialog.askinteger('转到行', '行号:',
                                           parent=self.window, minvalue=1,
                                           maxvalue=self._line_count())
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
            messagebox.showinfo('切换注释', f'当前语言 {self._lang} 的注释切换未实现', parent=self.window)
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
        messagebox.showinfo('跳转定义', '跳转到定义功能尚未实现', parent=self.window)

    def _find_references(self):
        messagebox.showinfo('查找引用', '查找引用功能尚未实现', parent=self.window)

    def _find_documentation(self):
        messagebox.showinfo('查找文档', '查找文档功能尚未实现', parent=self.window)

    def _reparse(self):
        self._apply_highlight()
        self._status_label.config(text='Re-parsed')

    def _set_theme(self, name: str, *, persist: bool = True):
        try:
            target = theme.by_name(name)
            if target is None:
                return
            theme.set_theme(target, refresh_root=self.window)
            if hasattr(self, '_theme_tk_var') and self._theme_tk_var is not None:
                self._theme_tk_var.set(name)
            self._status_label.config(text=f'Theme: {name}')
            self._force_redraw()
        except Exception as e:
            self._status_label.config(text=f'Theme error: {e}')
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
        self._status_label.config(text=f'Font: {family}')
        self._write_setting(SettingsScope.GLOBAL, 'ui.font_family', family)

    def _set_font_size(self, size: int):
        self._font_size = size
        if hasattr(self, '_font_size_tk_var') and self._font_size_tk_var is not None:
            self._font_size_tk_var.set(size)
        self._apply_editor_font()
        self._status_label.config(text=f'Font size: {size}')
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
            text = self._editor._text
            for tag in text.tag_names():
                text.tag_delete(tag)
        else:
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
                self._settings, parent=self.window, title='设置',
            )
            self._settings_window = win
            win._switch(SettingsScope.GLOBAL)  # noqa: SLF001 - 单文件集成
        except Exception as exc:
            messagebox.showerror('设置', f'设置面板加载失败:{exc}', parent=self.window)

    def _open_project_settings(self):
        """打开设置窗口并跳到"项目"Tab;无项目时自动提示。"""
        if self._settings.project_settings is None:
            if not messagebox.askyesno(
                '项目设置',
                '当前没有附加项目。是否选择一个项目目录?',
                parent=self.window,
            ):
                return
            chosen = filedialog.askdirectory(title='选择项目根目录', parent=self.window)
            if not chosen:
                return
            self._attach_project(chosen)
        from modules.settings.widgets import UProjectSettingsWindow
        try:
            win = UProjectSettingsWindow(
                self._settings, parent=self.window, title='项目设置',
            )
            # 切到项目 Tab
            try:
                win._switch(SettingsScope.PROJECT)  # noqa: SLF001 - 单文件集成
            except Exception:
                pass
            self._settings_window = win
        except Exception as exc:
            messagebox.showerror('项目设置', f'设置面板加载失败:{exc}', parent=self.window)

    def _attach_project(self, root: str) -> None:
        """附加项目目录到 SettingsManager,记录当前根。"""

        root = os.path.abspath(root)
        if self._current_project_root == root:
            return
        self._settings.detach_project()
        try:
            self._settings.attach_project(root)
            self._current_project_root = root
        except Exception as exc:
            messagebox.showerror('项目设置', f'无法挂载项目 {root}:{exc}', parent=self.window)

    def _reset_settings(self):
        if not messagebox.askyesno('重置设置', '确认将全局设置恢复为默认值?', parent=self.window):
            return
        try:
            self._settings.reset(SettingsScope.GLOBAL)
        except Exception:
            pass
        self._refresh_all_from_settings()
        try:
            self._settings.save_all()
        except Exception as exc:
            messagebox.showerror('重置失败', str(exc), parent=self.window)
            return
        self._status_label.config(text='Settings reset')

    def _show_documentation(self):
        messagebox.showinfo('文档',
                            'Python Editor\n\n'
                            '一个轻量级多语言代码编辑器。\n\n'
                            '功能：\n'
                            '• 语法高亮 (Python / C / C++)\n'
                            '• 智能补全\n'
                            '• 静态检查 (Flake8 / Pyright / CPython)\n'
                            '• 代码运行 (Python / GCC / G++)\n'
                            '• 多主题切换\n\n'
                            '快捷键详见 帮助 → 快捷键',
                            parent=self.window)

    def _show_shortcuts(self):
        text = (
            "文件:\n"
            "  新建         Ctrl+N\n"
            "  打开         Ctrl+O\n"
            "  保存         Ctrl+S\n"
            "  另存为       Ctrl+Shift+S\n"
            "  运行         F5\n"
            "  检查         Ctrl+R\n"
            "  清除输出     Ctrl+L\n\n"
            "编辑:\n"
            "  撤销         Ctrl+Z\n"
            "  重做         Ctrl+Y\n"
            "  剪切         Ctrl+X\n"
            "  复制         Ctrl+C\n"
            "  粘贴         Ctrl+V\n"
            "  全选         Ctrl+A\n"
            "  查找         Ctrl+F\n"
            "  替换         Ctrl+H\n"
            "  转到行       Ctrl+G\n"
            "  切换注释     Ctrl+/\n\n"
            "查询:\n"
            "  跳转到定义   F12\n"
            "  查找引用     Shift+F12\n"
            "  重新解析     F6\n"
            "  刷新高亮     F7\n"
            "  触发建议     Ctrl+Space\n"
            "  隐藏建议     Esc\n\n"
            "帮助:\n"
            "  文档         F1\n"
            "  快捷键       Ctrl+K"
        )
        messagebox.showinfo('快捷键', text, parent=self.window)

    def _show_about(self):
        messagebox.showinfo('关于',
                            'Python Editor\n'
                            '版本 0.1.0\n\n'
                            '基于 Tkinter + 自研 Uui 组件库\n'
                            '语法高亮 / 智能补全 / 静态检查 / 代码运行',
                            parent=self.window)

    def _check_updates(self):
        messagebox.showinfo('检查更新', '已是最新版本 (0.1.0)', parent=self.window)

    def _report_issue(self):
        messagebox.showinfo('报告问题', '请前往 GitHub 仓库提交 Issue。', parent=self.window)

    def _run_check(self):
        code = self._editor.get('1.0', 'end-1c')
        if not code.strip():
            self._append_output('No code to check.\n')
            return

        self._status_label.config(text='Checking...')
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
            self._status_label.config(text='Check complete')
        except Exception as e:
            self._output._text.config(state='normal')
            self._append_output(f'Check error: {e}\n')
            self._output._text.config(state='disabled')
            self._status_label.config(text='Check failed')
        finally:
            try:
                os.unlink(temp_path)
            except OSError:
                pass

    def _run_code(self):
        code = self._editor.get('1.0', 'end-1c')
        if not code.strip():
            return

        self._status_label.config(text='Running...')
        self.window.update_idletasks()

        ext = LANG_CONFIG[self._lang]['ext']
        with tempfile.NamedTemporaryFile(mode='w', suffix=ext, delete=False, encoding='utf-8') as f:
            f.write(code)
            temp_path = f.name

        try:
            if self._lang == 'Python':
                cmd = [sys.executable, temp_path]
            elif self._lang in ('C', 'C++'):
                binary = temp_path.rsplit('.', 1)[0] + '.exe'
                compiler = 'g++' if self._lang == 'C++' else 'gcc'
                compile_result = subprocess.run(
                    [compiler, temp_path, '-o', binary],
                    capture_output=True, text=True, timeout=30,
                )
                if compile_result.returncode != 0:
                    self._output._text.config(state='normal')
                    self._output.clear()
                    self._append_output(f'Compile error:\n{compile_result.stderr}\n')
                    self._output._text.config(state='disabled')
                    self._status_label.config(text='Compile failed')
                    return
                cmd = [binary]
            else:
                return

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            self._output._text.config(state='normal')
            self._output.clear()
            if result.stdout:
                self._append_output(result.stdout)
            if result.stderr:
                self._append_output(result.stderr)
            if result.returncode != 0:
                self._append_output(f'\n[Exit code: {result.returncode}]\n')
            self._output._text.config(state='disabled')
            self._status_label.config(text='Run complete')
        except subprocess.TimeoutExpired:
            self._append_output('Execution timed out.\n')
            self._status_label.config(text='Timeout')
        except FileNotFoundError:
            self._output._text.config(state='normal')
            self._output.clear()
            self._append_output('Compiler not found. Please install GCC/G++ for C/C++ support.\n')
            self._output._text.config(state='disabled')
            self._status_label.config(text='Compiler not found')
        except Exception as e:
            self._output._text.config(state='normal')
            self._output.clear()
            self._append_output(f'Run error: {e}\n')
            self._output._text.config(state='disabled')
            self._status_label.config(text='Run failed')
        finally:
            try:
                os.unlink(temp_path)
            except OSError:
                pass

    def _append_output(self, text):
        self._output._text.config(state='normal')
        self._output._text.insert(tk.END, text)
        self._output._text.see(tk.END)
        self._output._text.config(state='disabled')

    def _clear_output(self):
        self._output._text.config(state='normal')
        self._output.clear()
        self._output._text.config(state='disabled')
        self._status_label.config(text='Ready')

    def run(self):
        self.window.mainloop()


if __name__ == '__main__':
    editor = CodeEditor()
    editor.run()
