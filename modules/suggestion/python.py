import json
import os
import re

from modules.data import suggestions_path
from modules.highlighter.dom_cache import LibraryDOM, cache_exists, get_lib_dom
from modules.i18n import get_translator

from .base import DOMScope, SuggestionBlock, SuggestionExpert, SuggestionItem

# Priority constants (lower = higher priority)
# User-defined items take highest priority
_PRIORITY_USER_FUNCTION = 5
_PRIORITY_USER_VARIABLE = 10
_PRIORITY_IMPORT_FROM = 12  # items from imported module (before keywords)
_PRIORITY_KEYWORD = 15
_PRIORITY_USER_CLASS = 20
_PRIORITY_BUILTIN = 30

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
        filepath = suggestions_path("python", f"{category}_{lang_code}.json")
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
                            priority = item.get("priority", _PRIORITY_BUILTIN)
                        else:
                            label = item
                            priority = _PRIORITY_BUILTIN
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
# Format: (label, priority)
_FALLBACK_KEYWORDS = [
    ("False", 15),
    ("None", 15),
    ("True", 15),
    ("and", 15),
    ("as", 15),
    ("assert", 15),
    ("async", 15),
    ("await", 15),
    ("break", 15),
    ("class", 20),
    ("continue", 15),
    ("def", 20),
    ("del", 15),
    ("elif", 15),
    ("else", 15),
    ("except", 15),
    ("finally", 15),
    ("for", 15),
    ("from", 15),
    ("global", 15),
    ("if", 15),
    ("import", 15),
    ("in", 15),
    ("is", 15),
    ("lambda", 16),
    ("nonlocal", 15),
    ("not", 15),
    ("or", 15),
    ("pass", 15),
    ("raise", 15),
    ("return", 15),
    ("try", 15),
    ("while", 15),
    ("with", 15),
    ("yield", 15),
]

_FALLBACK_BUILTINS = [
    # Builtin functions
    ("abs", 30),
    ("all", 30),
    ("any", 30),
    ("ascii", 30),
    ("bin", 30),
    ("breakpoint", 30),
    ("callable", 30),
    ("chr", 30),
    ("compile", 30),
    ("delattr", 30),
    ("dir", 30),
    ("divmod", 30),
    ("eval", 30),
    ("exec", 30),
    ("format", 30),
    ("getattr", 30),
    ("globals", 30),
    ("hasattr", 30),
    ("hash", 30),
    ("help", 30),
    ("hex", 30),
    ("id", 30),
    ("input", 30),
    ("isinstance", 30),
    ("issubclass", 30),
    ("len", 30),
    ("locals", 30),
    ("max", 30),
    ("min", 30),
    ("next", 30),
    ("oct", 30),
    ("open", 30),
    ("ord", 30),
    ("pow", 30),
    ("print", 30),
    ("repr", 30),
    ("round", 30),
    ("setattr", 30),
    ("sorted", 30),
    ("sum", 30),
    ("vars", 30),
    ("__import__", 30),
    # Builtin classes
    ("bool", 30),
    ("bytearray", 30),
    ("bytes", 30),
    ("classmethod", 30),
    ("complex", 30),
    ("dict", 30),
    ("enumerate", 30),
    ("filter", 30),
    ("float", 30),
    ("frozenset", 30),
    ("int", 30),
    ("list", 30),
    ("map", 30),
    ("memoryview", 30),
    ("object", 30),
    ("property", 30),
    ("range", 30),
    ("reversed", 30),
    ("set", 30),
    ("slice", 30),
    ("staticmethod", 30),
    ("str", 30),
    ("super", 30),
    ("tuple", 30),
    ("zip", 30),
    # Builtin constants
    ("Ellipsis", 30),
    ("NotImplemented", 30),
    ("__name__", 30),
    ("__file__", 30),
    ("__doc__", 30),
    ("__package__", 30),
    ("__loader__", 30),
    ("__spec__", 30),
    ("__path__", 30),
    ("__all__", 30),
]

_FALLBACKS = {
    "keywords": _FALLBACK_KEYWORDS,
    "builtins": _FALLBACK_BUILTINS,
}

# Exported builtin sets for public API (used by tests and external consumers)
KEYWORDS: set[str] = {k for k, _ in _FALLBACK_KEYWORDS}

BUILTIN_FUNCTIONS: set[str] = {
    "abs",
    "all",
    "any",
    "ascii",
    "bin",
    "breakpoint",
    "callable",
    "chr",
    "compile",
    "delattr",
    "dir",
    "divmod",
    "eval",
    "exec",
    "format",
    "getattr",
    "globals",
    "hasattr",
    "hash",
    "help",
    "hex",
    "id",
    "input",
    "isinstance",
    "issubclass",
    "len",
    "locals",
    "max",
    "min",
    "next",
    "oct",
    "open",
    "ord",
    "pow",
    "print",
    "repr",
    "round",
    "setattr",
    "sorted",
    "sum",
    "vars",
    "__import__",
}

BUILTIN_CLASSES: set[str] = {
    "bool",
    "bytearray",
    "bytes",
    "classmethod",
    "complex",
    "dict",
    "enumerate",
    "filter",
    "float",
    "frozenset",
    "int",
    "list",
    "map",
    "memoryview",
    "object",
    "property",
    "range",
    "reversed",
    "set",
    "slice",
    "staticmethod",
    "str",
    "super",
    "tuple",
    "zip",
}

BUILTIN_PROPERTIES: set[str] = {
    "True",
    "False",
    "None",
    "Ellipsis",
    "NotImplemented",
    "__name__",
    "__file__",
    "__doc__",
    "__package__",
    "__loader__",
    "__spec__",
    "__path__",
    "__all__",
}


# Builtin attributes per type
BUILTIN_ATTRS: dict[str, list[str]] = {
    "str": [
        "__add__",
        "__class__",
        "__contains__",
        "__delattr__",
        "__dir__",
        "__doc__",
        "__eq__",
        "__format__",
        "__ge__",
        "__getattribute__",
        "__getitem__",
        "__getnewargs__",
        "__gt__",
        "__hash__",
        "__init__",
        "__iter__",
        "__le__",
        "__len__",
        "__lt__",
        "__mod__",
        "__mul__",
        "__ne__",
        "__new__",
        "__reduce__",
        "__reduce_ex__",
        "__repr__",
        "__rmod__",
        "__rmul__",
        "__setattr__",
        "__sizeof__",
        "__str__",
        "__subclasshook__",
        "capitalize",
        "casefold",
        "center",
        "count",
        "encode",
        "endswith",
        "expandtabs",
        "find",
        "format",
        "format_map",
        "index",
        "isalnum",
        "isalpha",
        "isascii",
        "isdecimal",
        "isdigit",
        "isidentifier",
        "islower",
        "isnumeric",
        "isprintable",
        "isspace",
        "istitle",
        "isupper",
        "join",
        "ljust",
        "lower",
        "lstrip",
        "maketrans",
        "partition",
        "removeprefix",
        "removesuffix",
        "replace",
        "rfind",
        "rindex",
        "rjust",
        "rpartition",
        "rsplit",
        "rstrip",
        "split",
        "splitlines",
        "startswith",
        "strip",
        "swapcase",
        "title",
        "translate",
        "upper",
        "zfill",
    ],
    "list": [
        "__add__",
        "__class__",
        "__contains__",
        "__delattr__",
        "__delitem__",
        "__dir__",
        "__doc__",
        "__eq__",
        "__format__",
        "__ge__",
        "__getattribute__",
        "__getitem__",
        "__gt__",
        "__hash__",
        "__iadd__",
        "__imul__",
        "__init__",
        "__iter__",
        "__le__",
        "__len__",
        "__lt__",
        "__mul__",
        "__ne__",
        "__new__",
        "__reduce__",
        "__reduce_ex__",
        "__repr__",
        "__reversed__",
        "__rmul__",
        "__setattr__",
        "__setitem__",
        "__sizeof__",
        "__str__",
        "__subclasshook__",
        "append",
        "clear",
        "copy",
        "count",
        "extend",
        "index",
        "insert",
        "pop",
        "remove",
        "reverse",
        "sort",
    ],
    "dict": [
        "__class__",
        "__contains__",
        "__delattr__",
        "__delitem__",
        "__dir__",
        "__doc__",
        "__eq__",
        "__format__",
        "__ge__",
        "__getattribute__",
        "__getitem__",
        "__gt__",
        "__hash__",
        "__init__",
        "__iter__",
        "__le__",
        "__len__",
        "__lt__",
        "__ne__",
        "__new__",
        "__reduce__",
        "__reduce_ex__",
        "__repr__",
        "__setattr__",
        "__setitem__",
        "__sizeof__",
        "__str__",
        "__subclasshook__",
        "clear",
        "copy",
        "fromkeys",
        "get",
        "items",
        "keys",
        "pop",
        "popitem",
        "setdefault",
        "update",
        "values",
    ],
    "int": [
        "__abs__",
        "__add__",
        "__and__",
        "__bool__",
        "__ceil__",
        "__class__",
        "__delattr__",
        "__dir__",
        "__divmod__",
        "__doc__",
        "__eq__",
        "__float__",
        "__floor__",
        "__floordiv__",
        "__format__",
        "__ge__",
        "__getattribute__",
        "__getnewargs__",
        "__gt__",
        "__hash__",
        "__index__",
        "__init__",
        "__int__",
        "__invert__",
        "__le__",
        "__lshift__",
        "__lt__",
        "__mod__",
        "__mul__",
        "__ne__",
        "__neg__",
        "__new__",
        "__or__",
        "__pos__",
        "__pow__",
        "__radd__",
        "__rand__",
        "__rdivmod__",
        "__reduce__",
        "__reduce_ex__",
        "__repr__",
        "__rfloordiv__",
        "__rlshift__",
        "__rmod__",
        "__rmul__",
        "__ror__",
        "__round__",
        "__rpow__",
        "__rrshift__",
        "__rshift__",
        "__rsub__",
        "__rtruediv__",
        "__rxor__",
        "__setattr__",
        "__sizeof__",
        "__str__",
        "__sub__",
        "__subclasshook__",
        "__truediv__",
        "__trunc__",
        "__xor__",
        "as_integer_ratio",
        "bit_count",
        "bit_length",
        "conjugate",
        "denominator",
        "from_bytes",
        "imag",
        "numerator",
        "real",
        "to_bytes",
    ],
    "float": [
        "__abs__",
        "__add__",
        "__bool__",
        "__ceil__",
        "__class__",
        "__delattr__",
        "__dir__",
        "__divmod__",
        "__doc__",
        "__eq__",
        "__float__",
        "__floor__",
        "__floordiv__",
        "__format__",
        "__ge__",
        "__getattribute__",
        "__getnewargs__",
        "__gt__",
        "__hash__",
        "__init__",
        "__int__",
        "__le__",
        "__lt__",
        "__mod__",
        "__mul__",
        "__ne__",
        "__neg__",
        "__new__",
        "__pos__",
        "__pow__",
        "__radd__",
        "__rdivmod__",
        "__reduce__",
        "__reduce_ex__",
        "__repr__",
        "__rfloordiv__",
        "__rmod__",
        "__rmul__",
        "__round__",
        "__rpow__",
        "__rsub__",
        "__rtruediv__",
        "__setattr__",
        "__sizeof__",
        "__str__",
        "__sub__",
        "__subclasshook__",
        "__truediv__",
        "__trunc__",
        "as_integer_ratio",
        "conjugate",
        "fromhex",
        "hex",
        "imag",
        "is_integer",
        "real",
    ],
    "set": [
        "__and__",
        "__class__",
        "__contains__",
        "__delattr__",
        "__dir__",
        "__doc__",
        "__eq__",
        "__format__",
        "__ge__",
        "__getattribute__",
        "__gt__",
        "__hash__",
        "__iand__",
        "__init__",
        "__ior__",
        "__isub__",
        "__iter__",
        "__ixor__",
        "__le__",
        "__len__",
        "__lt__",
        "__ne__",
        "__new__",
        "__or__",
        "__rand__",
        "__reduce__",
        "__reduce_ex__",
        "__repr__",
        "__ror__",
        "__rsub__",
        "__rxor__",
        "__setattr__",
        "__sizeof__",
        "__str__",
        "__sub__",
        "__subclasshook__",
        "__xor__",
        "add",
        "clear",
        "copy",
        "difference",
        "difference_update",
        "discard",
        "intersection",
        "intersection_update",
        "isdisjoint",
        "issubset",
        "issuperset",
        "pop",
        "remove",
        "symmetric_difference",
        "symmetric_difference_update",
        "union",
        "update",
    ],
    "tuple": [
        "__add__",
        "__class__",
        "__contains__",
        "__delattr__",
        "__dir__",
        "__doc__",
        "__eq__",
        "__format__",
        "__ge__",
        "__getattribute__",
        "__getitem__",
        "__getnewargs__",
        "__gt__",
        "__hash__",
        "__init__",
        "__iter__",
        "__le__",
        "__len__",
        "__lt__",
        "__mul__",
        "__ne__",
        "__new__",
        "__reduce__",
        "__reduce_ex__",
        "__repr__",
        "__rmul__",
        "__setattr__",
        "__sizeof__",
        "__str__",
        "__subclasshook__",
        "count",
        "index",
    ],
    "bytes": [
        "__add__",
        "__class__",
        "__contains__",
        "__delattr__",
        "__dir__",
        "__doc__",
        "__eq__",
        "__format__",
        "__ge__",
        "__getattribute__",
        "__getitem__",
        "__getnewargs__",
        "__gt__",
        "__hash__",
        "__init__",
        "__iter__",
        "__le__",
        "__len__",
        "__lt__",
        "__mod__",
        "__mul__",
        "__ne__",
        "__new__",
        "__reduce__",
        "__reduce_ex__",
        "__repr__",
        "__rmod__",
        "__rmul__",
        "__setattr__",
        "__sizeof__",
        "__str__",
        "__subclasshook__",
        "capitalize",
        "center",
        "count",
        "decode",
        "endswith",
        "expandtabs",
        "find",
        "fromhex",
        "hex",
        "index",
        "isalnum",
        "isalpha",
        "isascii",
        "isdigit",
        "islower",
        "isspace",
        "istitle",
        "isupper",
        "join",
        "ljust",
        "lower",
        "lstrip",
        "maketrans",
        "partition",
        "removeprefix",
        "removesuffix",
        "replace",
        "rfind",
        "rindex",
        "rjust",
        "rpartition",
        "rsplit",
        "rstrip",
        "split",
        "splitlines",
        "startswith",
        "strip",
        "swapcase",
        "title",
        "translate",
        "upper",
        "zfill",
    ],
    "bool": [
        "__abs__",
        "__add__",
        "__and__",
        "__bool__",
        "__ceil__",
        "__class__",
        "__delattr__",
        "__dir__",
        "__divmod__",
        "__doc__",
        "__eq__",
        "__float__",
        "__floor__",
        "__floordiv__",
        "__format__",
        "__ge__",
        "__getattribute__",
        "__getnewargs__",
        "__gt__",
        "__hash__",
        "__index__",
        "__init__",
        "__int__",
        "__invert__",
        "__le__",
        "__lshift__",
        "__lt__",
        "__mod__",
        "__mul__",
        "__ne__",
        "__neg__",
        "__new__",
        "__or__",
        "__pos__",
        "__pow__",
        "__radd__",
        "__rand__",
        "__rdivmod__",
        "__reduce__",
        "__reduce_ex__",
        "__repr__",
        "__rfloordiv__",
        "__rlshift__",
        "__rmod__",
        "__rmul__",
        "__ror__",
        "__round__",
        "__rpow__",
        "__rrshift__",
        "__rshift__",
        "__rsub__",
        "__rtruediv__",
        "__rxor__",
        "__setattr__",
        "__sizeof__",
        "__str__",
        "__sub__",
        "__subclasshook__",
        "__truediv__",
        "__trunc__",
        "__xor__",
    ],
}

# Regex patterns
CLASS_PATTERN = re.compile(
    r"^[ \t]*"
    r"class\s+"
    r"(?P<name>[A-Za-z_][A-Za-z0-9_]*)"
    r"\s*"
    r"(?:\([^()]*\))?"
    r"\s*"
    r":",
    re.MULTILINE,
)

FUNC_PATTERN = re.compile(
    r"^[ \t]*"
    r"(?:async\s+)?"
    r"def\s+"
    r"(?P<name>[A-Za-z_][A-Za-z0-9_]*)"
    r"\s*"
    r"\([^()]*\)"
    r"\s*"
    r"(?:->\s*[^:]*)?"
    r":",
    re.MULTILINE,
)


class PythonSuggestionExpert(SuggestionExpert):
    def __init__(self, lang: str = "en_US") -> None:
        super().__init__()
        self._lang = lang

    def get_languange_exts(self) -> list:
        return ["py"]

    def suggest(self, block: SuggestionBlock) -> list[SuggestionItem]:
        code = block.code
        pos = block.position

        text_before = code[:pos]
        line_no = text_before.count("\n")
        line_start = text_before.rfind("\n") + 1 if "\n" in text_before else 0
        col = pos - line_start

        lines = code.split("\n")
        current_line = lines[line_no] if line_no < len(lines) else ""
        before_cursor = current_line[:col]

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
            # For dotted paths like os.path, obj_name is just 'path' — reconstruct full path
            # by walking back through all dotted segments before it
            full_obj_name = obj_name
            if obj_start > 0 and current_line[obj_start] == ".":
                # obj_start is index of first char after the dot before obj_name
                # Walk back through identifier/dot sequences
                p = obj_start - 1
                while p >= 0 and (
                    current_line[p].isalnum() or current_line[p] == "_" or current_line[p] == "."
                ):
                    p -= 1
                p += 1
                full_path = current_line[p:obj_end].lstrip()
                if "." in full_path and any(c.isalnum() for c in full_path):
                    full_obj_name = full_path
            # Only proceed with attribute suggestions if we got a valid identifier name
            if full_obj_name and any(c.isalnum() for c in full_obj_name):
                suggestions = self._suggest_attributes(block, line_no, full_obj_name, before_cursor)
            else:
                suggestions = self._suggest_names(block, line_no)
        else:
            suggestions = self._suggest_names(block, line_no)

        # Filter by prefix — only when prefix looks like an identifier being typed
        # Skip filtering when prefix is a Python keyword (e.g., after 'from os import'
        # the prefix 'import' would filter out everything meaningful)
        if prefix and prefix.lower() not in KEYWORDS:
            suggestions = [s for s in suggestions if s.label.lower().startswith(prefix.lower())]

        # Sort by priority then alphabetically (case-insensitive)
        suggestions.sort(key=lambda x: (x.priority, x.label.lower()))

        return suggestions

    def _suggest_names(self, block: SuggestionBlock, line_no: int) -> list[SuggestionItem]:
        suggestions: list[SuggestionItem] = []

        # Load from data files with per-item priorities (use current language)
        lang = get_translator().current_language
        keywords = _load_suggestion_list(lang, "keywords")
        builtins = _load_suggestion_list(lang, "builtins")

        for label, priority in keywords:
            suggestions.append(SuggestionItem(label=label, priority=priority, kind="keyword"))
        for label, priority in builtins:
            suggestions.append(SuggestionItem(label=label, priority=priority, kind="builtin"))

        # Handle "from X import" — suggest names from the imported module
        self._add_import_from_suggestions(block, line_no, suggestions)

        # Extract user-defined items from scope
        root = self._build_scope_tree(block.code)

        def _walk(scope: DOMScope, pos: int) -> None:
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

            vars_in_scope = self._extract_variables(block.code, scope.begin, scope.end)
            for var in vars_in_scope:
                suggestions.append(
                    SuggestionItem(label=var, priority=_PRIORITY_USER_VARIABLE, kind="variable")
                )

            for sub in scope.subDOM:
                if sub.begin <= pos < sub.end:
                    _walk(sub, pos)
                    break

        _walk(root, line_no)
        return suggestions

    def _add_import_from_suggestions(
        self, block: SuggestionBlock, line_no: int, suggestions: list[SuggestionItem]
    ) -> None:
        """Detect 'from X import' lines across the whole file and add suggestions from module X's DOM.

        Only uses cached DOM entries (never scans at suggestion time) to keep suggestions snappy.
        Run ``build_full_cache()`` ahead of time to populate the cache for all installed packages.
        """
        lines = block.code.split("\n")
        # Scan all lines for import statements, not just the current line
        seen_modules: set[str] = set()
        for line in lines:
            stripped = line.strip()
            # Match "from <module> import" — module may be dotted like os.path
            # Also match "from <module> import *" (wildcard import)
            m = re.match(r"^from\s+([A-Za-z_][A-Za-z0-9_.]*)\s+import\b", stripped)
            if not m:
                continue
            module_name = m.group(1)
            if module_name in seen_modules:
                continue
            seen_modules.add(module_name)
            # Only use cached DOM — no scanning at suggestion time (could hang on heavy modules like tkinter)
            dom = get_lib_dom(module_name)
            if dom is None:
                continue
            # Add submodule names (some are real pkgutil-discovered, others are assignments like os.path)
            for sub in dom.submodules:
                suggestions.append(
                    SuggestionItem(label=sub, priority=_PRIORITY_IMPORT_FROM, kind="module")
                )
            # Special case: os.path is a well-known module assignment not discoverable by pkgutil
            if module_name == "os" and "path" not in dom.submodules:
                suggestions.append(
                    SuggestionItem(label="path", priority=_PRIORITY_IMPORT_FROM, kind="module")
                )
            for fn in dom.functions:
                suggestions.append(
                    SuggestionItem(label=fn, priority=_PRIORITY_IMPORT_FROM, kind="function")
                )
            for cls in dom.classes:
                suggestions.append(
                    SuggestionItem(label=cls, priority=_PRIORITY_IMPORT_FROM, kind="class")
                )

    def _suggest_attributes(
        self, block: SuggestionBlock, line_no: int, obj_name: str, before_cursor: str = ""
    ) -> list[SuggestionItem]:
        if obj_name == "self":
            cls_methods = self._enclosing_class_methods(block, line_no)
            if cls_methods:
                return [
                    SuggestionItem(label=m, priority=_PRIORITY_USER_FUNCTION, kind="method")
                    for m in cls_methods
                ]

        if obj_name in BUILTIN_ATTRS:
            return [
                SuggestionItem(label=a, priority=_PRIORITY_BUILTIN, kind="attribute")
                for a in BUILTIN_ATTRS[obj_name]
            ]

        if obj_name in ["str", "list", "dict", "int", "float", "set", "tuple", "bytes", "bool"]:
            return [
                SuggestionItem(label=a, priority=_PRIORITY_BUILTIN, kind="attribute")
                for a in BUILTIN_ATTRS.get(obj_name, [])
            ]

        # Try to resolve via DOM cache for imported external modules
        # Check for dotted paths like os.path → resolve inner module via cache
        dom: LibraryDOM | None = None
        parts = obj_name.rsplit(".", 1)

        # Special case: os.path is a real module (ntpath/posixpath) not discoverable by pkgutil
        if obj_name == "os.path":
            try:
                import os.path as opath

                public = getattr(opath, "__all__", [n for n in dir(opath) if not n.startswith("_")])
                suggestions = []
                for name in public:
                    try:
                        attr = getattr(opath, name)
                    except Exception:
                        continue
                    if isinstance(attr, type):
                        suggestions.append(
                            SuggestionItem(label=name, priority=_PRIORITY_BUILTIN, kind="class")
                        )
                    elif callable(attr):
                        suggestions.append(
                            SuggestionItem(label=name, priority=_PRIORITY_BUILTIN, kind="function")
                        )
                if suggestions:
                    return suggestions
            except Exception:
                pass

        if len(parts) == 2 and cache_exists(parts[0]):
            # obj_name is like "os.path" — first load parent module, then look up submodule
            parent_dom = get_lib_dom(parts[0])
            if parent_dom is not None and parts[1] in parent_dom.submodule_contents:
                sub_info = parent_dom.submodule_contents[parts[1]]
                suggestions: list[SuggestionItem] = []
                for fn in sub_info.get("functions", []):
                    suggestions.append(
                        SuggestionItem(label=fn, priority=_PRIORITY_BUILTIN, kind="function")
                    )
                for cls in sub_info.get("classes", []):
                    suggestions.append(
                        SuggestionItem(label=cls, priority=_PRIORITY_BUILTIN, kind="class")
                    )
                if suggestions:
                    return suggestions
            # Fall through: try direct lookup as single-level module name
            obj_name = parts[0]

        # Try to load from cache only — no scanning at suggestion time (avoids hangs on heavy modules)
        dom = get_lib_dom(obj_name)
        if dom is None and len(parts) == 2:
            # Couldn't find parent, try the full dotted name (e.g., package.submodule)
            dom = get_lib_dom(obj_name)

        if dom is not None:
            suggestions = []
            for fn in dom.functions:
                suggestions.append(
                    SuggestionItem(label=fn, priority=_PRIORITY_BUILTIN, kind="function")
                )
            for cls in dom.classes:
                suggestions.append(
                    SuggestionItem(label=cls, priority=_PRIORITY_BUILTIN, kind="class")
                )
            for sub in dom.submodules:
                suggestions.append(
                    SuggestionItem(label=sub, priority=_PRIORITY_BUILTIN, kind="module")
                )
            # Special case: os.path is a well-known module assignment not discoverable by pkgutil
            if obj_name == "os" and "path" not in dom.submodules:
                suggestions.append(
                    SuggestionItem(label="path", priority=_PRIORITY_BUILTIN, kind="module")
                )
            if suggestions:
                return suggestions

        # Default object attributes
        default_attrs = [
            "__class__",
            "__delattr__",
            "__dir__",
            "__doc__",
            "__eq__",
            "__format__",
            "__ge__",
            "__getattribute__",
            "__gt__",
            "__hash__",
            "__init__",
            "__le__",
            "__lt__",
            "__ne__",
            "__new__",
            "__reduce__",
            "__reduce_ex__",
            "__repr__",
            "__setattr__",
            "__sizeof__",
            "__str__",
            "__subclasshook__",
        ]
        return [
            SuggestionItem(label=a, priority=_PRIORITY_BUILTIN, kind="attribute")
            for a in default_attrs
        ]

    def _enclosing_class_methods(self, block: SuggestionBlock, line_no: int) -> list[str]:
        lines = block.code.split("\n")

        start_line = line_no
        while start_line >= 0:
            line = lines[start_line]
            m = re.match(r"^[ \t]*class\s+([A-Za-z_][A-Za-z0-9_]*)\s*(?:\([^()]*\))?\s*:", line)
            if m:
                class_indent = len(line) - len(line.lstrip())
                break
            start_line -= 1
        else:
            return []

        methods = []
        for i in range(start_line + 1, len(lines)):
            line = lines[i]
            line_stripped = line.lstrip()
            if not line_stripped or line_stripped.startswith("#"):
                continue
            indent = len(line) - len(line_stripped)
            if indent <= class_indent and line_stripped.startswith("class"):
                break
            if indent > class_indent:
                m = re.match(r"^[ \t]*def\s+([A-Za-z_][A-Za-z0-9_]*)", line)
                if m:
                    methods.append(m.group(1))

        if not methods:
            return []

        return [
            *methods,
            "__class__",
            "__delattr__",
            "__dir__",
            "__doc__",
            "__eq__",
            "__format__",
            "__ge__",
            "__getattribute__",
            "__gt__",
            "__hash__",
            "__init__",
            "__le__",
            "__lt__",
            "__ne__",
            "__new__",
            "__reduce__",
            "__reduce_ex__",
            "__repr__",
            "__setattr__",
            "__sizeof__",
            "__str__",
            "__subclasshook__",
        ]

    @staticmethod
    def _extract_variables(code: str, begin: int, end: int) -> list[str]:
        lines = code.split("\n")
        segment = "\n".join(lines[begin:end]) if begin < len(lines) else ""
        vars_found = set()

        for m in re.finditer(
            r"(?:^|[;\n])\s*([A-Za-z_][A-Za-z0-9_]*)\s*(?::\s*[^=]+)?\s*=\s*", segment
        ):
            vars_found.add(m.group(1))

        for m in re.finditer(r"\bfor\s+([A-Za-z_][A-Za-z0-9_]*)\s+in\b", segment):
            vars_found.add(m.group(1))

        for m in re.finditer(r"\bwith\s+[^:]*\s+as\s+([A-Za-z_][A-Za-z0-9_]*)", segment):
            vars_found.add(m.group(1))

        for m in re.finditer(r"\bexcept\s+[^:]*\s+as\s+([A-Za-z_][A-Za-z0-9_]*)", segment):
            vars_found.add(m.group(1))

        for m in re.finditer(r"\bdef\s+\w+\s*\(([^)]*)\)", segment):
            args = m.group(1)
            for arg in args.split(","):
                arg = arg.strip().split(":")[0].split("=")[0].strip()
                if arg:
                    vars_found.add(arg)
                    vars_found.add("self")
                    vars_found.add("cls")

        return list(vars_found)

    @staticmethod
    def _collect_entries(code: str) -> list[tuple[int, int, str, str, int]]:
        total_lines = code.count("\n") + 1

        entries = []
        for pattern, kind in ((CLASS_PATTERN, "class"), (FUNC_PATTERN, "function")):
            for m in pattern.finditer(code):
                line_no = code[: m.start()].count("\n")
                indent = len(m.group()) - len(m.group().lstrip())
                name = m.group("name")
                entries.append((line_no, indent, kind, name, 0))
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
    def iter_classes(block: SuggestionBlock) -> list[str]:
        return [
            name
            for _, _, kind, name, _ in PythonSuggestionExpert._collect_entries(block.code)
            if kind == "class"
        ]

    @staticmethod
    def iter_function(block: SuggestionBlock) -> list[str]:
        return [
            name
            for _, _, kind, name, _ in PythonSuggestionExpert._collect_entries(block.code)
            if kind == "function"
        ]

    @staticmethod
    def _build_scope_tree(code: str) -> DOMScope:
        entries = PythonSuggestionExpert._collect_entries(code)
        if not entries:
            return DOMScope(
                begin=0, end=code.count("\n") + 1, varibles=[], functions=[], classes=[], subDOM=[]
            )

        total_lines = entries[-1][4]

        root = DOMScope(begin=0, end=total_lines, varibles=[], functions=[], classes=[], subDOM=[])
        stack = [(root, -1)]

        for line_no, indent, kind, name, end in entries:
            while stack and stack[-1][1] >= indent:
                stack.pop()

            parent = stack[-1][0]
            scope = DOMScope(
                begin=line_no, end=end, varibles=[], functions=[], classes=[], subDOM=[]
            )

            if kind == "class":
                parent.classes.append(name)
            else:
                parent.functions.append(name)

            parent.subDOM.append(scope)
            stack.append((scope, indent))

        return root

    @staticmethod
    def find_domin(block: SuggestionBlock, position: int) -> DOMScope:
        root = PythonSuggestionExpert._build_scope_tree(block.code)

        def _deepest(scope: DOMScope, pos: int) -> DOMScope:
            for sub in scope.subDOM:
                if sub.begin <= pos < sub.end:
                    return _deepest(sub, pos)
            return scope

        return _deepest(root, position)
