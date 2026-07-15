import pytest

from modules.highlighter.base import HighlightBlock
from modules.highlighter.python import PythonHighlighterExpert


class TestPythonHighlighter:
    def test_init(self):
        expert = PythonHighlighterExpert()
        assert expert is not None

    def test_get_language_exts(self):
        expert = PythonHighlighterExpert()
        assert 'py' in expert.get_languange_exts()

    def test_highlight_empty_string(self):
        expert = PythonHighlighterExpert()
        block = HighlightBlock(code="")
        result = expert.highlight(block)
        assert result.code == ""
        assert result.tokens == []

    def test_highlight_keyword(self):
        expert = PythonHighlighterExpert()
        block = HighlightBlock(code="def foo(): pass")
        result = expert.highlight(block)
        assert result.code == "def foo(): pass"
        assert result.tokens is not None
        assert len(result.tokens) > 0

    def test_highlight_string(self):
        expert = PythonHighlighterExpert()
        block = HighlightBlock(code="'hello'")
        result = expert.highlight(block)
        assert result.code == "'hello'"
        assert result.tokens is not None
        string_tokens = [t for t in result.tokens if t.type == "string"]
        assert len(string_tokens) == 1

    def test_highlight_comment(self):
        expert = PythonHighlighterExpert()
        block = HighlightBlock(code="# comment")
        result = expert.highlight(block)
        assert result.code == "# comment"
        assert result.tokens is not None
        comment_tokens = [t for t in result.tokens if t.type == "comment"]
        assert len(comment_tokens) == 1

    def test_highlight_number(self):
        expert = PythonHighlighterExpert()
        block = HighlightBlock(code="42")
        result = expert.highlight(block)
        assert result.code == "42"
        assert result.tokens is not None
        number_tokens = [t for t in result.tokens if t.type == "number"]
        assert len(number_tokens) == 1

    def test_highlight_decorator(self):
        expert = PythonHighlighterExpert()
        block = HighlightBlock(code="@decorator")
        result = expert.highlight(block)
        assert result.code == "@decorator"
        assert result.tokens is not None
        decorator_tokens = [t for t in result.tokens if t.type == "decorator"]
        assert len(decorator_tokens) == 1

    def test_highlight_function_definition(self):
        expert = PythonHighlighterExpert()
        block = HighlightBlock(code="def my_func(): pass")
        result = expert.highlight(block)
        assert result.code == "def my_func(): pass"
        token_types = [t.type for t in result.tokens]
        assert "keyword" in token_types
        assert "function" in token_types

    def test_highlight_class_definition(self):
        expert = PythonHighlighterExpert()
        block = HighlightBlock(code="class MyClass: pass")
        result = expert.highlight(block)
        assert result.code == "class MyClass: pass"
        token_types = [t.type for t in result.tokens]
        assert "keyword" in token_types
        assert "class" in token_types

    def test_highlight_import_statement(self):
        expert = PythonHighlighterExpert()
        block = HighlightBlock(code="import os")
        result = expert.highlight(block)
        assert result.code == "import os"
        token_types = [t.type for t in result.tokens]
        assert "keyword" in token_types

    def test_highlight_from_import(self):
        expert = PythonHighlighterExpert()
        block = HighlightBlock(code="from os import path")
        result = expert.highlight(block)
        assert result.code == "from os import path"
        token_types = [t.type for t in result.tokens]
        assert "keyword" in token_types
