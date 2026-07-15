# `modules/runner/__init__.py`

源文件路径：`modules/runner/__init__.py`

`modules.runner` 包的公开入口。子进程执行与输出采集。

## 公开 API

- `RunResult` — 子进程结束后的结果数据类（`returncode` / `timed_out`）。
- `stream_command` — 异步流式执行 + 行回调。
- `run_blocking` — 同步 `subprocess.run` 包装，在流式关闭时被使用。

## `__all__`

```python
["RunResult", "stream_command", "run_blocking"]
```