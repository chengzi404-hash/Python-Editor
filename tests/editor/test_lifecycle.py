"""End-to-end tests for the :class:`CodeEditor` lifecycle.

These run against a single module-shared :class:`CodeEditor` to avoid the
known Windows / Python 3.14 issue with repeated Tk ``create``/``destroy``
cycles. Tests reset the parts of the editor they care about via the
:func:`reset_editor` autouse fixture.
"""

from __future__ import annotations

import tkinter as tk

import pytest

from core.editor.lang_config import LANG_CONFIG
from core.plugins import HookEvents, api as plugin_api


@pytest.fixture(autouse=True)
def _isolate(editor, reset_editor):
    """Reset tabs/project/language before every test in this module."""
    reset_editor(editor)


class TestEditorConstruction:
    def test_constructs_default_language_python(self, editor):
        # On first construction the active doc holds the Python sample.
        assert editor.current_language == "Python"
        text_widget = editor.buffer._text
        assert text_widget.get("1.0", "end-1c") == LANG_CONFIG["Python"]["sample"]

    def test_initial_state_has_one_tab(self, editor):
        assert len(editor.tabs.documents) == 1
        active = editor.tabs.active_id
        assert active is not None
        doc = editor.tabs.documents[active]
        assert doc.path is None  # Untitled
        assert doc.dirty is False

    def test_no_autostart_shell_by_default(self, editor):
        # SettingsManager.effective() should have suppressed auto_start because
        # conftest pre-seeded terminal.auto_start=False.
        assert editor.runner._run_handle is None

    def test_status_label_is_tk_widget(self, editor):
        assert isinstance(editor._status_label, tk.Widget)

    def test_position_label_is_shown(self, editor):
        editor.refresh_status()
        text = editor._pos_label.cget("text")
        # Format depends on locale; we only assert that *something* rendered.
        assert text

    def test_terminal_panel_attached(self, editor):
        assert editor.runner._terminal is not None

    def test_highlighter_attached_for_python(self, editor):
        assert editor.buffer.highlighter is not None
        # Calling apply_highlight should not raise.
        editor.buffer.apply_highlight()

    def test_managed_components_present(self, editor):
        assert editor.tabs is not None
        assert editor.buffer is not None
        assert editor.runner is not None
        assert editor.menus is not None
        assert editor.shortcuts is not None


class TestEditorHooks:
    def test_emit_silently_no_handlers(self, editor):
        """Emitting hooks with no subscribers should be a no-op."""
        editor.emit(HookEvents.EDITOR_LANGUAGE_CHANGED, "JSON")

    def test_emit_with_handler_invokes_callback(self, editor):
        received: list = []

        def _cb(*args, **kwargs):
            received.append((args, kwargs))

        # PluginManager only fires hooks belonging to *enabled* loaded plugins.
        # Register a fake record so the manager recognises the plugin_id.
        from core.plugins.api import PluginContext, PluginManifest
        from core.plugins.manager import _PluginRecord

        host = editor._plugin_manager
        ctx = PluginContext(plugin_id="editor-tests", plugin_name="Editor Tests", host=host)
        record = _PluginRecord(
            manifest=PluginManifest(id="editor-tests", name="Editor Tests"),
            module=None,
            ctx=ctx,
            location="<inline>",
            scope="system",
            enabled=True,
        )
        editor._plugin_manager._plugins["editor-tests"] = record

        sub = plugin_api._HookSubscription(
            hook=HookEvents.EDITOR_LANGUAGE_CHANGED,
            callback=_cb,
            plugin_id="editor-tests",
        )
        editor._plugin_manager.register_hook(sub)
        editor.emit(HookEvents.EDITOR_LANGUAGE_CHANGED, "JSON", extra=True)
        assert len(received) == 1
        args, kwargs = received[0]
        assert args == ("JSON",)
        assert kwargs == {"extra": True}


class TestEditorShutdown:
    def test_no_running_subprocess(self, editor):
        handle = editor.runner._run_handle
        assert handle is None or not handle.running


class TestEditorLanguageSwitch:
    def test_switch_to_json_loads_sample(self, editor):
        editor.switch_language("JSON")
        assert editor.current_language == "JSON"
        text_widget = editor.buffer._text
        assert text_widget.get("1.0", "end-1c") == LANG_CONFIG["JSON"]["sample"]

    def test_switch_back_to_python_restores_sample(self, editor):
        editor.switch_language("JSON")
        editor.switch_language("Python")
        text_widget = editor.buffer._text
        assert text_widget.get("1.0", "end-1c") == LANG_CONFIG["Python"]["sample"]

    def test_switch_to_yaml_highlighter_attached(self, editor):
        editor.switch_language("YAML")
        assert editor.current_language == "YAML"
        assert editor.buffer.highlighter is not None

    def test_switch_unsupported_language_noop(self, editor):
        before = editor.buffer.highlighter
        editor.switch_language("NotARealLang")
        assert editor.buffer.highlighter is before

    def test_switch_xml_highlighter_attached(self, editor):
        editor.switch_language("XML")
        assert editor.current_language == "XML"
        assert editor.buffer.highlighter is not None

    def test_switch_log_highlighter_attached(self, editor):
        editor.switch_language("LOG")
        assert editor.current_language == "LOG"
        assert editor.buffer.highlighter is not None

    def test_switch_to_json_then_python_keeps_unique_buffer_doc(self, editor):
        editor.switch_language("JSON")
        editor.switch_language("Python")
        # Tabs should still have just one document (the active untitled doc).
        assert len(editor.tabs.documents) == 1
