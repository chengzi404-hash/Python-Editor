"""``core.settings`` — Settings module.

This package contains:
- ``settings/`` — Settings management
- ``i18n/`` — Internationalization
- ``logging/`` — Logging configuration
"""

from core.settings.settings import (
    GLOBAL_SCHEMA,
    GLOBAL_SPECS,
    PROJECT_SCHEMA,
    PROJECT_SPECS,
    SCHEMA_BY_SCOPE,
    GlobalSettings,
    JsonFileSettings,
    ProjectSettings,
    Settings,
    SettingsChangeEvent,
    SettingsListener,
    SettingsManager,
    SettingSpec,
    SettingsSchema,
    SettingsScope,
    SettingValueType,
    default_global_path,
    default_project_path,
    get_schema,
)
from core.settings.settings.storage import CURRENT_VERSION

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
