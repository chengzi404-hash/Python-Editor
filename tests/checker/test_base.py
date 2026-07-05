"""针对 ``modules.checker.base`` 的测试。

覆盖:

* ``OutputRow`` 数据类
* ``Output`` 数据类
* ``Checker`` 抽象基类(无法直接实例化、抽象方法必须被子类实现)
"""

from __future__ import annotations

import pytest

from modules.checker import Checker, Output, OutputRow
from modules.checker.base import Checker as DirectChecker


# ---------------------------------------------------------------------------
# OutputRow
# ---------------------------------------------------------------------------


class TestOutputRow:
    """``OutputRow`` 包含 ``message`` 与 ``level`` 两个字段。"""

    def test_basic_construction(self) -> None:
        row = OutputRow(message="something", level="error")
        assert row.message == "something"
        assert row.level == "error"

    def test_equality(self) -> None:
        a = OutputRow(message="x", level="warning")
        b = OutputRow(message="x", level="warning")
        c = OutputRow(message="x", level="error")
        d = OutputRow(message="y", level="warning")
        assert a == b
        assert a != c
        assert a != d

    def test_supported_levels(self) -> None:
        """API 文档允许 ``error/warning/convention/notice/info``。"""
        for level in ("error", "warning", "convention", "notice", "info"):
            row = OutputRow(message="m", level=level)
            assert row.level == level


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------


class TestOutput:
    """``Output`` 包含 ``file`` 与 ``row`` 列表。"""

    def test_basic_construction(self) -> None:
        out = Output(file="a.py", row=[])
        assert out.file == "a.py"
        assert out.row == []

    def test_with_rows(self) -> None:
        rows = [
            OutputRow(message="m1", level="error"),
            OutputRow(message="m2", level="warning"),
        ]
        out = Output(file="b.py", row=rows)
        assert out.file == "b.py"
        assert len(out.row) == 2
        assert out.row[0].level == "error"
        assert out.row[1].level == "warning"

    def test_equality(self) -> None:
        out_a = Output(file="x.py", row=[OutputRow("a", "info")])
        out_b = Output(file="x.py", row=[OutputRow("a", "info")])
        assert out_a == out_b

    def test_mutation(self) -> None:
        """``row`` 应允许就地追加。"""
        out = Output(file="c.py", row=[])
        out.row.append(OutputRow(message="new", level="notice"))
        assert len(out.row) == 1
        assert out.row[0].level == "notice"


# ---------------------------------------------------------------------------
# Checker
# ---------------------------------------------------------------------------


class TestChecker:
    """``Checker`` 是抽象基类,不能直接实例化,必须被子类继承实现 ``check``。"""

    def test_cannot_instantiate_abstract_class(self) -> None:
        with pytest.raises(TypeError):
            Checker()  # type: ignore[abstract]

    def test_subclass_without_check_cannot_instantiate(self) -> None:
        class Partial(Checker):
            # 未实现 check
            pass

        with pytest.raises(TypeError):
            Partial()

    def test_subclass_with_check_can_instantiate(self) -> None:
        class Concrete(Checker):
            def check(self, file: str) -> Output:  # type: ignore[override]
                return Output(file=file, row=[])

        c = Concrete()
        out = c.check("example.py")
        assert isinstance(out, Output)
        assert out.file == "example.py"
        assert out.row == []

    def test_same_class_imported_from_submodule(self) -> None:
        """``modules.checker`` 与 ``modules.checker.base`` 应导出同一个 ``Checker`` 类。"""
        assert Checker is DirectChecker