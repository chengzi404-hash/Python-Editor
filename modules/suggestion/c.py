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
    for lang_code in (lang, "en_US"):
        filepath = suggestions_path("c", f"{category}_{lang_code}.json")
        if os.path.exists(filepath):
            try:
                with open(filepath, encoding="utf-8") as f:
                    data = json.load(f)
                    items_data = data.get("items", [])
                    # Parse per-item priorities
                    result = []
                    for item in items_data:
                        if isinstance(item, dict):
                            label = item["label"]
                            priority = item.get("priority", _PRIORITY_KEYWORD)
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
    if label.startswith("__"):
        return priority + 20
    elif label.startswith("_"):
        return priority + 10
    return priority


# Fallback hardcoded suggestion lists with per-item priorities
_FALLBACK_KEYWORDS = [
    ("auto", 15),
    ("break", 15),
    ("case", 15),
    ("char", 15),
    ("const", 15),
    ("continue", 15),
    ("default", 15),
    ("do", 15),
    ("double", 15),
    ("else", 15),
    ("enum", 20),
    ("extern", 15),
    ("float", 15),
    ("for", 15),
    ("goto", 15),
    ("if", 15),
    ("inline", 15),
    ("int", 15),
    ("long", 15),
    ("register", 15),
    ("restrict", 15),
    ("return", 15),
    ("short", 15),
    ("signed", 15),
    ("sizeof", 30),
    ("static", 15),
    ("struct", 20),
    ("switch", 15),
    ("typedef", 20),
    ("union", 20),
    ("unsigned", 15),
    ("void", 15),
    ("volatile", 15),
    ("while", 15),
]

_FALLBACK_BUILTINS = [
    ("offsetof", 30),
    ("NULL", 30),
    ("printf", 30),
    ("scanf", 30),
    ("malloc", 30),
    ("calloc", 30),
    ("free", 30),
    ("realloc", 30),
    ("memcpy", 30),
    ("memmove", 30),
    ("memset", 30),
    ("memcmp", 30),
    ("strcpy", 30),
    ("strncpy", 30),
    ("strcat", 30),
    ("strncat", 30),
    ("strcmp", 30),
    ("strncmp", 30),
    ("strlen", 30),
    ("sprintf", 30),
    ("sscanf", 30),
    ("fopen", 30),
    ("fclose", 30),
    ("fread", 30),
    ("fwrite", 30),
    ("fprintf", 30),
    ("fscanf", 30),
    ("getchar", 30),
    ("putchar", 30),
    ("gets", 30),
    ("puts", 30),
    ("fgets", 30),
    ("fputs", 30),
    ("getc", 30),
    ("putc", 30),
    ("ungetc", 30),
    ("feof", 30),
    ("ferror", 30),
    ("atoi", 30),
    ("atof", 30),
    ("atol", 30),
    ("strtol", 30),
    ("strtod", 30),
    ("abs", 30),
    ("labs", 30),
    ("div", 30),
    ("exit", 30),
]

_FALLBACK_HEADERS = [
    ("assert.h", 35),
    ("ctype.h", 35),
    ("errno.h", 35),
    ("float.h", 35),
    ("limits.h", 35),
    ("math.h", 35),
    ("signal.h", 35),
    ("stdarg.h", 35),
    ("stddef.h", 35),
    ("stdint.h", 35),
    ("stdio.h", 35),
    ("stdlib.h", 35),
    ("string.h", 35),
    ("time.h", 35),
]

_FALLBACK_PREPROCESSOR = [
    ("#define", 15),
    ("#elif", 15),
    ("#else", 15),
    ("#endif", 15),
    ("#error", 15),
    ("#if", 15),
    ("#ifdef", 15),
    ("#ifndef", 15),
    ("#include", 15),
    ("#line", 15),
    ("#pragma", 15),
    ("#undef", 15),
    ("#warning", 15),
]

_FALLBACKS = {
    "keywords": _FALLBACK_KEYWORDS,
    "builtins": _FALLBACK_BUILTINS,
    "headers": _FALLBACK_HEADERS,
    "preprocessor": _FALLBACK_PREPROCESSOR,
}


# Regex patterns
_STRUCT_CLASS_PATTERN = re.compile(
    r"^[ \t]*"
    r"(?:typedef\s+)?"
    r"(?:struct|union|enum)\s+"
    r"(?:[A-Za-z_][A-Za-z0-9_]*\s+)?"
    r"\{",
    re.MULTILINE,
)

_FUNC_PATTERN = re.compile(
    r"^[ \t]*"
    r"(?:(?:inline|static|extern|const|volatile)*\s+)*"
    r"(?:[A-Za-z_][A-Za-z0-9_*\s]+?\s+)?"
    r"([A-Za-z_][A-Za-z0-9_]*)"
    r"\s*\([^()]*\)"
    r"\s*\{",
    re.MULTILINE,
)

_TYPEDEF_PATTERN = re.compile(
    r"^[ \t]*"
    r"typedef\s+"
    r"(?:struct|union|enum|class)?\s*"
    r"(?:[A-Za-z_][A-Za-z0-9_*\s]+?\s+)?"
    r"([A-Za-z_][A-Za-z0-9_]*)",
    re.MULTILINE,
)


class CSuggestionExpert(SuggestionExpert):
    def __init__(self, lang: str = "en_US") -> None:
        super().__init__()
        self._lang = lang

    def get_languange_exts(self) -> list:
        return ["c", "h"]

    def suggest(self, block: SuggestionBlock) -> list[SuggestionItem]:
        code = block.code
        pos = block.position

        text_before = code[:pos]
        line_no = text_before.count("\n")
        line_start = text_before.rfind("\n") + 1 if "\n" in text_before else 0
        col = pos - line_start

        lines = code.split("\n")
        current_line = lines[line_no] if line_no < len(lines) else ""
        current_line[:col]

        word_start = col
        while word_start > 0 and (
            current_line[word_start - 1].isalnum() or current_line[word_start - 1] == "_"
        ):
            word_start -= 1
        prefix = current_line[word_start:col]

        if word_start > 0 and current_line[word_start - 1] == ".":
            obj_end = word_start - 1
            obj_start = obj_end - 1
            while obj_start >= 0 and (
                current_line[obj_start].isalnum() or current_line[obj_start] == "_"
            ):
                obj_start -= 1
            obj_name = current_line[obj_start + 1 : obj_end]
            suggestions = self._suggest_attributes(block, line_no, obj_name)
        elif (
            word_start > 0
            and current_line[word_start - 1] == ">"
            and word_start > 1
            and current_line[word_start - 2] == "-"
        ):
            obj_end = word_start - 2
            obj_start = obj_end - 1
            while obj_start >= 0 and (
                current_line[obj_start].isalnum() or current_line[obj_start] == "_"
            ):
                obj_start -= 1
            obj_name = current_line[obj_start + 1 : obj_end]
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
        keywords = _load_suggestion_list(lang, "keywords")
        builtins = _load_suggestion_list(lang, "builtins")
        headers = _load_suggestion_list(lang, "headers")
        preprocessor = _load_suggestion_list(lang, "preprocessor")

        for label, priority in keywords:
            suggestions.append(SuggestionItem(label=label, priority=priority, kind="keyword"))
        for label, priority in builtins:
            suggestions.append(SuggestionItem(label=label, priority=priority, kind="builtin"))
        for label, priority in headers:
            suggestions.append(SuggestionItem(label=label, priority=priority, kind="header"))
        for label, priority in preprocessor:
            suggestions.append(SuggestionItem(label=label, priority=priority, kind="preprocessor"))

        # Extract user-defined items
        root = self._build_scope_tree(block.code)

        def _walk(scope: DOMScope) -> None:
            for fn in scope.functions:
                suggestions.append(
                    SuggestionItem(label=fn, priority=_PRIORITY_USER_FUNCTION, kind="function")
                )
            for cls in scope.classes:
                suggestions.append(
                    SuggestionItem(label=cls, priority=_PRIORITY_USER_CLASS, kind="class")
                )
            for var in scope.varibles:
                suggestions.append(
                    SuggestionItem(label=var, priority=_PRIORITY_USER_VARIABLE, kind="variable")
                )

            for sub in scope.sub_dom:
                _walk(sub)

        _walk(root)
        return suggestions

    def _suggest_attributes(
        self, block: SuggestionBlock, line_no: int, obj_name: str
    ) -> list[SuggestionItem]:
        attrs = [
            "x",
            "y",
            "z",
            "width",
            "height",
            "left",
            "right",
            "top",
            "bottom",
            "data",
            "next",
            "prev",
            "count",
            "size",
            "ptr",
            "buf",
            "len",
        ]
        return [
            SuggestionItem(label=a, priority=_PRIORITY_BUILTIN, kind="attribute") for a in attrs
        ]

    @staticmethod
    def _collect_entries(code: str) -> list[tuple[int, int, str, str, int]]:
        total_lines = code.count("\n") + 1

        entries: list[tuple[int, int, str, str, int]] = []

        for m in _STRUCT_CLASS_PATTERN.finditer(code):
            line_no = code[: m.start()].count("\n")
            indent = len(m.group()) - len(m.group().lstrip())
            kind = "class"
            name_match = re.search(
                r"(?:struct|union|enum)\s+([A-Za-z_][A-Za-z0-9_]*)\s*\{", m.group()
            )
            name = name_match.group(1) if name_match else m.group().strip()
            entries.append((line_no, indent, kind, name, 0))

        for m in _FUNC_PATTERN.finditer(code):
            line_no = code[: m.start()].count("\n")
            indent = len(m.group()) - len(m.group().lstrip())
            name = m.group(1)
            entries.append((line_no, indent, "function", name, 0))

        for m in _TYPEDEF_PATTERN.finditer(code):
            line_no = code[: m.start()].count("\n")
            indent = len(m.group()) - len(m.group().lstrip())
            name = m.group(1)
            entries.append((line_no, indent, "typedef", name, 0))

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
            return DOMScope(
                begin=0, end=code.count("\n") + 1, varibles=[], functions=[], classes=[], sub_dom=[]
            )

        total_lines = entries[-1][4]

        root = DOMScope(begin=0, end=total_lines, varibles=[], functions=[], classes=[], sub_dom=[])
        stack: list[tuple[DOMScope, int]] = [(root, -1)]

        for line_no, indent, kind, name, end in entries:
            while stack and stack[-1][1] >= indent:
                stack.pop()

            parent = stack[-1][0]
            scope = DOMScope(
                begin=line_no, end=end, varibles=[], functions=[], classes=[], sub_dom=[]
            )

            if kind in ("class", "typedef"):
                parent.classes.append(name)
            else:
                parent.functions.append(name)

            parent.sub_dom.append(scope)
            stack.append((scope, indent))

        return root
