# `modules.runner`

**Source**:
- [`__init__.py`](../../modules/runner/__init__.py) — 13 lines
- [`runner.py`](../../modules/runner/runner.py) — 187 lines

Subprocess execution with two flavours:

- `stream_command()` — async, line-by-line callbacks (used by the editor's
  Run action).
- `run_blocking()` — synchronous, returns the entire result (used by
  `CPythonChecker` and quick utility tasks).

```python
from modules.runner import RunResult, stream_command, run_blocking
```

## `RunResult` `[runner.py:24]`

```python
@dataclass(frozen=True)
class RunResult:
    returncode: int          # 0 on success; -1 indicates forced kill
    timed_out: bool = False
```

Returned to the `done_callback` of `stream_command()` and from
`run_blocking()` via `CompletedProcess.returncode` (the latter does not
produce a `RunResult`).

## `stream_command(cmd, *, timeout_s=30.0, cwd=None, env=None, line_callback=None, done_callback=None)` `[runner.py:43]`

```python
def stream_command(
    cmd: List[str],
    *,
    timeout_s: float = 30.0,
    cwd: Optional[str] = None,
    env: Optional[Dict[str, str]] = None,
    line_callback: Optional[Callable[[str, str], None]] = None,
    done_callback: Optional[Callable[[RunResult], None]] = None,
) -> Tuple[subprocess.Popen, threading.Thread]: ...
```

| Parameter | Description |
| --- | --- |
| `cmd` | Command + arguments as a list. |
| `timeout_s` | Total runtime budget in seconds. After expiry the process is `kill()`-ed. |
| `cwd` | Subprocess working directory. `None` inherits. |
| `env` | Subprocess environment. `None` inherits. |
| `line_callback` | `callback("stdout" \| "stderr", line)` called from drain threads. Exceptions in the callback are swallowed. |
| `done_callback` | `callback(RunResult)` called exactly once after the process exits (normal, error, or timeout). |

**Returns**: `(Popen, supervisor_thread)`. The caller may keep the
`Popen` handle to `terminate()` the process; the supervisor thread is a
daemon and is collected on program exit.

### Internal design

- `Popen` is started with `text=True, bufsize=1` so subprocess output is
  line-buffered.
- `stdin=DEVNULL` to prevent child processes from blocking on input.
- Two daemon threads drain stdout and stderr independently — if one
  stalls (e.g. terminal screen with no reader), the other keeps
  progressing, avoiding a pipe-buffer deadlock.
- The supervisor thread `wait(timeout=...)`; on `TimeoutExpired`, it kills
  the process and waits 2 more seconds for clean termination. It then
  joins the drain threads (capped at 2 seconds) before invoking
  `done_callback`.

### Example

```python
from modules.runner import stream_command

def on_line(stream, line):
    print(f"[{stream}] {line}", end='')

def on_done(result):
    print("returncode =", result.returncode, "timed_out =", result.timed_out)

stream_command(
    ["python", "-u", "script.py"],
    timeout_s=10.0,
    line_callback=on_line,
    done_callback=on_done,
)
```

## `run_blocking(cmd, *, timeout_s=30.0, cwd=None, env=None) -> subprocess.CompletedProcess` `[runner.py:168]`

Thin wrapper around `subprocess.run(...)` with:

- `capture_output=True`
- `text=True`
- `timeout=timeout_s`

Returns a normal `CompletedProcess`; on timeout `subprocess.TimeoutExpired`
is raised to the caller (no callback). Used by `CPythonChecker`.