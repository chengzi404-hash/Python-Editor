"""Streaming file IO helpers for opening files into the editor widget."""

from __future__ import annotations

import contextlib
import os
import tkinter as tk
from collections.abc import Callable
from typing import Any

DEFAULT_LARGE_FILE_THRESHOLD = 5 * 1024 * 1024
DEFAULT_STREAM_CHUNK_SIZE = 64 * 1024


def resolve_threshold(raw: Any) -> int:
    """Convert a settings value to a non-negative byte threshold."""
    try:
        return max(0, int(raw))  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return DEFAULT_LARGE_FILE_THRESHOLD


def file_size(path: str) -> int:
    """Return the size of ``path`` in bytes, or 0 if it cannot be stat'd."""
    try:
        return os.path.getsize(path)
    except OSError:
        return 0


def read_full(path: str) -> str:
    """Read ``path`` to a UTF-8 string. Raises on failure."""
    with open(path, encoding="utf-8") as fh:
        return fh.read()


class StreamLoad:
    """Token returned by :func:`stream_load_file` to track or cancel a stream."""

    def __init__(self) -> None:
        self._after_id: str | None = None
        self._cancelled = False
        self._done = False
        self._window: tk.Misc | None = None

    def cancel(self) -> None:
        self._cancelled = True

    @property
    def done(self) -> bool:
        return self._done

    def cancel_after(self) -> None:
        if self._after_id is not None and self._window is not None:
            with contextlib.suppress(Exception):
                self._window.after_cancel(self._after_id)
            self._after_id = None


def stream_load_file(
    window: tk.Misc,
    text: tk.Text,
    path: str,
    *,
    on_complete: Callable[[str], None],
    on_error: Callable[[str], None] | None = None,
    chunk_size: int = DEFAULT_STREAM_CHUNK_SIZE,
) -> StreamLoad:
    """Stream ``path`` into ``text`` in chunks via ``window.after``.

    ``on_complete(content)`` is invoked with the full buffered text after the
    last chunk has been inserted. ``on_error(msg)`` (optional) is invoked if
    the file cannot be opened or read. The returned :class:`StreamLoad` token
    can be used to cancel an in-progress stream.
    """
    token = StreamLoad()
    token._window = window
    accumulated: list[str] = []

    def _report(msg: str) -> None:
        if on_error is not None:
            on_error(msg)
        else:
            with contextlib.suppress(Exception):
                tk.messagebox.showerror("Open failed", msg, parent=window)

    try:
        fh = open(path, encoding="utf-8", errors="replace")  # noqa: SIM115
    except OSError as exc:
        _report(str(exc))
        return token

    text.config(state="disabled")

    def _step() -> None:
        if token._cancelled:
            with contextlib.suppress(Exception):
                fh.close()
            return
        try:
            chunk = fh.read(chunk_size)
        except OSError as exc:
            with contextlib.suppress(Exception):
                fh.close()
            with contextlib.suppress(Exception):
                text.config(state="normal")
            _report(str(exc))
            return

        if not chunk:
            with contextlib.suppress(Exception):
                fh.close()
            with contextlib.suppress(Exception):
                text.config(state="normal")
            token._done = True
            on_complete("".join(accumulated))
            return

        accumulated.append(chunk)
        with contextlib.suppress(tk.TclError):
            text.insert(text.index("end-1c"), chunk)
        token._after_id = window.after(1, _step)

    token._after_id = window.after(1, _step)
    return token
