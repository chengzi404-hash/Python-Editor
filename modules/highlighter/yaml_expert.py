from .base import HighlighterExpert, HighlightBlock, HighlightToken
import re


_YAML_TOKEN_RE = re.compile(
    r'(?P<comment>#[^\n]*)'
    r'|(?P<keyword>\b(?:true|false|yes|no|on|off|null|~|True|False|Yes|No|NULL)\b)'
    r'|(?P<number>-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?)'
    r'|(?P<anchor>[&*][A-Za-z_][\w.-]*)'
    r'|(?P<tag>!![A-Za-z_][\w.]*)'
    r'|(?P<operator>: |- |\? )'
    r'|(?P<punctuation>[\[\]{}|>,])'
    r'|(?P<key>(?:[A-Za-z_][\w .-]*?)(?=\s*:))'
)


class YamlHighlighterExpert(HighlighterExpert):
    def get_languange_exts(self) -> list:
        return ['yaml', 'yml']

    def highlight(self, block: HighlightBlock) -> HighlightBlock:
        tokens: list[HighlightToken] = []
        code = block.code

        pos = 0
        for m in _YAML_TOKEN_RE.finditer(code):
            start = m.start()
            end = m.end()

            if start > pos:
                text_between = code[pos:start]

            kind = m.lastgroup
            if kind == 'comment':
                tokens.append(HighlightToken(start, end, 'comment'))
            elif kind == 'keyword':
                tokens.append(HighlightToken(start, end, 'keyword'))
            elif kind == 'number':
                tokens.append(HighlightToken(start, end, 'number'))
            elif kind == 'anchor':
                tokens.append(HighlightToken(start, end, 'preprocessor'))
            elif kind == 'tag':
                tokens.append(HighlightToken(start, end, 'type'))
            elif kind == 'operator':
                tokens.append(HighlightToken(start, end, 'operator'))
            elif kind == 'punctuation':
                tokens.append(HighlightToken(start, end, 'punctuation'))
            elif kind == 'key':
                tokens.append(HighlightToken(start, end, 'key'))

            pos = end

        return HighlightBlock(code=code, tokens=tokens)
