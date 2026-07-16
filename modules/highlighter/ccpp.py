import json
import os
import re

from .base import HighlightBlock, HighlighterExpert, HighlightToken

_KEYWORDS: set[str] = set()
_KEYWORDS_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "data", "keywords", "c&cpp", "cpp.json"
)
try:
    with open(_KEYWORDS_PATH, encoding="utf-8") as _f:
        _KEYWORDS.update(json.load(_f))
except (FileNotFoundError, json.JSONDecodeError):
    _KEYWORDS.update(
        [
            "alignas",
            "alignof",
            "and",
            "auto",
            "bool",
            "break",
            "case",
            "catch",
            "char",
            "class",
            "const",
            "consteval",
            "constexpr",
            "constinit",
            "continue",
            "co_await",
            "co_return",
            "co_yield",
            "decltype",
            "default",
            "delete",
            "do",
            "double",
            "else",
            "enum",
            "explicit",
            "export",
            "extern",
            "false",
            "float",
            "for",
            "friend",
            "goto",
            "if",
            "inline",
            "int",
            "long",
            "mutable",
            "namespace",
            "new",
            "noexcept",
            "not",
            "nullptr",
            "operator",
            "or",
            "private",
            "protected",
            "public",
            "register",
            "reinterpret_cast",
            "requires",
            "return",
            "short",
            "signed",
            "sizeof",
            "static",
            "static_assert",
            "static_cast",
            "struct",
            "switch",
            "template",
            "this",
            "thread_local",
            "throw",
            "true",
            "try",
            "typedef",
            "typeid",
            "typename",
            "union",
            "unsigned",
            "using",
            "virtual",
            "void",
            "volatile",
            "while",
            "and_eq",
            "bitand",
            "bitor",
            "compl",
            "not_eq",
            "or_eq",
            "xor_eq",
        ]
    )

_C_KEYWORDS: set[str] = set()
_C_KEYWORDS_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "data", "keywords", "c&cpp", "c.json"
)
try:
    with open(_C_KEYWORDS_PATH, encoding="utf-8") as _f:
        _C_KEYWORDS.update(json.load(_f))
except (FileNotFoundError, json.JSONDecodeError):
    _C_KEYWORDS.update(
        [
            "auto",
            "break",
            "case",
            "char",
            "const",
            "continue",
            "default",
            "do",
            "double",
            "else",
            "enum",
            "extern",
            "float",
            "for",
            "goto",
            "if",
            "inline",
            "int",
            "long",
            "register",
            "restrict",
            "return",
            "short",
            "signed",
            "sizeof",
            "static",
            "struct",
            "switch",
            "typedef",
            "union",
            "unsigned",
            "void",
            "volatile",
            "while",
            "_Alignas",
            "_Alignof",
            "_Atomic",
            "_Bool",
            "_Complex",
            "_Generic",
            "_Imaginary",
            "_Noreturn",
            "_Static_assert",
            "_Thread_local",
            "and",
            "not",
            "or",
        ]
    )

_BUILTINS: set[str] = {
    "sizeof",
    "offsetof",
    "NULL",
    "true",
    "false",
}

_PP_KEYWORDS: set[str] = {
    "#define",
    "#elif",
    "#else",
    "#endif",
    "#error",
    "#if",
    "#ifdef",
    "#ifndef",
    "#include",
    "#line",
    "#pragma",
    "#undef",
    "#warning",
}

_STR_PREFIX = r"(?:[uUL]|[uUL][8Uu])?"

_TOKEN_RE = re.compile(
    f"(?P<string>"
    f'{_STR_PREFIX}"(?:[^"\\\\]|\\\\.)*"|'
    f"{_STR_PREFIX}'(?:[^'\\\\]|\\\\.)*'"
    r")"
    r"|(?P<comment>//.*)"
    r"|(?P<multiline>/\*[\s\S]*?\*/)"
    r"|(?P<preprocessor>"
    r"#(?:define|elif|else|endif|error|if|ifdef|ifndef|include|include_next|"
    r"line|pragma|undef|warning)\b.*|"
    r"##[A-Za-z_][A-Za-z0-9_]*"
    r")"
    r"|(?P<number>"
    r"0[xX][0-9a-fA-F_]+[uUlL]*|"
    r"0[bB][01_]+[uUlL]*|"
    r"0[0-7_]+[uUlL]*|"
    r"\d+(?:\.\d+)?(?:[eE][+-]?\d+)?[fFlL]?|"
    r"\d*[.]\d+(?:[eE][+-]?\d+)?[fFlL]?"
    r")"
    r"|(?P<identifier>[A-Za-z_][A-Za-z0-9_]*)"
    r"|(?P<operator>"
    r"->|\+\+|--|<<=|>>=|\+=|-=|\*=|/=|%=|&=|\|=|\^=|::|"
    r"\|\||&&|<<|>>|<=|>=|==|!=|"
    r"\+=|-=|\*=|/=|%=|&=|\|=|\^=|->|"
    r"[+\-*/%=<>!&|^~?:]"
    r")"
    r"|(?P<punctuation>[()\[\]{};,.\-])"
)


class CcppHighlighterExpert(HighlighterExpert):
    def __init__(self) -> None:
        super().__init__()

    def get_languange_exts(self) -> list:
        return ["c", "cpp", "cc", "cxx", "h", "hpp", "hh"]

    def highlight(self, block: HighlightBlock) -> HighlightBlock:
        tokens = self._tokenize(block.code)
        return HighlightBlock(code=block.code, tokens=tokens)

    def _tokenize(self, code: str) -> list[HighlightToken]:
        tokens: list[HighlightToken] = []
        last_struct_class: int | None = None
        in_preprocessor = False

        for _i, char in enumerate(code):
            if char == "\n" and in_preprocessor:
                in_preprocessor = False

        for m in _TOKEN_RE.finditer(code):
            kind = m.lastgroup
            start = m.start()
            end = m.end()

            if kind == "string":
                tokens.append(HighlightToken(start, end, "string"))

            elif kind == "comment" or kind == "multiline":
                tokens.append(HighlightToken(start, end, "comment"))

            elif kind == "preprocessor":
                tokens.append(HighlightToken(start, end, "preprocessor"))
                in_preprocessor = True

            elif kind == "number":
                tokens.append(HighlightToken(start, end, "number"))

            elif kind == "identifier":
                word = m.group()
                if word in _KEYWORDS or word in _C_KEYWORDS:
                    tokens.append(HighlightToken(start, end, "keyword"))
                    if word in ("struct", "class", "enum"):
                        last_struct_class = end
                elif word in _BUILTINS:
                    tokens.append(HighlightToken(start, end, "builtin"))
                elif word in _PP_KEYWORDS:
                    tokens.append(HighlightToken(start, end, "preprocessor"))
                else:
                    if last_struct_class is not None:
                        between = code[last_struct_class:start]
                        if between.strip() == "":
                            type_ = (
                                "class"
                                if start >= 6 and code[start - 6 : start] == "class "
                                else "struct"
                            )
                            tokens.append(HighlightToken(start, end, type_))
                            last_struct_class = None
                            continue
                        last_struct_class = None
                    tokens.append(HighlightToken(start, end, "identifier"))

            elif kind == "operator":
                tokens.append(HighlightToken(start, end, "operator"))

            elif kind == "punctuation":
                tokens.append(HighlightToken(start, end, "punctuation"))

        return tokens
