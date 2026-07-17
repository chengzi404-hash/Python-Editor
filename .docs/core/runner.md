# `core.runner`

**Source**:
- [`__init__.py`](../../core/runner/__init__.py) — 12 lines
- [`runner.py`](../../core/runner/runner.py) — 186 lines

Subprocess execution and output collection. Only one core API is
exposed: `stream_command`. It launches a subprocess, streams
stdout/stderr line-by-line to the caller in real time, and calls the
`done` callback when the subprocess exits (or times out). The module
intentionally has no dependency on Tk or any UI framework — output is
passed through plain callbacks, and upper layers use mechanisms like
`tkinter.Tk.after` to dispatch lines to the main thread.

```python
from core.runner import RunResult, stream_command, run_blocking
```

## `RunResult` `[runner.py:26]`

```python
@dataclass(frozen=True)
class RunResult:
    returncode: int
    timed_out: bool = False
```

- `returncode` — Process exit code; `0` is normal, `-1` usually
  indicates forced termination (e.g. after a `kill` followed by a
  failed `wait`).
- `timed_out` — Whether the process was actively ended due to timeout.

## `stream_command` `[runner.py:45]`

```python
def stream_command(
    cmd: list[str],
    *,
    timeout_s: float = 30.0,
    cwd: str | None = None,
    env: dict[str, str] | None = None,
    line_callback: Callable[[str, str], None] | None = None,
    done_callback: Callable[[RunResult], None] | None = None,
) -> tuple[subprocess.Popen, threading.Thread]:
```

Asynchronously stream-execute `cmd`; stdout/stderr pushed line-by-line
to the callback.

| Parameter | Description |
| --- | --- |
| `cmd` | Command and arguments, as a list. |
| `timeout_s` | Total timeout in seconds; process is `kill()`ed on timeout. |
| `cwd` | Subprocess working directory; `None` inherits from parent. |
| `env` | Subprocess environment; `None` inherits from parent. |
| `line_callback` | `(stream_name, line)` callback. `stream_name` is `"stdout"` or `"stderr"`. Thread safety is the caller's responsibility. |
| `done_callback` | Called once when subprocess ends (normal / failure / timeout); receives `RunResult`. |

**Note**: stdin is fixed to `DEVNULL`. The editor does not pipe
interactive input, and this prevents the subprocess from blocking when
there is no consumer.

**Returns**: `(process, supervisor_thread)`. The caller keeps the
`process` handle to `terminate()` it if needed (the `done_callback` is
still called). `supervisor_thread` is a daemon thread and is reclaimed
on program exit; no `join()` is needed.

### Implementation notes

- `text=True, bufsize=1` so the subprocess flushes line-by-line;
  `Popen` keeps the two streams non-blocking.
- Two daemon threads drain stdout / stderr independently — one stream
  blocking does not stop the other.
- The supervisor thread `wait()`s on the process, `kill()`s on timeout
  and waits for exit; then `join()`s the two drain threads (they end
  naturally on EOF) and finally triggers `done_callback`.

## `run_blocking` `[runner.py:167]`

```python
def run_blocking(
    cmd: list[str],
    *,
    timeout_s: float = 30.0,
    cwd: str | None = None,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess:
```

Synchronous `subprocess.run` wrapper. Returns
`subprocess.CompletedProcess`. Used by `CPythonChecker` and quick
utility tasks where streaming is unnecessary.

## Public surface

`__all__ = ["RunResult", "run_blocking", "stream_command"]`.