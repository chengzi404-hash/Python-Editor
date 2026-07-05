"""针对 ``modules.highlighter.base`` 的测试。

覆盖:

* ``HighlightToken`` 数据类
* ``HighlightBlock`` 数据类
* ``HighlighterExpert`` 抽象基类(无法直接实例化、抽象方法必须被子类实现)
"""

from __future__ import annotations

import pytest

from modules.highlighter import (
    HighlightBlock,
    HighlightToken,
    HighlighterExpert,
)
from modules.highlighter.base import HighlighterExpert as DirectHighlighterExpert


# ---------------------------------------------------------------------------
# HighlightToken
# ---------------------------------------------------------------------------


class TestHighlightToken:
    """``HighlightToken`` 是一个简单的 dataclass,字段为 ``start`` / ``end`` / ``type``。"""

    def test_basic_construction(self) -> None:
        token = HighlightToken(start=0, end=4, type="keyword")
        assert token.start == 0
        assert token.end == 4
        assert token.type == "keyword"

    def test_equality(self) -> None:
        """dataclass 默认应支持 ``==`` 比较。"""
        a = HighlightToken(start=1, end=5, type="string")
        b = HighlightToken(start=1, end=5, type="string")
        c = HighlightToken(start=1, end=5, type="comment")
        assert a == b
        assert a != c

    def test_mutable_fields(self) -> None:
        token = HighlightToken(start=0, end=1, type="x")
        token.type = "y"
        assert token.type == "y"

    def test_required_fields(self) -> None:
        """缺少任意字段都应抛出 ``TypeError``。"""
        with pytest.raises(TypeError):
            HighlightToken(start=0, end=1)  # type: ignore[call-arg]
        with pytest.raises(TypeError):
            HighlightToken(end=1, type="x")  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# HighlightBlock
# ---------------------------------------------------------------------------


class TestHighlightBlock:
    """``HighlightBlock.code`` 必填,``tokens`` 默认为 ``None``。"""

    def test_default_tokens_is_none(self) -> None:
        block = HighlightBlock(code="print(1)")
        assert block.code == "print(1)"
        assert block.tokens is None

    def test_explicit_tokens(self) -> None:
        tokens = [HighlightToken(0, 5, "builtin")]
        block = HighlightBlock(code="print", tokens=tokens)
        assert block.tokens is not None
        assert len(block.tokens) == 1
        assert block.tokens[0].type == "builtin"

    def test_equality(self) -> None:
        block_a = HighlightBlock(code="x", tokens=None)
        block_b = HighlightBlock(code="x", tokens=None)
        assert block_a == block_b

    def test_empty_code(self) -> None:
        """空字符串也是合法的源码。"""
        block = HighlightBlock(code="")
        assert block.code == ""
        assert block.tokens is None


# ---------------------------------------------------------------------------
# HighlighterExpert
# ---------------------------------------------------------------------------


class TestHighlighterExpert:
    """抽象基类:不应能被直接实例化,且必须能被继承。"""

    def test_cannot_instantiate_abstract_class(self) -> None:
        with pytest.raises(TypeError):
            HighlighterExpert()  # type: ignore[abstract]

    def test_must_implement_highlight(self) -> None:
        """只实现 ``highlight`` 时,``get_languange_exts`` 仍是抽象的,无法实例化。"""

        class Partial(HighlighterExpert):
            # 只覆盖 highlight,保留 get_languange_exts 为抽象
            def highlight(self, block: HighlightBlock) -> HighlightBlock:  # type: ignore[override]
                return block

        with pytest.raises(TypeError):
            Partial()

    def test_must_implement_get_languange_exts(self) -> None:
        """只实现 ``get_languange_exts`` 时,``highlight`` 仍是抽象的,无法实例化。"""

        class Partial(HighlighterExpert):
            # 只覆盖 get_languange_exts,保留 highlight 为抽象
            def get_languange_exts(self) -> list:  # type: ignore[override]
                return ["x"]

        with pytest.raises(TypeError):
            Partial()

    def test_concrete_subclass_can_be_instantiated(self) -> None:
        """两个抽象方法都实现后应可正常实例化。"""

        class Concrete(HighlighterExpert):
            def highlight(self, block: HighlightBlock) -> HighlightBlock:  # type: ignore[override]
                return block

            def get_languange_exts(self) -> list:  # type: ignore[override]
                return ["x"]

        c = Concrete()
        assert c.get_languange_exts() == ["x"]
        assert c.highlight(HighlightBlock(code="")) .code == ""

    def test_same_class_imported_from_submodule(self) -> None:
        """顶层 ``modules.highlighter`` 与 ``modules.highlighter.base`` 应导出同一个类。"""
        assert HighlighterExpert is DirectHighlighterExpert