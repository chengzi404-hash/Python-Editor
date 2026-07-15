"""``modules.i18n.translator`` —— 翻译器核心实现。

翻译源: ``modules/i18n/locales/<lang>.json``, JSON 对象 ``{key: text}``。

* 支持 ``str.format`` 占位符: 翻译里的 ``{name}`` 会被调用时的关键字
  参数替换, 便于 ``t("greeting", name="Alice")``。
* 缺翻译时回退策略: 当前语言无 key → 英文(zh_CN 缺时)→ key 原文。
  任何情况下 UI 都不会因为翻译缺失而出现空白。
* 语言变更通过 :meth:`Translator.set_language` 触发, 注册的
  :data:`I18nListener` 会被同步调用。
"""

from __future__ import annotations

import contextlib
import json
import os
import threading
from collections.abc import Callable
from typing import Any

from modules.data import i18n_path

_LOCALE_DIR = i18n_path("locales")

AVAILABLE_LANGUAGES: tuple = ("zh_CN", "en_US")

I18nListener = Callable[[str], None]


def _load_locale(lang: str) -> dict[str, str]:
    """加载某语言的翻译 JSON。文件不存在或损坏时返回空 dict。

    兼容 BOM, 但容忍任何解析错误: 翻译缺失属于正常情况(后续会回退),
    抛异常只会把 UI 锁死。
    """

    path = os.path.join(_LOCALE_DIR, f"{lang}.json")
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(data, dict):
        return {}
    return {str(k): str(v) for k, v in data.items()}


class Translator:
    """全局翻译器实例。

    单例: 通过 :func:`get_translator` 获取, 整个进程共享一个实例, 避免
    不同模块里 ``t()`` 指向不同语言。
    """

    _FALLBACK_LANG = "en_US"

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._current: str = self._FALLBACK_LANG
        self._tables: dict[str, dict[str, str]] = {}
        self._listeners: list[I18nListener] = []
        self._changing: bool = False
        for lang in AVAILABLE_LANGUAGES:
            self._tables[lang] = _load_locale(lang)

    @property
    def current_language(self) -> str:
        with self._lock:
            return self._current

    @property
    def available_languages(self) -> tuple:
        return AVAILABLE_LANGUAGES

    def set_language(self, lang: str) -> bool:
        """切换当前语言。返回是否真的改了。"""

        if lang not in AVAILABLE_LANGUAGES:
            return False
        with self._lock:
            if self._changing:
                return False
            if lang == self._current:
                return False
            self._changing = True
            self._current = lang
            listeners = list(self._listeners)
        try:
            for cb in listeners:
                with contextlib.suppress(Exception):
                    cb(lang)
            return True
        finally:
            with self._lock:
                self._changing = False

    def add_listener(self, callback: I18nListener) -> None:
        with self._lock:
            if callback in self._listeners:
                return
            self._listeners.append(callback)

    def remove_listener(self, callback: I18nListener) -> None:
        with self._lock:
            with contextlib.suppress(ValueError):
                self._listeners.remove(callback)

    def reload(self) -> None:
        """从磁盘重读所有语言包。便于测试与开发期修改后立即生效。"""

        with self._lock:
            for lang in AVAILABLE_LANGUAGES:
                self._tables[lang] = _load_locale(lang)

    def has(self, key: str, locale: str | None = None) -> bool:
        """查询某 key 在指定(默认当前)语言下是否存在翻译。"""

        target = locale if locale is not None else self._current
        return key in self._tables.get(target, {})

    def translate(self, key: str, default: str | None = None,
                  locale: str | None = None, **kwargs: Any) -> str:
        """查询 key 对应的翻译。

        参数:
            key —— 翻译键, 例如 ``"menu.file.new"``。
            default —— 找不到时使用的兜底文本; 缺省则使用 key 本身。
            locale —— 强制使用某语言(默认当前语言), 便于插件按需求跨语言渲染。
            **kwargs —— 传给 ``str.format`` 的占位符。

        返回值: 翻译好的字符串。永远不会是 ``None``, 缺翻译至少返回 key。
        """

        with self._lock:
            target = locale if locale is not None else self._current
            text = self._tables.get(target, {}).get(key)
            if text is None and target != self._FALLBACK_LANG:
                text = self._tables.get(self._FALLBACK_LANG, {}).get(key)
            if text is None:
                text = default if default is not None else key
        if kwargs:
            try:
                return text.format(**kwargs)
            except (KeyError, IndexError, ValueError):
                # 占位符不匹配: 返回原始字符串而非抛错, 防止 UI 闪退
                return text
        return text


_TRANSLATOR = Translator()


def get_translator() -> Translator:
    """返回全局翻译器实例。"""

    return _TRANSLATOR


def t(key: str, default: str | None = None, **kwargs: Any) -> str:
    """模块级快捷翻译函数: 等价于 ``get_translator().translate(...)``。"""

    return _TRANSLATOR.translate(key, default=default, **kwargs)


__all__ = [
    "AVAILABLE_LANGUAGES",
    "I18nListener",
    "Translator",
    "get_translator",
    "t",
]
