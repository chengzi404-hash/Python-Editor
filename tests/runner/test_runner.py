import sys
import time

import pytest

from core.runner import RunHandle, RunResult, run_blocking, stream_command


class TestRunResult:
    def test_creation(self):
        result = RunResult(returncode=0, timed_out=False)
        assert result.returncode == 0
        assert not result.timed_out

    def test_creation_with_timeout(self):
        result = RunResult(returncode=-1, timed_out=True)
        assert result.returncode == -1
        assert result.timed_out


class TestStreamCommand:
    def test_returns_handle(self):
        handle = stream_command([sys.executable, "-c", "print('hello')"], timeout_s=5.0)
        assert isinstance(handle, RunHandle)
        assert handle.process.poll() is None or handle.process.poll() == 0
        handle.process.wait(timeout=10)
        handle.supervisor_thread.join(timeout=5)

    def test_simple_command(self):
        lines = []
        done_result = []

        def on_line(stream, line):
            lines.append((stream, line))

        def on_done(result):
            done_result.append(result)

        handle = stream_command(
            [sys.executable, "-c", "print('hello')"],
            line_callback=on_line,
            done_callback=on_done,
            timeout_s=5.0,
        )

        handle.process.wait(timeout=10)
        handle.supervisor_thread.join(timeout=5)

        assert len(done_result) == 1
        assert done_result[0].returncode == 0
        assert not done_result[0].timed_out
        # Drain output line is reported under the stdout stream name.
        assert any(stream == "stdout" and "hello" in line for stream, line in lines)

    def test_command_with_stderr(self):
        lines = []
        done_result = []

        def on_line(stream, line):
            lines.append((stream, line))

        def on_done(result):
            done_result.append(result)

        handle = stream_command(
            [sys.executable, "-c", "import sys; sys.stderr.write('error\\n')"],
            line_callback=on_line,
            done_callback=on_done,
            timeout_s=5.0,
        )

        handle.process.wait(timeout=10)
        handle.supervisor_thread.join(timeout=5)

        assert len(done_result) == 1
        assert done_result[0].returncode == 0
        assert any(stream == "stderr" and "error" in line for stream, line in lines)

    def test_command_with_error(self):
        done_result = []

        def on_done(result):
            done_result.append(result)

        handle = stream_command(
            [sys.executable, "-c", "raise ValueError('test')"],
            done_callback=on_done,
            timeout_s=5.0,
        )

        handle.process.wait(timeout=10)
        handle.supervisor_thread.join(timeout=5)

        assert len(done_result) == 1
        assert done_result[0].returncode != 0

    def test_timeout(self):
        done_result = []

        def on_done(result):
            done_result.append(result)

        handle = stream_command(
            [sys.executable, "-c", "import time; time.sleep(10)"],
            done_callback=on_done,
            timeout_s=1.0,
        )

        handle.process.wait(timeout=15)
        handle.supervisor_thread.join(timeout=5)

        assert len(done_result) == 1
        assert done_result[0].timed_out

    def test_stdin_pipe_roundtrip(self):
        """Subprocess should be able to read what we wrote through ``write_stdin``."""

        script = (
            "import sys\n"
            "for _ in range(3):\n"
            "    line = sys.stdin.readline()\n"
            "    if not line:\n"
            "        break\n"
            "    sys.stdout.write('GOT:' + line)\n"
            "    sys.stdout.flush()\n"
        )
        seen = []

        def on_line(stream, line):
            if stream == "stdout":
                seen.append(line)

        handle = stream_command(
            [sys.executable, "-u", "-c", script],
            line_callback=on_line,
            done_callback=lambda r: None,
            timeout_s=5.0,
        )

        assert handle.write_stdin("alpha\n")
        assert handle.write_stdin("beta\n")
        assert handle.write_stdin("gamma\n")
        handle.close_stdin()

        handle.process.wait(timeout=10)
        handle.supervisor_thread.join(timeout=5)

        joined = "".join(seen)
        assert "GOT:alpha" in joined
        assert "GOT:beta" in joined
        assert "GOT:gamma" in joined

    def test_write_stdin_after_exit_is_safe(self):
        handle = stream_command([sys.executable, "-c", "pass"], timeout_s=5.0)
        handle.process.wait(timeout=10)
        handle.supervisor_thread.join(timeout=5)
        # Should be a no-op rather than raise.
        assert handle.write_stdin("nope\n") is False
        handle.close_stdin()  # also a no-op

    def test_terminate_kills_long_running_process(self):
        handle = stream_command(
            [sys.executable, "-c", "import time; time.sleep(30)"], timeout_s=60.0
        )
        assert handle.running
        handle.terminate(wait_s=2.0)
        assert not handle.running
        handle.supervisor_thread.join(timeout=5)

    def test_stdin_disabled_falls_back_to_devnull(self):
        """Passing ``stdin=False`` should still work, just without a pipe."""

        handle = stream_command(
            [sys.executable, "-c", "print('hello')"],
            timeout_s=5.0,
            stdin=False,
        )
        assert isinstance(handle, RunHandle)
        assert handle.write_stdin("ignored\n") is False
        handle.process.wait(timeout=10)
        handle.supervisor_thread.join(timeout=5)

    @pytest.mark.skipif(sys.platform != "win32", reason="cmd.exe is Windows-only")
    def test_cmd_exe_interactive_session(self):
        """Drive ``cmd.exe`` interactively the same way the integrated terminal does.

        Acts as a stand-in for PowerShell on Windows CI: cmd reads lines from
        stdin and writes prompts / output back, so we can validate that the
        runner stays healthy across multiple ``write_stdin`` / drain rounds.
        """

        stdout_lines: list[str] = []
        done_result: list = []

        def on_line(stream, line):
            if stream == "stdout":
                stdout_lines.append(line.rstrip("\r\n"))

        def on_done(result):
            done_result.append(result)

        handle = stream_command(
            ["cmd.exe", "/Q", "/K", "@echo PROMPT_READY"],
            line_callback=on_line,
            done_callback=on_done,
            timeout_s=10.0,
        )

        # Wait for cmd's banner + our PROMPT_READY marker.
        deadline = time.time() + 5.0
        while time.time() < deadline and not any("PROMPT_READY" in ln for ln in stdout_lines):
            time.sleep(0.05)
        assert any("PROMPT_READY" in ln for ln in stdout_lines)

        assert handle.write_stdin("echo hello-from-cmd\r\n")
        assert handle.write_stdin("echo second-line\r\n")

        deadline = time.time() + 5.0
        while time.time() < deadline and not any("second-line" in ln for ln in stdout_lines):
            time.sleep(0.05)
        joined = "\n".join(stdout_lines)
        assert "hello-from-cmd" in joined
        assert "second-line" in joined

        handle.terminate(wait_s=2.0)
        handle.supervisor_thread.join(timeout=5)

    def test_auto_encoding_falls_back_to_cp936(self):
        """encoding='auto' should decode ASCII as UTF-8 and cp936 (GBK) bytes
        as Chinese characters, matching PowerShell 5.x's pipeline behaviour.

        Spawns a Python child that prints two lines: an ASCII line first
        (decodable as UTF-8), then a GBK-encoded Chinese line (which is
        invalid UTF-8 but valid cp936).  Once the decoder sees the second
        line it should permanently switch to cp936; both lines are delivered
        decoded correctly to the line callback.
        """

        chinese = "目录列表"
        script = (
            "import sys\n"
            f"sys.stdout.buffer.write(b'first line\\n')\n"
            f"sys.stdout.buffer.write({chinese!r}.encode('cp936'))\n"
            "sys.stdout.buffer.write(b'\\n')\n"
            "sys.stdout.buffer.flush()\n"
        )
        seen_lines: list[str] = []

        def collect(stream, line):
            if stream == "stdout":
                seen_lines.append(line)

        done: list = []

        def mark_done(result):
            done.append(result)

        handle = stream_command(
            [sys.executable, "-c", script],
            line_callback=collect,
            done_callback=mark_done,
            timeout_s=5.0,
        )
        handle.process.wait(timeout=10)
        handle.supervisor_thread.join(timeout=5)

        joined = "".join(seen_lines)
        assert "first line" in joined
        assert "目录列表" in joined
        assert done and done[0].returncode == 0
        """ANSI escape sequences emitted by the subprocess should be passed
        through to the line callback verbatim — the parser/rendering layer
        lives downstream of the runner.

        Drives a Python child that writes an obvious SGR sequence plus plain
        text, then checks both pieces arrive intact via ``line_callback``.
        """

        script = (
            "import sys\n"
            "sys.stdout.write('\\x1b[31mRED\\x1b[0m plain \\x1b[1;34mBOLD-BLUE\\x1b[0m\\n')\n"
            "sys.stdout.flush()\n"
        )
        seen: list[str] = []
        done_result: list = []

        def on_line(stream, line):
            if stream == "stdout":
                seen.append(line)

        def on_done(result):
            done_result.append(result)

        handle = stream_command(
            [sys.executable, "-c", script],
            line_callback=on_line,
            done_callback=on_done,
            timeout_s=5.0,
        )
        handle.process.wait(timeout=10)
        handle.supervisor_thread.join(timeout=5)

        joined = "".join(seen)
        assert "\x1b[31mRED\x1b[0m" in joined
        assert "\x1b[1;34mBOLD-BLUE\x1b[0m" in joined
        assert " plain " in joined
        assert done_result and done_result[0].returncode == 0


class TestRunBlocking:
    def test_successful_command(self):
        result = run_blocking([sys.executable, "-c", "print('hello')"], timeout_s=5.0)
        assert result.returncode == 0
        assert "hello" in result.stdout

    def test_failing_command(self):
        result = run_blocking([sys.executable, "-c", "raise ValueError('test')"], timeout_s=5.0)
        assert result.returncode != 0

    def test_invalid_command(self):
        result = run_blocking([sys.executable, "-c", "import sys; sys.exit(1)"], timeout_s=5.0)
        assert result.returncode == 1

    def test_with_cwd(self, temp_dir):
        result = run_blocking(
            [sys.executable, "-c", "import os; print(os.getcwd())"], cwd=temp_dir, timeout_s=5.0
        )
        assert result.returncode == 0
