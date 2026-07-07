"""``modules.settings`` — 统一的项目设置与全局设置接口。

快速上手::

    from modules.settings import (
        SettingsManager, SettingsScope,
        GlobalSettings, ProjectSettings,
    )

    manager = SettingsManager()                # 默认加载全局设置
    manager.attach_project("/path/to/proj")    # 附加项目

    # 全局
    manager.set(SettingsScope.GLOBAL, "ui.theme", "Light")
    # 项目
    manager.set(SettingsScope.PROJECT, "project.python_interpreter",
                "/usr/bin/python3")

    # 取生效值(项目优先, 回退全局)
    theme = manager.effective("ui.theme")
    interpreter = manager.effective("project.python_interpreter")

    # 持久化(也可使用 ``with SettingsManager() as m:`` 自动保存)
    manager.save_all()

公开 API:

* :class:`SettingsManager` — 统一入口。
* :class:`GlobalSettings` — 全局设置(``SettingsScope.GLOBAL``)。
* :class:`ProjectSettings` — 项目设置(``SettingsScope.PROJECT``)。
* :class:`SettingsScope` / :class:`SettingValueType` — 枚举。
* :class:`SettingSpec` / :class:`SettingsSchema` — Schema 元信息。
* :data:`GLOBAL_SCHEMA` / :data:`PROJECT_SCHEMA` / :data:`SCHEMA_BY_SCOPE` —
  默认 Schema。
"""

from __future__ import annotations

from .base import (
    SettingSpec,
    SettingValueType,
    Settings,
    SettingsChangeEvent,
    SettingsListener,
    SettingsSchema,
    SettingsScope,
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
    "SettingsManager",
    "GlobalSettings",
    "ProjectSettings",
    "Settings",
    "JsonFileSettings",
    "SettingsSchema",
    "SettingSpec",
    "SettingValueType",
    "SettingsScope",
    "SettingsChangeEvent",
    "SettingsListener",
    "GLOBAL_SCHEMA",
    "PROJECT_SCHEMA",
    "GLOBAL_SPECS",
    "PROJECT_SPECS",
    "SCHEMA_BY_SCOPE",
    "get_schema",
    "default_global_path",
    "default_project_path",
    "CURRENT_VERSION",
]