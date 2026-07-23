"""End-to-end tests for the runner / checker panel.

Drives :class:`CodeEditor.runner` to run static checks against the buffer
content and asserts that errors are surfaced into the output panel.
"""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _isolate(editor, reset_editor):
    reset_editor(editor)


class TestCheckPython:
    def test_check_empty_buffer_is_noop(self, editor):
        text_widget = editor.buffer._text
        text_widget.delete("1.0", "end-1c")
        # Should silently exit — empty code is not a syntax error to check.
        editor.runner.run_check()

    def test_check_valid_python_reports_no_errors(self, editor):
        text_widget = editor.buffer._text
        text_widget.delete("1.0", "end-1c")
        text_widget.insert("1.0", "x = 1\n")
        editor.runner.run_check()
        # We can't directly read the terminal buffer's content; we can only
        # verify no exception was raised and the runner is idle.
        assert editor.runner._run_handle is None

    def test_check_invalid_python_runs_without_crash(self, editor):
        text_widget = editor.buffer._text
        text_widget.delete("1.0", "end-1c")
        # Deliberate syntax error.
        text_widget.insert("1.0", "def foo(:\n    pass\n")
        # run_check uses CPythonChecker — must produce issues but not crash.
        editor.runner.run_check()

    def test_check_unsupported_language_skipped(self, editor):
        editor.switch_language("JSON")
        text_widget = editor.buffer._text
        text_widget.delete("1.0", "end-1c")
        text_widget.insert("1.0", '{"k": "v"}\n')
        # Should print a "not supported" message but not crash.
        editor.runner.run_check()


class TestCheckPythonCode:
    """Direct tests of the helper that ``run_check`` calls for Python."""

    def test_check_python_code_returns_none(self, editor):
        """The helper is a sink: it returns ``None`` and writes issues to the
        terminal panel. We just exercise the call path and confirm nothing
        explodes even with malformed Python.
        """
        assert editor.runner.check_python_code("def foo(:\n    pass\n") is None

    def test_check_python_code_passes_for_clean_code(self, editor):
        # No exception for clean code.
        assert editor.runner.check_python_code("x = 1\n") is None

    def test_check_python_code_appends_issues_to_terminal(self, editor):
        # Capture the rows that the helper appended by stubbing
        # ``append_output`` on the runner.
        captured: list = []
        editor.runner.append_output = lambda text, stream="system": captured.append((stream, text))
        editor.runner.check_python_code("def foo(:\n    pass\n")
        # At least one row should mention the syntax error.
        joined = "\n".join(text for _, text in captured)
        assert "SyntaxError" in joined or "invalid syntax" in joined.lower()


class TestRunnerLifecycle:
    def test_runner_panel_status_idle_at_start(self, editor):
        # Reset ensures the runner is in the idle state — verify the
        # terminal idle label is shown.
        editor.runner.set_terminal_idle()
        text = editor.runner._status_label.cget("text")
        assert text  # some non-empty status string

    def test_open_shell_invokes_shell_command(self, editor, monkeypatch):
        """`open_shell` spawns a subprocess via ``stream_command``.

        In headless tests we don't actually start a shell; we just verify
        that the runner transitions into the running state and ``run_handle``
        becomes non-None.
        """
        # Stub stream_command to return a fake handle.
        from core import runner as core_runner

        class _FakeProcess:
            def poll(self):
                return None

        class _FakeThread:
            def join(self, timeout=None):
                return None

        class _FakeHandle:
            running = True

            def __init__(self):
                self.process = _FakeProcess()
                self.supervisor_thread = _FakeThread()

            def write_stdin(self, _s):
                return True

            def close_stdin(self):
                return None

            def terminate(self, wait_s=None):
                return None

        fake = _FakeHandle()
        monkeypatch.setattr(core_runner, "stream_command", lambda *a, **kw: fake)
        monkeypatch.setattr("core.editor.runner_panel.stream_command", lambda *a, **kw: fake)

        editor.runner.open_shell()
        # After open_shell, run_handle should be the fake we returned.
        assert editor.runner._run_handle is fake

    def test_clear_output_clears_terminal(self, editor):
        # Smoke test: clear_output must not raise even with an empty terminal.
        editor.runner.clear_output()

    def test_set_message_updates_status_label(self, editor):
        editor.runner.set_message("panel.terminal.idle")
        # Status label should be set to the translated key.
        text = editor.runner._status_label.cget("text")
        assert text

    def test_stop_running_without_handle_is_noop(self, editor):
        editor.runner._run_handle = None
        editor.runner.stop_running()  # should not raise


class TestRunHandleIntegration:
    def test_terminate_running_does_nothing_when_idle(self, editor):
        # No-op when no subprocess is alive.
        editor.runner.terminate_running()
