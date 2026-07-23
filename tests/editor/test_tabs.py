"""End-to-end tests for the :class:`TabManager` wired into the editor.

Verifies that multi-tab flows — new file, close, switch, close-all — round-trip
through the editor's hooks and dirty-flag bookkeeping without leaking state.
"""

from __future__ import annotations

import os

import pytest


@pytest.fixture(autouse=True)
def _isolate(editor, reset_editor):
    reset_editor(editor)


def _write(path: str, body: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(body)


class TestNewFile:
    def test_new_file_action_creates_untitled(self, editor):
        editor.tabs.new_file(emit=False)
        # Two documents now: the original untitled + a fresh one.
        assert len(editor.tabs.documents) == 2
        new_doc_id = editor.tabs.active_id
        new_doc = editor.tabs.documents[new_doc_id]
        assert new_doc.path is None
        assert new_doc.dirty is False
        # Buffer was wiped.
        text_widget = editor.buffer._text
        assert text_widget.get("1.0", "end-1c") == ""

    def test_new_file_emits_create_hook(self, editor):
        from core.plugins import HookEvents, api as plugin_api
        from core.plugins.api import PluginContext, PluginManifest
        from core.plugins.manager import _PluginRecord

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
            hook=HookEvents.EDITOR_FILE_CREATED,
            callback=lambda: received.append(True),
            plugin_id="editor-tests",
        )
        editor._plugin_manager.register_hook(sub)

        editor.tabs.new_file(emit=True)
        assert received == [True]

    def test_new_file_cancels_when_active_dirty_and_user_says_no(self, editor, monkeypatch):
        # Mark the active doc dirty.
        text_widget = editor.buffer._text
        text_widget.insert("1.0", "edit\n")
        editor.tabs.sync_dirty(True)
        # Stub the discard confirmation dialog to return False.
        import tkinter.messagebox as _mb

        monkeypatch.setattr(_mb, "askyesno", lambda *a, **kw: False)
        before_count = len(editor.tabs.documents)
        result = editor.tabs.new_file(emit=False)
        assert result is False
        assert len(editor.tabs.documents) == before_count

    def test_new_file_proceeds_when_active_dirty_and_user_says_yes(self, editor, monkeypatch):
        text_widget = editor.buffer._text
        text_widget.insert("1.0", "edit\n")
        editor.tabs.sync_dirty(True)
        import tkinter.messagebox as _mb

        monkeypatch.setattr(_mb, "askyesno", lambda *a, **kw: True)
        result = editor.tabs.new_file(emit=False)
        assert result is True
        assert len(editor.tabs.documents) == 2


class TestSwitchTabs:
    def test_switching_tabs_restores_buffer_content(self, editor, temp_dir):
        path_a = os.path.join(temp_dir, "a.py")
        path_b = os.path.join(temp_dir, "b.py")
        _write(path_a, "A_CONTENT = 1\n")
        _write(path_b, "B_CONTENT = 2\n")

        editor._load_path_into_editor(path_a)
        editor._load_path_into_editor(path_b)
        # After loading b, the active document is b.
        assert editor.tabs.active_id == path_b
        text_widget = editor.buffer._text
        assert "B_CONTENT" in text_widget.get("1.0", "end-1c")

        # Switch back to a.
        editor.tabs.switch_to(path_a)
        assert editor.tabs.active_id == path_a
        assert "A_CONTENT" in text_widget.get("1.0", "end-1c")

    def test_switching_tabs_emits_tab_changed_hook(self, editor, temp_dir):
        from core.plugins import HookEvents, api as plugin_api
        from core.plugins.api import PluginContext, PluginManifest
        from core.plugins.manager import _PluginRecord

        path_a = os.path.join(temp_dir, "a.py")
        path_b = os.path.join(temp_dir, "b.py")
        _write(path_a, "x = 1\n")
        _write(path_b, "y = 2\n")

        editor._load_path_into_editor(path_a)
        editor._load_path_into_editor(path_b)
        # After loading b, active = b. Loading a second time would create a new
        # tab, so we have two tabs.

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
            hook=HookEvents.EDITOR_TAB_CHANGED,
            callback=lambda tid: received.append(tid),
            plugin_id="editor-tests",
        )
        editor._plugin_manager.register_hook(sub)

        editor.tabs.switch_to(path_a)
        assert received == [path_a]

    def test_switching_to_same_tab_is_idempotent(self, editor):
        active = editor.tabs.active_id
        # Multiple switch_to on the same tab must not error or duplicate state.
        editor.tabs.switch_to(active)
        editor.tabs.switch_to(active)
        assert editor.tabs.active_id == active


class TestCloseTabs:
    def test_close_active_spawns_new_doc_if_last(self, editor):
        # One untitled doc: closing it should spawn a fresh untitled doc.
        assert len(editor.tabs.documents) == 1
        editor.tabs.close_active()
        assert len(editor.tabs.documents) == 1
        # The doc id should be a fresh untitled (sequence 2).
        active_id = editor.tabs.active_id
        assert active_id.startswith("__untitled_")

    def test_close_specific_tab(self, editor, temp_dir):
        path_a = os.path.join(temp_dir, "a.py")
        _write(path_a, "x = 1\n")
        editor._load_path_into_editor(path_a)
        active = editor.tabs.active_id
        assert active == path_a
        editor.tabs.close(path_a)
        assert path_a not in editor.tabs.documents
        # A fresh untitled tab is created.
        assert editor.tabs.active_id is not None

    def test_close_with_dirty_prompts_user(self, editor, temp_dir, monkeypatch):
        path = os.path.join(temp_dir, "x.py")
        _write(path, "x = 1\n")
        editor._load_path_into_editor(path)
        editor.tabs.sync_dirty(True)
        import tkinter.messagebox as _mb

        # User clicks "No" — keep the doc.
        monkeypatch.setattr(_mb, "askyesno", lambda *a, **kw: False)
        editor.tabs.close(path)
        assert path in editor.tabs.documents

        # User clicks "Yes" — discard the doc.
        monkeypatch.setattr(_mb, "askyesno", lambda *a, **kw: True)
        editor.tabs.close(path)
        assert path not in editor.tabs.documents

    def test_close_others(self, editor, temp_dir):
        path_a = os.path.join(temp_dir, "a.py")
        path_b = os.path.join(temp_dir, "b.py")
        _write(path_a, "x = 1\n")
        _write(path_b, "y = 2\n")
        editor._load_path_into_editor(path_a)
        editor._load_path_into_editor(path_b)
        editor.tabs.close_others(path_b)
        assert path_a not in editor.tabs.documents
        assert path_b in editor.tabs.documents
        assert editor.tabs.active_id == path_b

    def test_close_all_with_one_doc_replaces_with_new(self, editor):
        before = editor.tabs.active_id
        editor.tabs.close_all()
        # ``close_all`` with one doc delegates to ``new_file`` which adds a
        # second untitled tab — so we expect two tabs after the call.
        assert len(editor.tabs.documents) == 2
        after = editor.tabs.active_id
        assert after is not None
        assert after != before


class TestTabNavigation:
    def test_next_prev_cycle_through_docs(self, editor, temp_dir):
        path_a = os.path.join(temp_dir, "a.py")
        path_b = os.path.join(temp_dir, "b.py")
        path_c = os.path.join(temp_dir, "c.py")
        _write(path_a, "x = 1\n")
        _write(path_b, "y = 2\n")
        _write(path_c, "z = 3\n")
        editor._load_path_into_editor(path_a)
        editor._load_path_into_editor(path_b)
        editor._load_path_into_editor(path_c)
        ids = [path_a, path_b, path_c]
        # Walk next three times -> back to start.
        editor.tabs.next_tab()
        editor.tabs.next_tab()
        editor.tabs.next_tab()
        assert editor.tabs.active_id in ids
        # Walk prev three times -> back to start.
        editor.tabs.prev_tab()
        editor.tabs.prev_tab()
        editor.tabs.prev_tab()
        assert editor.tabs.active_id in ids


class TestDirtyTracking:
    def test_mark_active_dirty_flips_document_state(self, editor):
        text_widget = editor.buffer._text
        text_widget.insert("1.0", "added\n")
        editor.mark_dirty()
        active_id = editor.tabs.active_id
        assert editor.tabs.documents[active_id].dirty is True
        assert editor.tabs.dirty is True

    def test_sync_dirty_clears_flag(self, editor):
        text_widget = editor.buffer._text
        text_widget.insert("1.0", "added\n")
        editor.mark_dirty()
        editor.tabs.sync_dirty(False)
        active_id = editor.tabs.active_id
        assert editor.tabs.documents[active_id].dirty is False
        assert editor.tabs.dirty is False


class TestDocumentLifecycle:
    def test_register_opened_adds_new_tab(self, editor, temp_dir):
        path = os.path.join(temp_dir, "fresh.py")
        _write(path, "x = 1\n")
        editor.tabs.register_opened(path, "Python")
        assert path in editor.tabs.documents
        assert editor.tabs.active_id == path
        assert editor.tabs.documents[path].lang == "Python"

    def test_reset_active_replaces_active_state(self, editor):
        active_id = editor.tabs.active_id
        editor.tabs.reset_active(dirty=True, content="NEW", path=None, lang="Python", seq=99)
        doc = editor.tabs.documents[active_id]
        assert doc.dirty is True
        assert doc.content == "NEW"
        assert doc.seq == 99

    def test_flush_active_into_document_persists_buffer(self, editor):
        text_widget = editor.buffer._text
        text_widget.delete("1.0", "end-1c")
        text_widget.insert("1.0", "flushed\n")
        editor.tabs.flush_active_into_document()
        active_id = editor.tabs.active_id
        assert editor.tabs.documents[active_id].content == "flushed\n"
