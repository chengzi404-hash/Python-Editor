from .base import HighlighterExpert, HighlightBlock, HighlightToken

import json
import os
import re


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
    r'|(?P<identifier>[A-Za-z_][A-Za-z0-9_]*)'
    r'|(?P<operator>'
    r'->|\*\*=|//=|<<=|>>=|\*\*|//|<<|>>|<=|>=|==|!=|'
    r'\+=|-=|\*=|/=|%=|&=|\|=|\^=|::|[\+\-*/%=&|^~<>!]'
    r')'
    r'|(?P<punctuation>[()\[\]{}:;,.\-])'
)


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

            elif kind == 'identifier':
                word = m.group()
                if word in _KEYWORDS:
                    tokens.append(HighlightToken(start, end, 'keyword'))
                    if word in ('def', 'class'):
                        pending_name = ('function' if word == 'def' else 'class', word, end)
                elif word in _BUILTINS:
                    tokens.append(HighlightToken(start, end, 'builtin'))
                else:
                    # Check pending name first (name right after def/class)
                    if pending_name is not None:
                        type_, kw_word, kw_end = pending_name
                        between = code[kw_end:start]
                        if between.strip() == '':
                            if type_ == 'function':
                                defined_functions.add(word)
                            else:
                                defined_classes.add(word)
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
