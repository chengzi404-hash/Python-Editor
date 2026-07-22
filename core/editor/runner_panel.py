"""Output panel: integrated terminal, run-check, and Python static analysis.

The :class:`RunnerPanel` builds the bottom terminal/output frame and exposes
operations for running code, launching the integrated shell, stopping the
active process, and routing stdout/stderr back to the embedded terminal.
"""

from __future__ import annotations

import contextlib
import os
import shlex
import tempfile
import tkinter as tk
from typing import Any, Protocol

from core.language.checker import CPythonChecker
from core.runner import RunHandle, RunResult, stream_command
from core.settings.i18n import t
from ui.widgets import UButton, UFrame, ULabel, UTerminal, theme

_SHELL_PROMPT_MARKER = "<<<__SHELL_READY__>>>"


class RunnerHost(Protocol):
    """A minimal contract :class:`RunnerPanel` needs from its host editor."""

    window: tk.Tk
    settings: Any
    current_project_root: str | None
    current_language: str
    editor_text: tk.Text
    shell_command: list[str]

    def get_active_path(self) -> str | None: ...
    def emit(self, hook: str, *args, **kwargs) -> None: ...


class RunnerPanel:
    """Owns the output panel frame, embedded terminal, and run-handle state."""

    def __init__(self, host: RunnerHost, parent: tk.Misc) -> None:
        self._host = host
        self._run_handle: RunHandle | None = None

        self._frame = UFrame(parent, variant="panel", height=180)
        self._frame.pack(fill=tk.X, padx=0, pady=0)
        self._frame.pack_propagate(False)

        header = UFrame(self._frame, variant="title")
        header.pack(fill=tk.X)

        ULabel(header, text=t("panel.terminal"), variant="secondary", bg=theme.BG_TITLE).pack(
            side=tk.LEFT, padx=4, pady=2
        )

        self._status_indicator = tk.Frame(
            header, width=10, height=10, bg=theme.FG_DISABLED, highlightthickness=0, bd=0
        )
        self._status_indicator.pack(side=tk.LEFT, padx=(4, 2), pady=4)

        self._status_label = ULabel(
            header,
            text=t("panel.terminal.idle"),
            variant="secondary",
            bg=theme.BG_TITLE,
        )
        self._status_label.pack(side=tk.LEFT, padx=(2, 8))

        buttons = UFrame(header, variant="title", bg=theme.BG_TITLE)
        buttons.pack(side=tk.RIGHT, padx=4, pady=2)

        self._run_btn = UButton(
            buttons,
            text=t("panel.btn.shell"),
            command=self.open_shell,
            variant="primary",
            width=84,
            height=22,
        )
        self._run_btn.pack(side=tk.LEFT, padx=2)

        self._stop_btn = UButton(
            buttons,
            text=t("panel.btn.stop"),
            command=self.stop_running,
            variant="danger",
            width=64,
            height=22,
        )
        self._stop_btn.config(state="disabled")
        self._stop_btn.pack(side=tk.LEFT, padx=2)

        self._clear_btn = UButton(
            buttons,
            text=t("panel.btn.clear"),
            command=self.clear_output,
            variant="default",
            width=64,
            height=22,
        )
        self._clear_btn.pack(side=tk.LEFT, padx=2)

        self._terminal = UTerminal(
            self._frame,
            width=80,
            height=6,
            submit_callback=self._on_terminal_submit,
            on_active_change=self._on_terminal_active_change,
        )
        self._terminal.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)
        self.set_terminal_idle()

    # ------------------------------------------------------------------
    # Output routing
    # ------------------------------------------------------------------

    def append_output(self, text: str, stream: str = "system") -> None:
        from ui.widgets.terminal import StreamName

        typed: StreamName = stream  # type: ignore[assignment]
        if stream == "stdout" and _SHELL_PROMPT_MARKER in text:
            parts = text.split(_SHELL_PROMPT_MARKER, 1)
            if parts[0].strip():
                with contextlib.suppress(Exception):
                    self._terminal.append_output(typed, parts[0])
            self._host.window.after(0, self._show_terminal_prompt)
            return
        with contextlib.suppress(Exception):
            self._terminal.append_output(typed, text)

    def clear_output(self) -> None:
        with contextlib.suppress(Exception):
            self._terminal.clear()

    def set_message(self, key: str, **kwargs) -> None:
        """Update the editor status label via the host-supplied emitter."""
        with contextlib.suppress(Exception):
            text = t(key, **kwargs) if kwargs else t(key)
            self._status_label.config(text=text)

    # ------------------------------------------------------------------
    # Terminal lifecycle
    # ------------------------------------------------------------------

    def set_terminal_idle(self) -> None:
        with contextlib.suppress(Exception):
            self._status_indicator.config(bg=theme.FG_DISABLED)
            self._status_label.config(text=t("panel.terminal.idle"))
            self._run_btn.config(state="normal")
            self._stop_btn.config(state="disabled")
            self._terminal.set_active(False)

    def set_terminal_running(self) -> None:
        with contextlib.suppress(Exception):
            self._status_indicator.config(bg=theme.GREEN)
            self._status_label.config(text=t("panel.terminal.running"))
            self._run_btn.config(state="disabled")
            self._stop_btn.config(state="normal")
            self._terminal.set_active(True)
            self._terminal.focus_input()

    def _on_terminal_submit(self, line: str) -> None:
        handle = self._run_handle
        if handle is None or not handle.running:
            return
        handle.write_stdin(line + "\n")
        handle.write_stdin(f"'{_SHELL_PROMPT_MARKER}'\n")

    def _show_terminal_prompt(self) -> None:
        if not self._run_handle or not self._run_handle.running:
            return
        path = self._host.current_project_root or os.getcwd()
        with contextlib.suppress(Exception):
            self._terminal.append_output("stdout", t("output.terminal_prompt", path=path))

    def _on_terminal_active_change(self, active: bool) -> None:
        if active:
            with contextlib.suppress(Exception):
                self._status_indicator.config(bg=theme.GREEN)
                self._stop_btn.config(state="normal")
        else:
            with contextlib.suppress(Exception):
                self._stop_btn.config(state="disabled")

    def stop_running(self) -> None:
        handle = self._run_handle
        if handle is None or not handle.running:
            return
        handle.terminate()
        self.append_output(f"\n[{t('output.interrupted')}]\n", "system")

    # ------------------------------------------------------------------
    # Run / shell / check
    # ------------------------------------------------------------------

    def open_shell(self) -> None:
        if self._run_handle is not None and self._run_handle.running:
            with contextlib.suppress(Exception):
                self._terminal.focus_input()
            return

        clear_first = bool(
            self._host.settings.global_settings.get("runner.clear_output_before_run", True)
        )
        if clear_first:
            self.clear_output()
        self.append_output(f"{t('output.terminal_banner')}\n", "system")
        self.append_output(f"{t('output.shell_starting')}...\n", "system")
        self._host.window.after(0, lambda: None)

        def on_line(stream: str, line: str) -> None:
            self.append_output(line, stream)

        def on_done(result: RunResult) -> None:
            self._host.window.after(0, self._on_shell_finished, result)

        try:
            self.set_terminal_running()
            self._run_handle = stream_command(
                self._host.shell_command,
                line_callback=on_line,
                done_callback=on_done,
                timeout_s=24 * 3600.0,
            )
            self._host.window.after(100, self._show_terminal_prompt)
        except Exception as exc:
            self.append_output(f"{t('output.error')}: {exc}\n", "system")
            self.set_terminal_idle()

    def _on_shell_finished(self, result: RunResult) -> None:
        self._run_handle = None
        if result.timed_out:
            self.append_output(
                f"\n[{t('status.timeout')}]\n{t('output.shell_exited', code=result.returncode)}\n",
                "system",
            )
        else:
            self.append_output(
                f"\n[{t('output.shell_exited', code=result.returncode)}]\n",
                "system",
            )
        self.set_terminal_idle()

    def run_check(self) -> None:
        code = self._host.editor_text.get("1.0", "end-1c")
        if not code.strip():
            return
        lang = self._host.current_language
        if lang == "Python":
            self.check_python_code(code)
        else:
            self.append_output(f"{t('output.check_unsupported', lang=lang)}\n", "system")

    def check_python_code(self, code: str) -> None:
        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".py", delete=False, encoding="utf-8"
            ) as f:
                f.write(code)
                temp_path = f.name

            self.append_output(f"{t('output.checking')}...\n", "system")
            checker = CPythonChecker()
            result = checker.check(temp_path)
            for row in result.row:
                self.append_output(f"{row}\n", "system")
            self.append_output(f"{t('output.check_done')}\n", "system")
        except Exception as exc:
            self.append_output(f"{t('output.error')}: {exc}\n", "system")

    def terminate_running(self) -> None:
        if self._run_handle is not None:
            with contextlib.suppress(Exception):
                self._run_handle.terminate()


def default_shell_argv(settings: Any) -> list[str]:
    """Return the argv used to launch the integrated shell.

    Honours the ``terminal.shell_cmd`` setting.  Defaults to ``powershell.exe``
    in non-interactive mode on Windows.
    """
    configured = settings.global_settings.get("terminal.shell_cmd")
    if isinstance(configured, list) and configured:
        return [str(x) for x in configured]
    if isinstance(configured, str) and configured.strip():
        return shlex.split(configured)
    return ["powershell.exe", "-NoLogo", "-Command", "-"]
