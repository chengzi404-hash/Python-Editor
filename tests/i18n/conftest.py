"""``modules.i18n`` 测试的共享 fixtures.

``Translator`` 是进程内单例, 直接 ``set_language`` 会污染后续测试。
``with_language`` 上下文管理器 / fixture 用 ``try/finally`` 保证用例
结束时一定恢复原语言。
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Generator

import pytest

from modules.i18n import get_translator


@contextmanager
def _with_language(locale: str) -> Generator[None, None, None]:
    """临时切换翻译器语言, 退出 with 时恢复原语言。"""

    tr = get_translator()
    original = tr.current_language
    tr.set_language(locale)
    try:
        yield
    finally:
        tr.set_language(original)


@pytest.fixture
def english_translator() -> Generator[None, None, None]:
    """用例期间把翻译器切到 ``en_US``, 用例结束自动恢复。"""

    with _with_language("en_US"):
        yield


@pytest.fixture
def chinese_translator() -> Generator[None, None, None]:
    """用例期间把翻译器切到 ``zh_CN``, 用例结束自动恢复。"""

    with _with_language("zh_CN"):
        yield