import re

from .base import HighlightBlock, HighlighterExpert, HighlightToken

_LOG_TOKEN_RE = re.compile(
    r'(?P<timestamp>'
    r'\d{4}[-/]\d{2}[-/]\d{2}[T ]\d{2}:\d{2}:\d{2}(?:[.,]\d+)?(?:Z|[+-]\d{2}:?\d{2})?|'
    r'[A-Z][a-z]{2}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}|'
    r'\d{2}:\d{2}:\d{2}(?:[.,]\d+)?'
    r')'
    r'|(?P<level>'
    r'\b(?:CRITICAL|FATAL)\b'
    r')'
    r'|(?P<level_error>'
    r'\b(?:ERROR|SEVERE)\b'
    r')'
    r'|(?P<level_warn>'
    r'\b(?:WARN(?:ING)?|WARNING)\b'
    r')'
    r'|(?P<level_info>'
    r'\b(?:INFO|INFORMATION)\b'
    r')'
    r'|(?P<level_debug>'
    r'\b(?:DEBUG|TRACE|VERBOSE)\b'
    r')'
    r'|(?P<number>'
    r'\b\d+\b'
    r')'
    r'|(?P<keyword>\b(?:at|in|line|file|raised|Traceback|traceback)\b)'
    r'|(?P<comment>(?:Traceback|traceback).*|'
    r'\s+File\s+".*",\s+line\s+\d+.*|'
    r'\s{2,}\S.*(?::\s+\S+)?)'
)


class LogHighlighterExpert(HighlighterExpert):
    def get_languange_exts(self) -> list:
        return ['log', 'txt', 'logs']

    def highlight(self, block: HighlightBlock) -> HighlightBlock:
        tokens: list[HighlightToken] = []
        code = block.code

        for m in _LOG_TOKEN_RE.finditer(code):
            kind = m.lastgroup
            start = m.start()
            end = m.end()

            if kind == 'timestamp':
                tokens.append(HighlightToken(start, end, 'timestamp'))
            elif kind == 'level':
                tokens.append(HighlightToken(start, end, 'level_critical'))
            elif kind == 'level_error':
                tokens.append(HighlightToken(start, end, 'level_error'))
            elif kind == 'level_warn':
                tokens.append(HighlightToken(start, end, 'level_warn'))
            elif kind == 'level_info':
                tokens.append(HighlightToken(start, end, 'level_info'))
            elif kind == 'level_debug':
                tokens.append(HighlightToken(start, end, 'level_debug'))
            elif kind == 'number':
                tokens.append(HighlightToken(start, end, 'number'))
            elif kind == 'keyword':
                tokens.append(HighlightToken(start, end, 'keyword'))
            elif kind == 'comment':
                tokens.append(HighlightToken(start, end, 'comment'))

        return HighlightBlock(code=code, tokens=tokens)
