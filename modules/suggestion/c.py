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


def _load_suggestion_list(lang: str, category: str) -> list[tuple[str, int]]:
    """Load suggestion list from data file.

    Args:
        lang: Language code (e.g., 'en_US', 'zh_CN')
        category: Category name (e.g., 'keywords', 'builtins')

    Returns:
        List of (label, priority) tuples
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
                    items_data = data.get('items', [])
                    # Parse per-item priorities
                    result = []
                    for item in items_data:
                        if isinstance(item, dict):
                            result.append((item['label'], item.get('priority', _PRIORITY_KEYWORD)))
                        else:
                            result.append((item, _PRIORITY_KEYWORD))
                    _CACHED_LISTS[cache_key] = result
                    return result
            except (json.JSONDecodeError, OSError):
                pass

    # Fallback hardcoded values
    _CACHED_LISTS[cache_key] = _FALLBACKS.get(category, [])
    return _CACHED_LISTS[cache_key]


# Fallback hardcoded suggestion lists with per-item priorities
_FALLBACK_KEYWORDS = [
    ('auto', 10), ('break', 10), ('case', 10), ('char', 10), ('const', 10),
    ('continue', 10), ('default', 10), ('do', 10), ('double', 10), ('else', 10),
    ('enum', 30), ('extern', 10), ('float', 10), ('for', 10), ('goto', 10),
    ('if', 10), ('inline', 10), ('int', 10), ('long', 10), ('register', 10),
    ('restrict', 10), ('return', 10), ('short', 10), ('signed', 10), ('sizeof', 20),
    ('static', 10), ('struct', 30), ('switch', 10), ('typedef', 30), ('union', 30),
    ('unsigned', 10), ('void', 10), ('volatile', 10), ('while', 10),
]

_FALLBACK_BUILTINS = [
    ('offsetof', 20), ('NULL', 20), ('printf', 20), ('scanf', 20), ('malloc', 20),
    ('calloc', 20), ('free', 20), ('realloc', 20), ('memcpy', 20), ('memmove', 20),
    ('memset', 20), ('memcmp', 20), ('strcpy', 20), ('strncpy', 20), ('strcat', 20),
    ('strncat', 20), ('strcmp', 20), ('strncmp', 20), ('strlen', 20), ('sprintf', 20),
    ('sscanf', 20), ('fopen', 20), ('fclose', 20), ('fread', 20), ('fwrite', 20),
    ('fprintf', 20), ('fscanf', 20), ('getchar', 20), ('putchar', 20), ('gets', 20),
    ('puts', 20), ('fgets', 20), ('fputs', 20), ('getc', 20), ('putc', 20),
    ('ungetc', 20), ('feof', 20), ('ferror', 20), ('atoi', 20), ('atof', 20),
    ('atol', 20), ('strtol', 20), ('strtod', 20), ('abs', 20), ('labs', 20),
    ('div', 20), ('exit', 20),
]

_FALLBACK_HEADERS = [
    ('assert.h', 25), ('ctype.h', 25), ('errno.h', 25), ('float.h', 25),
    ('limits.h', 25), ('math.h', 25), ('signal.h', 25), ('stdarg.h', 25),
    ('stddef.h', 25), ('stdint.h', 25), ('stdio.h', 25), ('stdlib.h', 25),
    ('string.h', 25), ('time.h', 25),
]

_FALLBACK_PREPROCESSOR = [
    ('#define', 10), ('#elif', 10), ('#else', 10), ('#endif', 10), ('#error', 10),
    ('#if', 10), ('#ifdef', 10), ('#ifndef', 10), ('#include', 10), ('#line', 10),
    ('#pragma', 10), ('#undef', 10), ('#warning', 10),
]

_FALLBACKS = {
    'keywords': _FALLBACK_KEYWORDS,
    'builtins': _FALLBACK_BUILTINS,
    'headers': _FALLBACK_HEADERS,
    'preprocessor': _FALLBACK_PREPROCESSOR,
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
            suggestions = self._suggest_names(block)

        if prefix:
            suggestions = [s for s in suggestions if s.label.lower().startswith(prefix.lower())]

        suggestions.sort(key=lambda x: (x.priority, x.label.lower()))
        return suggestions

    def _suggest_names(self, block: SuggestionBlock) -> list[SuggestionItem]:
        suggestions: list[SuggestionItem] = []

        # Load from data files with per-item priorities (use current language)
        lang = get_translator().current_language
        keywords = _load_suggestion_list(lang, 'keywords')
        builtins = _load_suggestion_list(lang, 'builtins')
        headers = _load_suggestion_list(lang, 'headers')
        preprocessor = _load_suggestion_list(lang, 'preprocessor')

        for label, priority in keywords:
            suggestions.append(SuggestionItem(label=label, priority=priority, kind='keyword'))
        for label, priority in builtins:
            suggestions.append(SuggestionItem(label=label, priority=priority, kind='builtin'))
        for label, priority in headers:
            suggestions.append(SuggestionItem(label=label, priority=priority, kind='header'))
        for label, priority in preprocessor:
            suggestions.append(SuggestionItem(label=label, priority=priority, kind='preprocessor'))

        # Extract user-defined items
        root = self._build_scope_tree(block.code)

        def _walk(scope: DOMScope) -> None:
            for fn in scope.functions:
                suggestions.append(SuggestionItem(label=fn, priority=_PRIORITY_FUNCTION, kind='function'))
            for cls in scope.classes:
                suggestions.append(SuggestionItem(label=cls, priority=_PRIORITY_CLASS, kind='class'))
            for var in scope.varibles:
                suggestions.append(SuggestionItem(label=var, priority=_PRIORITY_VARIABLE, kind='variable'))

            for sub in scope.subDOM:
                _walk(sub)

        _walk(root)
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
