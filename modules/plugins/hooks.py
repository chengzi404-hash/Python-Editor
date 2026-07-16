"""``modules.plugins.hooks`` — Editor hook event constants and parameter conventions.

Hook naming style
=================

``<namespace>:<event>``, two namespaces:

* ``editor.*`` — Editor core lifecycle events (file opened, run finished, etc.), \
  all plugins can subscribe.
* ``language.*`` — Language-related events (reserved, not currently emitted, namespace retained).

Parameter conventions
=====================

Each event is described by :class:`HookSpec`, plugin callbacks receive positional arguments in declaration order.

* ``editor:file_opened`` —— ``(path: str)``
* ``editor:file_saved`` —— ``(path: str)``
* ``editor:file_created`` —— ``()`` (new empty file)
* ``editor:content_changed`` —— ``(code: str, cursor_pos: int)``
* ``editor:language_changed`` —— ``(lang: str)``
* ``editor:cursor_moved`` —— ``(line: int, col: int)``
* ``editor:run_started`` —— ``(lang: str, temp_path: str)``
* ``editor:run_finished`` —— ``(lang: str, returncode: int, stdout: str, stderr: str)``
* ``editor:check_finished`` —— ``(lang: str, issues: list)``
* ``editor:closing`` —— ``()``
"""

from __future__ import annotations

from dataclasses import dataclass


class HookEvents:
    """Hook event name constants. Use ``ctx.on(HookEvents.EDITOR_FILE_OPENED, cb)`` directly."""

    EDITOR_FILE_OPENED = "editor:file_opened"
    EDITOR_FILE_SAVED = "editor:file_saved"
    EDITOR_FILE_CREATED = "editor:file_created"
    EDITOR_CONTENT_CHANGED = "editor:content_changed"
    EDITOR_LANGUAGE_CHANGED = "editor:language_changed"
    EDITOR_CURSOR_MOVED = "editor:cursor_moved"
    EDITOR_RUN_STARTED = "editor:run_started"
    EDITOR_RUN_FINISHED = "editor:run_finished"
    EDITOR_CHECK_FINISHED = "editor:check_finished"
    EDITOR_CLOSING = "editor:closing"


@dataclass(frozen=True)
class HookSpec:
    """Describes hook event parameter signatures, for UI display / type checking only."""

    name: str
    params: tuple[str, ...]
    description: str = ""


HOOK_SPECS = (
    HookSpec(HookEvents.EDITOR_FILE_OPENED, ("path",), "File loaded into editor"),
    HookSpec(HookEvents.EDITOR_FILE_SAVED, ("path",), "File saved"),
    HookSpec(HookEvents.EDITOR_FILE_CREATED, (), "New empty file created"),
    HookSpec(
        HookEvents.EDITOR_CONTENT_CHANGED,
        ("code", "cursor_pos"),
        "Editor content changed (after debounce)",
    ),
    HookSpec(HookEvents.EDITOR_LANGUAGE_CHANGED, ("lang",), "Language switched"),
    HookSpec(HookEvents.EDITOR_CURSOR_MOVED, ("line", "col"), "Cursor moved"),
    HookSpec(
        HookEvents.EDITOR_RUN_STARTED,
        ("lang", "temp_path"),
        "Started running code (temp file created)",
    ),
    HookSpec(
        HookEvents.EDITOR_RUN_FINISHED,
        ("lang", "returncode", "stdout", "stderr"),
        "Code execution finished",
    ),
    HookSpec(
        HookEvents.EDITOR_CHECK_FINISHED,
        ("lang", "issues"),
        "Static check finished, issues is a list of issue objects",
    ),
    HookSpec(HookEvents.EDITOR_CLOSING, (), "Editor is about to close"),
)


__all__ = ["HOOK_SPECS", "HookEvents", "HookSpec"]
