"""Fixtures for end-to-end :class:`CodeEditor` tests.

The tests in this package exercise the full editor (Tk window + buffer + tabs +
runner + settings + plugin manager) on a headless display. Two Windows-specific
quirks shaped this file:

1. The default settings path lives in the user's ``%APPDATA%`` (or ``~/.config``),
   so we redirect it to a private temp dir via :func:`default_global_path`
   monkey-patching. That keeps the user's real ``settings.json`` and global
   plugin folder untouched.

2. Python 3.14 on Windows loses the Tcl/Tk library path after repeated Tk
   ``create``/``destroy`` cycles. Creating a brand-new editor per test is
   therefore unreliable. Instead we build one editor for the whole session
   and let each test "reset" the parts of state it cares about. The
   ``reset_editor`` fixture handles this; tests can also reach into the
   editor to wipe tabs, detach projects, etc. directly.
"""

from __future__ import annotations

import contextlib
import os
import shutil
import sys
import tempfile

import pytest

# Make Tcl/Tk resolvable for the headless Tk that powers the editor.
_TCL_ROOT = os.path.join(sys.base_prefix, "tcl")
os.environ.setdefault("TCL_LIBRARY", os.path.join(_TCL_ROOT, "tcl8.6"))
os.environ.setdefault("TK_LIBRARY", os.path.join(_TCL_ROOT, "tk8.6"))


@pytest.fixture(scope="session")
def _fake_root_dir():
    """Allocate a private per-session directory used for global settings + plugins."""
    path = tempfile.mkdtemp(prefix="PythonEditor_tests_")
    yield path
    shutil.rmtree(path, ignore_errors=True)


@pytest.fixture(scope="session")
def _session_settings_path(_fake_root_dir):
    return os.path.join(_fake_root_dir, "settings.json")


@pytest.fixture(autouse=True)
def _redirect_global_paths(monkeypatch, _session_settings_path, _fake_root_dir):
    """Force settings + global plugins into the per-session temp dir.

    Without this, an editor test would persist to the user's real
    ``%APPDATA%/PythonEditor/settings.json`` and load any plugins the user has
    installed, which is not what we want.
    """
    settings_path = _session_settings_path
    plugins_dir = os.path.join(_fake_root_dir, "plugins")
    os.makedirs(plugins_dir, exist_ok=True)

    import core.plugins.manager as _pm_mod
    import core.settings
    import core.settings.settings.global_settings as _gs_mod

    monkeypatch.setattr(core.settings, "default_global_path", lambda: settings_path)
    monkeypatch.setattr(_gs_mod, "default_global_path", lambda: settings_path)
    monkeypatch.setattr(
        _pm_mod.PluginManager, "_default_global_dir", staticmethod(lambda: plugins_dir)
    )
    # Pre-seed so the editor constructor's first read finds a valid file.
    from core.settings.settings.global_settings import GlobalSettings

    gs = GlobalSettings(path=settings_path, auto_load=False)
    gs.set("editor.auto_save", False)
    gs.set("terminal.auto_start", False)
    gs.set("runner.clear_output_before_run", False)
    gs.save()
    yield


def _seed_settings(settings_path: str, *, autosave: bool, autostart_shell: bool) -> None:
    """Pre-seed the global settings file with the editor's expected defaults."""
    from core.settings.settings.global_settings import GlobalSettings

    gs = GlobalSettings(path=settings_path, auto_load=False)
    gs.set("editor.auto_save", autosave)
    gs.set("terminal.auto_start", autostart_shell)
    gs.set("runner.clear_output_before_run", False)
    gs.save()


@pytest.fixture(scope="session", autouse=True)
def _verify_tk_available():
    """Confirm Tk can create a real window in this environment.

    CI runners without a display server (and developers running without
    ``DISPLAY`` on Linux) cannot initialize Tk. Skip the entire test
    session cleanly instead of crashing every test with a TclError.
    """
    import tkinter as tk

    probe = tk.Tk()
    probe.update_idletasks()
    probe.destroy()


@pytest.fixture(scope="session")
def editor(make_session_editor):
    """Session-scoped editor fixture.

    Tests reach into ``editor.tabs``, ``editor.buffer``, ``editor.runner``,
    ``editor.settings`` — and use the :func:`reset_editor` fixture (autouse)
    to wipe per-test mutable state.

    A single editor is reused across every test in the session because Python
    3.14 + Tk on Windows loses the Tcl library path after repeated Tk
    ``create``/``destroy`` cycles, which makes a per-test editor build flaky.
    """
    return make_session_editor()


@pytest.fixture(scope="session")
def make_session_editor(_session_settings_path):
    """Session-scoped factory that builds a single :class:`CodeEditor`.

    The factory returns a function ``_factory(**kwargs)`` that constructs the
    editor on the first call; subsequent calls reuse the same instance but
    re-seed settings so callers can override ``autosave`` / ``autostart_shell``.
    """
    settings_path = _session_settings_path
    cached: dict = {}

    def _factory(*, autosave: bool = False, autostart_shell: bool = False):
        if "instance" not in cached:
            _seed_settings(
                settings_path,
                autosave=autosave,
                autostart_shell=autostart_shell,
            )
            from core.editor.app import CodeEditor

            cached["instance"] = CodeEditor()
        return cached["instance"]

    yield _factory

    editor = cached.get("instance")
    if editor is not None:
        _teardown_editor(editor)


def _teardown_editor(editor) -> None:
    """Destroy a previously constructed editor cleanly (used by session scope)."""
    with contextlib.suppress(Exception):
        handle = editor.runner._run_handle
        if handle is not None and handle.running:
            handle.terminate(wait_s=2.0)

    with contextlib.suppress(Exception):
        for attr in ("_settings_window", "_plugin_manager_window"):
            win = getattr(editor, attr, None)
            if win is not None:
                with contextlib.suppress(Exception):
                    if win.winfo_exists():
                        win.destroy()

    with contextlib.suppress(Exception):
        for after_id in editor.window.tk.call("after", "info"):
            with contextlib.suppress(Exception):
                editor.window.after_cancel(after_id)

    with contextlib.suppress(Exception):
        editor.window.destroy()


@pytest.fixture
def reset_editor(monkeypatch):
    """Autouse fixture returning a callable that wipes per-test mutable state.

    Tests can call ``reset_editor(...)`` to clear documents, dirty flags,
    loaded projects, etc., before running assertions. We also stub the
    ``tkinter.messagebox.askyesno`` "discard changes" prompt to never block:
    without this, a dirty tab left behind by a previous test would pop up a
    modal dialog mid-test, which is undrivable in headless CI.
    """

    def _clear(editor, *, keep_active: bool = False) -> None:
        # Make sure closing any dirty tab does not pop a modal dialog.
        with contextlib.suppress(Exception):
            import tkinter.messagebox as _mb

            monkeypatch.setattr(_mb, "askyesno", lambda *a, **kw: True)
            monkeypatch.setattr(_mb, "askokcancel", lambda *a, **kw: True)
            monkeypatch.setattr(_mb, "showinfo", lambda *a, **kw: None)
            monkeypatch.setattr(_mb, "showerror", lambda *a, **kw: None)
            monkeypatch.setattr(_mb, "showwarning", lambda *a, **kw: None)

        # Clear dirty flags so close() does not even need to consult the dialog.
        for doc in list(editor.tabs.documents.values()):
            doc.dirty = False
        editor.tabs.sync_dirty(False)

        # Close every tab except maybe the active one.
        ids = list(editor.tabs.documents.keys())
        for doc_id in ids:
            if keep_active and doc_id == editor.tabs.active_id:
                continue
            with contextlib.suppress(Exception):
                editor.tabs.close(doc_id)
        # Detach any project.
        with contextlib.suppress(Exception):
            editor._settings.detach_project()
            editor._current_project_root = None
        # Switch back to a known language.
        editor.switch_language("Python")
        # Reset autosave / autostart flags to test defaults.
        editor._autosave_enabled = False
        editor._highlighting_enabled = True
        editor._suggestions_enabled = True
        # Reset font / tab width to known defaults so tests don't see the
        # side-effects of an earlier test in the session.
        editor._font_family = "Consolas"
        editor._font_size = 10
        editor._tab_width = 4
        editor.buffer.apply_font()
        editor.buffer.apply_tab_width()
        if editor._highlight_theme_tk_var is not None:
            editor._highlight_theme_tk_var.set("Default Dark")
        editor._highlight_theme_name = "Default Dark"
        from core.language.highlighter import highlight_themes

        highlight_themes.set_theme("Default Dark")
        # Wipe suggestion popup if visible.
        editor.buffer.hide_suggestions()
        editor.buffer.hide_ghost_text()
        editor.buffer.close_find_dialog()

    return _clear
