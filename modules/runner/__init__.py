"""``modules.runner`` — 子进程执行与输出采集.

公开 API:

* :class:`RunResult` —— 进程结束结果。
* :func:`stream_command` —— 异步流式执行 + 行回调。
* :func:`run_blocking` —— 同步 ``subprocess.run`` 包装, 在流式关闭时使用。
"""

from .runner import RunResult, run_blocking, stream_command

__all__ = ["RunResult", "run_blocking", "stream_command"]
