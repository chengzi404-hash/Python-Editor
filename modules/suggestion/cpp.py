import json
import os
import re

from modules.data import suggestions_path
from modules.i18n import get_translator

from .base import DOMScope, SuggestionBlock, SuggestionExpert, SuggestionItem

# Priority constants (lower = higher priority)
# User-defined items take highest priority
_PRIORITY_USER_FUNCTION = 5
_PRIORITY_USER_VARIABLE = 10
_PRIORITY_KEYWORD = 15
_PRIORITY_USER_CLASS = 20
_PRIORITY_BUILTIN = 30
_PRIORITY_HEADER = 35

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
                            label = item['label']
                            priority = item.get('priority', _PRIORITY_KEYWORD)
                        else:
                            label = item
                            priority = _PRIORITY_KEYWORD
                        # Auto-adjust priority based on underscore prefix
                        priority = _adjust_underscore_priority(label, priority)
                        result.append((label, priority))
                    _CACHED_LISTS[cache_key] = result
                    return result
            except (json.JSONDecodeError, OSError):
                pass

    # Fallback hardcoded values
    _CACHED_LISTS[cache_key] = _FALLBACKS.get(category, [])
    return _CACHED_LISTS[cache_key]


def _adjust_underscore_priority(label: str, priority: int) -> int:
    """Adjust priority based on underscore prefix.

    - '__' prefix: priority +20 (appears after single '_' prefixed items)
    - '_' prefix (not '__'): priority +10 (appears after normal items)
    """
    if label.startswith('__'):
        return priority + 20
    elif label.startswith('_'):
        return priority + 10
    return priority


# Fallback hardcoded suggestion lists with per-item priorities
_FALLBACK_KEYWORDS = [
    ('alignas', 15), ('alignof', 15), ('and', 15), ('and_eq', 15), ('auto', 15),
    ('bitand', 15), ('bitor', 15), ('bool', 15), ('break', 15), ('case', 15),
    ('catch', 15), ('char', 15), ('char8_t', 15), ('char16_t', 15), ('char32_t', 15),
    ('class', 20), ('compl', 15), ('concept', 15), ('const', 15), ('consteval', 15),
    ('constexpr', 15), ('constinit', 15), ('const_cast', 15), ('continue', 15),
    ('co_await', 15), ('co_return', 15), ('co_yield', 15), ('decltype', 15),
    ('default', 15), ('delete', 15), ('do', 15), ('double', 15), ('dynamic_cast', 15),
    ('else', 15), ('enum', 20), ('explicit', 15), ('export', 15), ('extern', 15),
    ('false', 15), ('float', 15), ('for', 15), ('friend', 15), ('goto', 15),
    ('if', 15), ('inline', 15), ('int', 15), ('long', 15), ('mutable', 15),
    ('namespace', 20), ('new', 15), ('noexcept', 15), ('not', 15), ('not_eq', 15),
    ('nullptr', 15), ('operator', 20), ('or', 15), ('or_eq', 15), ('private', 15),
    ('protected', 15), ('public', 15), ('register', 15), ('reinterpret_cast', 15),
    ('requires', 15), ('return', 15), ('short', 15), ('signed', 15), ('sizeof', 30),
    ('static', 15), ('static_assert', 15), ('static_cast', 15), ('struct', 20),
    ('switch', 15), ('template', 20), ('this', 15), ('thread_local', 15), ('throw', 15),
    ('true', 15), ('try', 15), ('typedef', 20), ('typeid', 15), ('typename', 15),
    ('union', 20), ('unsigned', 15), ('using', 15), ('virtual', 15), ('void', 15),
    ('volatile', 15), ('wchar_t', 15), ('while', 15), ('xor', 15), ('xor_eq', 15),
]

_FALLBACK_HEADERS = [
    ('algorithm', 35), ('array', 35), ('atomic', 35), ('bitset', 35), ('chrono', 35),
    ('deque', 35), ('exception', 35), ('fstream', 35), ('functional', 35),
    ('future', 35), ('iostream', 35), ('map', 35), ('memory', 35), ('mutex', 35),
    ('optional', 35), ('queue', 35), ('random', 35), ('regex', 35), ('set', 35),
    ('shared_mutex', 35), ('stack', 35), ('string', 35), ('thread', 35), ('tuple', 35),
    ('unordered_map', 35), ('unordered_set', 35), ('variant', 35), ('vector', 35),
]

_FALLBACK_BUILTINS = [
    ('NULL', 30), ('nullptr', 30), ('printf', 30), ('scanf', 30), ('malloc', 30),
    ('calloc', 30), ('free', 30), ('realloc', 30), ('memcpy', 30), ('memset', 30),
    ('string', 30), ('vector', 30), ('map', 30), ('set', 30), ('pair', 30),
    ('make_pair', 30), ('make_shared', 30), ('make_unique', 30), ('move', 30),
    ('forward', 30), ('swap', 30), ('begin', 30), ('end', 30), ('size', 30),
    ('empty', 30), ('push_back', 30), ('pop_back', 30), ('insert', 30), ('erase', 30),
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
        current_line[:col]

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
                suggestions.append(SuggestionItem(label=fn, priority=_PRIORITY_USER_FUNCTION, kind='function'))
            for cls in scope.classes:
                suggestions.append(SuggestionItem(label=cls, priority=_PRIORITY_USER_CLASS, kind='class'))
            for var in scope.varibles:
                suggestions.append(SuggestionItem(label=var, priority=_PRIORITY_USER_VARIABLE, kind='variable'))

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
                suggestions.append(SuggestionItem(label=cls, priority=_PRIORITY_USER_CLASS, kind='class'))
            for fn in scope.functions:
                suggestions.append(SuggestionItem(label=fn, priority=_PRIORITY_USER_FUNCTION, kind='function'))
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
