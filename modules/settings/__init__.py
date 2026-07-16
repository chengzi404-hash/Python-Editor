"""``modules.settings`` — Unified project settings and global settings interface.

Quick start::

    from modules.settings import (
        SettingsManager, SettingsScope,
        GlobalSettings, ProjectSettings,
    )

    manager = SettingsManager()                # Default loads global settings
    manager.attach_project("/path/to/proj")    # Attach project

    # Global
    manager.set(SettingsScope.GLOBAL, "ui.theme", "Light")
    # Project
    manager.set(SettingsScope.PROJECT, "project.python_interpreter",
                "/usr/bin/python3")

    # Get effective value (project first, fallback to global)
    theme = manager.effective("ui.theme")
    interpreter = manager.effective("project.python_interpreter")

    # Persist (can also use ``with SettingsManager() as m:`` for auto-save)
    manager.save_all()

Public API:

* :class:`SettingsManager` — Unified entry point.
* :class:`GlobalSettings` — Global settings (``SettingsScope.GLOBAL``).
* :class:`ProjectSettings` — Project settings (``SettingsScope.PROJECT``).
* :class:`SettingsScope` / :class:`SettingValueType` — Enums.
* :class:`SettingSpec` / :class:`SettingsSchema` — Schema metadata.
* :data:`GLOBAL_SCHEMA` / :data:`PROJECT_SCHEMA` / :data:`SCHEMA_BY_SCOPE` —
  Default Schema.
"""

from __future__ import annotations

from .base import (
    Settings,
    SettingsChangeEvent,
    SettingsListener,
    SettingSpec,
    SettingsSchema,
    SettingsScope,
    SettingValueType,
)
from .global_settings import (
    GLOBAL_SCHEMA,
    GLOBAL_SPECS,
    GlobalSettings,
    default_global_path,
)
from .manager import SettingsManager
from .project_settings import (
    PROJECT_SCHEMA,
    PROJECT_SPECS,
    ProjectSettings,
    default_project_path,
)
from .schema import SCHEMA_BY_SCOPE, get_schema
from .storage import CURRENT_VERSION, JsonFileSettings

__all__ = [
    "CURRENT_VERSION",
    "GLOBAL_SCHEMA",
    "GLOBAL_SPECS",
    "PROJECT_SCHEMA",
    "PROJECT_SPECS",
    "SCHEMA_BY_SCOPE",
    "GlobalSettings",
    "JsonFileSettings",
    "ProjectSettings",
    "SettingSpec",
    "SettingValueType",
    "Settings",
    "SettingsChangeEvent",
    "SettingsListener",
    "SettingsManager",
    "SettingsSchema",
    "SettingsScope",
    "default_global_path",
    "default_project_path",
    "get_schema",
]
