"""针对 ``modules.highlighter.python.PythonHighlighterExpert`` 的测试。

按照 ``API_DOCS.md`` 中描述的行为编写用例,覆盖:

* 文件扩展名
* 字符串 / 注释 / 装饰器 / 数值 / 关键字 / 内建名 / 标识符
* ``def`` / ``class`` 后紧跟的名称被标记为 ``function`` / ``class``
* ``highlight`` 返回的新对象不会污染入参
"""

from __future__ import annotations

import pytest

from modules.highlighter import HighlightBlock, HighlightToken, PythonHighlighterExpert




def _token_types(result: HighlightBlock) -> list[str]:
    """返回 token 类型列表(便于顺序无关断言)。"""
    assert result.tokens is not None
    return [t.type for t in result.tokens]


def _tokens_of_type(result: HighlightBlock, type_: str) -> list[HighlightToken]:
    assert result.tokens is not None
    return [t for t in result.tokens if t.type == type_]


def _snippet(token: HighlightToken, code: str) -> str:
    return code[token.start:token.end]




class TestPythonHighlighterExpertBasics:
    def test_get_languange_exts(self) -> None:
        expert = PythonHighlighterExpert()
        assert expert.get_languange_exts() == ["py"]

    def test_highlight_returns_new_block(self) -> None:
        """``highlight`` 必须返回新的 ``HighlightBlock``,且填充 ``tokens``。"""
        expert = PythonHighlighterExpert()
        block = HighlightBlock(code="x = 1", tokens=None)
        result = expert.highlight(block)
        assert isinstance(result, HighlightBlock)
        assert result is not block
        assert result.tokens is not None
        assert result.code == block.code

    def test_empty_code(self) -> None:
        expert = PythonHighlighterExpert()
        result = expert.highlight(HighlightBlock(code=""))
        assert result.tokens == []

    def test_no_match_code(self) -> None:
        """当代码不含任何 token 时,应返回空列表。"""
        expert = PythonHighlighterExpert()
        result = expert.highlight(HighlightBlock(code="   \n\t  "))
        assert result.tokens == []




class TestKeywordAndBuiltin:
    @pytest.mark.parametrize(
        "keyword",
        ["def", "class", "if", "else", "return", "import", "from", "for", "while", "lambda"],
    )
    def test_keyword_detection(self, keyword: str) -> None:
        expert = PythonHighlighterExpert()
        result = expert.highlight(HighlightBlock(code=keyword))
        assert _token_types(result) == ["keyword"]

    @pytest.mark.parametrize(
        "builtin",
        ["print", "len", "range", "open", "isinstance"],
    )
    def test_builtin_detection(self, builtin: str) -> None:
        expert = PythonHighlighterExpert()
        result = expert.highlight(HighlightBlock(code=builtin))
        assert _token_types(result) == ["builtin"]

    def test_identifier_detection(self) -> None:
        expert = PythonHighlighterExpert()
        result = expert.highlight(HighlightBlock(code="my_variable"))
        assert _token_types(result) == ["identifier"]

    def test_keyword_takes_precedence_over_builtin(self) -> None:
        """``type`` 既在关键字列表中也在内建名集合中,关键字优先。"""
        expert = PythonHighlighterExpert()
        result = expert.highlight(HighlightBlock(code="type"))
        assert _token_types(result) == ["keyword"]




class TestDefAndClass:
    def test_def_marks_function(self) -> None:
        code = "def greet(name):\n    return name\n"
        expert = PythonHighlighterExpert()
        result = expert.highlight(HighlightBlock(code=code))

        kinds = _token_types(result)
        assert kinds[0] == "keyword"  # def
        assert kinds[1] == "function"  # greet

        function_tokens = _tokens_of_type(result, "function")
        assert function_tokens and _snippet(function_tokens[0], code) == "greet"

    def test_class_marks_class(self) -> None:
        code = "class Greeter:\n    pass\n"
        expert = PythonHighlighterExpert()
        result = expert.highlight(HighlightBlock(code=code))

        kinds = _token_types(result)
        assert kinds[0] == "keyword"  # class
        assert kinds[1] == "class"  # Greeter

    def test_async_def_still_marks_function(self) -> None:
        """async def 后跟的仍应被识别为函数名。"""
        code = "async def fetch():\n    return 1\n"
        expert = PythonHighlighterExpert()
        result = expert.highlight(HighlightBlock(code=code))

        kinds = _token_types(result)
        assert "function" in kinds
        assert kinds.index("keyword") < kinds.index("function")

    def test_def_with_decorator_still_marks_function(self) -> None:
        """``@dec\\ndef func`` 中装饰器单独标记,函数名也单独标记。"""
        code = "@dec\ndef func():\n    pass\n"
        expert = PythonHighlighterExpert()
        result = expert.highlight(HighlightBlock(code=code))

        kinds = _token_types(result)
        assert "decorator" in kinds
        assert "function" in kinds

    def test_def_then_punct_does_not_mark_function(self) -> None:
        """``def`` 与下一标识符之间有非空白字符时,后续标识符应视为普通 ``identifier``。

        实现里 ``between = code[kw_end:start]; if between.strip() == ''`` 即:只有当
        ``def`` 与下一个标识符之间全是空白时,才把下一个标识符标记为 function。
        ``def:foo`` 中的 ``:`` 是非空白字符,foo 应当保持 ``identifier`` 类型。
        """
        code = "def:foo\n"
        expert = PythonHighlighterExpert()
        result = expert.highlight(HighlightBlock(code=code))

        kinds = _token_types(result)
        assert "function" not in kinds
        ids = _tokens_of_type(result, "identifier")
        assert ids and _snippet(ids[0], code) == "foo"

    def test_decorator_detection(self) -> None:
        code = "@property\n"
        expert = PythonHighlighterExpert()
        result = expert.highlight(HighlightBlock(code=code))
        decorators = _tokens_of_type(result, "decorator")
        assert len(decorators) == 1
        assert _snippet(decorators[0], code) == "@property"

    def test_dotted_decorator(self) -> None:
        code = "@module.decorator\n"
        expert = PythonHighlighterExpert()
        result = expert.highlight(HighlightBlock(code=code))
        decorators = _tokens_of_type(result, "decorator")
        assert len(decorators) == 1
        assert _snippet(decorators[0], code) == "@module.decorator"




class TestString:
    @pytest.mark.parametrize(
        "src, expected_text",
        [
            ('"hello"', '"hello"'),
            ("'world'", "'world'"),
            ('"""triple"""', '"""triple"""'),
            ("'''triple'''", "'''triple'''"),
            ('r"raw"', 'r"raw"'),
            ('b"bytes"', 'b"bytes"'),
            ('f"fstring {x}"', 'f"fstring {x}"'),
            ('rb"raw bytes"', 'rb"raw bytes"'),
            ('R"upper raw"', 'R"upper raw"'),
        ],
    )
    def test_string_variants(self, src: str, expected_text: str) -> None:
        expert = PythonHighlighterExpert()
        result = expert.highlight(HighlightBlock(code=src))
        tokens = _tokens_of_type(result, "string")
        assert len(tokens) == 1
        assert _snippet(tokens[0], src) == expected_text

    def test_string_does_not_break_comment(self) -> None:
        """字符串后的注释应被独立标记为 comment。"""
        code = '"hi" # comment\n'
        expert = PythonHighlighterExpert()
        result = expert.highlight(HighlightBlock(code=code))
        kinds = _token_types(result)
        assert "string" in kinds
        assert "comment" in kinds




class TestComment:
    def test_single_line_comment(self) -> None:
        code = "# this is a comment\n"
        expert = PythonHighlighterExpert()
        result = expert.highlight(HighlightBlock(code=code))
        comments = _tokens_of_type(result, "comment")
        assert len(comments) == 1
        assert _snippet(comments[0], code) == "# this is a comment"

    def test_inline_comment(self) -> None:
        code = "x = 1  # comment\n"
        expert = PythonHighlighterExpert()
        result = expert.highlight(HighlightBlock(code=code))
        comments = _tokens_of_type(result, "comment")
        assert len(comments) == 1
        assert _snippet(comments[0], code).startswith("#")




class TestNumber:
    @pytest.mark.parametrize(
        "src",
        [
            "0",
            "123",
            "3.14",
            "1e10",
            "2.5e-3",
            "0xDEAD",
            "0b1010",
            "0o777",
            "1j",
        ],
    )
    def test_number_variants(self, src: str) -> None:
        expert = PythonHighlighterExpert()
        result = expert.highlight(HighlightBlock(code=src))
        numbers = _tokens_of_type(result, "number")
        assert len(numbers) == 1
        assert _snippet(numbers[0], src) == src

    def test_number_with_underscore(self) -> None:
        """当前正则不支持下划线,故 ``1_000_000`` 只会匹配到 ``1``。"""
        expert = PythonHighlighterExpert()
        result = expert.highlight(HighlightBlock(code="1_000_000"))
        numbers = _tokens_of_type(result, "number")
        assert len(numbers) == 1
        assert _snippet(numbers[0], "1_000_000") == "1"




class TestOperatorAndPunctuation:
    @pytest.mark.parametrize(
        "op",
        ["+", "-", "*", "/", "%", "**", "//", "<<", ">>", "&", "|", "^", "~",
         "<", ">", "<=", ">=", "==", "!=", "+=", "-=", "*=", "/=", "%="],
    )
    def test_basic_operators(self, op: str) -> None:
        expert = PythonHighlighterExpert()
        result = expert.highlight(HighlightBlock(code=op))
        operators = _tokens_of_type(result, "operator")
        assert len(operators) == 1
        assert _snippet(operators[0], op) == op

    def test_arrow_operator(self) -> None:
        expert = PythonHighlighterExpert()
        result = expert.highlight(HighlightBlock(code="->"))
        assert _token_types(result) == ["operator"]

    @pytest.mark.parametrize(
        "punct",
        list("()[]{}:;,."),
    )
    def test_punctuation(self, punct: str) -> None:
        """``-`` 因为也匹配运算符,单独测试;此处只测真正的标点。"""
        expert = PythonHighlighterExpert()
        result = expert.highlight(HighlightBlock(code=punct))
        tokens = _tokens_of_type(result, "punctuation")
        assert len(tokens) == 1
        assert _snippet(tokens[0], punct) == punct

    def test_minus_is_operator(self) -> None:
        """``-`` 因正则顺序优先匹配 operator。"""
        expert = PythonHighlighterExpert()
        result = expert.highlight(HighlightBlock(code="-"))
        assert _token_types(result) == ["operator"]




class TestEndToEnd:
    def test_full_function_example(self) -> None:
        """来自 API_DOCS.md 的样例。"""
        code = (
            "def greet(name: str) -> str:\n"
            '    """Say hello."""\n'
            '    return f"hello, {name}"\n'
        )
        expert = PythonHighlighterExpert()
        result = expert.highlight(HighlightBlock(code=code))
        kinds = _token_types(result)

        for expected in ("keyword", "function", "identifier", "string", "punctuation", "operator"):
            assert expected in kinds, f"missing token type: {expected}"

        funcs = _tokens_of_type(result, "function")
        assert funcs and _snippet(funcs[0], code) == "greet"

        strings = _tokens_of_type(result, "string")
        assert any(_snippet(t, code).startswith('"""') for t in strings)
        assert any(_snippet(t, code).startswith('f"') for t in strings)

    def test_tokens_are_non_overlapping_and_ordered(self) -> None:
        """所有 token 必须按 ``start`` 升序排列,且区间互不重叠。"""
        code = "@dec\ndef foo(x: int) -> int:\n    return x + 1\n"
        expert = PythonHighlighterExpert()
        result = expert.highlight(HighlightBlock(code=code))
        assert result.tokens

        sorted_tokens = sorted(result.tokens, key=lambda t: t.start)
        cursor = -1
        for t in sorted_tokens:
            assert t.start > cursor, (
                f"tokens overlap or out-of-order: cursor={cursor}, token=({t.start},{t.end})"
            )
            assert t.end > t.start, "empty token"
            cursor = t.start

    def test_input_block_not_mutated(self) -> None:
        expert = PythonHighlighterExpert()
        original = HighlightBlock(code="def foo():\n    pass\n", tokens=None)
        _ = expert.highlight(original)
        assert original.tokens is None

    def test_token_snippets_concatenate_back_to_source(self) -> None:
        """相邻 token 的 ``code[start:end]`` 拼接后,加上空白可还原源码。"""
        code = "def foo():\n    return 1\n"
        expert = PythonHighlighterExpert()
        result = expert.highlight(HighlightBlock(code=code))
        assert result.tokens

        joined = "".join(code[t.start:t.end] for t in sorted(result.tokens, key=lambda t: t.start))
        non_ws_source = [c for c in code if not c.isspace()]
        non_ws_joined = [c for c in joined if not c.isspace()]
        assert non_ws_joined == non_ws_source