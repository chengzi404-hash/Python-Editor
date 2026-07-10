"""``modules.data`` — 统一的数据文件访问接口。

所有数据文件统一从 ``data/`` 目录加载, 通过此模块暴露的 API 访问。

支持的子模块:

* ``i18n`` — 翻译文件, 通过 :func:`i18n_path` 获取 locales 目录路径。
"""

from __future__ import annotations

import os


_ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")


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


__all__ = ["i18n_path", "data_path", "data_dir", "suggestions_path"]
