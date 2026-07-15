import pytest

from modules.highlighter.base import HighlightBlock
from modules.highlighter.ccpp import CcppHighlighterExpert


class TestCcppHighlighter:
    def test_init(self):
        expert = CcppHighlighterExpert()
        assert expert is not None

    def test_get_language_exts(self):
        expert = CcppHighlighterExpert()
        exts = expert.get_languange_exts()
        assert 'c' in exts
        assert 'cpp' in exts
        assert 'h' in exts
        assert 'hpp' in exts

    def test_highlight_empty_string(self):
        expert = CcppHighlighterExpert()
        block = HighlightBlock(code="")
        result = expert.highlight(block)
        assert result.code == ""
        assert result.tokens == []

    def test_highlight_include(self):
        expert = CcppHighlighterExpert()
        block = HighlightBlock(code='#include <stdio.h>')
        result = expert.highlight(block)
        assert result.code == '#include <stdio.h>'
        assert result.tokens is not None

    def test_highlight_string(self):
        expert = CcppHighlighterExpert()
        block = HighlightBlock(code='"hello"')
        result = expert.highlight(block)
        assert result.code == '"hello"'
        assert result.tokens is not None
        string_tokens = [t for t in result.tokens if t.type == "string"]
        assert len(string_tokens) == 1

    def test_highlight_comment(self):
        expert = CcppHighlighterExpert()
        block = HighlightBlock(code='// comment')
        result = expert.highlight(block)
        assert result.code == '// comment'
        assert result.tokens is not None
        comment_tokens = [t for t in result.tokens if t.type == "comment"]
        assert len(comment_tokens) == 1

    def test_highlight_multiline_comment(self):
        expert = CcppHighlighterExpert()
        block = HighlightBlock(code='/* multi\nline\ncomment */')
        result = expert.highlight(block)
        assert result.code == '/* multi\nline\ncomment */'
        assert result.tokens is not None

    def test_highlight_number(self):
        expert = CcppHighlighterExpert()
        block = HighlightBlock(code='42')
        result = expert.highlight(block)
        assert result.code == '42'
        assert result.tokens is not None
        number_tokens = [t for t in result.tokens if t.type == "number"]
        assert len(number_tokens) == 1

    def test_highlight_keyword(self):
        expert = CcppHighlighterExpert()
        block = HighlightBlock(code='int main()')
        result = expert.highlight(block)
        assert result.code == 'int main()'
        token_types = [t.type for t in result.tokens]
        assert "keyword" in token_types

    def test_highlight_struct(self):
        expert = CcppHighlighterExpert()
        block = HighlightBlock(code='struct MyStruct { };')
        result = expert.highlight(block)
        assert result.code == 'struct MyStruct { };'
        token_types = [t.type for t in result.tokens]
        assert "keyword" in token_types

    def test_highlight_class(self):
        expert = CcppHighlighterExpert()
        block = HighlightBlock(code='class MyClass { };')
        result = expert.highlight(block)
        assert result.code == 'class MyClass { };'
        token_types = [t.type for t in result.tokens]
        assert "keyword" in token_types

    def test_highlight_enum(self):
        expert = CcppHighlighterExpert()
        block = HighlightBlock(code='enum Color { RED };')
        result = expert.highlight(block)
        assert result.code == 'enum Color { RED };'
        token_types = [t.type for t in result.tokens]
        assert "keyword" in token_types
