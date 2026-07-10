from .base import HighlighterExpert, HighlightBlock, HighlightToken
import re


_XML_TOKEN_RE = re.compile(
    r'(?P<comment><!--.*?-->)'
    r'|(?P<tag><(?:/[A-Za-z_:][A-Za-z0-9_:.-]*|'
    r'[A-Za-z_:][A-Za-z0-9_:.-]*(?:\s+[^>]*?)?/?>))'
    r'|(?P<string>"(?:[^"\\]|\\.)*"|'
    r"'(?:[^'\\]|\\.)*')"
    r'|(?P<entity>&[A-Za-z]+;|&#\d+;|&#x[0-9a-fA-F]+;)'
    r'|(?P<operator>=)'
    r'|(?P<punctuation>[<>/])'
)


class XmlHighlighterExpert(HighlighterExpert):
    def get_languange_exts(self) -> list:
        return ['xml', 'html', 'xhtml', 'xsd', 'xsl', 'svg']

    def highlight(self, block: HighlightBlock) -> HighlightBlock:
        tokens: list[HighlightToken] = []
        code = block.code

        for m in _XML_TOKEN_RE.finditer(code):
            kind = m.lastgroup
            start = m.start()
            end = m.end()

            if kind == 'comment':
                tokens.append(HighlightToken(start, end, 'comment'))
            elif kind == 'tag':
                token_text = m.group()
                if token_text.startswith('</') or token_text.startswith('<'):
                    tokens.append(HighlightToken(start, end, 'tag'))
                else:
                    tokens.append(HighlightToken(start, end, 'tag'))
            elif kind == 'string':
                tokens.append(HighlightToken(start, end, 'string'))
            elif kind == 'entity':
                tokens.append(HighlightToken(start, end, 'keyword'))
            elif kind == 'operator':
                tokens.append(HighlightToken(start, end, 'operator'))
            elif kind == 'punctuation':
                tokens.append(HighlightToken(start, end, 'punctuation'))

        return HighlightBlock(code=code, tokens=tokens)
