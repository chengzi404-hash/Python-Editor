"""``modules.runner`` — Subprocess execution and output collection.

Only one public API is exposed: :func:`stream_command`. It launches a subprocess,
streams stdout/stderr line-by-line to the caller in real-time, and calls the done
callback when the subprocess exits (or times out).

This module intentionally has no dependency on Tk or any UI framework — output is
passed through plain callbacks, and upper layers like ``main.py`` use mechanisms
like :func:`tkinter.Tk.after` to dispatch lines to the main thread. This lets
the module be unit-tested independently without opening a window.
"""

from __future__ import annotations

import contextlib
import subprocess
import threading
from collections.abc import Callable
from dataclasses import dataclass

# --------------------------------------------------------------------------
# Result types
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class RunResult:
    """Result payload after subprocess finishes.

    Fields:
        * ``returncode`` — Process exit code; 0 means normal, -1 usually indicates
          forced termination (e.g. after timeout ``kill`` followed by ``wait`` failure).
        * ``timed_out`` — Whether the process was actively ended due to timeout.
    """

    returncode: int
    timed_out: bool = False


# --------------------------------------------------------------------------
# Streaming execution
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
    """Asynchronously stream-execute ``cmd``; stdout/stderr pushed line-by-line to callback.

    Args:
        cmd — Command and arguments to execute, as a list.
        timeout_s — Total timeout for the entire execution (seconds); process is ``kill``ed on timeout.
        cwd — Subprocess working directory; ``None`` inherits from parent.
        env — Subprocess environment variables; ``None`` inherits from parent.
        line_callback — ``(stream_name, line)`` callback, where ``stream_name``
            is ``"stdout"`` or ``"stderr"``; thread safety is the caller's responsibility.
        done_callback — Called once when subprocess ends (normal / failure / timeout),
            receives :class:`RunResult`.
        stdin — Fixed to ``DEVNULL``; editor code does not expect interactive input,
            preventing subprocess from blocking when there's no consumer.

    Returns:
        ``(process, supervisor_thread)`` tuple. Caller keeps the ``process``
        handle to ``terminate()`` if needed (``done_callback`` will still be called).
        ``supervisor_thread`` is a daemon thread, automatically reclaimed on program exit,
        no ``join()`` needed.

    Design notes:
        * Uses ``text=True, bufsize=1`` so subprocess flushes line-by-line; ``Popen``'s
          ``stdout=PIPE, stderr=PIPE`` keeps the two streams non-blocking.
        * Two daemon threads drain stdout / stderr independently, not waiting on each other —
          this ensures the subprocess can continue if writing to one stream is blocked while
          the other progresses, avoiding the deadlock of "subprocess fills stderr buffer before
          writing stdout".
        * Supervisor thread ``wait()``s on the process, ``kill()``s on timeout and waits for
          exit; then ``join()``s the two drain threads (they end naturally on EOF), and finally
          triggers ``done_callback``.
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
        """Read stream line-by-line in a daemon thread and invoke callback; drain even
        when ``line_callback`` is None, otherwise subprocess pipe buffer fills and blocks."""
        try:
            if line_callback is None:
                # Don't care about content, but still need to read to EOF, otherwise Popen won't recycle pipe.
                for _ in stream:
                    pass
                return
            for line in stream:
                with contextlib.suppress(Exception):
                    line_callback(name, line)
        except (ValueError, OSError):
            # When process externally closes the stream, iter raises ValueError; treat as end.
            pass
        finally:
            with contextlib.suppress(Exception):
                stream.close()

    stdout_thread = threading.Thread(
        target=_drain,
        args=(process.stdout, "stdout"),
        name="runner-stdout",
        daemon=True,
    )
    stderr_thread = threading.Thread(
        target=_drain,
        args=(process.stderr, "stderr"),
        name="runner-stderr",
        daemon=True,
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
            with contextlib.suppress(Exception):
                process.kill()
            try:
                returncode = process.wait(timeout=2.0)
            except Exception:
                returncode = -1
        # Wait for drain threads to flush remaining content before triggering done,
        # avoiding race where "done is fired but trailing lines are still in flight".
        stdout_thread.join(timeout=2.0)
        stderr_thread.join(timeout=2.0)
        if done_callback is not None:
            with contextlib.suppress(Exception):
                done_callback(RunResult(returncode=returncode, timed_out=timed_out))

    supervisor = threading.Thread(
        target=_supervise,
        name="runner-supervisor",
        daemon=True,
    )
    supervisor.start()

    return process, supervisor


# --------------------------------------------------------------------------
# Synchronous (blocking) execution — preserves original ``subprocess.run`` behavior, used when streaming is disabled
# --------------------------------------------------------------------------


def run_blocking(
    cmd: list[str],
    *,
    timeout_s: float = 30.0,
    cwd: str | None = None,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess:
    """Synchronously execute ``cmd`` and return ``CompletedProcess`` after completion."""

    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout_s,
        cwd=cwd,
        env=env,
    )


__all__ = ["RunResult", "run_blocking", "stream_command"]
