"""``modules.settings.project_settings`` — Settings bound to a specific project directory.

Storage location: ``<project_root>/.pyeditor/settings.json``

Callers must explicitly specify the project root directory via ``root=`` when constructing :class:`ProjectSettings`.
"""

from __future__ import annotations

import os

from .base import SettingsScope
from .schema import PROJECT_SCHEMA, PROJECT_SPECS
from .storage import JsonFileSettings

_HIDDEN_DIR = ".pyeditor"
_FILE_NAME = "settings.json"


def default_project_path(project_root: str) -> str:
    """Return the path where the project settings file should be located.

    The ``project_root`` parameter must point to an existing directory; returns ``<root>/.pyeditor/settings.json``.
    """

    return os.path.join(project_root, _HIDDEN_DIR, _FILE_NAME)


class ProjectSettings(JsonFileSettings):
    """Settings instance bound to a single project.

    Identifies the project root directory via :attr:`root`; switching projects requires
    reconstructing the instance, or using :meth:`attach_project` in
    :class:`~modules.settings.manager.SettingsManager`.
    """

    def __init__(
        self,
        root: str,
        path: str | None = None,
        *,
        auto_load: bool = True,
    ) -> None:
        if not root:
            raise ValueError("ProjectSettings requires non-empty project root")
        self._root = os.path.abspath(root)

        if path is None and auto_load:
            # Immediately resolve default path to ensure any existing settings.json can be loaded.
            resolved = self._resolve_path()
            super().__init__(
                PROJECT_SCHEMA,
                scope=SettingsScope.PROJECT,
                path=resolved,
                auto_load=True,
            )
            return

        super().__init__(
            PROJECT_SCHEMA,
            scope=SettingsScope.PROJECT,
            path=path,
            auto_load=auto_load,
        )

    @property
    def root(self) -> str:
        return self._root

    def _resolve_path(self) -> str:
        return default_project_path(self._root)

    def project_name(self) -> str:
        """Convenience method: returns ``project.name`` if set, otherwise uses the directory name."""

        name = self.get("project.name", "")
        if isinstance(name, str) and name.strip():
            return name
        return os.path.basename(self._root) or self._root


__all__ = [
    "PROJECT_SCHEMA",
    "PROJECT_SPECS",
    "ProjectSettings",
    "default_project_path",
]
