"""针对 ``modules.checker.python`` 的测试。

按 ``API_DOCS.md`` 描述覆盖:

* ``Flake8Checker`` — flake8 已装 / 未装 / 文件不存在 / 语法错误,以及
  ``_code_to_level`` 错误码 → 级别 的映射。
* ``PyrightChecker`` — pyright 未装 / JSON 输出 / 文本输出回退。
* ``CPythonChecker`` — 正常执行 / 运行时错误 / 超时 / 文件不存在。

为了不依赖外部工具,使用 ``monkeypatch`` 把 ``subprocess.run`` 替换为
受测可控的 ``FakeProc``。
"""

from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass
from typing import Any

import pytest

from modules.checker.python import (
    CPYTHON_CHECK_FAILED,
    CPythonChecker,
    FLAKE8_NOT_FOUND,
    Flake8Checker,
    PYRIGHT_NOT_FOUND,
    PyrightChecker,
)




@dataclass
class FakeProc:
    """``subprocess.CompletedProcess`` 替代品,可在测试中按需构造。"""

    returncode: int = 0
    stdout: str = ""
    stderr: str = ""
    raise_exc: BaseException | None = None


def _make_run_script(
    monkeypatch: pytest.MonkeyPatch,
    responses: list[FakeProc],
):
    """构造一个 ``FakeProc`` 队列,返回一个 ``subprocess.run`` 的替代函数。"""

    queue = list(responses)

    def fake_run(*args: Any, **kwargs: Any) -> FakeProc:
        if not queue:
            raise AssertionError("subprocess.run called more times than expected")
        item = queue.pop(0)
        if item.raise_exc is not None:
            raise item.raise_exc
        return item

    monkeypatch.setattr(subprocess, "run", fake_run)
    return fake_run




@pytest.fixture()
def tmp_python_file(tmp_path):
    """返回一个简单合法 Python 文件的路径(无扩展名的盘符前缀)。"""
    path = tmp_path / "ok.py"
    path.write_text("x = 1\n", encoding="utf-8")
    return str(path)


@pytest.fixture()
def fake_path() -> str:
    """flake8 / pyright 输出格式里的路径占位符(不带 ``C:`` 前缀)。"""
    return "ok.py"


@pytest.fixture()
def tmp_bad_syntax_file(tmp_path):
    """包含语法错误的 Python 文件。"""
    path = tmp_path / "bad.py"
    path.write_text("def foo(:\n", encoding="utf-8")
    return str(path)




class TestFlake8CheckerCodeToLevel:
    """``_code_to_level`` 是一组稳定的字符串映射。"""

    @pytest.mark.parametrize(
        "code, expected",
        [
            ("E101", "error"),
            ("E501", "error"),
            ("F401", "error"),
            ("F841", "error"),
            ("W291", "warning"),
            ("W605", "warning"),
            ("C901", "convention"),
            ("C101", "convention"),
            ("N801", "notice"),
            ("N803", "notice"),
            ("X999", "info"),  # 其他
            ("", "info"),
            ("ABC", "info"),
        ],
    )
    def test_code_to_level_mapping(self, code: str, expected: str) -> None:
        assert Flake8Checker._code_to_level(code) == expected


class TestFlake8CheckerRuntime:
    """测试 flake8 子进程集成:有 flake8 输出 / 无 flake8 / 文件不存在。"""

    def test_returns_empty_when_no_flake8_issues(
        self, monkeypatch: pytest.MonkeyPatch, tmp_python_file: str
    ) -> None:
        _make_run_script(monkeypatch, [FakeProc(returncode=0, stdout="", stderr="")])
        out = Flake8Checker().check(tmp_python_file)
        assert out.file == tmp_python_file
        assert out.row == []

    def test_parses_flake8_lines(
        self, monkeypatch: pytest.MonkeyPatch, tmp_python_file: str, fake_path: str
    ) -> None:
        stdout = (
            f"{fake_path}:1:1: E501 line too long\n"
            f"{fake_path}:2:5: W291 trailing whitespace\n"
            f"{fake_path}:3:1: C901 function is too complex\n"
            f"{fake_path}:4:1: N801 class name should be CamelCase\n"
            f"{fake_path}:5:1: Z999 some custom code\n"
        )
        _make_run_script(monkeypatch, [FakeProc(returncode=1, stdout=stdout, stderr="")])

        out = Flake8Checker().check(tmp_python_file)
        levels = [r.level for r in out.row]
        assert levels == ["error", "warning", "convention", "notice", "info"]

    def test_module_not_found_falls_back_to_ast(
        self, monkeypatch: pytest.MonkeyPatch, tmp_python_file: str
    ) -> None:
        """``No module named flake8`` 时,应回退到 ast 语法检查 + 追加 FLAKE8_NOT_FOUND。"""
        _make_run_script(
            monkeypatch,
            [FakeProc(returncode=1, stdout="", stderr="... No module named flake8 ...")],
        )
        out = Flake8Checker().check(tmp_python_file)
        levels = [r.level for r in out.row]
        messages = [r.message for r in out.row]
        assert levels == ["info"]
        assert messages[0] == FLAKE8_NOT_FOUND

    def test_module_not_found_with_syntax_error_reports_it(
        self, monkeypatch: pytest.MonkeyPatch, tmp_bad_syntax_file: str
    ) -> None:
        _make_run_script(
            monkeypatch,
            [FakeProc(returncode=1, stdout="", stderr="... No module named flake8 ...")],
        )
        out = Flake8Checker().check(tmp_bad_syntax_file)
        kinds = [(r.level, r.message) for r in out.row]
        assert any(level == "info" and msg == FLAKE8_NOT_FOUND for level, msg in kinds)
        assert any(level == "error" and "SyntaxError" in msg for level, msg in kinds)

    def test_file_not_found_falls_back_to_error(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path
    ) -> None:
        missing = tmp_path / "does_not_exist.py"
        _make_run_script(
            monkeypatch,
            [FakeProc(returncode=1, stdout="", stderr="... No module named flake8 ...")],
        )
        out = Flake8Checker().check(str(missing))
        kinds = [(r.level, r.message) for r in out.row]
        assert any(level == "info" and msg == FLAKE8_NOT_FOUND for level, msg in kinds)
        assert any(level == "error" and "file not found" in msg for level, msg in kinds)

    def test_flake8_subprocess_failure_skipped(
        self, monkeypatch: pytest.MonkeyPatch, tmp_python_file: str
    ) -> None:
        """``subprocess.run`` 抛 ``FileNotFoundError`` 时,应回退到 ast 检查。"""
        _make_run_script(
            monkeypatch,
            [FakeProc(raise_exc=FileNotFoundError("flake8 binary missing"))],
        )
        out = Flake8Checker().check(tmp_python_file)
        assert any(r.level == "info" and r.message == FLAKE8_NOT_FOUND for r in out.row)

    def test_flake8_timeout_falls_back(
        self, monkeypatch: pytest.MonkeyPatch, tmp_python_file: str
    ) -> None:
        """``subprocess.TimeoutExpired`` 时,同样回退到 ast 检查。"""
        _make_run_script(
            monkeypatch,
            [FakeProc(raise_exc=subprocess.TimeoutExpired(cmd="flake8", timeout=30))],
        )
        out = Flake8Checker().check(tmp_python_file)
        assert any(r.level == "info" and r.message == FLAKE8_NOT_FOUND for r in out.row)

    def test_malformed_flake8_line_skipped(
        self, monkeypatch: pytest.MonkeyPatch, tmp_python_file: str, fake_path: str
    ) -> None:
        """flake8 输出不符合 ``path:row:col: code message`` 格式时,该行被忽略。"""
        stdout = (
            "garbage line without colons\n"
            f"{fake_path}:1:1: W291 ok\n"
            "another:bad:line\n"
        )
        _make_run_script(monkeypatch, [FakeProc(returncode=1, stdout=stdout, stderr="")])
        out = Flake8Checker().check(tmp_python_file)
        assert len(out.row) == 1
        assert out.row[0].level == "warning"




class TestPyrightCheckerRuntime:
    def test_pyright_not_installed_returns_info(
        self, monkeypatch: pytest.MonkeyPatch, tmp_python_file: str
    ) -> None:
        _make_run_script(
            monkeypatch,
            [FakeProc(raise_exc=FileNotFoundError("pyright not installed"))],
        )
        out = PyrightChecker().check(tmp_python_file)
        assert out.file == tmp_python_file
        assert len(out.row) == 1
        assert out.row[0].level == "info"
        assert out.row[0].message == PYRIGHT_NOT_FOUND

    def test_pyright_command_not_found_via_stderr(
        self, monkeypatch: pytest.MonkeyPatch, tmp_python_file: str
    ) -> None:
        _make_run_script(
            monkeypatch,
            [FakeProc(returncode=1, stdout="", stderr="pyright: command not found")],
        )
        out = PyrightChecker().check(tmp_python_file)
        assert len(out.row) == 1
        assert out.row[0].level == "info"
        assert out.row[0].message == PYRIGHT_NOT_FOUND

    def test_pyright_not_recognized_via_stderr(
        self, monkeypatch: pytest.MonkeyPatch, tmp_python_file: str
    ) -> None:
        _make_run_script(
            monkeypatch,
            [FakeProc(returncode=1, stdout="", stderr="'pyright' is not recognized")],
        )
        out = PyrightChecker().check(tmp_python_file)
        assert out.row[0].level == "info"
        assert out.row[0].message == PYRIGHT_NOT_FOUND

    def test_pyright_timeout_falls_back_to_info(
        self, monkeypatch: pytest.MonkeyPatch, tmp_python_file: str
    ) -> None:
        _make_run_script(
            monkeypatch,
            [FakeProc(raise_exc=subprocess.TimeoutExpired(cmd="pyright", timeout=60))],
        )
        out = PyrightChecker().check(tmp_python_file)
        assert out.row[0].level == "info"
        assert out.row[0].message == PYRIGHT_NOT_FOUND

    def test_pyright_json_with_no_diagnostics(
        self, monkeypatch: pytest.MonkeyPatch, tmp_python_file: str
    ) -> None:
        stdout = '{"summary": {"errorCount": 0, "warningCount": 0}, "generalDiagnostics": []}'
        _make_run_script(monkeypatch, [FakeProc(returncode=0, stdout=stdout, stderr="")])
        out = PyrightChecker().check(tmp_python_file)
        assert out.row == []

    def test_pyright_json_with_diagnostics(
        self, monkeypatch: pytest.MonkeyPatch, tmp_python_file: str
    ) -> None:
        import json as _json

        stdout = _json.dumps(
            {
                "summary": {"errorCount": 2, "warningCount": 1},
                "generalDiagnostics": [
                    {"message": "Type error", "severity": "error"},
                    {"message": "Type warning", "severity": "warning"},
                    {"message": "Note info", "severity": "information"},
                ],
            }
        )
        _make_run_script(monkeypatch, [FakeProc(returncode=1, stdout=stdout, stderr="")])
        out = PyrightChecker().check(tmp_python_file)
        levels = [r.level for r in out.row]
        assert levels == ["error", "warning", "info"]
        messages = [r.message for r in out.row]
        assert "Type error" in messages
        assert "Type warning" in messages
        assert "Note info" in messages

    def test_pyright_text_fallback(
        self, monkeypatch: pytest.MonkeyPatch, tmp_python_file: str, fake_path: str
    ) -> None:
        """stdout 不是合法 JSON 时,回退到文本格式解析。

        实现的解析器期望 ``path:line:col:LEVEL message`` 的格式(注意 part[3]
        由 ``split(':', 3)`` 得到并 ``strip()`` 去掉首尾空白,然后 ``startswith``
        ``warning`` / ``information`` / ``error`` 来识别级别)。
        """
        stdout = (
            f"{fake_path}:1:1:error type mismatch\n"
            f"{fake_path}:2:1:warning unused variable\n"
            f"{fake_path}:3:1:information some hint\n"
        )
        _make_run_script(monkeypatch, [FakeProc(returncode=1, stdout=stdout, stderr="")])
        out = PyrightChecker().check(tmp_python_file)
        levels = [r.level for r in out.row]
        assert levels == ["error", "warning", "info"]




class TestCPythonCheckerRuntime:
    def test_successful_execution_returns_empty(
        self, monkeypatch: pytest.MonkeyPatch, tmp_python_file: str
    ) -> None:
        _make_run_script(monkeypatch, [FakeProc(returncode=0, stdout="", stderr="")])
        out = CPythonChecker().check(tmp_python_file)
        assert out.file == tmp_python_file
        assert out.row == []

    def test_runtime_error_is_reported(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path
    ) -> None:
        bad = tmp_path / "runtime_err.py"
        bad.write_text("raise ValueError('boom')\n", encoding="utf-8")
        stderr = (
            "Traceback (most recent call last):\n"
            f'  File "{bad}", line 1, in <module>\n'
            "ValueError: boom\n"
        )
        _make_run_script(monkeypatch, [FakeProc(returncode=1, stdout="", stderr=stderr)])
        out = CPythonChecker().check(str(bad))
        messages = [r.message for r in out.row]
        assert "ValueError: boom" in messages
        assert not any("Traceback" in m for m in messages)
        assert not any(m.startswith('  File "') for m in messages)

    def test_timeout_returns_error_message(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path
    ) -> None:
        path = tmp_path / "slow.py"
        path.write_text("import time; time.sleep(99)\n", encoding="utf-8")
        _make_run_script(
            monkeypatch,
            [FakeProc(raise_exc=subprocess.TimeoutExpired(cmd="python", timeout=30))],
        )
        out = CPythonChecker().check(str(path))
        assert len(out.row) == 1
        assert out.row[0].level == "error"
        assert out.row[0].message == "execution timed out"

    def test_file_not_found(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path
    ) -> None:
        missing = tmp_path / "missing.py"
        out = CPythonChecker().check(str(missing))
        assert len(out.row) == 1
        assert out.row[0].level == "error"
        assert "file not found" in out.row[0].message

    def test_multiple_runtime_errors_all_reported(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path
    ) -> None:
        bad = tmp_path / "multi.py"
        bad.write_text("raise RuntimeError('a')\nraise RuntimeError('b')\n", encoding="utf-8")
        stderr = "RuntimeError: a\nRuntimeError: b\n"
        _make_run_script(monkeypatch, [FakeProc(returncode=1, stdout="", stderr=stderr)])
        out = CPythonChecker().check(str(bad))
        messages = [r.message for r in out.row]
        assert "RuntimeError: a" in messages
        assert "RuntimeError: b" in messages
        assert all(r.level == "error" for r in out.row)

    def test_failed_check_uses_sys_executable(
        self, monkeypatch: pytest.MonkeyPatch, tmp_python_file: str
    ) -> None:
        """应使用 ``sys.executable -c <source>`` 来执行。"""

        captured: dict[str, Any] = {}

        def fake_run(cmd, *args: Any, **kwargs: Any):
            captured["cmd"] = cmd
            captured["kwargs"] = kwargs
            return FakeProc(returncode=0, stdout="", stderr="")

        monkeypatch.setattr(subprocess, "run", fake_run)
        CPythonChecker().check(tmp_python_file)
        cmd = captured["cmd"]
        assert cmd[0] == sys.executable
        assert cmd[1:3] == ["-c", "x = 1\n"]
        assert captured["kwargs"].get("timeout") == 30




class TestConstants:
    def test_constant_values(self) -> None:
        assert FLAKE8_NOT_FOUND == "flake8 is not installed, using basic syntax check only"
        assert PYRIGHT_NOT_FOUND == "pyright is not installed, type checking skipped"
        assert CPYTHON_CHECK_FAILED == "python execution check failed"