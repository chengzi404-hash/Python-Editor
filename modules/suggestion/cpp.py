from .base import SuggestionExpert, SuggestionBlock, DOMScope

import re
import os
import json


_CPP_KEYWORDS: list[str] = []
_CPP_KEYWORDS_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'keywords', 'c&cpp', 'cpp.json')
try:
    with open(_CPP_KEYWORDS_PATH, encoding='utf-8') as _f:
        _CPP_KEYWORDS = json.load(_f)
except (FileNotFoundError, json.JSONDecodeError):
    _CPP_KEYWORDS = [
        'alignas', 'alignof', 'and', 'and_eq', 'auto', 'bitand', 'bitor', 'bool',
        'break', 'case', 'catch', 'char', 'char8_t', 'char16_t', 'char32_t',
        'class', 'compl', 'concept', 'const', 'consteval', 'constexpr',
        'constinit', 'const_cast', 'continue', 'co_await', 'co_return',
        'co_yield', 'decltype', 'default', 'delete', 'do', 'double',
        'dynamic_cast', 'else', 'enum', 'explicit', 'export', 'extern', 'false',
        'float', 'for', 'friend', 'goto', 'if', 'inline', 'int', 'long',
        'mutable', 'namespace', 'new', 'noexcept', 'not', 'not_eq', 'nullptr',
        'operator', 'or', 'or_eq', 'private', 'protected', 'public',
        'register', 'reinterpret_cast', 'requires', 'return', 'short', 'signed',
        'sizeof', 'static', 'static_assert', 'static_cast', 'struct', 'switch',
        'template', 'this', 'thread_local', 'throw', 'true', 'try', 'typedef',
        'typeid', 'typename', 'union', 'unsigned', 'using', 'virtual', 'void',
        'volatile', 'wchar_t', 'while', 'xor', 'xor_eq',
    ]

_CPP_HEADERS: list[str] = []
_CPP_HEADERS_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'keywords', 'c&cpp', 'headers.json')
try:
    with open(_CPP_HEADERS_PATH, encoding='utf-8') as _f:
        _CPP_HEADERS = json.load(_f)
except (FileNotFoundError, json.JSONDecodeError):
    _CPP_HEADERS = [
        'algorithm', 'array', 'atomic', 'bitset', 'chrono', 'deque', 'exception',
        'fstream', 'functional', 'future', 'iostream', 'map', 'memory',
        'mutex', 'optional', 'queue', 'random', 'regex', 'set', 'shared_mutex',
        'stack', 'string', 'thread', 'tuple', 'unordered_map', 'unordered_set',
        'variant', 'vector',
    ]

_BUILTINS: list[str] = [
    'sizeof', 'NULL', 'nullptr', 'printf', 'scanf', 'malloc', 'calloc', 'free',
    'realloc', 'memcpy', 'memset', 'string', 'vector', 'map', 'set', 'pair',
    'make_pair', 'make_shared', 'make_unique', 'move', 'forward', 'swap',
    'begin', 'end', 'size', 'empty', 'push_back', 'pop_back', 'insert', 'erase',
]

_CLASS_PATTERN = re.compile(
    r'^[ \t]*'
    r'(?:template\s*<[^>]*>\s*)?'
    r'(?:export\s+)?'
    r'(?:class|struct)\s+'
    r'(?:[A-Za-z_][A-Za-z0-9_]*\s*::\s*)?'
    r'([A-Za-z_][A-Za-z0-9_]*)'
    r'(?:\s*:\s*(?:public|private|protected)\s+[^{]*)?'
    r'\s*\{',
    re.MULTILINE
)

_FUNC_PATTERN = re.compile(
    r'^[ \t]*'
    r'(?:template\s*<[^>]*>\s*)?'
    r'(?:(?:inline|static|extern|virtual|explicit|const|volatile|noexcept)*\s+)*'
    r'(?:(?:auto\s+)?(?:\*|\&)+?\s*)?'
    r'(?:[A-Za-z_][A-Za-z0-9_:*\s]+?\s+)?'
    r'([A-Za-z_][A-Za-z0-9_:]*)'
    r'\s*\([^()]*\)'
    r'(?:\s*const)?(?:\s*override)?(?:\s*noexcept)?'
    r'\s*(?:\{|;)',
    re.MULTILINE
)

_NAMESPACE_PATTERN = re.compile(
    r'^[ \t]*'
    r'namespace\s+'
    r'([A-Za-z_][A-Za-z0-9_]*)'
    r'(?:\s*\{)?',
    re.MULTILINE
)

_ENUM_PATTERN = re.compile(
    r'^[ \t]*'
    r'enum\s+'
    r'(?:class\s+)?'
    r'([A-Za-z_][A-Za-z0-9_]*)'
    r'(?:\s*\{)?',
    re.MULTILINE
)


class CppSuggestionExpert(SuggestionExpert):
    def __init__(self) -> None:
        super().__init__()

    def get_languange_exts(self) -> list:
        return ['cpp', 'cc', 'cxx', 'hpp', 'hh']

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
        while word_start > 0 and (current_line[word_start - 1].isalnum() or current_line[word_start - 1] == '_' or current_line[word_start - 1] == ':'):
            word_start -= 1
        prefix = current_line[word_start:col]

        if word_start > 0 and current_line[word_start - 1] == '.':
            obj_end = word_start - 1
            obj_start = obj_end - 1
            while obj_start >= 0 and (current_line[obj_start].isalnum() or current_line[obj_start] == '_'):
                obj_start -= 1
            obj_name = current_line[obj_start + 1:obj_end]
            suggestions = self._suggest_attributes(block, line_no, obj_name)
        elif word_start > 0 and word_start > 1 and current_line[word_start - 2:word_start] == '->':
            obj_end = word_start - 2
            obj_start = obj_end - 1
            while obj_start >= 0 and (current_line[obj_start].isalnum() or current_line[obj_start] == '_'):
                obj_start -= 1
            obj_name = current_line[obj_start + 1:obj_end]
            suggestions = self._suggest_attributes(block, line_no, obj_name)
        elif word_start > 0 and current_line[word_start - 1] == ':' and word_start > 1 and current_line[word_start - 2] == ':':
            suggestions = self._suggest_scope(block, line_no)
        else:
            suggestions = self._suggest_names(block, line_no)

        if prefix:
            suggestions = [s for s in suggestions if s.startswith(prefix)]

        return sorted(set(suggestions))

    def _suggest_names(self, block: SuggestionBlock, line_no: int) -> list[str]:
        suggestions: set[str] = set()

        suggestions.update(_CPP_KEYWORDS)
        suggestions.update(_BUILTINS)

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
            'begin', 'end', 'size', 'empty', 'capacity', 'max_size', 'resize',
            'push_back', 'pop_back', 'insert', 'erase', 'clear', 'swap',
            'find', 'count', 'lower_bound', 'upper_bound', 'first', 'second',
            'data', 'length', 'c_str', 'substr', 'append', 'replace', 'copy',
        ]

    def _suggest_scope(self, block: SuggestionBlock, line_no: int) -> list[str]:
        suggestions: set[str] = set()

        root = self._build_scope_tree(block.code)

        def _walk(scope: DOMScope) -> None:
            suggestions.update(scope.classes)
            suggestions.update(scope.functions)
            for sub in scope.subDOM:
                _walk(sub)

        _walk(root)
        suggestions.update(['std', 'cout', 'cin', 'endl', 'string', 'vector', 'map', 'set'])
        return list(suggestions)

    @staticmethod
    def _collect_entries(code: str) -> list[tuple[int, int, str, str, int]]:
        total_lines = code.count('\n') + 1

        entries: list[tuple[int, int, str, str, int]] = []

        for m in _CLASS_PATTERN.finditer(code):
            line_no = code[:m.start()].count('\n')
            indent = len(m.group()) - len(m.group().lstrip())
            kind = 'class'
            name = m.group(1)
            entries.append((line_no, indent, kind, name, 0))

        for m in _FUNC_PATTERN.finditer(code):
            line_no = code[:m.start()].count('\n')
            indent = len(m.group()) - len(m.group().lstrip())
            name = m.group(1)
            if name not in ('if', 'while', 'for', 'switch', 'catch', 'sizeof'):
                entries.append((line_no, indent, 'function', name, 0))

        for m in _NAMESPACE_PATTERN.finditer(code):
            line_no = code[:m.start()].count('\n')
            indent = len(m.group()) - len(m.group().lstrip())
            name = m.group(1)
            entries.append((line_no, indent, 'namespace', name, 0))

        for m in _ENUM_PATTERN.finditer(code):
            line_no = code[:m.start()].count('\n')
            indent = len(m.group()) - len(m.group().lstrip())
            name = m.group(1)
            entries.append((line_no, indent, 'enum', name, 0))

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
        entries = CppSuggestionExpert._collect_entries(code)
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

            if kind in ('class', 'namespace'):
                parent.classes.append(name)
            else:
                parent.functions.append(name)

            parent.subDOM.append(scope)
            stack.append((scope, indent))

        return root
