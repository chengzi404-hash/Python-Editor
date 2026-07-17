import contextlib
from dataclasses import dataclass


@dataclass
class Document:
    """Data model for a single document, corresponding to an open file (or Untitled)."""

    path: str | None
    content: str = ""
    dirty: bool = False
    lang: str = "Python"
    seq: int = 0


class _Debouncer:
    """Lightweight debounce scheduler that only keeps the last callback on multiple ``schedule`` calls."""

    def __init__(self, after, cancel):
        self._after = after
        self._cancel = cancel
        self._after_id = None

    def schedule(self, callback, delay_ms: int) -> None:
        if self._after_id is not None:
            with contextlib.suppress(Exception):
                self._cancel(self._after_id)
            self._after_id = None
        delay = max(0, int(delay_ms))
        try:
            self._after_id = self._after(delay, callback)
        except Exception:
            self._after_id = None

    def cancel(self) -> None:
        if self._after_id is None:
            return
        with contextlib.suppress(Exception):
            self._cancel(self._after_id)
        self._after_id = None

    @property
    def pending_id(self):
        return self._after_id
