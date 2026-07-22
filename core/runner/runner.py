"""``modules.runner`` — Subprocess execution and output collection.

Public API:
* :class:`RunResult` — Process exit result.
* :class:`RunHandle` — Live handle returned by :func:`stream_command`; provides
  thread-safe :meth:`RunHandle.write_stdin` / :meth:`RunHandle.close_stdin` /
  :meth:`RunHandle.terminate` so upper layers can drive an interactive session.
* :func:`stream_command` — Async streaming execution + line callback, with
  optional stdin pipe.
* :func:`run_blocking` — Synchronous ``subprocess.run`` wrapper.
"""

from __future__ import annotations

import codecs
import contextlib
import io
import subprocess
import threading
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from typing import IO, Any

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
# Live run handle — returned by ``stream_command`` so callers can drive stdin
# and terminate the subprocess while it is still running.
# --------------------------------------------------------------------------


class RunHandle:
    """Handle to a subprocess launched by :func:`stream_command`.

    The handle exposes thread-safe stdin writing, stdin closing, and forced
    termination. ``process`` and ``supervisor_thread`` are kept available for
    advanced consumers (e.g. tests that need to ``wait``).
    """

    def __init__(
        self,
        process: subprocess.Popen,
        supervisor_thread: threading.Thread,
        stdin_stream: IO[str] | None,
    ) -> None:
        self.process = process
        self.supervisor_thread = supervisor_thread
        self._stdin = stdin_stream
        self._stdin_lock = threading.Lock()
        self._stdin_closed = False

    def write_stdin(self, text: str) -> bool:
        """Write ``text`` to the subprocess stdin (no trailing newline appended).

        Returns ``True`` if the bytes were handed to the pipe, ``False`` if the
        pipe is already closed or the process exited. Safe to call from any
        thread; concurrent writers are serialized via an internal lock.

        When ``stream_command`` was invoked in ``encoding="auto"`` mode the
        underlying stdin pipe is raw bytes, so the string is UTF-8 encoded
        here.  In fixed-encoding mode the pipe is text and we write the
        string directly.  Callers don't need to know which.
        """
        if self._stdin is None:
            return False
        with self._stdin_lock:
            if self._stdin_closed or self.process.poll() is not None:
                return False
            try:
                stdin = self._stdin
                # ``io.TextIOBase`` covers both BufferedReader-wrapped and
                # ``Popen`` text-mode writers, both of which expect ``str``.
                # Anything else (BufferedWriter/Reader from binary Popen)
                # expects ``bytes``.
                text_io = isinstance(stdin, io.TextIOBase)
                payload: str | bytes = text if text_io else text.encode("utf-8")
                stdin.write(payload)  # type: ignore[arg-type]
                stdin.flush()
            except (ValueError, OSError):
                self._stdin_closed = True
                return False
            return True

    def close_stdin(self) -> None:
        """Close the stdin pipe (EOF to the subprocess). Idempotent."""

        if self._stdin is None:
            return
        with self._stdin_lock:
            if self._stdin_closed:
                return
            self._stdin_closed = True
            with contextlib.suppress(Exception):
                self._stdin.close()

    def terminate(self, wait_s: float = 1.0) -> None:
        """Politely terminate the subprocess via ``SIGTERM``/``TerminateProcess``.

        Falls back to ``kill`` if the process has not exited after ``wait_s``.
        """

        if self.process.poll() is not None:
            return
        with contextlib.suppress(Exception):
            self.process.terminate()
        try:
            self.process.wait(timeout=wait_s)
        except subprocess.TimeoutExpired:
            with contextlib.suppress(Exception):
                self.process.kill()
            with contextlib.suppress(Exception):
                self.process.wait(timeout=2.0)

    @property
    def running(self) -> bool:
        return self.process.poll() is None


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
    stdin: bool = True,
    encoding: str = "auto",
    errors: str = "replace",
) -> RunHandle:
    """Asynchronously stream-execute ``cmd``; stdout/stderr pushed line-by-line to callback.

    Args:
        cmd — Command and arguments to execute, as a list.
        timeout_s — Total timeout for the entire execution (seconds); process is
            ``kill``ed on timeout.
        cwd — Subprocess working directory; ``None`` inherits from parent.
        env — Subprocess environment variables; ``None`` inherits from parent.
        line_callback — ``(stream_name, line)`` callback, where ``stream_name``
            is ``"stdout"`` or ``"stderr"``; thread safety is the caller's
            responsibility.
        done_callback — Called once when subprocess ends (normal / failure /
            timeout / termination), receives :class:`RunResult`.
        stdin — When ``True`` (default) the subprocess gets a writable stdin
            pipe that can be driven via :meth:`RunHandle.write_stdin`. Pass
            ``False`` to fall back to the legacy ``DEVNULL`` behaviour for
            non-interactive scripts.
        encoding — Text encoding used to decode the child's stdout/stderr pipes.
            Defaults to ``"auto"``: lines that decode cleanly as UTF-8 stay
            UTF-8; on the first ``UnicodeDecodeError`` the runner permanently
            switches to ``cp936`` (the Chinese Windows OEM/ANSI codepage) and
            every subsequent line uses that.  This handles the case where
            Windows PowerShell 5.x pipes its own ASCII output as UTF-8 but
            the formatting system's ``Format-Table`` writes Chinese strings
            as GBK bytes — without the user having to flip a setting every
            time the script switches commandlets.  Pass a specific codec name
            to lock the runner to it (errors then defaults to ``"replace"``).
        errors — How to handle decoding errors. Defaults to ``"replace"``;
            only used when ``encoding`` is a specific codec name.  In
            ``encoding="auto"`` mode errors are strict until the decoder
            switches to the fallback; afterwards they stay replace.

    Returns:
        :class:`RunHandle` exposing ``process``, ``supervisor_thread``,
        ``write_stdin``, ``close_stdin``, ``terminate`` and ``running``.

    Design notes:
        * Uses ``text=True, bufsize=1`` (or binary ``bufsize=0`` with manual
          line splitting in ``auto`` mode) so subprocess flushes line-by-line;
          ``Popen``'s ``stdout=PIPE, stderr=PIPE`` keeps the two streams
          non-blocking.
        * Two daemon threads drain stdout / stderr independently, not waiting
          on each other — this ensures the subprocess can continue if writing
          to one stream is blocked while the other progresses, avoiding the
          deadlock of "subprocess fills stderr buffer before writing stdout".
        * Supervisor thread ``wait()``s on the process, ``kill()``s on timeout
          and waits for exit; then ``join()``s the two drain threads (they end
          naturally on EOF), and finally triggers ``done_callback``.
        * In ``encoding="auto"`` mode the runner opens pipes in binary mode
          and decodes per line inside the drain threads so the fallback
          behaviour can change mid-stream.  Tk's bundled ``Popen(text=...)``
          decoder is fixed at spawn time.
    """

    stdin_target: Any = subprocess.PIPE if stdin else subprocess.DEVNULL
    use_auto = encoding.lower() == "auto"
    if use_auto:
        # Open pipes in binary mode with default-sized buffering so we
        # get a ``BufferedReader`` (which provides ``read1``).  Drain
        # threads decode per line and fall back to cp936 on the first
        # UTF-8 error.
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=stdin_target,
            text=False,
            bufsize=-1,
            cwd=cwd,
            env=env,
        )
    else:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=stdin_target,
            text=True,
            encoding=encoding,
            errors=errors,
            bufsize=1,
            cwd=cwd,
            env=env,
        )

    handle = RunHandle(
        process=process,
        supervisor_thread=threading.Thread(  # placeholder, replaced below
            target=lambda: None,
            daemon=True,
        ),
        stdin_stream=process.stdin,
    )

    def _iter_binary_lines(stream) -> Iterator[bytes]:
        """Yield ``bytes`` lines from a binary pipe.

        Reads in small chunks and splits on ``\\n`` so multi-byte UTF-8
        sequences are never split across a chunk boundary by accident.
        """
        buf = bytearray()
        while True:
            chunk = stream.read1(4096)
            if not chunk:
                if buf:
                    yield bytes(buf)
                    buf.clear()
                return
            buf.extend(chunk)
            while True:
                nl = buf.find(b"\n")
                if nl < 0:
                    break
                # Yield line *including* the trailing newline so downstream
                # text-mode callers see the same shape they'd get from a
                # text-mode pipe.
                yield bytes(buf[: nl + 1])
                del buf[: nl + 1]

    class _AutoEncodingDecoder:
        """Line-level UTF-8 → cp936 fallback decoder.

        Keeps two codecs side-by-side and feeds incoming lines to UTF-8
        first.  On the first ``UnicodeDecodeError`` the decoder flips
        permanently to cp936 (the Chinese Windows ANSI/OEM codepage),
        which is good enough for mojibake-prone shells like
        Windows PowerShell 5.x's formatting system.
        """

        def __init__(self) -> None:
            self._active: str = "utf-8"
            self._cp936 = codecs.getincrementaldecoder("cp936")("replace")
            self._utf8 = codecs.getincrementaldecoder("utf-8")("strict")

        def decode(self, raw: bytes) -> str:
            if self._active == "cp936":
                return self._cp936.decode(raw)
            try:
                return self._utf8.decode(raw)
            except UnicodeDecodeError:
                self._active = "cp936"
                return self._cp936.decode(raw)

        def flush(self) -> str:
            if self._active == "cp936":
                return self._cp936.decode(b"", final=True)
            return self._utf8.decode(b"", final=True)

    def _drain(stream, name: str) -> None:
        """Read stream line-by-line in a daemon thread and invoke callback; drain even
        when ``line_callback`` is None, otherwise subprocess pipe buffer fills and blocks.

        In ``auto`` encoding mode the stream yields raw ``bytes`` (binary
        pipe); :class:`_AutoEncodingDecoder` handles the UTF-8 → cp936
        fallback.  In fixed encoding mode Tk's text wrapper has already
        decoded the line; we feed it straight through.
        """
        decoder = _AutoEncodingDecoder() if use_auto else None
        cb = line_callback
        if cb is None:
            # Don't care about content, but still need to read to EOF, otherwise Popen won't recycle pipe.
            try:
                if use_auto:
                    while True:
                        chunk = stream.read1(4096)
                        if not chunk:
                            break
                else:
                    for _ in stream:
                        pass
            except (ValueError, OSError):
                pass
            finally:
                with contextlib.suppress(Exception):
                    stream.close()
            return
        try:
            if use_auto:
                line_iter = _iter_binary_lines(stream)
            else:
                line_iter = iter(stream)
            for chunk in line_iter:
                if decoder is not None:
                    text: str = decoder.decode(chunk)
                else:
                    text = (
                        chunk.decode("utf-8", errors="replace")
                        if isinstance(chunk, bytes)
                        else chunk
                    )
                with contextlib.suppress(Exception):
                    cb(name, text)
        except (ValueError, OSError):
            # When process externally closes the stream, iter raises ValueError; treat as end.
            pass
        finally:
            if decoder is not None:
                with contextlib.suppress(Exception):
                    tail = decoder.flush()
                    if tail:
                        cb(name, tail)
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
    handle.supervisor_thread = supervisor
    supervisor.start()

    return handle


# --------------------------------------------------------------------------
# Synchronous (blocking) execution — preserves original ``subprocess.run`` behavior,
# used when streaming is disabled (e.g. inside static checker tools).
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


__all__ = ["RunHandle", "RunResult", "run_blocking", "stream_command"]
