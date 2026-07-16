import pytest

from modules.suggestion.base import DOMScope, SuggestionBlock, SuggestionExpert, SuggestionItem


class MockSuggestionExpert(SuggestionExpert):
    def suggest(self, block: SuggestionBlock):
        return []

    def get_languange_exts(self):
        return ["mock"]


class TestSuggestionBlock:
    def test_creation(self):
        block = SuggestionBlock(code="print('hello')", position=5)
        assert block.code == "print('hello')"
        assert block.position == 5


class TestSuggestionItem:
    def test_creation(self):
        item = SuggestionItem(label="print", priority=10, kind="function")
        assert item.label == "print"
        assert item.priority == 10
        assert item.kind == "function"

    def test_default_priority(self):
        item = SuggestionItem(label="print")
        assert item.priority == 0

    def test_default_kind(self):
        item = SuggestionItem(label="print")
        assert item.kind == ""


class TestDOMScope:
    def test_creation(self):
        scope = DOMScope(
            begin=0, end=10, varibles=["x"], functions=["foo"], classes=["MyClass"], subDOM=[]
        )
        assert scope.begin == 0
        assert scope.end == 10
        assert "x" in scope.varibles
        assert "foo" in scope.functions
        assert "MyClass" in scope.classes


class TestSuggestionExpert:
    def test_is_abstract(self):
        with pytest.raises(TypeError):
            SuggestionExpert()

    def test_mock_expert(self):
        expert = MockSuggestionExpert()
        assert expert.get_languange_exts() == ["mock"]
