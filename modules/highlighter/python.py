import json
import os
import re

from .base import HighlightBlock, HighlighterExpert, HighlightToken
from .dom_cache import LibraryDOM, cache_exists, get_or_load_lib_dom

_KEYWORDS: set[str] = set()
_KEYWORDS_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'keywords', 'python.json')
try:
    with open(_KEYWORDS_PATH, encoding='utf-8') as _f:
        _KEYWORDS.update(json.load(_f))
except (FileNotFoundError, json.JSONDecodeError):
    _KEYWORDS.update([
        'False', 'None', 'True', 'and', 'as', 'assert', 'async', 'await',
        'break', 'class', 'continue', 'def', 'del', 'elif', 'else', 'except',
        'finally', 'for', 'from', 'global', 'if', 'import', 'in', 'is',
        'lambda', 'match', 'case', 'nonlocal', 'not', 'or', 'pass', 'raise',
        'return', 'try', 'type', 'while', 'with', 'yield',
    ])

_BUILTINS: set[str] = {
    'abs', 'all', 'any', 'bin', 'bool', 'bytearray', 'bytes', 'callable',
    'chr', 'classmethod', 'compile', 'complex', 'delattr', 'dict', 'dir',
    'divmod', 'enumerate', 'eval', 'exec', 'filter', 'float', 'format',
    'frozenset', 'getattr', 'globals', 'hasattr', 'hash', 'help', 'hex',
    'id', 'input', 'int', 'isinstance', 'issubclass', 'iter', 'len', 'list',
    'locals', 'map', 'max', 'memoryview', 'min', 'next', 'object', 'oct',
    'open', 'ord', 'pow', 'print', 'property', 'range', 'repr', 'reversed',
    'round', 'set', 'setattr', 'slice', 'sorted', 'staticmethod', 'str',
    'sum', 'super', 'tuple', 'type', 'vars', 'zip', '__import__',
}

_STR_PREFIX = r'(?:[rR][bBfF]|[bBfF][rR]|[bBuUfFrR])?'

_TOKEN_RE = re.compile(
    f'(?P<string>'
    f'{_STR_PREFIX}"""(?:[^"\\\\]|\\\\.|"(?!""))*"""|'
    f'{_STR_PREFIX}\'\'\'(?:[^\'\\\\]|\\\\.|\'(?!\'\'))*\'\'\'|'
    f'{_STR_PREFIX}"(?:[^"\\\\]|\\\\.)*"|'
    f"{_STR_PREFIX}'(?:[^'\\\\]|\\\\.)*'"
    r')'
    r'|(?P<comment>#.*)'
    r'|(?P<decorator>@[A-Za-z_][A-Za-z0-9_.]*)'
    r'|(?P<number>'
    r'0[xX][0-9a-fA-F_]+l?|'
    r'0[bB][01_]+l?|'
    r'0[oO][0-7_]+l?|'
    r'\d+(?:\.\d+)?(?:[eE][+-]?\d+)?[jJ]?l?|'
    r'\d+[jJ]'
    r')'
    r'|(?P<module_attr>'
    r'(?P<module_name>[A-Za-z_][A-Za-z0-9_]*)'
    r'\.(?P<attr_name>[A-Za-z_][A-Za-z0-9_]*)'
    r')'
    r'|(?P<identifier>[A-Za-z_][A-Za-z0-9_]*)'
    r'|(?P<operator>'
    r'->|\*\*=|//=|<<=|>>=|\*\*|//|<<|>>|<=|>=|==|!=|'
    r'\+=|-=|\*=|/=|%=|&=|\|=|\^=|::|[\+\-*/%=&|^~<>!]'
    r')'
    r'|(?P<punctuation>[()\[\]{}:;,.\-])'
)

# Pattern to match "from X import" — capture module X
_FROM_IMPORT_RE = re.compile(r'\bfrom\s+([A-Za-z_][A-Za-z0-9_]*)\s+import\b')

# Pattern to match "import X" — capture module X
_IMPORT_RE = re.compile(r'\bimport\s+([A-Za-z_][A-Za-z0-9_]*)')


def _resolve_module_attr(module_name: str, attr_name: str,
                          cached_libs: dict[str, LibraryDOM]) -> str | None:
    """Resolve ``module_name.attr_name`` using the DOM cache.

    Returns:
        'class'  — attr is a class in the cached DOM
        'function' — attr is a function in the cached DOM
        'module'  — attr is a submodule in the cached DOM
        None      — cannot resolve or not in cache
    """
    # Try cached DOM from this session
    dom = cached_libs.get(module_name)
    if dom is None:
        if not cache_exists(module_name):
            return None
        dom = get_or_load_lib_dom(module_name)
        if dom is None:
            return None
        cached_libs[module_name] = dom

    # Direct class / function in the top-level module
    if attr_name in dom.classes:
        return 'class'
    if attr_name in dom.functions:
        return 'function'
    if attr_name in dom.submodules:
        return 'module'

    # Check submodule contents: dom.submodule_contents[sub_name] -> {classes, functions}
    sub_contents = dom.submodule_contents
    if attr_name in sub_contents:
        return 'module'

    for sub_name, sub_info in sub_contents.items():
        classes = sub_info.get("classes", [])
        functions = sub_info.get("functions", [])
        if attr_name in classes:
            return 'class'
        if attr_name in functions:
            return 'function'

    return None


def _collect_imports(code: str) -> dict[str, LibraryDOM]:
    """Scan ``code`` for ``import X`` / ``from X import`` and pre-load DOM cache.

    Returns a dict mapping module name -> LibraryDOM for resolved modules.
    """
    cached: dict[str, LibraryDOM] = {}

    # Find all imported module names (top-level, not dotted)
    for m in _IMPORT_RE.finditer(code):
        lib_name = m.group(1).split('.')[0]
        if lib_name in cached or lib_name in _BUILTINS or lib_name in _KEYWORDS:
            continue
        if cache_exists(lib_name):
            dom = get_or_load_lib_dom(lib_name)
            if dom is not None:
                cached[lib_name] = dom

    for m in _FROM_IMPORT_RE.finditer(code):
        lib_name = m.group(1).split('.')[0]
        if lib_name in cached or lib_name in _BUILTINS or lib_name in _KEYWORDS:
            continue
        if cache_exists(lib_name):
            dom = get_or_load_lib_dom(lib_name)
            if dom is not None:
                cached[lib_name] = dom

    return cached


class PythonHighlighterExpert(HighlighterExpert):
    def __init__(self) -> None:
        super().__init__()

    def get_languange_exts(self) -> list:
        return ['py']

    def highlight(self, block: HighlightBlock) -> HighlightBlock:
        tokens = self._tokenize(block.code)
        return HighlightBlock(code=block.code, tokens=tokens)

    def _tokenize(self, code: str) -> list[HighlightToken]:
        tokens: list[HighlightToken] = []

        # Pre-load DOM for all imports in this block
        cached_libs = _collect_imports(code)

        # Track names defined in this block for later highlighting
        defined_functions: set[str] = set()
        defined_classes: set[str] = set()
        # Name immediately after def/class (pending highlight)
        pending_name: tuple[str, str, int] | None = None  # (type_, name, end_pos)

        for m in _TOKEN_RE.finditer(code):
            kind = m.lastgroup
            start = m.start()
            end = m.end()

            if kind == 'string':
                tokens.append(HighlightToken(start, end, 'string'))

            elif kind == 'comment':
                tokens.append(HighlightToken(start, end, 'comment'))

            elif kind == 'decorator':
                tokens.append(HighlightToken(start, end, 'decorator'))

            elif kind == 'number':
                tokens.append(HighlightToken(start, end, 'number'))

            elif kind == 'module_attr':
                module_name = m.group('module_name')
                attr_name = m.group('attr_name')
                resolved = _resolve_module_attr(module_name, attr_name, cached_libs)
                if resolved is not None:
                    tokens.append(HighlightToken(start, end, resolved))
                else:
                    tokens.append(HighlightToken(start, end, 'identifier'))

            elif kind == 'identifier':
                word = m.group()
                if word in _KEYWORDS:
                    tokens.append(HighlightToken(start, end, 'keyword'))
                    if word in ('def', 'class'):
                        pending_name = ('function' if word == 'def' else 'class', word, end)
                    elif word == 'from':
                        pending_name = ('module', word, end)
                    elif word == 'import':
                        # After 'import', the next name is typically a module.
                        # We can't distinguish `import os` from `import deque` (a class
                        # imported from collections) without static analysis, so we
                        # highlight it as 'module' — the most common case.
                        pending_name = ('module', word, end)
                elif word in _BUILTINS:
                    tokens.append(HighlightToken(start, end, 'builtin'))
                else:
                    # Check pending name first (name right after def/class/from/import)
                    if pending_name is not None:
                        type_, kw_word, kw_end = pending_name
                        between = code[kw_end:start]
                        if between.strip() == '':
                            if type_ == 'function':
                                defined_functions.add(word)
                            elif type_ == 'class':
                                defined_classes.add(word)
                            elif type_ == 'module':
                                # Module name after 'from' or 'import': highlight as module
                                defined_functions.add(word)
                                tokens.append(HighlightToken(start, end, 'module'))
                                pending_name = None
                                continue
                            tokens.append(HighlightToken(start, end, type_))
                            pending_name = None
                            continue
                        pending_name = None

                    # Highlight previously defined names when they are used
                    if word in defined_functions:
                        tokens.append(HighlightToken(start, end, 'function'))
                    elif word in defined_classes:
                        tokens.append(HighlightToken(start, end, 'class'))
                    else:
                        tokens.append(HighlightToken(start, end, 'identifier'))

            elif kind == 'operator':
                tokens.append(HighlightToken(start, end, 'operator'))

            elif kind == 'punctuation':
                tokens.append(HighlightToken(start, end, 'punctuation'))

        return tokens
