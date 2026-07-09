"""针对 ``modules.suggestion.base`` 的测试。

覆盖:

* ``SuggestionBlock`` 数据类
* ``DOMScope`` 数据类(注意 ``varibles`` 拼写保留)
* ``SuggestionExpert`` 抽象基类
* ``modules/suggestion/__init__.py`` 与占位 ``c.py`` / ``cpp.py``
"""

from __future__ import annotations

import importlib

import pytest

from modules.suggestion.base import (
    DOMScope,
    SuggestionBlock,
    SuggestionExpert,
)




class TestSuggestionBlock:
    """``SuggestionBlock`` 包含 ``code`` 与 ``position``。"""

    def test_basic_construction(self) -> None:
        block = SuggestionBlock(code="print(", position=6)
        assert block.code == "print("
        assert block.position == 6

    def test_position_zero(self) -> None:
        """光标在文档开头也是合法的。"""
        block = SuggestionBlock(code="x", position=0)
        assert block.position == 0

    def test_equality(self) -> None:
        a = SuggestionBlock(code="x", position=1)
        b = SuggestionBlock(code="x", position=1)
        c = SuggestionBlock(code="x", position=2)
        assert a == b
        assert a != c

    def test_required_fields(self) -> None:
        with pytest.raises(TypeError):
            SuggestionBlock(code="x")  # type: ignore[call-arg]




class TestDOMScope:
    """``DOMScope`` 字段包含 ``begin/end/varibles/functions/classes/subDOM``。"""

    def test_basic_construction(self) -> None:
        scope = DOMScope(
            begin=0,
            end=10,
            varibles=["a"],
            functions=["foo"],
            classes=["Bar"],
            subDOM=[],
        )
        assert scope.begin == 0
        assert scope.end == 10
        assert scope.varibles == ["a"]
        assert scope.functions == ["foo"]
        assert scope.classes == ["Bar"]
        assert scope.subDOM == []

    def test_nested_scopes(self) -> None:
        inner = DOMScope(2, 5, [], [], [], [])
        outer = DOMScope(0, 10, [], [], [], [inner])
        assert outer.subDOM == [inner]
        assert inner.subDOM == []

    def test_typo_varibles_preserved(self) -> None:
        """``varibles`` 是源码中的拼写(可能是 typo),不应修复。"""
        scope = DOMScope(0, 1, ["x"], [], [], [])
        assert hasattr(scope, "varibles")
        assert scope.varibles == ["x"]

    def test_equality(self) -> None:
        s1 = DOMScope(0, 1, ["a"], [], [], [])
        s2 = DOMScope(0, 1, ["a"], [], [], [])
        s3 = DOMScope(0, 2, ["a"], [], [], [])
        assert s1 == s2
        assert s1 != s3




class TestSuggestionExpert:
    def test_cannot_instantiate_abstract_class(self) -> None:
        with pytest.raises(TypeError):
            SuggestionExpert()  # type: ignore[abstract]

    def test_must_implement_suggest(self) -> None:
        class Partial(SuggestionExpert):
            def get_languange_exts(self) -> list:  # type: ignore[override]
                return ["x"]

        with pytest.raises(TypeError):
            Partial()  # type: ignore[abstract]

    def test_must_implement_get_languange_exts(self) -> None:
        class Partial(SuggestionExpert):
            def suggest(self, block: SuggestionBlock) -> list:  # type: ignore[override]
                return []

        with pytest.raises(TypeError):
            Partial()  # type: ignore[abstract]

    def test_subclass_can_be_instantiated(self) -> None:
        class Concrete(SuggestionExpert):
            def suggest(self, block: SuggestionBlock) -> list:  # type: ignore[override]
                return []

            def get_languange_exts(self) -> list:  # type: ignore[override]
                return ["x"]

        c = Concrete()
        assert c.get_languange_exts() == ["x"]
        assert c.suggest(SuggestionBlock(code="", position=0)) == []




class TestPackageInit:
    def test_init_can_be_imported(self) -> None:
        """``modules.suggestion`` 应当能被成功导入(即便 ``__init__.py`` 为空)。"""
        suggestion_pkg = importlib.import_module("modules.suggestion")
        assert suggestion_pkg is not None

    def test_c_suggestion_expert_exists(self) -> None:
        """``c.py`` 已实现 ``CSuggestionExpert``。"""
        c_mod = importlib.import_module("modules.suggestion.c")
        assert hasattr(c_mod, "CSuggestionExpert")
        assert issubclass(c_mod.CSuggestionExpert, c_mod.SuggestionExpert)

    def test_cpp_suggestion_expert_exists(self) -> None:
        """``cpp.py`` 已实现 ``CppSuggestionExpert``。"""
        cpp_mod = importlib.import_module("modules.suggestion.cpp")
        assert hasattr(cpp_mod, "CppSuggestionExpert")
        assert issubclass(cpp_mod.CppSuggestionExpert, cpp_mod.SuggestionExpert)