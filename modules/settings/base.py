"""``modules.settings.base`` — 设置模块的抽象层。

本文件只定义 ``类型`` 与 ``协议``，**不** 包含任何具体实现：

* :class:`SettingSpec` 描述一个设置项（键、默认值、类型、标签、选项、范围等元信息）。
* :class:`SettingValueType` 列出允许的底层值类型，便于序列化校验。
* :class:`SettingsScope` 区分 ``全局（跨项目共享）`` 与 ``项目（当前工作区）`` 两类作用域。
* :class:`Settings` 是设置存储的抽象基类，提供 ``get / set / has / all / reset / save`` 等
  必须实现的接口。
* :class:`SettingsChangeEvent` / :class:`SettingsListener` 定义订阅/回调签名。

具体的全局/项目设置分别见 :mod:`modules.settings.global_settings` 与
:mod:`modules.settings.project_settings`；统一的对外入口是
:class:`modules.settings.manager.SettingsManager`。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Mapping, Optional, Tuple, Union




class SettingsScope(str, Enum):
    """设置作用域。

    * ``GLOBAL`` — 跨项目共享，存放在用户主目录下。
    * ``PROJECT`` — 与具体项目目录绑定，只对当前打开的项目生效。
    """

    GLOBAL = "global"
    PROJECT = "project"


class SettingValueType(str, Enum):
    """设置项支持的底层值类型。"""

    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    CHOICE = "choice"     # 字符串枚举，由 ``choices`` 提供候选项
    LIST = "list"         # 字符串列表（json 数组）
    PATH = "path"         # 文件系统路径




@dataclass(frozen=True)
class SettingSpec:
    """单个设置项的元信息。

    字段含义：

    * ``key`` —— 在作用域内唯一的标识符，使用 ``.`` 分段（例如 ``editor.tab_size``）。
    * ``type`` —— 底层值类型，详见 :class:`SettingValueType`。
    * ``default`` —— 默认值；类型必须与 ``type`` 兼容。
    * ``label`` —— UI 显示用的简短标题。
    * ``description`` —— 更长的说明，可选。
    * ``choices`` —— 当 ``type == CHOICE`` 时，列出所有候选值。
    * ``min`` / ``max`` —— 数值类型的可选边界。
    * ``choices`` —— ``CHOICE`` 类型的候选项。
    * ``scope`` —— 限定该规格只允许出现在哪种作用域。
    """

    key: str
    type: SettingValueType
    default: Any
    label: str = ""
    description: str = ""
    choices: Tuple[Any, ...] = ()
    min: Optional[float] = None
    max: Optional[float] = None
    scope: SettingsScope = SettingsScope.GLOBAL


    def validate(self, value: Any) -> Any:
        """校验并强制将 ``value`` 转换为 ``type`` 允许的类型。

        校验失败时抛出 :class:`ValueError`。返回 ``value`` 的"规整化"结果。
        """

        if self.type is SettingValueType.STRING:
            if not isinstance(value, str):
                raise ValueError(
                    f"setting {self.key!r} expects str, got {type(value).__name__}"
                )
            return value

        if self.type is SettingValueType.INTEGER:
            if isinstance(value, bool):
                raise ValueError(
                    f"setting {self.key!r} expects int, got bool"
                )
            if not isinstance(value, int):
                raise ValueError(
                    f"setting {self.key!r} expects int, got {type(value).__name__}"
                )
            if self.min is not None and value < self.min:
                raise ValueError(
                    f"setting {self.key!r} must be >= {self.min}, got {value}"
                )
            if self.max is not None and value > self.max:
                raise ValueError(
                    f"setting {self.key!r} must be <= {self.max}, got {value}"
                )
            return value

        if self.type is SettingValueType.FLOAT:
            if isinstance(value, bool):
                raise ValueError(
                    f"setting {self.key!r} expects number, got bool"
                )
            if not isinstance(value, (int, float)):
                raise ValueError(
                    f"setting {self.key!r} expects number, got {type(value).__name__}"
                )
            value = float(value)
            if self.min is not None and value < self.min:
                raise ValueError(
                    f"setting {self.key!r} must be >= {self.min}, got {value}"
                )
            if self.max is not None and value > self.max:
                raise ValueError(
                    f"setting {self.key!r} must be <= {self.max}, got {value}"
                )
            return value

        if self.type is SettingValueType.BOOLEAN:
            if not isinstance(value, bool):
                raise ValueError(
                    f"setting {self.key!r} expects bool, got {type(value).__name__}"
                )
            return value

        if self.type is SettingValueType.CHOICE:
            if not self.choices:
                raise ValueError(
                    f"setting {self.key!r} is CHOICE but has no choices"
                )
            if value not in self.choices:
                raise ValueError(
                    f"setting {self.key!r} must be one of {list(self.choices)!r}, "
                    f"got {value!r}"
                )
            return value

        if self.type is SettingValueType.LIST:
            if not isinstance(value, list):
                raise ValueError(
                    f"setting {self.key!r} expects list, got {type(value).__name__}"
                )
            for i, item in enumerate(value):
                if not isinstance(item, str):
                    raise ValueError(
                        f"setting {self.key!r}[{i}] must be str, "
                        f"got {type(item).__name__}"
                    )
            return list(value)

        if self.type is SettingValueType.PATH:
            if not isinstance(value, str):
                raise ValueError(
                    f"setting {self.key!r} expects str path, got {type(value).__name__}"
                )
            return value

        raise ValueError(f"unknown setting type: {self.type!r}")




@dataclass
class SettingsSchema:
    """一组 :class:`SettingSpec` 的集合，提供按 ``key`` 索引。

    使用示例::

        schema = SettingsSchema((SettingSpec("editor.tab_size",
                                             SettingValueType.INTEGER, 4),))
        spec = schema.get("editor.tab_size")
        assert spec is not None
    """

    specs: Tuple[SettingSpec, ...] = ()

    def __post_init__(self) -> None:
        seen: Dict[str, None] = {}
        for spec in self.specs:
            if not spec.key:
                raise ValueError("SettingSpec.key must be non-empty")
            if spec.key in seen:
                raise ValueError(f"duplicate setting key in schema: {spec.key!r}")
            seen[spec.key] = None


    def keys(self) -> List[str]:
        return [s.key for s in self.specs]

    def get(self, key: str) -> Optional[SettingSpec]:
        for spec in self.specs:
            if spec.key == key:
                return spec
        return None

    def __contains__(self, key: object) -> bool:
        return isinstance(key, str) and self.get(key) is not None

    def __iter__(self):
        return iter(self.specs)

    def __len__(self) -> int:
        return len(self.specs)


    def defaults(self) -> Dict[str, Any]:
        return {spec.key: spec.default for spec in self.specs}




@dataclass
class SettingsChangeEvent:
    """设置变更事件载荷。

    * ``scope`` —— 发生变更的作用域。
    * ``key`` —— 变更的键（``None`` 表示批量重置）。
    * ``old`` —— 变更前的值；若 ``key`` 为 ``None`` 则表示整个作用域旧快照。
    * ``new`` —— 变更后的值；若 ``key`` 为 ``None`` 则表示整个作用域新快照。
    """

    scope: SettingsScope
    key: Optional[str]
    old: Any
    new: Any


SettingsListener = Callable[[SettingsChangeEvent], None]




class Settings(ABC):
    """设置存储的抽象基类。

    子类需要将数据持久化到某个后端（磁盘文件、内存、远端……），但对外只暴露
    统一的访问接口。本类本身**不**涉及项目/全局之分——该区分由作用域参数完成。
    """

    def __init__(
        self,
        schema: SettingsSchema,
        *,
        scope: SettingsScope = SettingsScope.GLOBAL,
    ) -> None:
        super().__init__()
        self._schema = schema
        self._scope = scope
        self._listeners: List[SettingsListener] = []


    @property
    def scope(self) -> SettingsScope:
        return self._scope

    @property
    def schema(self) -> SettingsSchema:
        return self._schema


    def add_listener(self, callback: SettingsListener) -> None:
        """注册一个变更回调。"""

        if callback not in self._listeners:
            self._listeners.append(callback)

    def remove_listener(self, callback: SettingsListener) -> None:
        """移除一个已注册的回调，未注册则忽略。"""

        try:
            self._listeners.remove(callback)
        except ValueError:
            pass

    def _notify(self, event: SettingsChangeEvent) -> None:
        """内部触发回调：捕获异常避免单个监听器影响其它订阅者。"""

        for cb in list(self._listeners):
            try:
                cb(event)
            except Exception:
                pass


    @abstractmethod
    def get(self, key: str, default: Any = None) -> Any:
        """读取一个键的值。

        若键不存在或尚未被显式赋值，应返回 ``default`` 或 schema 中的默认值。
        """

    @abstractmethod
    def set(self, key: str, value: Any) -> None:
        """写入一个键的值，会触发类型校验和监听器回调。"""

    @abstractmethod
    def has(self, key: str) -> bool:
        """返回该键是否被显式赋值过。"""

    @abstractmethod
    def all(self) -> Dict[str, Any]:
        """返回 *所有* 键的当前值（包括默认值的填充快照）。"""

    @abstractmethod
    def defined(self) -> Dict[str, Any]:
        """仅返回被显式赋值过的键值对。"""

    @abstractmethod
    def reset(self, key: Optional[str] = None) -> None:
        """重置一个键或全部键。``key=None`` 表示清空所有自定义值。"""

    @abstractmethod
    def save(self) -> None:
        """将当前状态持久化到底层存储。"""

    @abstractmethod
    def load(self) -> None:
        """从底层存储重新载入（覆盖当前内存状态）。"""


    def spec(self, key: str) -> Optional[SettingSpec]:
        """返回键对应的 :class:`SettingSpec`，未注册则返回 ``None``。"""

        return self._schema.get(key)


__all__ = [
    "SettingsScope",
    "SettingValueType",
    "SettingSpec",
    "SettingsSchema",
    "SettingsChangeEvent",
    "SettingsListener",
    "Settings",
]