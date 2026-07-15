"""``modules.settings.global_settings`` — 跨项目共享的全局设置。

默认存储位置：

* Windows —— ``%APPDATA%/PythonEditor/settings.json``
  （若 ``APPDATA`` 未设置则回退到 ``~/PythonEditor/settings.json``）。
* macOS —— ``~/Library/Application Support/PythonEditor/settings.json``
* Linux —— ``$XDG_CONFIG_HOME/PythonEditor/settings.json``
  （若 ``XDG_CONFIG_HOME`` 未设置则回退到 ``~/.config/PythonEditor/settings.json``）

调用方可通过 ``path=`` 显式覆盖（测试场景）。
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
    """返回默认的全局设置文件路径。

    跨平台策略:

    * Windows → ``%APPDATA%\\PythonEditor\\settings.json`` (回退到 ``~``)
    * macOS → ``~/Library/Application Support/PythonEditor/settings.json``
    * 其它 → ``$XDG_CONFIG_HOME/PythonEditor/settings.json``
            (回退到 ``~/.config/PythonEditor/settings.json``)
    """

    home = os.path.expanduser("~")

    if sys.platform.startswith("win"):
        base = os.environ.get("APPDATA") or os.path.join(home, "AppData", "Roaming")
        return os.path.join(base, _APP_NAME, _FILE_NAME)

    if sys.platform == "darwin":
        return os.path.join(
            home, "Library", "Application Support", _APP_NAME, _FILE_NAME
        )

    base = os.environ.get("XDG_CONFIG_HOME") or os.path.join(home, ".config")
    return os.path.join(base, _APP_NAME, _FILE_NAME)


class GlobalSettings(JsonFileSettings):
    """跨项目共享的全局设置实例。

    直接通过 :class:`Settings` 接口读写，文件会在 :meth:`save` 时落盘。
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
