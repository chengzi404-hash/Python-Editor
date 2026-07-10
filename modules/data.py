"""``modules.data`` — 统一的数据文件访问接口。

所有数据文件统一从 ``data/`` 目录加载, 通过此模块暴露的 API 访问。

支持的子模块:

* ``i18n`` — 翻译文件, 通过 :func:`i18n_path` 获取 locales 目录路径。
* ``cache`` — 运行时缓存(库 DOM 等), 通过 :func:`cache_path` 获取缓存目录路径。
"""

from __future__ import annotations

import os


_ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
_CACHE_ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cache")


def i18n_path(*parts: str) -> str:
    """返回 ``data/i18n/<parts>`` 的绝对路径。"""
    return os.path.join(_ROOT, "i18n", *parts)


def data_path(*parts: str) -> str:
    """返回 ``data/<parts>`` 的绝对路径。"""
    return os.path.join(_ROOT, *parts)


def data_dir() -> str:
    """返回 data 根目录路径。"""
    return _ROOT


def suggestions_path(*parts: str) -> str:
    """返回 ``data/suggestions/<parts>`` 的绝对路径。"""
    return os.path.join(_ROOT, "suggestions", *parts)


def cache_dir() -> str:
    """返回 cache 根目录路径(项目根目录下 ``cache/``),不存在时会自动创建。"""
    os.makedirs(_CACHE_ROOT, exist_ok=True)
    return _CACHE_ROOT


def cache_path(*parts: str) -> str:
    """返回 ``cache/<parts>`` 的绝对路径,父目录会自动创建。"""
    base = cache_dir()
    target = os.path.join(base, *parts) if parts else base
    if parts:
        os.makedirs(os.path.dirname(target) or base, exist_ok=True)
    return target


__all__ = ["i18n_path", "data_path", "data_dir", "suggestions_path", "cache_dir", "cache_path"]
