import os

import pytest

from core.language.checker import CPythonChecker, Flake8Checker, PyrightChecker


class TestFlake8Checker:
    def test_init(self):
        checker = Flake8Checker()
        assert checker is not None

    def test_check_valid_file(self, sample_python_file):
        checker = Flake8Checker()
        output = checker.check(sample_python_file)
        assert output.file == sample_python_file
        assert isinstance(output.row, list)

    def test_check_nonexistent_file(self):
        checker = Flake8Checker()
        output = checker.check("/nonexistent/path/file.py")
        assert output.file == "/nonexistent/path/file.py"
        assert len(output.row) >= 1

    def test_check_syntax_error(self, sample_syntax_error_file):
        checker = Flake8Checker()
        output = checker.check(sample_syntax_error_file)
        assert output.file == sample_syntax_error_file
        has_issue = len(output.row) >= 1
        assert has_issue

    def test_code_to_level(self):
        assert Flake8Checker._code_to_level("E501") == "error"
        assert Flake8Checker._code_to_level("W503") == "warning"
        assert Flake8Checker._code_to_level("C901") == "convention"
        assert Flake8Checker._code_to_level("N802") == "notice"
        assert Flake8Checker._code_to_level("X100") == "info"


class TestPyrightChecker:
    def test_init(self):
        checker = PyrightChecker()
        assert checker is not None

    def test_check_nonexistent_file(self):
        checker = PyrightChecker()
        output = checker.check("/nonexistent/path/file.py")
        assert output.file == "/nonexistent/path/file.py"
        assert isinstance(output.row, list)


class TestCPythonChecker:
    def test_init(self):
        checker = CPythonChecker()
        assert checker is not None

    def test_check_valid_file(self, sample_python_file):
        checker = CPythonChecker()
        output = checker.check(sample_python_file)
        assert output.file == sample_python_file
        assert isinstance(output.row, list)

    def test_check_nonexistent_file(self):
        checker = CPythonChecker()
        output = checker.check("/nonexistent/path/file.py")
        assert output.file == "/nonexistent/path/file.py"
        assert len(output.row) >= 1
        assert output.row[0].level == "error"

    def test_check_runtime_error(self, temp_dir):
        file_path = os.path.join(temp_dir, "runtime_error.py")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("raise ValueError('test error')\n")
        checker = CPythonChecker()
        output = checker.check(file_path)
        assert output.file == file_path
        has_error = any(row.level == "error" for row in output.row)
        assert has_error
