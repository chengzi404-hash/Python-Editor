"""针对 ``modules.suggestion.cpp.CppSuggestionExpert`` 的测试。

覆盖:

* 基础接口(扩展名、``suggest`` 返回列表)
* 标识符补全:C++ 关键字、内建 (``printf`` / ``vector`` / ...)、前缀过滤
* 属性补全:``obj.`` / ``ptr->``、前缀过滤
* 作用域补全:``std::`` 后列出 ``cout`` / ``cin`` / ``vector`` 等
* 作用域内 namespace / enum class 名称能出现在补全候选
"""

from __future__ import annotations

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
        assert result == sorted(result, key=lambda x: (x.priority, x.label.lower()))


class TestIdentifierSuggestion:
    def test_includes_cpp_keywords(self) -> None:
        expert = CppSuggestionExpert()
        result = expert.suggest(SuggestionBlock(code="\n", position=0))
        labels = {s.label for s in result}
        for kw in ("int", "return", "class", "namespace", "virtual", "template", "public", "private"):
            assert kw in labels, f"missing keyword: {kw}"

    def test_includes_builtins(self) -> None:
        expert = CppSuggestionExpert()
        result = expert.suggest(SuggestionBlock(code="\n", position=0))
        labels = {s.label for s in result}
        for name in ("printf", "malloc", "sizeof", "nullptr", "vector", "string", "push_back", "size"):
            assert name in labels

    def test_prefix_filter(self) -> None:
        expert = CppSuggestionExpert()
        block = SuggestionBlock(code="vec", position=3)
        result = expert.suggest(block)
        for s in result:
            assert s.label.startswith("vec"), f"unexpected suggestion: {s!r}"

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
        assert any(s.label == "helper" for s in result)

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
        assert any(s.label == "Greeter" for s in result)


class TestAttributeSuggestion:
    def test_dot_suggests_attributes(self) -> None:
        expert = CppSuggestionExpert()
        code = "obj."
        pos = code.index("obj.") + len("obj.")
        block = SuggestionBlock(code=code, position=pos)
        result = expert.suggest(block)
        assert len(result) > 0
        labels = {s.label for s in result}
        for attr in ("begin", "end", "size", "empty", "push_back", "data"):
            assert attr in labels

    def test_arrow_suggests_attributes(self) -> None:
        expert = CppSuggestionExpert()
        code = "ptr->"
        pos = code.index("ptr->") + len("ptr->")
        block = SuggestionBlock(code=code, position=pos)
        result = expert.suggest(block)
        assert len(result) > 0
        labels = {s.label for s in result}
        assert "size" in labels
        assert "data" in labels

    def test_attribute_prefix_filter(self) -> None:
        expert = CppSuggestionExpert()
        code = "obj.si"
        pos = code.index("obj.si") + len("obj.si")
        block = SuggestionBlock(code=code, position=pos)
        result = expert.suggest(block)
        for s in result:
            assert s.label.startswith("si"), f"unexpected suggestion: {s!r}"
        assert any(s.label == "size" for s in result)


class TestScopeSuggestion:
    def test_scope_suggests_std_members(self) -> None:
        expert = CppSuggestionExpert()
        code = "std::"
        pos = code.index("std::") + len("std::")
        block = SuggestionBlock(code=code, position=pos)
        result = expert.suggest(block)
        labels = {s.label for s in result}
        assert "cout" in labels
        assert "cin" in labels
        assert "endl" in labels
        assert "string" in labels
        assert "vector" in labels

    def test_scope_prefix_filter(self) -> None:
        expert = CppSuggestionExpert()
        code = "std::co"
        pos = code.index("std::co") + len("std::co")
        block = SuggestionBlock(code=code, position=pos)
        result = expert.suggest(block)
        for s in result:
            assert s.label.startswith("co"), f"unexpected suggestion: {s!r}"
        assert any(s.label == "cout" for s in result)


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
        assert any(s.label == "mylib" for s in result)

    def test_enum_found_in_scope(self) -> None:
        code = "enum class Color { Red, Green, Blue };\n"
        expert = CppSuggestionExpert()
        block = SuggestionBlock(code=code, position=0)
        result = expert.suggest(block)
        assert any(s.label == "Color" for s in result)