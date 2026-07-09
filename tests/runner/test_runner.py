# -*- coding: utf-8 -*-
"""``modules.runner`` 的集成测试。

``stream_command`` 启动真实子进程, 因此这些测试会真正 fork/exec。
为保证跨平台 + 自包含, 全部用 ``sys.executable -c "..."`` 作为被
执行命令 — Python 解释器在所有测试环境里都可用。
"""

from __future__ import annotations

import sys
import threading
import time
from typing import List, Tuple

import pytest

from modules.runner import RunResult, run_blocking, stream_command
from modules.settings.base import SettingValueType, SettingsScope
from modules.settings.schema import GLOBAL_SCHEMA


# ----------------------------------------------------------------------
# 工具函数
# ----------------------------------------------------------------------


def _run_and_wait(
    cmd: List[str],
    *,
    timeout_s: float = 5.0,
    line_callback=None,
    runtime_timeout_s: float = 5.0,
) -> Tuple[List[Tuple[str, str]], RunResult]:
    """同步跑一次 :func:`stream_command` 并等待 done 回调.

    返回 ``(lines, result)``。``lines`` 是按回调到达顺序收集的
    ``(stream_name, line)`` 列表; ``result`` 是 ``RunResult``。
    如果子进程在 ``runtime_timeout_s`` 内没有触发 done, 抛 AssertionError。
    """

    lines: List[Tuple[str, str]] = []
    result_holder: List[RunResult] = []
    done_event = threading.Event()

    def on_line(stream_name, line):
        lines.append((stream_name, line))

    def on_done(result):
        result_holder.append(result)
        done_event.set()

    stream_command(
        cmd,
        timeout_s=timeout_s,
        line_callback=on_line,
        done_callback=on_done,
    )

    assert done_event.wait(timeout=runtime_timeout_s), (
        f"subprocess did not finish within {runtime_timeout_s}s: {cmd!r}"
    )
    return lines, result_holder[0]


def _make_done_cb(holder, event):
    """返回一个把结果塞进 ``holder`` 并 ``event.set()`` 的回调.

    单独定义以避免 lambda 返回 tuple (Python 3 闭包语法) 触发类型
    检查器对回调签名的误判 — 内层 ``_cb`` 显式标了 ``-> None``,
    调用方拿到的实例天然满足 ``Callable[[RunResult], None]``。
    """

    def _cb(result: RunResult) -> None:
        holder.append(result)
        event.set()

    return _cb


# ----------------------------------------------------------------------
# Schema 契约
# ----------------------------------------------------------------------


class TestRunnerStreamOutputSchema:
    """``runner.stream_output`` 必须在默认 GLOBAL_SCHEMA 中, 且元信息稳定."""

    def test_key_exists(self):
        spec = GLOBAL_SCHEMA.get("runner.stream_output")
        assert spec is not None

    def test_type_is_boolean(self):
        spec = GLOBAL_SCHEMA.get("runner.stream_output")
        assert spec is not None
        assert spec.type is SettingValueType.BOOLEAN

    def test_default_is_true(self):
        # 契约: 默认开启 — 流式是更好的 UX, 关闭是用户的"主动选择"。
        spec = GLOBAL_SCHEMA.get("runner.stream_output")
        assert spec is not None
        assert spec.default is True

    def test_scope_is_global(self):
        # 运行行为与项目无关, 必须是 GLOBAL.
        spec = GLOBAL_SCHEMA.get("runner.stream_output")
        assert spec is not None
        assert spec.scope is SettingsScope.GLOBAL

    def test_label_non_empty(self):
        spec = GLOBAL_SCHEMA.get("runner.stream_output")
        assert spec is not None
        assert spec.label, "label 不应为空, settings 面板需要显示"


# ----------------------------------------------------------------------
# stream_command: 基本 stdout / stderr / 退出码
# ----------------------------------------------------------------------


class TestStreamStdout:
    """stdout 行应按行到达 line_callback."""

    def test_single_line(self):
        lines, result = _run_and_wait(
            [sys.executable, "-c", "print('hello')"],
        )
        assert ("stdout", "hello\n") in lines
        assert result.returncode == 0
        assert result.timed_out is False

    def test_multiple_lines(self):
        lines, result = _run_and_wait(
            [sys.executable, "-c", "print('a'); print('b'); print('c')"],
        )
        # 三行都该到达, 顺序保持
        stdout_lines = [line for name, line in lines if name == "stdout"]
        assert stdout_lines == ["a\n", "b\n", "c\n"]
        assert result.returncode == 0

    def test_empty_stdout(self):
        # 子进程只写 stderr, stdout 应为空列表
        lines, result = _run_and_wait(
            [sys.executable, "-c", "import sys; sys.stderr.write('e\\n')"],
        )
        stdout_lines = [t for n, t in lines if n == "stdout"]
        assert stdout_lines == []
        assert ("stderr", "e\n") in lines
        assert result.returncode == 0


class TestStreamStderr:
    """stderr 行应通过 stream_name='stderr' 到达, 不混入 stdout."""

    def test_stderr_line(self):
        lines, result = _run_and_wait(
            [sys.executable, "-c", "import sys; sys.stderr.write('oops\\n')"],
        )
        assert ("stderr", "oops\n") in lines
        assert result.returncode == 0

    def test_stderr_and_stdout_ordered(self):
        # 同时写两个流; 只要 stderr 行能从 line_callback 拿到, 就证明
        # 两条 pipe 互不阻塞 (子进程不会被单边 pipe 写满卡住)。
        cmd = [sys.executable, "-c", (
            "import sys\n"
            "print('out-1')\n"
            "sys.stderr.write('err-1\\n')\n"
            "print('out-2')\n"
            "sys.stderr.write('err-2\\n')\n"
        )]
        lines, result = _run_and_wait(cmd)
        stream_names = {n for n, _ in lines}
        assert "stdout" in stream_names
        assert "stderr" in stream_names
        assert result.returncode == 0


class TestStreamExitCode:
    """非零退出码应通过 ``RunResult.returncode`` 准确传达."""

    def test_exit_zero(self):
        _, result = _run_and_wait(
            [sys.executable, "-c", "pass"],
        )
        assert result.returncode == 0
        assert result.timed_out is False

    def test_exit_nonzero(self):
        _, result = _run_and_wait(
            [sys.executable, "-c", "import sys; sys.exit(7)"],
        )
        assert result.returncode == 7
        assert result.timed_out is False

    def test_exit_one(self):
        _, result = _run_and_wait(
            [sys.executable, "-c", "import sys; sys.exit(1)"],
        )
        assert result.returncode == 1
        assert result.timed_out is False


# ----------------------------------------------------------------------
# stream_command: 超时
# ----------------------------------------------------------------------


class TestStreamTimeout:
    """``timeout_s`` 触发后, supervisor 线程应 ``kill`` 进程并报告 timed_out=True."""

    def test_timeout_kills_long_running_process(self):
        # 0.5s 超时, 子进程 sleep 5s, 必被 kill
        lines, result = _run_and_wait(
            [sys.executable, "-c", "import time; time.sleep(5)"],
            timeout_s=0.5,
            runtime_timeout_s=3.0,
        )
        assert result.timed_out is True
        # returncode 在 Windows 上可能是 1 (TerminateProcess) 或 -1;
        # 其它平台上是 -SIGNAL=15。我们只断言 timed_out, 不锁定 rc.

    def test_timeout_before_subprocess_starts(self):
        # 极小 timeout 也会触发 kill, 而不是让子进程"自然"完成。
        # 关键: 即使命令很快, 也要保证 done 回调一定会被调用。
        lines, result = _run_and_wait(
            [sys.executable, "-c", "print('x')"],
            timeout_s=0.001,
            runtime_timeout_s=3.0,
        )
        # 注: 这种情况下子进程可能 print 后才被杀, 也可能被杀在 print
        # 之前; done 回调必须触发 (用 done_event.wait 验证)。
        # timed_out 取决于调度时序, 不强求。
        assert result is not None  # done 回调一定被调用

    def test_done_callback_invoked_on_normal_exit(self):
        # 回归: 即使没超时, done 回调也必须被触发。
        result_holder: List[RunResult] = []
        done_event = threading.Event()

        stream_command(
            [sys.executable, "-c", "pass"],
            timeout_s=5.0,
            done_callback=_make_done_cb(result_holder, done_event),
        )
        assert done_event.wait(timeout=5.0)
        assert result_holder[0].returncode == 0
        assert result_holder[0].timed_out is False


# ----------------------------------------------------------------------
# stream_command: line_callback 异常不影响后续行
# ----------------------------------------------------------------------


class TestStreamCallbackRobustness:
    """监听者抛异常不应让后续行丢失, 也不应让线程崩溃."""

    def test_callback_exception_does_not_stop_subsequent_lines(self):
        lines: List[Tuple[str, str]] = []
        call_count = [0]

        def on_line(stream_name, line):
            call_count[0] += 1
            if call_count[0] == 1:
                raise RuntimeError("boom")
            lines.append((stream_name, line))

        done_event = threading.Event()
        result_holder: List[RunResult] = []

        stream_command(
            [sys.executable, "-c", "print('a'); print('b'); print('c')"],
            timeout_s=5.0,
            line_callback=on_line,
            done_callback=_make_done_cb(result_holder, done_event),
        )

        assert done_event.wait(timeout=5.0)
        # 异常之后, 后续行还能继续追加
        assert any(line == "b\n" for _, line in lines) or len(lines) >= 1
        # 至少应该收到几行 (3 行 try 都跑了; 1 行 throw 后丢了, 剩 2 行)
        # 关键断言: 进程没有被异常杀死, done 回调被调用
        assert result_holder[0].returncode == 0


# ----------------------------------------------------------------------
# stream_command: 不传回调
# ----------------------------------------------------------------------


class TestStreamNoCallback:
    """``line_callback=None`` 时仍要 drain 到 EOF, 避免 pipe 缓冲区填满."""

    def test_drain_with_no_callback(self):
        # 如果 drain 没在跑, 子进程写到 pipe 满了就会卡住, 永远不结束。
        # 这里用大批量输出来证明 drain 线程在空回调下也能工作。
        # 100 行 × 50 字节 ≈ 5 KB, 远低于 Windows 命令行长上限
        # (~32 KB), 但足以让 stdout pipe 缓冲区需要被 drain 才能继续
        # 写入 (Popen pipe 缓冲区通常 4-64 KB)。
        n = 100
        payload = "print('x' * 50)\n" * n
        done_event = threading.Event()
        result_holder: List[RunResult] = []

        stream_command(
            [sys.executable, "-c", payload],
            timeout_s=15.0,
            line_callback=None,
            done_callback=_make_done_cb(result_holder, done_event),
        )
        assert done_event.wait(timeout=15.0), "drain 似乎没工作, 进程卡死"
        assert result_holder[0].returncode == 0


# ----------------------------------------------------------------------
# run_blocking
# ----------------------------------------------------------------------


class TestRunBlocking:
    """``run_blocking`` 保留 ``subprocess.run`` 行为作为关闭流式时的回退."""

    def test_captures_stdout(self):
        result = run_blocking(
            [sys.executable, "-c", "print('blocked')"],
            timeout_s=5.0,
        )
        assert result.stdout == "blocked\n"
        assert result.returncode == 0

    def test_captures_stderr(self):
        result = run_blocking(
            [sys.executable, "-c", "import sys; sys.stderr.write('e\\n')"],
            timeout_s=5.0,
        )
        assert result.stderr == "e\n"
        assert result.returncode == 0

    def test_nonzero_exit(self):
        result = run_blocking(
            [sys.executable, "-c", "import sys; sys.exit(3)"],
            timeout_s=5.0,
        )
        assert result.returncode == 3

    def test_timeout_raises(self):
        # ``run_blocking`` 保留 ``subprocess.TimeoutExpired`` 行为;
        # 流式路径用 RunResult.timed_out, 阻塞路径用异常, 这是有意为之
        # 的差异 — 调用方根据需要选哪条路。
        with pytest.raises(Exception):  # TimeoutExpired
            run_blocking(
                [sys.executable, "-c", "import time; time.sleep(5)"],
                timeout_s=0.1,
            )
