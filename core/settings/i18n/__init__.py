"""``modules.i18n`` — Lightweight internationalization (i18n) support.

Design goals:

* **Zero dependencies**: No ``gettext`` / ``babel`` or other third-party packages;
  uses JSON directly as translation source, easy for users to modify in PRs.
* **Key-based lookup**: Retrieve strings for the current language via semantic keys
  (e.g. ``menu.file.new``); missing translations gracefully degrade to the key itself,
  avoiding blank UI text.
* **Runtime switching**: Provides a listener interface; the editor can rebuild menus /
  re-render the status bar upon language change events.
* **Integrated with settings system**: Preferences persisted via the
  ``i18n.language`` option in ``modules.settings``, loaded automatically at startup.

Public API::

    from core.settings.i18n import t, translator, get_translator

    translator.set_language("en_US")
    print(t("menu.file.new"))          # -> "New"
    print(t("greeting", name="Alice")) # -> "Hello, Alice!"

    def on_change(lang):
        print("language switched to", lang)
    translator.add_listener(on_change)
"""

from __future__ import annotations

from . import marketplace as language_marketplace
from .translator import (
    AVAILABLE_LANGUAGES,
    I18nListener,
    Translator,
    get_translator,
    t,
)

__all__ = [
    "AVAILABLE_LANGUAGES",
    "I18nListener",
    "Translator",
    "get_translator",
    "language_marketplace",
    "t",
]
