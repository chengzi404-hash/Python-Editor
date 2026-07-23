"""End-to-end tests for the settings bridge.

Exercises :class:`CodeEditor`'s settings listener — verifies that changing a
global setting propagates to the editor's font, tab width, highlighting,
autosave, and theme state.
"""

from __future__ import annotations

import pytest

from core.settings import SettingsChangeEvent, SettingsScope


@pytest.fixture(autouse=True)
def _isolate(editor, reset_editor):
    reset_editor(editor)


class TestFont:
    def test_set_font_family_changes_buffer_widget(self, editor):
        editor._set_font_family("Courier New")
        text_widget = editor.buffer._text
        font = text_widget.cget("font")
        assert "Courier New" in str(font)

    def test_set_font_size_changes_buffer_widget(self, editor):
        editor._set_font_size(16)
        text_widget = editor.buffer._text
        font = text_widget.cget("font")
        assert "16" in str(font)

    def test_settings_change_for_font_family_propagates(self, editor):
        # Emit a fake settings event directly to the listener.
        event = SettingsChangeEvent(
            scope=SettingsScope.GLOBAL,
            key="ui.font_family",
            old="Consolas",
            new="Consolas",
        )
        # Setting the same value should be a no-op (no error).
        editor._on_settings_changed(event)
        # Setting a new value should update the buffer font.
        event2 = SettingsChangeEvent(
            scope=SettingsScope.GLOBAL,
            key="ui.font_family",
            old="Consolas",
            new="Courier New",
        )
        editor._on_settings_changed(event2)
        text_widget = editor.buffer._text
        font = text_widget.cget("font")
        assert "Courier New" in str(font)


class TestTabWidth:
    def test_set_tab_width_applies_to_text_widget(self, editor):
        editor._set_tab_width(2)
        tabs = editor.buffer._text.cget("tabs")
        # Tab width 2 * default font size 10 = 20 pixels.
        assert "20" in str(tabs)

    def test_settings_change_for_tab_size_propagates(self, editor):
        event = SettingsChangeEvent(scope=SettingsScope.GLOBAL, key="editor.tab_size", old=4, new=2)
        editor._on_settings_changed(event)
        tabs = editor.buffer._text.cget("tabs")
        assert "20" in str(tabs)


class TestTheme:
    def test_set_highlight_theme_applies(self, editor):
        before = editor._highlight_theme_name
        editor._set_highlight_theme("Default Dark")
        assert editor._highlight_theme_name == "Default Dark"
        # Same theme — no-op.
        editor._set_highlight_theme("Default Dark")
        assert editor._highlight_theme_name == "Default Dark"
        assert before == "Default Dark"

    def test_set_highlight_theme_unknown_is_noop(self, editor):
        before = editor._highlight_theme_name
        editor._set_highlight_theme("NotARealTheme")
        assert editor._highlight_theme_name == before

    def test_set_ui_theme_changes_color(self, editor):
        from ui.widgets import theme

        editor._set_theme("Dark")
        assert theme.current().name == "Dark"

    def test_settings_change_for_theme_propagates(self, editor):
        event = SettingsChangeEvent(
            scope=SettingsScope.GLOBAL, key="ui.theme", old="Dark", new="Light"
        )
        editor._on_settings_changed(event)
        from ui.widgets import theme

        assert theme.current().name == "Light"


class TestHighlighting:
    def test_toggle_highlighting_disables(self, editor):
        editor._highlighting_enabled = True
        # Simulate the user flipping the toggle off.
        editor._highlight_tk_var = None
        editor._toggle_highlighting()
        # The buffer's apply_highlight early-outs when disabled.
        editor.buffer.apply_highlight()  # should not raise

    def test_settings_change_for_completion_toggles_state(self, editor):
        event = SettingsChangeEvent(
            scope=SettingsScope.GLOBAL, key="completion.enabled", old=True, new=False
        )
        editor._on_settings_changed(event)
        assert editor._highlighting_enabled is False
        assert editor._suggestions_enabled is False

        event2 = SettingsChangeEvent(
            scope=SettingsScope.GLOBAL, key="completion.enabled", old=False, new=True
        )
        editor._on_settings_changed(event2)
        assert editor._highlighting_enabled is True
        assert editor._suggestions_enabled is True


class TestAutosave:
    def test_settings_change_for_autosave_propagates(self, editor):
        event = SettingsChangeEvent(
            scope=SettingsScope.GLOBAL, key="editor.auto_save", old=False, new=True
        )
        editor._on_settings_changed(event)
        assert editor._autosave_enabled is True

    def test_settings_change_for_autosave_format(self, editor):
        event = SettingsChangeEvent(
            scope=SettingsScope.GLOBAL,
            key="editor.auto_save_format",
            old=None,
            new="autosave_{year}-{month}-{day}.py",
        )
        editor._on_settings_changed(event)
        # Format string is stored verbatim — the auto_save_format property
        # surfaces whatever the listener wrote.
        assert "{year}" in editor.autosave_format


class TestHighlightDelay:
    def test_settings_change_for_highlight_delay_propagates(self, editor):
        event = SettingsChangeEvent(
            scope=SettingsScope.GLOBAL,
            key="editor.highlight_delay_ms",
            old=300,
            new=500,
        )
        editor._on_settings_changed(event)
        assert editor.highlight_delay_ms == 500


class TestSuppressListener:
    def test_write_setting_does_not_re_fire_listener(self, editor):
        fired: list = []

        def _listener(event):
            fired.append(event)

        editor._settings.add_listener(_listener)
        editor._write_setting(SettingsScope.GLOBAL, "ui.font_family", "Helvetica")
        # _write_setting suppresses the editor's listener but does not stop
        # other listeners (the manager broadcasts to all). At least one event
        # should still fire for the user listener.
        assert fired


class TestResetAll:
    def test_refresh_all_from_settings_is_safe(self, editor):
        # Smoke test: invoking the "all keys changed" path should not raise.
        editor._refresh_all_from_settings()
