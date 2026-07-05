import sys
import os
import tempfile
import tkinter as tk

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from modules.Uui.widgets import UFrame, ULabel, UButton, UText, UComboBox, theme
from modules.Uui.widgets.window import Window
from modules.Uui.widgets.editor_suggestion import UEditorSuggestion, CompletionItem
from modules.highlighter import PythonHighlighterExpert, CcppHighlighterExpert, HighlightBlock
from modules.suggestion import PythonSuggestionExpert, CSuggestionExpert, CppSuggestionExpert, SuggestionBlock
from modules.checker import Flake8Checker, PyrightChecker, CPythonChecker

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


class CodeEditor:
    def __init__(self):
        self.window = Window(title='Python Editor')
        self.window.geometry('960x680+200+100')
        self.window.configure(bg=theme.BG_BASE)
        self.window.resizable(width=True, height=True)

        self._lang = 'Python'
        self._current_file = None
        self._suggestion_popup = None
        self._highlighting_enabled = True

        self._build_toolbar()
        self._build_editor()
        self._build_output_panel()
        self._build_status_bar()

        self._switch_language('Python')

        self.window.bind('<Control-n>', lambda e: self._new_file())
        self.window.bind('<Control-s>', lambda e: self._save_file())
        self.window.bind('<Control-r>', lambda e: self._run_check())
        self.window.bind('<F5>', lambda e: self._run_code())

    def _build_toolbar(self):
        bar = UFrame(self.window, variant='title')
        bar.pack(fill=tk.X, padx=0, pady=0)

        self._lang_combo = UComboBox(
            bar, values=['Python', 'C', 'C++'],
            command=self._on_lang_changed,
        )
        self._lang_combo.pack(side=tk.LEFT, padx=10, pady=6)

        UButton(bar, text='Run', command=self._run_code, variant='success',
                width=72, height=28).pack(side=tk.LEFT, padx=4, pady=6)
        UButton(bar, text='Check', command=self._run_check, variant='primary',
                width=72, height=28).pack(side=tk.LEFT, padx=4, pady=6)
        UButton(bar, text='Clear', command=self._clear_output, variant='default',
                width=72, height=28).pack(side=tk.LEFT, padx=4, pady=6)

    def _build_editor(self):
        body = UFrame(self.window, variant='base')
        body.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)

        self._editor = UText(body, width=80, height=20)
        self._editor.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)

        self._editor._text.bind('<KeyRelease>', self._on_key_release)
        self._editor._text.bind('<KeyPress>', self._on_key_press)
        self._editor._text.bind('<ButtonRelease-1>', self._on_click)
        self._editor._text.bind('<FocusIn>', self._on_focus_in)

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
        self._lang = lang
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
        self._show_suggestions()

    def _on_key_press(self, event=None):
        if self._suggestion_popup and self._suggestion_popup.winfo_exists():
            if event.keysym in ('Escape',):
                self._suggestion_popup.hide()
            elif event.keysym in ('Down', 'Up', 'Return', 'Tab'):
                return

    def _on_click(self, event=None):
        self._update_status()
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
            import subprocess
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

    def _new_file(self):
        self._editor._text.delete('1.0', tk.END)
        self._status_label.config(text='New file')

    def _save_file(self):
        from tkinter import filedialog
        code = self._editor.get('1.0', 'end-1c')
        ext = LANG_CONFIG[self._lang]['ext']
        filetypes = [(f'{self._lang} files', f'*{ext}'), ('All files', '*.*')]
        path = filedialog.asksaveasfilename(defaultextension=ext, filetypes=filetypes)
        if path:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(code)
            self._current_file = path
            self._status_label.config(text=f'Saved: {os.path.basename(path)}')

    def run(self):
        self.window.mainloop()


if __name__ == '__main__':
    editor = CodeEditor()
    editor.run()