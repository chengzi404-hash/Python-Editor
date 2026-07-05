from __future__ import annotations

import pytest

from modules.suggestion.base import SuggestionBlock
from modules.suggestion.c import CSuggestionExpert


class TestBasicInterface:
    def test_get_languange_exts(self) -> None:
        expert = CSuggestionExpert()
        assert expert.get_languange_exts() == ['c', 'h']

    def test_suggest_returns_list(self) -> None:
        expert = CSuggestionExpert()
        result = expert.suggest(SuggestionBlock(code="x", position=1))
        assert isinstance(result, list)

    def test_suggest_is_sorted_and_unique(self) -> None:
        expert = CSuggestionExpert()
        result = expert.suggest(SuggestionBlock(code="\n", position=0))
        assert result == sorted(set(result))


class TestIdentifierSuggestion:
    def test_includes_c_keywords(self) -> None:
        expert = CSuggestionExpert()
        result = expert.suggest(SuggestionBlock(code="\n", position=0))
        for kw in ("int", "return", "if", "else", "for", "while", "void", "struct"):
            assert kw in result, f"missing keyword: {kw}"

    def test_includes_builtins(self) -> None:
        expert = CSuggestionExpert()
        result = expert.suggest(SuggestionBlock(code="\n", position=0))
        for name in ("printf", "malloc", "sizeof", "NULL"):
            assert name in result

    def test_includes_preprocessor_keywords(self) -> None:
        expert = CSuggestionExpert()
        result = expert.suggest(SuggestionBlock(code="\n", position=0))
        for kw in ("#define", "#include", "#ifdef", "#ifndef"):
            assert kw in result

    def test_prefix_filter(self) -> None:
        expert = CSuggestionExpert()
        block = SuggestionBlock(code="int", position=3)
        result = expert.suggest(block)
        for s in result:
            assert s.startswith("int"), f"unexpected suggestion: {s!r}"

    def test_no_match_returns_empty(self) -> None:
        expert = CSuggestionExpert()
        block = SuggestionBlock(code="zzq", position=3)
        result = expert.suggest(block)
        assert result == []

    def test_function_in_scope_is_suggested(self) -> None:
        expert = CSuggestionExpert()
        code = (
            "void helper() {\n"
            "    return;\n"
            "}\n"
            "hel\n"
        )
        block = SuggestionBlock(code=code, position=len(code))
        result = expert.suggest(block)
        assert "helper" in result


class TestAttributeSuggestion:
    def test_dot_suggests_attributes(self) -> None:
        expert = CSuggestionExpert()
        code = "struct data."
        pos = code.index("data.") + len("data.")
        block = SuggestionBlock(code=code, position=pos)
        result = expert.suggest(block)
        assert len(result) > 0
        for attr in ("x", "y", "data", "next", "prev", "count", "size"):
            assert attr in result

    def test_arrow_suggests_attributes(self) -> None:
        expert = CSuggestionExpert()
        code = "ptr->"
        pos = code.index("ptr->") + len("ptr->")
        block = SuggestionBlock(code=code, position=pos)
        result = expert.suggest(block)
        assert len(result) > 0
        assert "data" in result

    def test_attribute_prefix_filter(self) -> None:
        expert = CSuggestionExpert()
        code = "obj.da"
        pos = code.index("obj.da") + len("obj.da")
        block = SuggestionBlock(code=code, position=pos)
        result = expert.suggest(block)
        for s in result:
            assert s.startswith("da"), f"unexpected suggestion: {s!r}"
        assert "data" in result


class TestStructAndFunction:
    def test_struct_found_in_scope(self) -> None:
        code = (
            "typedef struct Point {\n"
            "    int x;\n"
            "    int y;\n"
            "} Point;\n"
        )
        expert = CSuggestionExpert()
        block = SuggestionBlock(code=code, position=0)
        result = expert.suggest(block)
        assert "Point" in result

    def test_typedef_found_in_scope(self) -> None:
        code = "typedef int MyInt;\n"
        expert = CSuggestionExpert()
        block = SuggestionBlock(code=code, position=0)
        result = expert.suggest(block)
        assert "MyInt" in result