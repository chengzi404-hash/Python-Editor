from __future__ import annotations

import pytest

from modules.highlighter import HighlightBlock, HighlightToken, CcppHighlighterExpert


def _token_types(result: HighlightBlock) -> list[str]:
    assert result.tokens is not None
    return [t.type for t in result.tokens]


def _tokens_of_type(result: HighlightBlock, type_: str) -> list[HighlightToken]:
    assert result.tokens is not None
    return [t for t in result.tokens if t.type == type_]


def _snippet(token: HighlightToken, code: str) -> str:
    return code[token.start:token.end]


class TestCcppHighlighterExpertBasics:
    def test_get_languange_exts(self) -> None:
        expert = CcppHighlighterExpert()
        assert expert.get_languange_exts() == ['c', 'cpp', 'cc', 'cxx', 'h', 'hpp', 'hh']

    def test_highlight_returns_new_block(self) -> None:
        expert = CcppHighlighterExpert()
        block = HighlightBlock(code="int x = 1;", tokens=None)
        result = expert.highlight(block)
        assert isinstance(result, HighlightBlock)
        assert result is not block
        assert result.tokens is not None
        assert result.code == block.code

    def test_empty_code(self) -> None:
        expert = CcppHighlighterExpert()
        result = expert.highlight(HighlightBlock(code=""))
        assert result.tokens == []

    def test_no_match_code(self) -> None:
        expert = CcppHighlighterExpert()
        result = expert.highlight(HighlightBlock(code="   \n\t  "))
        assert result.tokens == []


class TestKeywordAndBuiltin:
    @pytest.mark.parametrize(
        "keyword",
        ["int", "return", "if", "else", "for", "while", "struct", "class", "void", "const"],
    )
    def test_keyword_detection(self, keyword: str) -> None:
        expert = CcppHighlighterExpert()
        result = expert.highlight(HighlightBlock(code=keyword))
        assert _token_types(result) == ["keyword"]

    @pytest.mark.parametrize(
        "builtin",
        ["NULL"],
    )
    def test_builtin_detection(self, builtin: str) -> None:
        expert = CcppHighlighterExpert()
        result = expert.highlight(HighlightBlock(code=builtin))
        assert _token_types(result) == ["builtin"]

    def test_identifier_detection(self) -> None:
        expert = CcppHighlighterExpert()
        result = expert.highlight(HighlightBlock(code="my_variable"))
        assert _token_types(result) == ["identifier"]

    def test_keyword_takes_precedence_over_builtin(self) -> None:
        expert = CcppHighlighterExpert()
        result = expert.highlight(HighlightBlock(code="sizeof"))
        assert _token_types(result) == ["keyword"]


class TestStructAndClass:
    def test_struct_marks_name(self) -> None:
        code = "struct Point { int x; };"
        expert = CcppHighlighterExpert()
        result = expert.highlight(HighlightBlock(code=code))
        kinds = _token_types(result)
        assert kinds[0] == "keyword"
        assert "struct" in kinds

    def test_class_marks_name(self) -> None:
        code = "class Widget { public: int id; };"
        expert = CcppHighlighterExpert()
        result = expert.highlight(HighlightBlock(code=code))
        kinds = _token_types(result)
        assert kinds[0] == "keyword"
        assert "class" in kinds


class TestString:
    @pytest.mark.parametrize(
        "src, expected_text",
        [
            ('"hello"', '"hello"'),
            ("'c'", "'c'"),
            ('"escape\\n"', '"escape\\n"'),
        ],
    )
    def test_string_variants(self, src: str, expected_text: str) -> None:
        expert = CcppHighlighterExpert()
        result = expert.highlight(HighlightBlock(code=src))
        tokens = _tokens_of_type(result, "string")
        assert len(tokens) == 1
        assert _snippet(tokens[0], src) == expected_text


class TestComment:
    def test_single_line_comment(self) -> None:
        code = "// this is a comment\n"
        expert = CcppHighlighterExpert()
        result = expert.highlight(HighlightBlock(code=code))
        comments = _tokens_of_type(result, "comment")
        assert len(comments) == 1
        assert _snippet(comments[0], code) == "// this is a comment"

    def test_multiline_comment(self) -> None:
        code = "/* block comment */\n"
        expert = CcppHighlighterExpert()
        result = expert.highlight(HighlightBlock(code=code))
        comments = _tokens_of_type(result, "comment")
        assert len(comments) == 1
        assert _snippet(comments[0], code) == "/* block comment */"

    def test_multiline_comment_spans_lines(self) -> None:
        code = "/* line1\n   line2 */\n"
        expert = CcppHighlighterExpert()
        result = expert.highlight(HighlightBlock(code=code))
        comments = _tokens_of_type(result, "comment")
        assert len(comments) == 1
        assert _snippet(comments[0], code) == "/* line1\n   line2 */"

    def test_inline_comment(self) -> None:
        code = "int x = 1; // comment\n"
        expert = CcppHighlighterExpert()
        result = expert.highlight(HighlightBlock(code=code))
        comments = _tokens_of_type(result, "comment")
        assert len(comments) == 1
        assert _snippet(comments[0], code).startswith("//")


class TestPreprocessor:
    def test_include(self) -> None:
        code = '#include <stdio.h>\n'
        expert = CcppHighlighterExpert()
        result = expert.highlight(HighlightBlock(code=code))
        pp = _tokens_of_type(result, "preprocessor")
        assert len(pp) == 1
        assert _snippet(pp[0], code) == '#include <stdio.h>'

    def test_define(self) -> None:
        code = '#define MAX 100\n'
        expert = CcppHighlighterExpert()
        result = expert.highlight(HighlightBlock(code=code))
        pp = _tokens_of_type(result, "preprocessor")
        assert len(pp) == 1
        assert _snippet(pp[0], code) == '#define MAX 100'

    def test_ifdef(self) -> None:
        code = '#ifdef DEBUG\n'
        expert = CcppHighlighterExpert()
        result = expert.highlight(HighlightBlock(code=code))
        pp = _tokens_of_type(result, "preprocessor")
        assert len(pp) == 1
        assert _snippet(pp[0], code) == '#ifdef DEBUG'

    def test_pragma(self) -> None:
        code = '#pragma once\n'
        expert = CcppHighlighterExpert()
        result = expert.highlight(HighlightBlock(code=code))
        pp = _tokens_of_type(result, "preprocessor")
        assert len(pp) == 1
        assert _snippet(pp[0], code) == '#pragma once'


class TestNumber:
    @pytest.mark.parametrize(
        "src",
        ["0", "123", "3.14", "1e10", "2.5e-3", "0xDEAD", "0b1010", "42", "0.5f", "1.0L"],
    )
    def test_number_variants(self, src: str) -> None:
        expert = CcppHighlighterExpert()
        result = expert.highlight(HighlightBlock(code=src))
        numbers = _tokens_of_type(result, "number")
        assert len(numbers) == 1
        assert _snippet(numbers[0], src) == src


class TestOperatorAndPunctuation:
    @pytest.mark.parametrize(
        "op",
        ["+", "-", "*", "/", "%", "++", "--", "<<", ">>", "&", "|", "^", "~",
         "<", ">", "<=", ">=", "==", "!=", "+=", "-=", "*=", "/=", "%=", "->", "::"],
    )
    def test_basic_operators(self, op: str) -> None:
        expert = CcppHighlighterExpert()
        result = expert.highlight(HighlightBlock(code=op))
        operators = _tokens_of_type(result, "operator")
        assert len(operators) == 1
        assert _snippet(operators[0], op) == op

    @pytest.mark.parametrize(
        "punct",
        list("()[]{};,"),
    )
    def test_punctuation(self, punct: str) -> None:
        expert = CcppHighlighterExpert()
        result = expert.highlight(HighlightBlock(code=punct))
        tokens = _tokens_of_type(result, "punctuation")
        assert len(tokens) == 1
        assert _snippet(tokens[0], punct) == punct


class TestEndToEnd:
    def test_full_function_example(self) -> None:
        code = (
            'int add(int a, int b) {\n'
            '    return a + b;\n'
            '}\n'
        )
        expert = CcppHighlighterExpert()
        result = expert.highlight(HighlightBlock(code=code))
        kinds = _token_types(result)
        for expected in ("keyword", "identifier", "punctuation", "operator"):
            assert expected in kinds, f"missing token type: {expected}"

    def test_tokens_are_non_overlapping_and_ordered(self) -> None:
        code = '#include <stdio.h>\nint main() {\n    printf("hello");\n    return 0;\n}\n'
        expert = CcppHighlighterExpert()
        result = expert.highlight(HighlightBlock(code=code))
        assert result.tokens
        sorted_tokens = sorted(result.tokens, key=lambda t: t.start)
        cursor = -1
        for t in sorted_tokens:
            assert t.start > cursor
            assert t.end > t.start
            cursor = t.start

    def test_input_block_not_mutated(self) -> None:
        expert = CcppHighlighterExpert()
        original = HighlightBlock(code="int main() { return 0; }", tokens=None)
        _ = expert.highlight(original)
        assert original.tokens is None

    def test_token_snippets_concatenate_back_to_source(self) -> None:
        code = "int x = 42;\n"
        expert = CcppHighlighterExpert()
        result = expert.highlight(HighlightBlock(code=code))
        assert result.tokens
        joined = "".join(code[t.start:t.end] for t in sorted(result.tokens, key=lambda t: t.start))
        non_ws_source = [c for c in code if not c.isspace()]
        non_ws_joined = [c for c in joined if not c.isspace()]
        assert non_ws_joined == non_ws_source