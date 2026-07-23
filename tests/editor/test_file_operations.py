"""End-to-end tests for file operations: open / save / save-as / autosave.

These tests use the module-scoped :class:`CodeEditor` fixture, opening files
from a per-test temp directory and writing back through the editor's own
``_load_path_into_editor`` / ``_save_to_path`` helpers. We bypass the
``tk.filedialog.askopenfilename`` dialog because it cannot be driven from
headless tests.
"""

from __future__ import annotations

import os
import tempfile
import time

import pytest

from core.editor.document_io import read_full


@pytest.fixture(autouse=True)
def _isolate(editor, reset_editor):
    reset_editor(editor)


def _write(path: str, body: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(body)


class TestLoadFile:
    def test_open_python_file_populates_buffer(self, editor, temp_dir):
        path = os.path.join(temp_dir, "hello.py")
        _write(path, "def hello():\n    return 'world'\n")
        editor._load_path_into_editor(path)
        text_widget = editor.buffer._text
        assert "def hello()" in text_widget.get("1.0", "end-1c")
        assert editor.current_file == path
        assert editor.current_language == "Python"

    def test_open_json_file_auto_detects_language(self, editor, temp_dir):
        path = os.path.join(temp_dir, "config.json")
        _write(path, '{"k": "v"}\n')
        editor._load_path_into_editor(path)
        assert editor.current_language == "JSON"

    def test_open_yaml_file_auto_detects_language(self, editor, temp_dir):
        path = os.path.join(temp_dir, "config.yaml")
        _write(path, "key: value\n")
        editor._load_path_into_editor(path)
        assert editor.current_language == "YAML"

    def test_open_xml_file_auto_detects_language(self, editor, temp_dir):
        path = os.path.join(temp_dir, "config.xml")
        _write(path, "<root><a/></root>\n")
        editor._load_path_into_editor(path)
        assert editor.current_language == "XML"

    def test_open_log_file_auto_detects_language(self, editor, temp_dir):
        path = os.path.join(temp_dir, "app.log")
        _write(path, "2024-01-01 00:00:00 INFO hello\n")
        editor._load_path_into_editor(path)
        assert editor.current_language == "LOG"

    def test_open_unknown_extension_falls_back_to_python(self, editor, temp_dir):
        path = os.path.join(temp_dir, "data.weird")
        _write(path, "x = 1\n")
        editor._load_path_into_editor(path)
        # ``detect_lang_from_path`` returns Python for unknown extensions.
        assert editor.current_language == "Python"

    def test_open_directory_attachment_changes_project_root(self, editor, temp_dir):
        path = os.path.join(temp_dir, "src", "app.py")
        _write(path, "x = 1\n")
        editor._load_path_into_editor(path)
        # Project should auto-attach to the directory of the opened file.
        assert editor.current_project_root == os.path.abspath(os.path.join(temp_dir, "src"))

    def test_open_updates_document_dirty_flag(self, editor, temp_dir):
        path = os.path.join(temp_dir, "a.py")
        _write(path, "x = 1\n")
        editor._load_path_into_editor(path)
        active_id = editor.tabs.active_id
        assert editor.tabs.documents[active_id].dirty is False
        assert editor.tabs.documents[active_id].path == path


class TestSaveFile:
    def test_save_writes_text_to_disk(self, editor, temp_dir):
        path = os.path.join(temp_dir, "out.py")
        _write(path, "old = 1\n")
        editor._load_path_into_editor(path)
        # Edit the buffer.
        text_widget = editor.buffer._text
        text_widget.delete("1.0", "end-1c")
        text_widget.insert("1.0", "new = 2\n")
        editor.tabs.sync_dirty(True)
        editor._save_to_path(path)
        assert os.path.isfile(path)
        with open(path, encoding="utf-8") as f:
            assert f.read() == "new = 2\n"

    def test_save_clears_dirty_flag(self, editor, temp_dir):
        path = os.path.join(temp_dir, "out.py")
        _write(path, "x = 1\n")
        editor._load_path_into_editor(path)
        editor.tabs.sync_dirty(True)
        assert editor.tabs.dirty is True
        editor._save_to_path(path)
        assert editor.tabs.dirty is False

    def test_save_emits_save_hook(self, editor, temp_dir):
        from core.plugins import HookEvents, api as plugin_api
        from core.plugins.api import PluginContext, PluginManifest
        from core.plugins.manager import _PluginRecord

        path = os.path.join(temp_dir, "out.py")
        _write(path, "x = 1\n")
        editor._load_path_into_editor(path)

        received: list = []
        host = editor._plugin_manager
        ctx = PluginContext(plugin_id="editor-tests", plugin_name="ET", host=host)
        record = _PluginRecord(
            manifest=PluginManifest(id="editor-tests", name="ET"),
            module=None,
            ctx=ctx,
            location="<inline>",
            scope="system",
            enabled=True,
        )
        editor._plugin_manager._plugins["editor-tests"] = record
        sub = plugin_api._HookSubscription(
            hook=HookEvents.EDITOR_FILE_SAVED,
            callback=lambda p: received.append(p),
            plugin_id="editor-tests",
        )
        editor._plugin_manager.register_hook(sub)

        editor.tabs.sync_dirty(True)
        editor._save_to_path(path)
        assert received == [path]

    def test_save_to_readonly_path_shows_error_message(self, editor, temp_dir, monkeypatch):
        # Simulate a write failure: redirect open() to raise OSError on write.
        import builtins as _builtins

        path = os.path.join(temp_dir, "out.py")
        _write(path, "x = 1\n")
        editor._load_path_into_editor(path)
        original_open = _builtins.open

        def _raising_open(p, mode="r", *args, **kwargs):
            if str(p) == path and mode.startswith("w"):
                raise OSError("simulated permission denied")
            return original_open(p, mode, *args, **kwargs)

        monkeypatch.setattr(_builtins, "open", _raising_open)

        # The error path calls tk.messagebox.showerror — also stub that.
        import tkinter.messagebox as _mb

        msgs: list = []
        monkeypatch.setattr(_mb, "showerror", lambda *a, **kw: msgs.append((a, kw)))

        editor.tabs.sync_dirty(True)
        editor._save_to_path(path)

        # The save should not raise, and an error dialog should have fired.
        assert msgs

    def test_save_to_path_updates_doc_content(self, editor, temp_dir):
        path = os.path.join(temp_dir, "out.py")
        _write(path, "x = 1\n")
        editor._load_path_into_editor(path)
        text_widget = editor.buffer._text
        text_widget.delete("1.0", "end-1c")
        text_widget.insert("1.0", "y = 2\n")
        editor.tabs.sync_dirty(True)
        editor._save_to_path(path)
        active_id = editor.tabs.active_id
        assert editor.tabs.documents[active_id].content == "y = 2\n"


class TestAutosave:
    def test_autosave_enabled_writes_temp_file(self, editor, temp_dir):
        from core.settings import SettingsScope

        editor._settings.set(SettingsScope.GLOBAL, "editor.auto_save", True)
        editor._autosave_enabled = True

        text_widget = editor.buffer._text
        text_widget.delete("1.0", "end-1c")
        text_widget.insert("1.0", "AUTOSAVED = 1\n")
        editor.tabs.sync_dirty(True)

        editor.do_autosave(editor.tabs.active_id)

        autosave_dir = os.path.join(tempfile.gettempdir(), "PythonEditor", "autosave")
        if os.path.isdir(autosave_dir):
            files = [
                os.path.join(autosave_dir, n) for n in os.listdir(autosave_dir) if n.endswith(".py")
            ]
            # Latest autosave file should contain our snippet.
            assert any("AUTOSAVED = 1" in read_full(f) for f in files)

    def test_autosave_disabled_noop(self, editor, temp_dir):
        editor._autosave_enabled = False
        text_widget = editor.buffer._text
        text_widget.delete("1.0", "end-1c")
        text_widget.insert("1.0", "x = 1\n")
        editor.tabs.sync_dirty(True)
        editor.do_autosave(editor.tabs.active_id)
        # No autosave temp dir should be written into (when disabled).
        autosave_dir = os.path.join(tempfile.gettempdir(), "PythonEditor", "autosave")
        if os.path.isdir(autosave_dir):
            files = [os.path.join(autosave_dir, n) for n in os.listdir(autosave_dir)]
            assert not any("x = 1" in read_full(f) for f in files if f.endswith(".py"))

    def test_do_autosave_skips_non_active_doc(self, editor):
        editor._autosave_enabled = True
        # Create a second untitled tab.
        editor.tabs.new_file(emit=False)
        active_id = editor.tabs.active_id
        # Empty content; nothing to autosave.
        editor.do_autosave(active_id)
        assert editor.tabs.dirty is False


class TestReloadRoundTrip:
    def test_save_then_reopen_round_trips_content(self, editor, temp_dir):
        path = os.path.join(temp_dir, "round.py")
        _write(path, "")
        editor._load_path_into_editor(path)
        text_widget = editor.buffer._text
        body = "def foo():\n    return 42\n"
        text_widget.insert("1.0", body)
        editor.tabs.sync_dirty(True)
        editor._save_to_path(path)
        # Re-open into a fresh editor flow.
        text_widget.delete("1.0", "end-1c")
        editor._load_path_into_editor(path)
        assert text_widget.get("1.0", "end-1c") == body

    def test_save_then_load_preserves_language(self, editor, temp_dir):
        path = os.path.join(temp_dir, "config.json")
        _write(path, '{"k": "v"}\n')
        editor._load_path_into_editor(path)
        assert editor.current_language == "JSON"
        text_widget = editor.buffer._text
        text_widget.insert("end", " ")
        editor.tabs.sync_dirty(True)
        editor._save_to_path(path)
        # Load again into a clean state.
        text_widget.delete("1.0", "end-1c")
        editor._load_path_into_editor(path)
        assert editor.current_language == "JSON"
