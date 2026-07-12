"""``modules.highlighter`` 子树的共享 fixtures 与断言辅助.

将所有 ``test_*`` 文件通用的 ``HighlightBlock`` token 抽取/比较
辅助集中到这里, 避免在 ``test_python.py`` / ``test_ccpp.py`` 之间
复制实现。
"""

from __future__ import annotations

from modules.highlighter import HighlightBlock, HighlightToken


def token_types(result: HighlightBlock) -> list[str]:
    """返回 token ``type`` 列表(便于顺序无关断言)。

    若结果 ``tokens`` 为 ``None`` 直接失败, 让测试用例看到清晰错误。
    """

    assert result.tokens is not None
    return [t.type for t in result.tokens]


def tokens_of_type(result: HighlightBlock, type_: str) -> list[HighlightToken]:
    """按 ``type_`` 过滤 token 列表。"""

    assert result.tokens is not None
    return [t for t in result.tokens if t.type == type_]


def snippet(token: HighlightToken, code: str) -> str:
    """取 token 区间对应的源码切片。"""

    return code[token.start : token.end]