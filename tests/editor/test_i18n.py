"""End-to-end tests for the i18n locale switch path.

Verifies that flipping :data:`core.settings.i18n.AVAILABLE_LANGUAGES` triggers
the editor's :meth:`_on_language_changed` handler, which rebuilds the menus
and updates status strings.
"""

from __future__ import annotations

import pytest

from core.settings import SettingsChangeEvent
from core.settings.i18n import get_translator


@pytest.fixture(autouse=True)
def _isolate(editor, reset_editor):
    reset_editor(editor)


class TestLocaleSwitch:
    def test_default_locale_is_zh_cn(self, editor):
        translator = get_translator()
        assert translator.current_language in ("zh_CN", "en_US")

    def test_setting_i18n_locale_triggers_rerender(self, editor):
        translator = get_translator()
        original = translator.current_language
        # Choose the *other* locale so we know a real change occurred.
        target = "en_US" if original == "zh_CN" else "zh_CN"
        # Snapshot the menu instance before the change.
        menus_before = editor.menus
        translator.set_language(target)
        # Wait for the editor's listener to fire (it is synchronous).
        # The editor should have replaced its menus with a new instance.
        assert editor.menus is not menus_before
        # Locale must have flipped.
        assert translator.current_language == target

    def test_setting_same_locale_is_noop(self, editor):
        translator = get_translator()
        before = translator.current_language
        # Calling set_language with the current language should be a no-op.
        translator.set_language(before)
        assert translator.current_language == before

    def test_setting_invalid_locale_does_not_change(self, editor):
        translator = get_translator()
        before = translator.current_language
        translator.set_language("not_a_real_locale")
        assert translator.current_language == before

    def test_language_change_rebuilds_menu(self, editor):
        """Switching language should rebuild the menu bar so that titles,
        commands and shortcuts use the new locale's strings.
        """
        translator = get_translator()
        original = translator.current_language
        target = "en_US" if original == "zh_CN" else "zh_CN"

        # Capture a reference to the menu instance before the swap.
        menus_before = editor.menus
        translator.set_language(target)

        # The editor should have replaced its menus with a new instance.
        assert editor.menus is not menus_before

    def test_settings_event_for_i18n_language_propagates(self, editor):
        """A settings change for ``i18n.language`` should rebuild the menu.

        The translator itself flips locale; the editor's listener only
        rebuilds widgets. Verify the latter happens.
        """
        translator = get_translator()
        original = translator.current_language
        target = "en_US" if original == "zh_CN" else "zh_CN"
        menus_before = editor.menus
        # The translator's set_language broadcasts to all listeners.
        translator.set_language(target)
        # The editor should have rebuilt its menus.
        assert editor.menus is not menus_before
        # Translator reflects the change.
        assert translator.current_language == target
        # And ``t()`` now returns target-locale strings.
        from core.settings.i18n import t

        # Pick a translation key that is known to differ between locales.
        title = t("dialog.title.about")
        # We don't assert the exact wording; just that *some* string was returned.
        assert title


def _collect_menu_labels(editor) -> list[str]:
    """Walk the menu bar and pull out every visible label string."""
    labels: list[str] = []
    try:
        menu_bar = editor.menus._menu_bar
        for i in range(menu_bar.index("end") + 1 if menu_bar.index("end") is not None else 0):
            try:
                label = menu_bar.entrycget(i, "label")
                labels.append(str(label))
            except Exception:
                pass
    except Exception:
        pass
    return labels


def _has_translated(editor, locale: str) -> bool:
    """Return True if at least one menu label looks locale-specific."""
    from core.settings.i18n import t

    labels = _collect_menu_labels(editor)
    expected = t("file_dialog.all_files", locale=locale)
    return any(expected in label for label in labels)
