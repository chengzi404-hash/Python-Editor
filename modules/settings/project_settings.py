"""``modules.settings.project_settings`` — 与具体项目目录绑定的设置。

存储位置: ``<project_root>/.pyeditor/settings.json``

调用方必须在 :class:`ProjectSettings` 构造时通过 ``root=`` 显式指定项目根目录。
"""

from __future__ import annotations

import os
from typing import Optional

from .base import SettingsScope
from .schema import PROJECT_SCHEMA, PROJECT_SPECS
from .storage import JsonFileSettings


_HIDDEN_DIR = ".pyeditor"
_FILE_NAME = "settings.json"


def default_project_path(project_root: str) -> str:
    """返回项目设置文件应该位于的路径。

    参数 ``project_root`` 必须指向已存在的目录；返回 ``<root>/.pyeditor/settings.json``。
    """

    return os.path.join(project_root, _HIDDEN_DIR, _FILE_NAME)


class ProjectSettings(JsonFileSettings):
    """与单个项目绑定的设置实例。

    通过 :attr:`root` 标识项目根目录；切换项目需要重新构造实例，
    或在 :class:`~modules.settings.manager.SettingsManager` 中通过
    :meth:`attach_project` 完成。
    """

    def __init__(
        self,
        root: str,
        path: Optional[str] = None,
        *,
        auto_load: bool = True,
    ) -> None:
        if not root:
            raise ValueError("ProjectSettings requires non-empty project root")
        self._root = os.path.abspath(root)

        if path is None and auto_load:
            # 立即解析默认路径,确保之前已存在的 settings.json 能被加载。
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
        """便捷方法: 返回 ``project.name`` 若已设置,否则使用目录名。"""

        name = self.get("project.name", "")
        if isinstance(name, str) and name.strip():
            return name
        return os.path.basename(self._root) or self._root


__all__ = [
    "ProjectSettings",
    "default_project_path",
    "PROJECT_SPECS",
    "PROJECT_SCHEMA",
]