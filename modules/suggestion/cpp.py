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
        filepath = suggestions_path('cpp', f'{category}_{lang_code}.json')
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
    ('alignas', 10), ('alignof', 10), ('and', 10), ('and_eq', 10), ('auto', 10),
    ('bitand', 10), ('bitor', 10), ('bool', 10), ('break', 10), ('case', 10),
    ('catch', 10), ('char', 10), ('char8_t', 10), ('char16_t', 10), ('char32_t', 10),
    ('class', 30), ('compl', 10), ('concept', 10), ('const', 10), ('consteval', 10),
    ('constexpr', 10), ('constinit', 10), ('const_cast', 10), ('continue', 10),
    ('co_await', 10), ('co_return', 10), ('co_yield', 10), ('decltype', 10),
    ('default', 10), ('delete', 10), ('do', 10), ('double', 10), ('dynamic_cast', 10),
    ('else', 10), ('enum', 30), ('explicit', 10), ('export', 10), ('extern', 10),
    ('false', 10), ('float', 10), ('for', 10), ('friend', 10), ('goto', 10),
    ('if', 10), ('inline', 10), ('int', 10), ('long', 10), ('mutable', 10),
    ('namespace', 30), ('new', 10), ('noexcept', 10), ('not', 10), ('not_eq', 10),
    ('nullptr', 10), ('operator', 30), ('or', 10), ('or_eq', 10), ('private', 10),
    ('protected', 10), ('public', 10), ('register', 10), ('reinterpret_cast', 10),
    ('requires', 10), ('return', 10), ('short', 10), ('signed', 10), ('sizeof', 20),
    ('static', 10), ('static_assert', 10), ('static_cast', 10), ('struct', 30),
    ('switch', 10), ('template', 30), ('this', 10), ('thread_local', 10), ('throw', 10),
    ('true', 10), ('try', 10), ('typedef', 30), ('typeid', 10), ('typename', 10),
    ('union', 30), ('unsigned', 10), ('using', 10), ('virtual', 10), ('void', 10),
    ('volatile', 10), ('wchar_t', 10), ('while', 10), ('xor', 10), ('xor_eq', 10),
]

_FALLBACK_HEADERS = [
    ('algorithm', 25), ('array', 25), ('atomic', 25), ('bitset', 25), ('chrono', 25),
    ('deque', 25), ('exception', 25), ('fstream', 25), ('functional', 25),
    ('future', 25), ('iostream', 25), ('map', 25), ('memory', 25), ('mutex', 25),
    ('optional', 25), ('queue', 25), ('random', 25), ('regex', 25), ('set', 25),
    ('shared_mutex', 25), ('stack', 25), ('string', 25), ('thread', 25), ('tuple', 25),
    ('unordered_map', 25), ('unordered_set', 25), ('variant', 25), ('vector', 25),
]

_FALLBACK_BUILTINS = [
    ('NULL', 20), ('nullptr', 20), ('printf', 20), ('scanf', 20), ('malloc', 20),
    ('calloc', 20), ('free', 20), ('realloc', 20), ('memcpy', 20), ('memset', 20),
    ('string', 20), ('vector', 20), ('map', 20), ('set', 20), ('pair', 20),
    ('make_pair', 20), ('make_shared', 20), ('make_unique', 20), ('move', 20),
    ('forward', 20), ('swap', 20), ('begin', 20), ('end', 20), ('size', 20),
    ('empty', 20), ('push_back', 20), ('pop_back', 20), ('insert', 20), ('erase', 20),
]

_FALLBACKS = {
    'keywords': _FALLBACK_KEYWORDS,
    'builtins': _FALLBACK_BUILTINS,
    'headers': _FALLBACK_HEADERS,
}


# Regex patterns
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
    r'(?:[A-Za-z_][A-Za-z0-9:*\s]+?\s+)?'
    r'([A-Za-z_][A-Za-z0-9:]*)'
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
    def __init__(self, lang: str = 'en_US') -> None:
        super().__init__()
        self._lang = lang

    def get_languange_exts(self) -> list:
        return ['cpp', 'cc', 'cxx', 'hpp', 'hh']

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

        if col >= 2 and current_line[col - 2:col] == '::':
            prefix = ''
            suggestions = self._suggest_scope(block, line_no)
        else:
            word_start = col
            while word_start > 0 and (current_line[word_start - 1].isalnum() or current_line[word_start - 1] == '_'):
                word_start -= 1
            prefix = current_line[word_start:col]

            if word_start >= 2 and current_line[word_start - 2:word_start] == '::':
                suggestions = self._suggest_scope(block, line_no)
            elif word_start > 0 and current_line[word_start - 1] == '.':
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

        for label, priority in keywords:
            suggestions.append(SuggestionItem(label=label, priority=priority, kind='keyword'))
        for label, priority in builtins:
            suggestions.append(SuggestionItem(label=label, priority=priority, kind='builtin'))
        for label, priority in headers:
            suggestions.append(SuggestionItem(label=label, priority=priority, kind='header'))

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
        attrs = [
            'begin', 'end', 'size', 'empty', 'capacity', 'max_size', 'resize',
            'push_back', 'pop_back', 'insert', 'erase', 'clear', 'swap',
            'find', 'count', 'lower_bound', 'upper_bound', 'first', 'second',
            'data', 'length', 'c_str', 'substr', 'append', 'replace', 'copy',
        ]
        return [SuggestionItem(label=a, priority=_PRIORITY_BUILTIN, kind='attribute') for a in attrs]

    def _suggest_scope(self, block: SuggestionBlock, line_no: int) -> list[SuggestionItem]:
        suggestions: list[SuggestionItem] = []

        root = self._build_scope_tree(block.code)

        def _walk(scope: DOMScope) -> None:
            for cls in scope.classes:
                suggestions.append(SuggestionItem(label=cls, priority=_PRIORITY_CLASS, kind='class'))
            for fn in scope.functions:
                suggestions.append(SuggestionItem(label=fn, priority=_PRIORITY_FUNCTION, kind='function'))
            for sub in scope.subDOM:
                _walk(sub)

        _walk(root)

        # Add common C++ scope items
        common = ['std', 'cout', 'cin', 'endl', 'string', 'vector', 'map', 'set']
        for c in common:
            suggestions.append(SuggestionItem(label=c, priority=_PRIORITY_BUILTIN, kind='builtin'))

        return suggestions

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
