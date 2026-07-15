# `modules/runner/runner.py`

源文件路径：`modules/runner/runner.py`

子进程执行与输出采集。不依赖任何 UI 框架，输出通过回调传出，便于上层在主线程中投递。

## 数据类

### `RunResult`（`@dataclass(frozen=True)`）
- `returncode: int` — 进程退出码；`-1` 表示被强制终止（如超时后 `kill`）。
- `timed_out: bool = False` — 是否因超时被主动结束。

## 函数

### `stream_command(cmd, *, timeout_s=30.0, cwd=None, env=None, line_callback=None, done_callback=None) -> Tuple[subprocess.Popen, threading.Thread]`
异步启动子进程并流式回调 stdout/stderr。
- `cmd: List[str]` — 命令及其参数。
- `timeout_s: float` — 总超时；超时后调用 `process.kill()` 并再 `wait(2s)`。
- `cwd: Optional[str]`、`env: Optional[Dict[str, str]]` — 子进程工作目录/环境变量。
- `line_callback: Optional[Callable[[str, str], None]]` — `(stream_name, line)` 回调，`stream_name ∈ {"stdout", "stderr"}`；为 `None` 时仍需 drain 流，否则 pipe 缓冲区写满会导致子进程阻塞。
- `done_callback: Optional[Callable[[RunResult], None]]` — 子进程结束（正常 / 失败 / 超时）时调用一次。
- 固定 `stdin=subprocess.DEVNULL`，防止无消费者时阻塞。
- 使用 `text=True, bufsize=1`，`Popen(stdout=PIPE, stderr=PIPE)` 避免两流互锁。
- 内部启三条守护线程：stdout drain、stderr drain、supervisor。supervisor 调用 `wait()` 等待进程结束，再 `join()` 两个 drain 线程，最后触发 `done_callback`。
- 返回 `(process, supervisor_thread)`。`process` 可由调用方 `terminate()` 主动取消；supervisor 线程为守护线程，进程退出时自动回收，无需 `join`。

### `run_blocking(cmd, *, timeout_s=30.0, cwd=None, env=None) -> subprocess.CompletedProcess`
同步执行 `cmd`，使用 `subprocess.run(capture_output=True, text=True, timeout=...)`。返回 `CompletedProcess`。

## `__all__`

```python
["RunResult", "stream_command", "run_blocking"]
```