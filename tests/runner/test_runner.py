import sys

import pytest

from core.runner import RunResult, run_blocking, stream_command


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
    def test_simple_command(self):
        lines = []
        done_result = []

        def on_line(stream, line):
            lines.append((stream, line))

        def on_done(result):
            done_result.append(result)

        proc, thread = stream_command(
            [sys.executable, "-c", "print('hello')"],
            line_callback=on_line,
            done_callback=on_done,
            timeout_s=5.0,
        )

        proc.wait(timeout=10)
        thread.join(timeout=5)

        assert len(done_result) == 1
        assert done_result[0].returncode == 0
        assert not done_result[0].timed_out

    def test_command_with_stderr(self):
        lines = []
        done_result = []

        def on_line(stream, line):
            lines.append((stream, line))

        def on_done(result):
            done_result.append(result)

        proc, thread = stream_command(
            [sys.executable, "-c", "import sys; sys.stderr.write('error\\n')"],
            line_callback=on_line,
            done_callback=on_done,
            timeout_s=5.0,
        )

        proc.wait(timeout=10)
        thread.join(timeout=5)

        assert len(done_result) == 1
        assert done_result[0].returncode == 0

    def test_command_with_error(self):
        done_result = []

        def on_done(result):
            done_result.append(result)

        proc, thread = stream_command(
            [sys.executable, "-c", "raise ValueError('test')"], done_callback=on_done, timeout_s=5.0
        )

        proc.wait(timeout=10)
        thread.join(timeout=5)

        assert len(done_result) == 1
        assert done_result[0].returncode != 0

    def test_timeout(self):
        done_result = []

        def on_done(result):
            done_result.append(result)

        proc, thread = stream_command(
            [sys.executable, "-c", "import time; time.sleep(10)"],
            done_callback=on_done,
            timeout_s=1.0,
        )

        proc.wait(timeout=15)
        thread.join(timeout=5)

        assert len(done_result) == 1
        assert done_result[0].timed_out


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
