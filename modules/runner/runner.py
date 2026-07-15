"""``modules.runner`` — 子进程执行与输出采集。

对外暴露 :func:`stream_command` 一个公开 API: 启动子进程, 实时逐行
把 stdout/stderr 推给调用方, 子进程结束(或超时)后调用 done 回调。

本模块故意不依赖 Tk / 任何 UI 框架 — 输出通过普通回调传出, 由
``main.py`` 之类的上层用 :func:`tkinter.Tk.after` 之类的机制把行
投递到主线程。这样本模块可以独立单元测试, 不需要打开窗口。
"""

from __future__ import annotations

import subprocess
import threading
from collections.abc import Callable
from dataclasses import dataclass

# --------------------------------------------------------------------------
# 结果类型
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class RunResult:
    """子进程结束后的结果载荷.

    字段:
        * ``returncode`` —— 进程退出码; 0 表示正常, -1 通常表示被强制终止
          (例如超时后 ``kill`` 之后 ``wait`` 失败)。
        * ``timed_out`` —— 是否因超时被主动结束。
    """

    returncode: int
    timed_out: bool = False


# --------------------------------------------------------------------------
# 流式执行
# --------------------------------------------------------------------------


def stream_command(
    cmd: list[str],
    *,
    timeout_s: float = 30.0,
    cwd: str | None = None,
    env: dict[str, str] | None = None,
    line_callback: Callable[[str, str], None] | None = None,
    done_callback: Callable[[RunResult], None] | None = None,
) -> tuple[subprocess.Popen, threading.Thread]:
    """异步流式执行 ``cmd``; stdout/stderr 按行推给回调.

    参数:
        cmd —— 要执行的命令及参数, 列表形式。
        timeout_s —— 整次执行的总超时 (秒); 超过会 ``kill`` 进程。
        cwd —— 子进程工作目录; ``None`` 继承父进程。
        env —— 子进程环境变量; ``None`` 继承父进程。
        line_callback —— ``(stream_name, line)`` 回调, ``stream_name``
            为 ``"stdout"`` 或 ``"stderr"``; 线程安全由调用方负责。
        done_callback —— 子进程结束 (正常 / 失败 / 超时) 时调用一次,
            接收 :class:`RunResult`。
        stdin —— 固定为 ``DEVNULL``; 编辑器里的代码不期望交互输入,
            防止子进程在没消费者时阻塞。

    返回:
        ``(process, supervisor_thread)`` 元组。调用方保留 ``process``
        句柄即可在需要时 ``terminate()`` 主动取消 (``done_callback``
        仍会被调用)。``supervisor_thread`` 是守护线程, 程序退出时
        自动回收, 不需要 ``join()``。

    设计要点:
        * 用 ``text=True, bufsize=1`` 让子进程按行刷新; ``Popen`` 的
          ``stdout=PIPE, stderr=PIPE`` 让两个流互不阻塞。
        * 启动两个守护线程分别 drain stdout / stderr, 互不等待 ——
          这样子进程写其中一个被卡住时另一个仍能持续推进, 避免
          "子进程先写满 stderr 缓冲区再写 stdout" 导致的死锁。
        * supervisor 线程 ``wait()`` 进程, 超时则 ``kill()`` 并等待
          退出; 之后 ``join()`` 两个 drain 线程 (它们读到 EOF 自然
          结束), 最后触发 ``done_callback``。
    """

    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        stdin=subprocess.DEVNULL,
        text=True,
        bufsize=1,
        cwd=cwd,
        env=env,
    )

    def _drain(stream, name: str) -> None:
        """在守护线程中逐行读流并回调; ``line_callback`` 为 None 时仍
        需 drain, 否则子进程 pipe 缓冲区写满后会卡住。"""

        try:
            if line_callback is None:
                # 不关心内容, 但仍要读到 EOF, 否则 Popen 不会回收 pipe.
                for _ in stream:
                    pass
                return
            for line in stream:
                try:
                    line_callback(name, line)
                except Exception:
                    # 监听者异常不应影响后续行的传递; 也不应杀死线程。
                    pass
        except (ValueError, OSError):
            # 进程被外部关闭 stream 时, iter 会抛 ValueError; 视作结束。
            pass
        finally:
            try:
                stream.close()
            except Exception:
                pass

    stdout_thread = threading.Thread(
        target=_drain, args=(process.stdout, "stdout"),
        name="runner-stdout", daemon=True,
    )
    stderr_thread = threading.Thread(
        target=_drain, args=(process.stderr, "stderr"),
        name="runner-stderr", daemon=True,
    )
    stdout_thread.start()
    stderr_thread.start()

    def _supervise() -> None:
        timed_out = False
        returncode = -1
        try:
            returncode = process.wait(timeout=timeout_s)
        except subprocess.TimeoutExpired:
            timed_out = True
            try:
                process.kill()
            except Exception:
                pass
            try:
                returncode = process.wait(timeout=2.0)
            except Exception:
                returncode = -1
        # 等 drain 线程把剩余内容吐完再触发 done, 避免"done 已经
        # 发出但尾巴行还在路上"的竞态。
        stdout_thread.join(timeout=2.0)
        stderr_thread.join(timeout=2.0)
        if done_callback is not None:
            try:
                done_callback(RunResult(returncode=returncode, timed_out=timed_out))
            except Exception:
                pass

    supervisor = threading.Thread(
        target=_supervise, name="runner-supervisor", daemon=True,
    )
    supervisor.start()

    return process, supervisor


# --------------------------------------------------------------------------
# 同步 (阻塞) 执行 — 保留原 ``subprocess.run`` 行为, 供关闭流式时使用
# --------------------------------------------------------------------------


def run_blocking(
    cmd: list[str],
    *,
    timeout_s: float = 30.0,
    cwd: str | None = None,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess:
    """同步执行 ``cmd`` 并在结束后一次性返回 ``CompletedProcess``."""

    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout_s,
        cwd=cwd,
        env=env,
    )


__all__ = ["RunResult", "run_blocking", "stream_command"]
