import pytest

from core.language.highlighter import HighlightBlock
from core.language.highlighter.json_expert import JsonHighlighterExpert


class TestJsonHighlighterExpert:
    def test_init(self):
        expert = JsonHighlighterExpert()
        assert expert is not None

    def test_get_language_exts(self):
        expert = JsonHighlighterExpert()
        exts = expert.get_languange_exts()
        assert "json" in exts

    def test_highlight_empty_string(self):
        expert = JsonHighlighterExpert()
        block = HighlightBlock(code="")
        result = expert.highlight(block)
        assert result.code == ""
        assert result.tokens == []

    def test_highlight_object(self):
        expert = JsonHighlighterExpert()
        block = HighlightBlock(code='{"key": "value"}')
        result = expert.highlight(block)
        assert result.code == '{"key": "value"}'
        assert result.tokens is not None

    def test_highlight_string_value(self):
        expert = JsonHighlighterExpert()
        block = HighlightBlock(code='"hello"')
        result = expert.highlight(block)
        assert result.code == '"hello"'
        assert result.tokens is not None
        string_tokens = [t for t in result.tokens if t.type == "string"]
        assert len(string_tokens) == 1

    def test_highlight_number(self):
        expert = JsonHighlighterExpert()
        block = HighlightBlock(code="42")
        result = expert.highlight(block)
        assert result.code == "42"
        assert result.tokens is not None
        number_tokens = [t for t in result.tokens if t.type == "number"]
        assert len(number_tokens) == 1

    def test_highlight_float(self):
        expert = JsonHighlighterExpert()
        block = HighlightBlock(code="3.14")
        result = expert.highlight(block)
        assert result.code == "3.14"
        assert result.tokens is not None
        number_tokens = [t for t in result.tokens if t.type == "number"]
        assert len(number_tokens) == 1

    def test_highlight_negative_number(self):
        expert = JsonHighlighterExpert()
        block = HighlightBlock(code="-273.15")
        result = expert.highlight(block)
        assert result.code == "-273.15"
        assert result.tokens is not None

    def test_highlight_keyword_true(self):
        expert = JsonHighlighterExpert()
        block = HighlightBlock(code="true")
        result = expert.highlight(block)
        assert result.code == "true"
        assert result.tokens is not None
        keyword_tokens = [t for t in result.tokens if t.type == "keyword"]
        assert len(keyword_tokens) == 1

    def test_highlight_keyword_false(self):
        expert = JsonHighlighterExpert()
        block = HighlightBlock(code="false")
        result = expert.highlight(block)
        assert result.code == "false"
        assert result.tokens is not None
        keyword_tokens = [t for t in result.tokens if t.type == "keyword"]
        assert len(keyword_tokens) == 1

    def test_highlight_keyword_null(self):
        expert = JsonHighlighterExpert()
        block = HighlightBlock(code="null")
        result = expert.highlight(block)
        assert result.code == "null"
        assert result.tokens is not None
        keyword_tokens = [t for t in result.tokens if t.type == "keyword"]
        assert len(keyword_tokens) == 1

    def test_highlight_array(self):
        expert = JsonHighlighterExpert()
        block = HighlightBlock(code='[1, 2, 3]')
        result = expert.highlight(block)
        assert result.code == '[1, 2, 3]'
        assert result.tokens is not None
        punctuation_tokens = [t for t in result.tokens if t.type == "punctuation"]
        assert len(punctuation_tokens) == 2

    def test_highlight_punctuation(self):
        expert = JsonHighlighterExpert()
        block = HighlightBlock(code="{}")
        result = expert.highlight(block)
        assert result.code == "{}"
        assert result.tokens is not None
        punctuation_tokens = [t for t in result.tokens if t.type == "punctuation"]
        assert len(punctuation_tokens) == 2

    def test_highlight_operator(self):
        expert = JsonHighlighterExpert()
        block = HighlightBlock(code=":")
        result = expert.highlight(block)
        assert result.code == ":"
        assert result.tokens is not None
        operator_tokens = [t for t in result.tokens if t.type == "operator"]
        assert len(operator_tokens) == 1

    def test_highlight_key(self):
        expert = JsonHighlighterExpert()
        block = HighlightBlock(code='{"name": "test"}')
        result = expert.highlight(block)
        assert result.code == '{"name": "test"}'
        assert result.tokens is not None
        key_tokens = [t for t in result.tokens if t.type == "key"]
        assert len(key_tokens) >= 1

    def test_highlight_nested_object(self):
        expert = JsonHighlighterExpert()
        block = HighlightBlock(code='{"nested": {"key": "value"}}')
        result = expert.highlight(block)
        assert result.code == '{"nested": {"key": "value"}}'
        assert result.tokens is not None

    def test_highlight_scientific_notation(self):
        expert = JsonHighlighterExpert()
        block = HighlightBlock(code="1e10")
        result = expert.highlight(block)
        assert result.code == "1e10"
        assert result.tokens is not None
