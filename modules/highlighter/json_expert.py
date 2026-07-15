import re

from .base import HighlightBlock, HighlighterExpert, HighlightToken

_JSON_KEY_VALUE_RE = re.compile(
    r'(?P<string>'
    r'"(?:[^"\\]|\\.)*"'
    r')'
    r'|(?P<number>'
    r'-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?'
    r')'
    r'|(?P<keyword>\b(?:true|false|null)\b)'
    r'|(?P<punctuation>[\[\]{}])'
    r'|(?P<operator>[:,])'
    r'|(?P<comment>//[^\n]*|/\*.*?\*/)'
)


class JsonHighlighterExpert(HighlighterExpert):
    def get_languange_exts(self) -> list:
        return ['json']

    def highlight(self, block: HighlightBlock) -> HighlightBlock:
        tokens: list[HighlightToken] = []
        code = block.code
        i = 0

        def is_key_position(pos: int) -> bool:
            scanned = code[:pos].rstrip()
            if not scanned:
                return True
            return scanned[-1] in '{,'

        for m in _JSON_KEY_VALUE_RE.finditer(code):
            kind = m.lastgroup
            start = m.start()
            end = m.end()

            if kind == 'string':
                if (is_key_position(start) and code[start:end].endswith('":')) or (is_key_position(start) and end < len(code) and code[end:end+1] == ':'):
                    tokens.append(HighlightToken(start, end, 'key'))
                else:
                    tokens.append(HighlightToken(start, end, 'string'))
            elif kind == 'number':
                tokens.append(HighlightToken(start, end, 'number'))
            elif kind == 'keyword':
                tokens.append(HighlightToken(start, end, 'keyword'))
            elif kind == 'punctuation':
                tokens.append(HighlightToken(start, end, 'punctuation'))
            elif kind == 'operator':
                tokens.append(HighlightToken(start, end, 'operator'))
            elif kind == 'comment':
                tokens.append(HighlightToken(start, end, 'comment'))

        return HighlightBlock(code=code, tokens=tokens)
