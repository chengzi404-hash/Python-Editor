"""``modules.settings.storage`` — 基于 JSON 文件的设置持久化基类。

为了避免 :class:`~modules.settings.global_settings.GlobalSettings` 和
:class:`~modules.settings.project_settings.ProjectSettings` 在 json I/O 与线程安全
方面重复实现，本文件提供了一个抽象基类 :class:`JsonFileSettings`。

* 数据存储为单个 JSON 对象 ``{"version": 1, "values": {...}}``。
* 所有 IO 操作通过 :class:`threading.RLock` 串行化，支持跨线程安全使用。
* :meth:`save` 写入临时文件再 ``os.replace``，避免半写状态被读到。
* :meth:`load` 容忍磁盘缺失或格式错误（回退到默认值）。
"""

from __future__ import annotations

import contextlib
import json
import os
import tempfile
import threading
from typing import Any

from .base import (
    Settings,
    SettingsChangeEvent,
    SettingsSchema,
    SettingsScope,
)

CURRENT_VERSION = 1


class JsonFileSettings(Settings):
    """基于 JSON 文件的 :class:`Settings` 基类。

    子类只需要实现 :meth:`_resolve_path` 来告知"数据写到哪里"。
    """

    def __init__(
        self,
        schema: SettingsSchema,
        *,
        scope: SettingsScope,
        path: str | None = None,
        auto_load: bool = True,
    ) -> None:
        super().__init__(schema, scope=scope)
        self._lock = threading.RLock()
        self._path: str | None = path
        self._values: dict[str, Any] = {}
        # 旁路存储: 插件专属键 (plugins.<id>.*) 不走 schema 校验,
        # 因为插件 id 是动态的、schema 注册时还未知。
        self._extras: dict[str, Any] = {}

        if self._path is not None and auto_load:
            try:
                self.load()
            except Exception:
                self._values = {}
                self._extras = {}


    def _resolve_path(self) -> str:
        """子类必须返回当前应使用的 JSON 文件绝对路径。

        当构造时显式传入了 ``path``，将直接使用该路径；
        否则调用本方法懒加载解析（例如基于用户主目录 / 项目目录）。
        """

        raise NotImplementedError(
            "JsonFileSettings subclass must implement _resolve_path() "
            "or pass path=... explicitly."
        )

    def _ensure_parent_dir(self, path: str) -> None:
        """确保 ``path`` 的父目录存在。默认 ``os.makedirs(..., exist_ok=True)``。"""

        parent = os.path.dirname(path)
        if parent:
            os.makedirs(parent, exist_ok=True)

    @property
    def path(self) -> str:
        """返回当前文件路径（懒解析）。"""

        if self._path is None:
            self._path = self._resolve_path()
        return self._path


    def _raw_default(self, key: str) -> Any:
        spec = self.spec(key)
        return spec.default if spec is not None else None


    @staticmethod
    def _is_plugin_key(key: str) -> bool:
        """判断 ``key`` 是否属于插件命名空间 (``plugins.<id>.*``)。

        该命名空间允许任意字符串 id, 不走 schema 校验, 由插件系统
        自行保证值的合理性。
        """

        if not isinstance(key, str) or not key:
            return False
        return key.startswith("plugins.") and key.count(".") >= 2

    def get(self, key: str, default: Any = None) -> Any:
        with self._lock:
            if key in self._values:
                return self._values[key]
            if key in self._extras:
                return self._extras[key]
            if default is None:
                return self._raw_default(key)
            return default

    def set(self, key: str, value: Any) -> None:
        # 插件命名空间: 走 _extras 旁路, 不校验 schema, 但仍然发事件
        # 让 PluginContext.set_setting 之外的监听者也能感知。
        if self._is_plugin_key(key):
            with self._lock:
                old = self._extras.get(key)
                if old == value and key in self._extras:
                    return
                self._extras[key] = value
                event = SettingsChangeEvent(
                    scope=self.scope,
                    key=key,
                    old=old,
                    new=value,
                )
            self._notify(event)
            return

        spec = self.spec(key)
        if spec is None:
            raise KeyError(
                f"unknown setting key in scope={self.scope.value!r}: {key!r}"
            )
        coerced = spec.validate(value)

        with self._lock:
            old = self._values.get(key, self._raw_default(key))
            if old == coerced and key in self._values:
                return
            self._values[key] = coerced
            event = SettingsChangeEvent(
                scope=self.scope,
                key=key,
                old=old,
                new=coerced,
            )

        self._notify(event)

    def has(self, key: str) -> bool:
        with self._lock:
            return key in self._values or key in self._extras

    def all(self) -> dict[str, Any]:
        """所有键的当前值，缺失字段填充默认值。"""

        with self._lock:
            result: dict[str, Any] = {}
            for spec in self._schema:
                result[spec.key] = self._values.get(spec.key, spec.default)
            for k, v in self._extras.items():
                result[k] = v
            return result

    def defined(self) -> dict[str, Any]:
        with self._lock:
            merged = dict(self._values)
            merged.update(self._extras)
            return merged

    def reset(self, key: str | None = None) -> None:
        with self._lock:
            if key is None:
                if not self._values and not self._extras:
                    return
                old_snapshot = self.all()
                self._values.clear()
                self._extras.clear()
                new_snapshot = self.all()
                event = SettingsChangeEvent(
                    scope=self.scope,
                    key=None,
                    old=old_snapshot,
                    new=new_snapshot,
                )
                self._notify(event)
                return

            if key in self._extras:
                old = self._extras.pop(key)
                event = SettingsChangeEvent(
                    scope=self.scope,
                    key=key,
                    old=old,
                    new=None,
                )
                self._notify(event)
                return
            if key not in self._values:
                return  # 已经是默认状态,无需重置
            old = self._values.pop(key)
            new = self._raw_default(key)
            event = SettingsChangeEvent(
                scope=self.scope,
                key=key,
                old=old,
                new=new,
            )
            self._notify(event)


    def save(self) -> None:
        path = self.path
        self._ensure_parent_dir(path)

        with self._lock:
            merged_values = dict(self._values)
            merged_values.update(self._extras)
            payload = {
                "version": CURRENT_VERSION,
                "scope": self.scope.value,
                "values": merged_values,
            }

        parent = os.path.dirname(path) or "."
        fd, tmp_path = tempfile.mkstemp(prefix=".settings_", suffix=".tmp", dir=parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
                f.flush()
                with contextlib.suppress(OSError, AttributeError):
                    os.fsync(f.fileno())
            os.replace(tmp_path, path)
        except Exception:
            with contextlib.suppress(OSError):
                os.unlink(tmp_path)
            raise

    def load(self) -> None:
        path = self.path
        if not os.path.isfile(path):
            return

        try:
            with open(path, encoding="utf-8") as f:
                raw = json.load(f)
        except (OSError, json.JSONDecodeError):
            return

        if not isinstance(raw, dict):
            return

        raw_values = raw.get("values", {})
        if not isinstance(raw_values, dict):
            return

        new_values: dict[str, Any] = {}
        new_extras: dict[str, Any] = {}
        for key, value in raw_values.items():
            if self._is_plugin_key(key):
                new_extras[key] = value
                continue
            spec = self.spec(key)
            if spec is None:
                continue
            try:
                new_values[key] = spec.validate(value)
            except (ValueError, TypeError):
                continue

        with self._lock:
            self._values = new_values
            self._extras = new_extras


__all__ = ["CURRENT_VERSION", "JsonFileSettings"]
