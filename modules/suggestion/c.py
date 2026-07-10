from .base import SuggestionExpert, SuggestionBlock, DOMScope, SuggestionItem
from modules.data import suggestions_path
from modules.i18n import get_translator
import json
import os
import re

# Priority constants (lower = higher priority)
_PRIORITY_KEYWORD = 10
_PRIORITY_BUILTIN = 20
_PRIORITY_HEADER = 25
_PRIORITY_CLASS = 30
_PRIORITY_FUNCTION = 40
_PRIORITY_VARIABLE = 50

# Cache for loaded suggestion lists
_CACHED_LISTS: dict = {}


def _load_suggestion_list(lang: str, category: str) -> tuple[list[str], int]:
    """Load suggestion list from data file.

    Args:
        lang: Language code (e.g., 'en_US', 'zh_CN')
        category: Category name (e.g., 'keywords', 'builtins')

    Returns:
        Tuple of (items list, priority)
    """
    cache_key = f"{lang}:{category}"
    if cache_key in _CACHED_LISTS:
        return _CACHED_LISTS[cache_key]

    # Try language-specific file first, then fallback to en_US
    for lang_code in (lang, 'en_US'):
        filepath = suggestions_path('c', f'{category}_{lang_code}.json')
        if os.path.exists(filepath):
            try:
                with open(filepath, encoding='utf-8') as f:
                    data = json.load(f)
                    items = data.get('items', [])
                    priority = data.get('priority', _PRIORITY_KEYWORD)
                    _CACHED_LISTS[cache_key] = (items, priority)
                    return (items, priority)
            except (json.JSONDecodeError, OSError):
                pass

    # Fallback hardcoded values
    _CACHED_LISTS[cache_key] = _FALLBACKS.get(category, ([], _PRIORITY_KEYWORD))
    return _CACHED_LISTS[cache_key]


# Fallback hardcoded suggestion lists
_FALLBACK_KEYWORDS = [
    'auto', 'break', 'case', 'char', 'const', 'continue', 'default', 'do',
    'double', 'else', 'enum', 'extern', 'float', 'for', 'goto', 'if',
    'inline', 'int', 'long', 'register', 'restrict', 'return', 'short',
    'signed', 'sizeof', 'static', 'struct', 'switch', 'typedef', 'union',
    'unsigned', 'void', 'volatile', 'while',
]

_FALLBACK_BUILTINS = [
    'sizeof', 'offsetof', 'NULL', 'printf', 'scanf', 'malloc', 'calloc', 'free',
    'realloc', 'memcpy', 'memmove', 'memset', 'memcmp', 'strcpy', 'strncpy',
    'strcat', 'strncat', 'strcmp', 'strncmp', 'strlen', 'sprintf', 'sscanf',
    'fopen', 'fclose', 'fread', 'fwrite', 'fprintf', 'fscanf', 'getchar', 'putchar',
    'gets', 'puts', 'fgets', 'fputs', 'getc', 'putc', 'ungetc', 'feof', 'ferror',
    'atoi', 'atof', 'atol', 'strtol', 'strtod', 'abs', 'labs', 'div', 'exit',
]

_FALLBACK_HEADERS = [
    'assert.h', 'ctype.h', 'errno.h', 'float.h', 'limits.h', 'math.h',
    'signal.h', 'stdarg.h', 'stddef.h', 'stdint.h', 'stdio.h', 'stdlib.h',
    'string.h', 'time.h',
]

_FALLBACK_PREPROCESSOR = [
    '#define', '#elif', '#else', '#endif', '#error', '#if', '#ifdef',
    '#ifndef', '#include', '#line', '#pragma', '#undef', '#warning',
]

_FALLBACKS = {
    'keywords': (_FALLBACK_KEYWORDS, _PRIORITY_KEYWORD),
    'builtins': (_FALLBACK_BUILTINS, _PRIORITY_BUILTIN),
    'headers': (_FALLBACK_HEADERS, _PRIORITY_HEADER),
    'preprocessor': (_FALLBACK_PREPROCESSOR, _PRIORITY_KEYWORD),
}


# Regex patterns
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
    def __init__(self, lang: str = 'en_US') -> None:
        super().__init__()
        self._lang = lang

    def get_languange_exts(self) -> list:
        return ['c', 'h']

    def suggest(self, block: SuggestionBlock) -> list[SuggestionItem]:
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
            suggestions = [s for s in suggestions if s.label.lower().startswith(prefix.lower())]

        suggestions.sort(key=lambda x: (x.priority, x.label.lower()))
        return suggestions

    def _suggest_names(self, block: SuggestionBlock, line_no: int) -> list[SuggestionItem]:
        suggestions: list[SuggestionItem] = []

        # Load from data files (use current language)
        lang = get_translator().current_language
        keywords, kw_priority = _load_suggestion_list(lang, 'keywords')
        builtins, builtin_priority = _load_suggestion_list(lang, 'builtins')
        headers, header_priority = _load_suggestion_list(lang, 'headers')
        preprocessor, pp_priority = _load_suggestion_list(lang, 'preprocessor')

        for kw in keywords:
            suggestions.append(SuggestionItem(label=kw, priority=kw_priority, kind='keyword'))
        for b in builtins:
            suggestions.append(SuggestionItem(label=b, priority=builtin_priority, kind='builtin'))
        for h in headers:
            suggestions.append(SuggestionItem(label=h, priority=header_priority, kind='header'))
        for pp in preprocessor:
            suggestions.append(SuggestionItem(label=pp, priority=pp_priority, kind='preprocessor'))

        # Extract user-defined items
        root = self._build_scope_tree(block.code)

        def _walk(scope: DOMScope, pos: int) -> None:
            for fn in scope.functions:
                suggestions.append(SuggestionItem(label=fn, priority=_PRIORITY_FUNCTION, kind='function'))
            for cls in scope.classes:
                suggestions.append(SuggestionItem(label=cls, priority=_PRIORITY_CLASS, kind='class'))
            for var in scope.varibles:
                suggestions.append(SuggestionItem(label=var, priority=_PRIORITY_VARIABLE, kind='variable'))

            for sub in scope.subDOM:
                if sub.begin <= pos < sub.end:
                    _walk(sub, pos)
                    break

        _walk(root, line_no)
        return suggestions

    def _suggest_attributes(self, block: SuggestionBlock, line_no: int, obj_name: str) -> list[SuggestionItem]:
        attrs = ['x', 'y', 'z', 'width', 'height', 'left', 'right', 'top', 'bottom',
                 'data', 'next', 'prev', 'count', 'size', 'ptr', 'buf', 'len']
        return [SuggestionItem(label=a, priority=_PRIORITY_BUILTIN, kind='attribute') for a in attrs]

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
