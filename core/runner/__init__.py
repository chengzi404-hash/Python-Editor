"""``modules.runner`` — Subprocess execution and output collection.

Public API:

* :class:`RunResult` — Process exit result.
* :class:`RunHandle` — Live handle returned by :func:`stream_command`; provides
  thread-safe :meth:`RunHandle.write_stdin` / :meth:`RunHandle.close_stdin` /
  :meth:`RunHandle.terminate` so upper layers can drive an interactive session.
* :func:`stream_command` — Async streaming execution + line callback, with
  optional stdin pipe.
* :func:`run_blocking` — Synchronous ``subprocess.run`` wrapper, used when
  streaming is disabled.
"""

from .runner import RunHandle, RunResult, run_blocking, stream_command

__all__ = ["RunHandle", "RunResult", "run_blocking", "stream_command"]
