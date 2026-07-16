"""``modules.runner`` — Subprocess execution and output collection.

Public API:

* :class:`RunResult` — Process exit result.
* :func:`stream_command` — Async streaming execution + line callback.
* :func:`run_blocking` — Synchronous ``subprocess.run`` wrapper, used when streaming is disabled.
"""

from .runner import RunResult, run_blocking, stream_command

__all__ = ["RunResult", "run_blocking", "stream_command"]
