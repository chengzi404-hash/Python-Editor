"""``modules.settings.global_settings`` — Global settings shared across projects.

Default storage locations:

* Windows —— ``%APPDATA%/PythonEditor/settings.json``
  (falls back to ``~/PythonEditor/settings.json`` if ``APPDATA`` is not set).
* macOS —— ``~/Library/Application Support/PythonEditor/settings.json``
* Linux —— ``$XDG_CONFIG_HOME/PythonEditor/settings.json``
  (falls back to ``~/.config/PythonEditor/settings.json`` if ``XDG_CONFIG_HOME`` is not set)

Callers can explicitly override with ``path=`` (useful for testing scenarios).
"""

from __future__ import annotations

import os
import sys

from .base import SettingsScope
from .schema import GLOBAL_SCHEMA, GLOBAL_SPECS
from .storage import JsonFileSettings

_APP_NAME = "PythonEditor"
_FILE_NAME = "settings.json"


def default_global_path() -> str:
    """Return the default global settings file path.

    Cross-platform strategy:

    * Windows → ``%APPDATA%\\PythonEditor\\settings.json`` (fallback to ``~``)
    * macOS → ``~/Library/Application Support/PythonEditor/settings.json``
    * Other → ``$XDG_CONFIG_HOME/PythonEditor/settings.json``
            (fallback to ``~/.config/PythonEditor/settings.json``)
    """

    home = os.path.expanduser("~")

    if sys.platform.startswith("win"):
        base = os.environ.get("APPDATA") or os.path.join(home, "AppData", "Roaming")
        return os.path.join(base, _APP_NAME, _FILE_NAME)

    if sys.platform == "darwin":
        return os.path.join(home, "Library", "Application Support", _APP_NAME, _FILE_NAME)

    base = os.environ.get("XDG_CONFIG_HOME") or os.path.join(home, ".config")
    return os.path.join(base, _APP_NAME, _FILE_NAME)


class GlobalSettings(JsonFileSettings):
    """Global settings instance shared across projects.

    Read/write directly through the :class:`Settings` interface; the file is persisted
    to disk when :meth:`save` is called.
    """

    def __init__(
        self,
        path: str | None = None,
        *,
        auto_load: bool = True,
    ) -> None:
        super().__init__(
            GLOBAL_SCHEMA,
            scope=SettingsScope.GLOBAL,
            path=path,
            auto_load=auto_load,
        )

    def _resolve_path(self) -> str:
        return default_global_path()


__all__ = ["GLOBAL_SCHEMA", "GLOBAL_SPECS", "GlobalSettings", "default_global_path"]
