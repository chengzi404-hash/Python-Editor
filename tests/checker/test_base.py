import pytest

from modules.checker.base import Checker, Output, OutputRow


class MockChecker(Checker):
    def check(self, file: str) -> Output:
        return Output(file=file, row=[OutputRow(message="test", level="info")])


class TestCheckerBase:
    def test_output_row_creation(self):
        row = OutputRow(message="test message", level="error")
        assert row.message == "test message"
        assert row.level == "error"

    def test_output_creation(self):
        output = Output(file="test.py", row=[])
        assert output.file == "test.py"
        assert output.row == []

    def test_output_with_rows(self):
        rows = [
            OutputRow(message="error 1", level="error"),
            OutputRow(message="warning 1", level="warning"),
        ]
        output = Output(file="test.py", row=rows)
        assert len(output.row) == 2
        assert output.row[0].message == "error 1"
        assert output.row[1].level == "warning"

    def test_checker_is_abstract(self):
        with pytest.raises(TypeError):
            Checker()
