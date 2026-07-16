import ast
import subprocess
import sys

from .base import Checker, Output, OutputRow

FLAKE8_NOT_FOUND = "flake8 is not installed, using basic syntax check only"


class Flake8Checker(Checker):
    def __init__(self) -> None:
        super().__init__()

    def check(self, file: str) -> Output:
        output = Output(file=file, row=[])

        if self._try_flake8(file, output):
            return output

        output.row.append(OutputRow(message=FLAKE8_NOT_FOUND, level="info"))
        self._syntax_check(file, output)
        return output

    def _try_flake8(self, file: str, output: Output) -> bool:
        try:
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "flake8",
                    "--format",
                    "%(path)s:%(row)d:%(col)d: %(code)s %(text)s",
                    file,
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

        if result.returncode != 0 and result.stderr and "No module named flake8" in result.stderr:
            return False

        for line in result.stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            parts = line.split(":", 3)
            if len(parts) < 4:
                continue
            code = parts[3].strip().split(" ")[0] if " " in parts[3] else parts[3].strip()
            message = parts[3].strip()
            level = self._code_to_level(code)
            output.row.append(OutputRow(message=message, level=level))

        return True

    @staticmethod
    def _code_to_level(code: str) -> str:
        if code.startswith("E") or code.startswith("F"):
            return "error"
        if code.startswith("W"):
            return "warning"
        if code.startswith("C"):
            return "convention"
        if code.startswith("N"):
            return "notice"
        return "info"

    @staticmethod
    def _syntax_check(file: str, output: Output) -> None:
        try:
            with open(file, encoding="utf-8") as f:
                source = f.read()
        except FileNotFoundError:
            output.row.append(OutputRow(message=f"file not found: {file}", level="error"))
            return
        except OSError as e:
            output.row.append(OutputRow(message=f"cannot read file: {e}", level="error"))
            return

        try:
            ast.parse(source, filename=file)
        except SyntaxError as e:
            msg = f"SyntaxError at line {e.lineno}, column {e.offset}: {e.msg}"
            output.row.append(OutputRow(message=msg, level="error"))


PYRIGHT_NOT_FOUND = "pyright is not installed, type checking skipped"


class PyrightChecker(Checker):
    def __init__(self) -> None:
        super().__init__()

    def check(self, file: str) -> Output:
        output = Output(file=file, row=[])

        if self._try_pyright(file, output):
            return output

        output.row.append(OutputRow(message=PYRIGHT_NOT_FOUND, level="info"))
        return output

    def _try_pyright(self, file: str, output: Output) -> bool:
        try:
            result = subprocess.run(
                ["pyright", "--outputjson", file], capture_output=True, text=True, timeout=60
            )
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

        if result.returncode == 0 and not result.stdout:
            return True

        if result.stderr and "command not found" in result.stderr.lower():
            return False
        if result.stderr and "not recognized" in result.stderr.lower():
            return False

        import json

        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError:
            for line in result.stdout.splitlines():
                line = line.strip()
                if not line:
                    continue
                parts = line.split(":", 3)
                if len(parts) < 4:
                    continue
                rest = parts[3].strip()
                if rest.startswith(" - "):
                    rest = rest[3:]
                level = "error"
                if rest.startswith("warning"):
                    level = "warning"
                    rest = rest[8:].strip()
                elif rest.startswith("information"):
                    level = "info"
                    rest = rest[12:].strip()
                elif rest.startswith("error"):
                    rest = rest[6:].strip()
                output.row.append(OutputRow(message=rest, level=level))
            return True

        summary = data.get("summary", {})
        diagnostics = data.get("generalDiagnostics", [])
        if not diagnostics:
            return True

        for diag in diagnostics:
            message = diag.get("message", "")
            severity = diag.get("severity", "error")
            level_map = {"error": "error", "warning": "warning", "information": "info"}
            level = level_map.get(severity, "error")
            output.row.append(OutputRow(message=message, level=level))

        if summary.get("errorCount", 0) == 0 and summary.get("warningCount", 0) == 0:
            pass

        return True


CPYTHON_CHECK_FAILED = "python execution check failed"


class CPythonChecker(Checker):
    def __init__(self) -> None:
        super().__init__()

    def check(self, file: str) -> Output:
        output = Output(file=file, row=[])

        try:
            with open(file, encoding="utf-8") as f:
                source = f.read()
        except FileNotFoundError:
            output.row.append(OutputRow(message=f"file not found: {file}", level="error"))
            return output
        except OSError as e:
            output.row.append(OutputRow(message=f"cannot read file: {e}", level="error"))
            return output

        try:
            result = subprocess.run(
                [sys.executable, "-c", source], capture_output=True, text=True, timeout=30
            )
        except subprocess.TimeoutExpired:
            output.row.append(OutputRow(message="execution timed out", level="error"))
            return output

        if result.returncode != 0:
            for line in result.stderr.splitlines():
                line = line.strip()
                if not line:
                    continue
                if "Traceback (most recent call last)" in line:
                    continue
                if line.startswith('  File "'):
                    continue
                level = "error"
                output.row.append(OutputRow(message=line, level=level))

        return output
