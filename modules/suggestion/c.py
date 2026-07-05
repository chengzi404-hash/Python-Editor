from .base import SuggestionExpert, SuggestionBlock, DOMScope

import re
import os
import json


_C_KEYWORDS: list[str] = []
_C_KEYWORDS_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'keywords', 'c&cpp', 'c.json')
try:
    with open(_C_KEYWORDS_PATH, encoding='utf-8') as _f:
        _C_KEYWORDS = json.load(_f)
except (FileNotFoundError, json.JSONDecodeError):
    _C_KEYWORDS = [
        'auto', 'break', 'case', 'char', 'const', 'continue', 'default', 'do',
        'double', 'else', 'enum', 'extern', 'float', 'for', 'goto', 'if',
        'inline', 'int', 'long', 'register', 'restrict', 'return', 'short',
        'signed', 'sizeof', 'static', 'struct', 'switch', 'typedef', 'union',
        'unsigned', 'void', 'volatile', 'while',
    ]

_PP_KEYWORDS: list[str] = []
_PP_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'keywords', 'c&cpp', 'preprocessor.json')
try:
    with open(_PP_PATH, encoding='utf-8') as _f:
        _PP_KEYWORDS = json.load(_f)
except (FileNotFoundError, json.JSONDecodeError):
    _PP_KEYWORDS = ['#define', '#elif', '#else', '#endif', '#error', '#if', '#ifdef', '#ifndef', '#include', '#line', '#pragma', '#undef', '#warning']

_C_HEADERS: list[str] = []
_CH_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'keywords', 'c&cpp', 'cheaders.json')
try:
    with open(_CH_PATH, encoding='utf-8') as _f:
        _C_HEADERS = json.load(_f)
except (FileNotFoundError, json.JSONDecodeError):
    _C_HEADERS = ['assert.h', 'ctype.h', 'errno.h', 'float.h', 'limits.h', 'math.h', 'signal.h', 'stdarg.h', 'stddef.h', 'stdint.h', 'stdio.h', 'stdlib.h', 'string.h', 'time.h']

_BUILTINS: list[str] = [
    'sizeof', 'offsetof', 'NULL', 'printf', 'scanf', 'malloc', 'calloc', 'free',
    'realloc', 'memcpy', 'memmove', 'memset', 'memcmp', 'strcpy', 'strncpy',
    'strcat', 'strncat', 'strcmp', 'strncmp', 'strlen', 'sprintf', 'sscanf',
    'fopen', 'fclose', 'fread', 'fwrite', 'fprintf', 'fscanf', 'getchar', 'putchar',
    'gets', 'puts', 'fgets', 'fputs', 'getc', 'putc', 'ungetc', 'feof', 'ferror',
    'atoi', 'atof', 'atol', 'strtol', 'strtod', 'abs', 'labs', 'div', 'exit',
]

_STRUCT_CLASS_PATTERN = re.compile(
    r'^[ \t]*'
    r'(?:typedef\s+)?'
    r'(?:struct|union|enum)\s+'
    r'(?:[A-Za-z_][A-Za-z0-9_]*\s+)?'
    r'\{',
    re.MULTILINE
)

_FUNC_PATTERN = re.compile(
    r'^[ \t]*'
    r'(?:(?:inline|static|extern|const|volatile)*\s+)*'
    r'(?:[A-Za-z_][A-Za-z0-9_*\s]+?\s+)?'
    r'([A-Za-z_][A-Za-z0-9_]*)'
    r'\s*\([^()]*\)'
    r'\s*\{',
    re.MULTILINE
)

_TYPEDEF_PATTERN = re.compile(
    r'^[ \t]*'
    r'typedef\s+'
    r'(?:struct|union|enum|class)?\s*'
    r'(?:[A-Za-z_][A-Za-z0-9_*\s]+?\s+)?'
    r'([A-Za-z_][A-Za-z0-9_]*)',
    re.MULTILINE
)


class CSuggestionExpert(SuggestionExpert):
    def __init__(self) -> None:
        super().__init__()

    def get_languange_exts(self) -> list:
        return ['c', 'h']

    def suggest(self, block: SuggestionBlock) -> list:
        code = block.code
        pos = block.position

        text_before = code[:pos]
        line_no = text_before.count('\n')
        line_start = text_before.rfind('\n') + 1 if '\n' in text_before else 0
        col = pos - line_start

        lines = code.split('\n')
        current_line = lines[line_no] if line_no < len(lines) else ''
        before_cursor = current_line[:col]

        word_start = col
        while word_start > 0 and (current_line[word_start - 1].isalnum() or current_line[word_start - 1] == '_'):
            word_start -= 1
        prefix = current_line[word_start:col]

        if word_start > 0 and current_line[word_start - 1] == '.':
            obj_end = word_start - 1
            obj_start = obj_end - 1
            while obj_start >= 0 and (current_line[obj_start].isalnum() or current_line[obj_start] == '_'):
                obj_start -= 1
            obj_name = current_line[obj_start + 1:obj_end]
            suggestions = self._suggest_attributes(block, line_no, obj_name)
        elif word_start > 0 and current_line[word_start - 1] == '>' and word_start > 1 and current_line[word_start - 2] == '-':
            obj_end = word_start - 2
            obj_start = obj_end - 1
            while obj_start >= 0 and (current_line[obj_start].isalnum() or current_line[obj_start] == '_'):
                obj_start -= 1
            obj_name = current_line[obj_start + 1:obj_end]
            suggestions = self._suggest_attributes(block, line_no, obj_name)
        else:
            suggestions = self._suggest_names(block, line_no)

        if prefix:
            suggestions = [s for s in suggestions if s.startswith(prefix)]

        return sorted(set(suggestions))

    def _suggest_names(self, block: SuggestionBlock, line_no: int) -> list[str]:
        suggestions: set[str] = set()

        suggestions.update(_C_KEYWORDS)
        suggestions.update(_BUILTINS)
        suggestions.update(_PP_KEYWORDS)

        root = self._build_scope_tree(block.code)

        def _walk(scope: DOMScope, pos: int) -> None:
            suggestions.update(scope.functions)
            suggestions.update(scope.classes)
            suggestions.update(scope.varibles)

            for sub in scope.subDOM:
                if sub.begin <= pos < sub.end:
                    _walk(sub, pos)
                    break

        _walk(root, line_no)
        return list(suggestions)

    def _suggest_attributes(self, block: SuggestionBlock, line_no: int, obj_name: str) -> list[str]:
        return [
            'x', 'y', 'z', 'width', 'height', 'left', 'right', 'top', 'bottom',
            'data', 'next', 'prev', 'count', 'size', 'ptr', 'buf', 'len',
        ]

    @staticmethod
    def _collect_entries(code: str) -> list[tuple[int, int, str, str, int]]:
        total_lines = code.count('\n') + 1

        entries: list[tuple[int, int, str, str, int]] = []

        for m in _STRUCT_CLASS_PATTERN.finditer(code):
            line_no = code[:m.start()].count('\n')
            indent = len(m.group()) - len(m.group().lstrip())
            kind = 'class'
            name_match = re.search(r'(?:struct|union|enum)\s+([A-Za-z_][A-Za-z0-9_]*)\s*\{', m.group())
            name = name_match.group(1) if name_match else m.group().strip()
            entries.append((line_no, indent, kind, name, 0))

        for m in _FUNC_PATTERN.finditer(code):
            line_no = code[:m.start()].count('\n')
            indent = len(m.group()) - len(m.group().lstrip())
            name = m.group(1)
            entries.append((line_no, indent, 'function', name, 0))

        for m in _TYPEDEF_PATTERN.finditer(code):
            line_no = code[:m.start()].count('\n')
            indent = len(m.group()) - len(m.group().lstrip())
            name = m.group(1)
            entries.append((line_no, indent, 'typedef', name, 0))

        entries.sort(key=lambda x: x[0])

        for i in range(len(entries)):
            end = total_lines
            for j in range(i + 1, len(entries)):
                if entries[j][1] <= entries[i][1]:
                    end = entries[j][0]
                    break
            entries[i] = (entries[i][0], entries[i][1], entries[i][2], entries[i][3], end)

        return entries

    @staticmethod
    def _build_scope_tree(code: str) -> DOMScope:
        entries = CSuggestionExpert._collect_entries(code)
        if not entries:
            return DOMScope(begin=0, end=code.count('\n') + 1, varibles=[], functions=[], classes=[], subDOM=[])

        total_lines = entries[-1][4]

        root = DOMScope(begin=0, end=total_lines, varibles=[], functions=[], classes=[], subDOM=[])
        stack: list[tuple[DOMScope, int]] = [(root, -1)]

        for line_no, indent, kind, name, end in entries:
            while stack and stack[-1][1] >= indent:
                stack.pop()

            parent = stack[-1][0]
            scope = DOMScope(begin=line_no, end=end, varibles=[], functions=[], classes=[], subDOM=[])

            if kind in ('class', 'typedef'):
                parent.classes.append(name)
            else:
                parent.functions.append(name)

            parent.subDOM.append(scope)
            stack.append((scope, indent))

        return root
