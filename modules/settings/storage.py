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

import json
import os
import tempfile
import threading
from typing import Any, Dict, Optional

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
        path: Optional[str] = None,
        auto_load: bool = True,
    ) -> None:
        super().__init__(schema, scope=scope)
        self._lock = threading.RLock()
        self._path: Optional[str] = path
        self._values: Dict[str, Any] = {}

        if self._path is not None and auto_load:
            try:
                self.load()
            except Exception:
                self._values = {}


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


    def get(self, key: str, default: Any = None) -> Any:
        with self._lock:
            if key in self._values:
                return self._values[key]
            if default is None:
                return self._raw_default(key)
            return default

    def set(self, key: str, value: Any) -> None:
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
            return key in self._values

    def all(self) -> Dict[str, Any]:
        """所有键的当前值，缺失字段填充默认值。"""

        with self._lock:
            result: Dict[str, Any] = {}
            for spec in self._schema:
                result[spec.key] = self._values.get(spec.key, spec.default)
            return result

    def defined(self) -> Dict[str, Any]:
        with self._lock:
            return dict(self._values)

    def reset(self, key: Optional[str] = None) -> None:
        with self._lock:
            if key is None:
                if not self._values:
                    return
                old_snapshot = self.all()
                self._values.clear()
                new_snapshot = self.all()
                event = SettingsChangeEvent(
                    scope=self.scope,
                    key=None,
                    old=old_snapshot,
                    new=new_snapshot,
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
            payload = {
                "version": CURRENT_VERSION,
                "scope": self.scope.value,
                "values": self._values,
            }

        parent = os.path.dirname(path) or "."
        fd, tmp_path = tempfile.mkstemp(prefix=".settings_", suffix=".tmp", dir=parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
                f.flush()
                try:
                    os.fsync(f.fileno())
                except (OSError, AttributeError):
                    pass
            os.replace(tmp_path, path)
        except Exception:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise

    def load(self) -> None:
        path = self.path
        if not os.path.isfile(path):
            return

        try:
            with open(path, "r", encoding="utf-8") as f:
                raw = json.load(f)
        except (OSError, json.JSONDecodeError):
            return

        if not isinstance(raw, dict):
            return

        raw_values = raw.get("values", {})
        if not isinstance(raw_values, dict):
            return

        new_values: Dict[str, Any] = {}
        for key, value in raw_values.items():
            spec = self.spec(key)
            if spec is None:
                continue
            try:
                new_values[key] = spec.validate(value)
            except (ValueError, TypeError):
                continue

        with self._lock:
            self._values = new_values


__all__ = ["JsonFileSettings", "CURRENT_VERSION"]