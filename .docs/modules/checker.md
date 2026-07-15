# `modules.checker`

**Source**:
- [`modules/checker/__init__.py`](../../modules/checker/__init__.py) — 12 lines
- [`modules/checker/base.py`](../../modules/checker/base.py) — 21 lines
- [`modules/checker/python.py`](../../modules/checker/python.py) — 198 lines

Static-analysis backends for Python files. Three implementations of the same
abstract `Checker` interface are provided; the editor picks whichever tools
are installed.

```python
from modules.checker import (
    OutputRow, Output, Checker,
    Flake8Checker, PyrightChecker, CPythonChecker,
)
```

## Data model

### `OutputRow` `[base.py:6]`

```python
@dataclass
class OutputRow:
    message: str
    level: str        # 'error' | 'warning' | 'convention' | 'notice' | 'info'
```

### `Output` `[base.py:11]`

```python
@dataclass
class Output:
    file: str
    row: list[OutputRow]
```

### `Checker` `[base.py:15]`

```python
class Checker(ABC):
    @abstractmethod
    def check(self, file: str) -> Output: ...
```

A `Checker` consumes a file path and returns all diagnostics for it. There
is no streaming; the entire result fits in one `Output`.

## Implementations

### `Flake8Checker` `[python.py:11]`

Runs `python -m flake8` against the file and parses its line-oriented output.

| Behaviour | Detail |
| --- | --- |
| Success | Parses each `path:line:col: CODE message` row and maps the code prefix to a level (`E`/`F`→`error`, `W`→`warning`, `C`→`convention`, `N`→`notice`). |
| Module missing | Emits `FLAKE8_NOT_FOUND` at level `info` and falls back to `ast.parse` syntax check. |
| Subprocess timeout | 30 seconds; `subprocess.TimeoutExpired` triggers the same fallback as above. |

### `PyrightChecker` `[python.py:84]`

Runs `pyright --outputjson` against the file.

| Behaviour | Detail |
| --- | --- |
| JSON output | Parses `generalDiagnostics` and `summary`. Levels are mapped `error`/`warning`/`information` → `error`/`warning`/`info`. |
| Plain-text fallback | Splits on `:` and detects `warning` / `information` / `error` prefixes. |
| Tool missing | Emits `PYRIGHT_NOT_FOUND` at level `info` and returns. |
| Subprocess timeout | 60 seconds. |

### `CPythonChecker` `[python.py:160]`

Executes the file with the interpreter running `main.py`:

```
python -c <source>
```

| Behaviour | Detail |
| --- | --- |
| Non-zero exit | Each line of stderr (after stripping `Traceback` markers and file frames) becomes an `OutputRow` at level `error`. |
| Timeout | 30 seconds; emits `execution timed out`. |
| Read failure | Emits `file not found: …` or `cannot read file: …` at level `error`. |

This checker is **destructive** — it actually runs the code. Use only for
short, safe scripts, or replace with a sandboxed runner.

## Module-level constants `[python.py]`

| Name | Line | Value |
| --- | --- | --- |
| `FLAKE8_NOT_FOUND` | 8 | `'flake8 is not installed, using basic syntax check only'` |
| `PYRIGHT_NOT_FOUND` | 81 | `'pyright is not installed, type checking skipped'` |
| `CPYTHON_CHECK_FAILED` | 157 | `'python execution check failed'` (currently unused; reserved for future use) |

## Usage pattern

```python
from modules.checker import Flake8Checker, PyrightChecker, CPythonChecker

checker = Flake8Checker()             # or PyrightChecker() / CPythonChecker()
result = checker.check("/path/to/file.py")
for row in result.row:
    print(row.level.upper(), row.message)
```

The editor (`main.py:_run_check`) constructs all three and runs them in
sequence, picking the first that succeeds.