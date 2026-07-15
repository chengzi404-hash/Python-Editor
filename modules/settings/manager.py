"""``modules.settings.manager`` — 统一对外接口 :class:`SettingsManager`。

封装"全局设置 + (可选) 当前项目设置"，对外提供：

* :meth:`get` / :meth:`set` —— 在指定作用域上读写单个键。
* :meth:`effective` —— 解析"项目覆盖全局"的最终生效值。
* :meth:`attach_project` / :meth:`detach_project` —— 切换当前项目。
* :meth:`add_listener` —— 同时监听全局 / 项目变更。
* :meth:`save_all` —— 将两侧一并持久化。

典型用法::

    from modules.settings import SettingsManager, SettingsScope

    manager = SettingsManager()
    # 全局设置
    manager.set(SettingsScope.GLOBAL, "ui.theme", "Light")
    # 附加项目
    manager.attach_project("/path/to/project")
    manager.set(SettingsScope.PROJECT, "project.python_interpreter", "/usr/bin/python3")
    # 生效值(项目优先, 否则回退全局)
    interpreter = manager.effective("project.python_interpreter")
"""

from __future__ import annotations

import contextlib
import threading
from typing import Any

from .base import (
    Settings,
    SettingsChangeEvent,
    SettingsListener,
    SettingsScope,
)
from .global_settings import GlobalSettings
from .project_settings import ProjectSettings


class SettingsManager:
    """全局 + 项目设置的统一管理器。

    始终持有一个 :class:`GlobalSettings` 实例；
    当前项目 (:class:`ProjectSettings`) 可选, 通过 :meth:`attach_project` 绑定。
    """

    def __init__(
        self,
        global_settings: GlobalSettings | None = None,
        project_settings: ProjectSettings | None = None,
    ) -> None:
        self._lock = threading.RLock()
        self._global = global_settings or GlobalSettings()
        self._project: ProjectSettings | None = project_settings
        self._user_listeners: list[SettingsListener] = []


    @property
    def global_settings(self) -> GlobalSettings:
        return self._global

    @property
    def project_settings(self) -> ProjectSettings | None:
        return self._project

    @property
    def project_root(self) -> str | None:
        return self._project.root if self._project is not None else None


    def attach_project(self, root: str) -> ProjectSettings:
        """挂载项目根目录并返回新的 :class:`ProjectSettings` 实例。

        若已经挂载过其它项目,会先调用 :meth:`save_all` 持久化旧项目。
        """

        with self._lock:
            if self._project is not None:
                with contextlib.suppress(Exception):
                    self.save_all()
            self._project = ProjectSettings(root=root)
            self._project.add_listener(self._relay_event)
            return self._project

    def detach_project(self) -> None:
        """卸载当前项目并保存。"""

        with self._lock:
            if self._project is None:
                return
            with contextlib.suppress(Exception):
                self._project.save()
            self._project.remove_listener(self._relay_event)
            self._project = None


    def _resolve(self, scope: SettingsScope) -> Settings:
        if scope is SettingsScope.PROJECT:
            if self._project is None:
                raise LookupError(
                    "no project attached; call attach_project() first"
                )
            return self._project
        return self._global

    def get(self, scope: SettingsScope, key: str, default: Any = None) -> Any:
        """在指定作用域上读取一个键的值。"""

        target = self._resolve(scope)
        return target.get(key, default)

    def effective(self, key: str, default: Any = None) -> Any:
        """解析"项目覆盖全局"的最终生效值。

        解析顺序:

        1. 当前项目（若已挂载）若定义了键 → 使用项目值。
        2. 全局值（默认填充）。
        3. ``default`` 参数。
        """

        if self._project is not None and self._project.has(key):
            return self._project.get(key)
        return self._global.get(key, default)


    def set(self, scope: SettingsScope, key: str, value: Any) -> None:
        """在指定作用域上写入一个键。会触发校验、事件与桥接监听。"""

        target = self._resolve(scope)
        target.set(key, value)

    def reset(self, scope: SettingsScope, key: str | None = None) -> None:
        """重置作用域下的一个键或全部键。"""

        target = self._resolve(scope)
        target.reset(key)


    def add_listener(self, callback: SettingsListener) -> None:
        """注册一个变更回调, 同时监听全局与(当前)项目。"""

        if callback in self._user_listeners:
            return
        self._user_listeners.append(callback)
        self._global.add_listener(self._relay_event)
        if self._project is not None:
            self._project.add_listener(self._relay_event)

    def remove_listener(self, callback: SettingsListener) -> None:
        """移除一个回调。"""

        try:
            self._user_listeners.remove(callback)
        except ValueError:
            return
        if not self._user_listeners:
            self._global.remove_listener(self._relay_event)
            if self._project is not None:
                self._project.remove_listener(self._relay_event)

    def _relay_event(self, event: SettingsChangeEvent) -> None:
        """把子对象事件原样转发给所有 manager 级订阅者。"""

        for cb in list(self._user_listeners):
            with contextlib.suppress(Exception):
                cb(event)


    def save_all(self) -> None:
        """保存全局 + 当前项目(若存在)。"""

        self._global.save()
        if self._project is not None:
            self._project.save()

    def reload_all(self) -> None:
        """重新加载全局 + 当前项目。"""

        self._global.load()
        if self._project is not None:
            self._project.load()


    def global_all(self) -> dict[str, Any]:
        return self._global.all()

    def project_all(self) -> dict[str, Any]:
        if self._project is None:
            return {}
        return self._project.all()

    def effective_all(self) -> dict[str, Any]:
        """返回合并后的生效配置(项目覆盖全局)。"""

        merged = self._global.all()
        if self._project is not None:
            for key, value in self._project.all().items():
                if self._project.has(key):
                    merged[key] = value
        return merged


    def __enter__(self) -> SettingsManager:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        with contextlib.suppress(Exception):
            self.save_all()

    def __repr__(self) -> str:
        root = self.project_root
        return (
            f"SettingsManager(global={self._global.path!r}, "
            f"project={root!r})"
        )


__all__ = ["SettingsManager"]
