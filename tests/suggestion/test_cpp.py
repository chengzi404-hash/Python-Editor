from __future__ import annotations

import pytest

from modules.suggestion.base import SuggestionBlock
from modules.suggestion.cpp import CppSuggestionExpert


class TestBasicInterface:
    def test_get_languange_exts(self) -> None:
        expert = CppSuggestionExpert()
        assert expert.get_languange_exts() == ['cpp', 'cc', 'cxx', 'hpp', 'hh']

    def test_suggest_returns_list(self) -> None:
        expert = CppSuggestionExpert()
        result = expert.suggest(SuggestionBlock(code="x", position=1))
        assert isinstance(result, list)

    def test_suggest_is_sorted_and_unique(self) -> None:
        expert = CppSuggestionExpert()
        result = expert.suggest(SuggestionBlock(code="\n", position=0))
        assert result == sorted(set(result))


class TestIdentifierSuggestion:
    def test_includes_cpp_keywords(self) -> None:
        expert = CppSuggestionExpert()
        result = expert.suggest(SuggestionBlock(code="\n", position=0))
        for kw in ("int", "return", "class", "namespace", "virtual", "template", "public", "private"):
            assert kw in result, f"missing keyword: {kw}"

    def test_includes_builtins(self) -> None:
        expert = CppSuggestionExpert()
        result = expert.suggest(SuggestionBlock(code="\n", position=0))
        for name in ("printf", "malloc", "sizeof", "nullptr", "vector", "string", "push_back", "size"):
            assert name in result

    def test_prefix_filter(self) -> None:
        expert = CppSuggestionExpert()
        block = SuggestionBlock(code="vec", position=3)
        result = expert.suggest(block)
        for s in result:
            assert s.startswith("vec"), f"unexpected suggestion: {s!r}"

    def test_no_match_returns_empty(self) -> None:
        expert = CppSuggestionExpert()
        block = SuggestionBlock(code="zzq", position=3)
        result = expert.suggest(block)
        assert result == []

    def test_function_in_scope_is_suggested(self) -> None:
        expert = CppSuggestionExpert()
        code = (
            "void helper() {\n"
            "    return;\n"
            "}\n"
            "hel\n"
        )
        block = SuggestionBlock(code=code, position=len(code))
        result = expert.suggest(block)
        assert "helper" in result

    def test_class_in_scope_is_suggested(self) -> None:
        expert = CppSuggestionExpert()
        code = (
            "class Greeter {\n"
            "public:\n"
            "    void greet();\n"
            "};\n"
            "Gre\n"
        )
        block = SuggestionBlock(code=code, position=len(code))
        result = expert.suggest(block)
        assert "Greeter" in result


class TestAttributeSuggestion:
    def test_dot_suggests_attributes(self) -> None:
        expert = CppSuggestionExpert()
        code = "obj."
        pos = code.index("obj.") + len("obj.")
        block = SuggestionBlock(code=code, position=pos)
        result = expert.suggest(block)
        assert len(result) > 0
        for attr in ("begin", "end", "size", "empty", "push_back", "data"):
            assert attr in result

    def test_arrow_suggests_attributes(self) -> None:
        expert = CppSuggestionExpert()
        code = "ptr->"
        pos = code.index("ptr->") + len("ptr->")
        block = SuggestionBlock(code=code, position=pos)
        result = expert.suggest(block)
        assert len(result) > 0
        assert "size" in result
        assert "data" in result

    def test_attribute_prefix_filter(self) -> None:
        expert = CppSuggestionExpert()
        code = "obj.si"
        pos = code.index("obj.si") + len("obj.si")
        block = SuggestionBlock(code=code, position=pos)
        result = expert.suggest(block)
        for s in result:
            assert s.startswith("si"), f"unexpected suggestion: {s!r}"
        assert "size" in result


class TestScopeSuggestion:
    def test_scope_suggests_std_members(self) -> None:
        expert = CppSuggestionExpert()
        code = "std::"
        pos = code.index("std::") + len("std::")
        block = SuggestionBlock(code=code, position=pos)
        result = expert.suggest(block)
        assert "cout" in result
        assert "cin" in result
        assert "endl" in result
        assert "string" in result
        assert "vector" in result

    def test_scope_prefix_filter(self) -> None:
        expert = CppSuggestionExpert()
        code = "std::co"
        pos = code.index("std::co") + len("std::co")
        block = SuggestionBlock(code=code, position=pos)
        result = expert.suggest(block)
        for s in result:
            assert s.startswith("co"), f"unexpected suggestion: {s!r}"
        assert "cout" in result


class TestNamespaceAndClass:
    def test_namespace_found_in_scope(self) -> None:
        code = (
            "namespace mylib {\n"
            "    void foo();\n"
            "}\n"
        )
        expert = CppSuggestionExpert()
        block = SuggestionBlock(code=code, position=0)
        result = expert.suggest(block)
        assert "mylib" in result

    def test_enum_found_in_scope(self) -> None:
        code = "enum class Color { Red, Green, Blue };\n"
        expert = CppSuggestionExpert()
        block = SuggestionBlock(code=code, position=0)
        result = expert.suggest(block)
        assert "Color" in result