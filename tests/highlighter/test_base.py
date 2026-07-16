import pytest

from modules.highlighter.base import HighlightBlock, HighlighterExpert, HighlightToken


class MockHighlighter(HighlighterExpert):
    def highlight(self, block: HighlightBlock) -> HighlightBlock:
        return block

    def get_languange_exts(self) -> list:
        return ["mock"]


class TestHighlightToken:
    def test_creation(self):
        token = HighlightToken(start=0, end=5, type="keyword")
        assert token.start == 0
        assert token.end == 5
        assert token.type == "keyword"


class TestHighlightBlock:
    def test_creation_with_code(self):
        block = HighlightBlock(code="print('hello')")
        assert block.code == "print('hello')"
        assert block.tokens is None

    def test_creation_with_tokens(self):
        tokens = [HighlightToken(0, 5, "keyword"), HighlightToken(6, 11, "identifier")]
        block = HighlightBlock(code="print", tokens=tokens)
        assert block.code == "print"
        assert len(block.tokens) == 2


class TestHighlighterExpert:
    def test_is_abstract(self):
        with pytest.raises(TypeError):
            HighlighterExpert()

    def test_mock_highlighter(self):
        highlighter = MockHighlighter()
        assert highlighter.get_languange_exts() == ["mock"]
        block = HighlightBlock(code="test")
        result = highlighter.highlight(block)
        assert result.code == "test"
