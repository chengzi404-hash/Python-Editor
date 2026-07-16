"""``core.editor`` — 编辑器核心模块。

提供文档模型、语言配置、UI 常量等基础数据结构。
"""

from .document import Document, _Debouncer
from .lang_config import (
    FONT_FAMILIES,
    FONT_SIZES,
    HIGHLIGHT_TOKENS,
    LANG_CONFIG,
    TAB_WIDTHS,
    THEME_NAMES,
)

__all__ = [
    "FONT_FAMILIES",
    "FONT_SIZES",
    "HIGHLIGHT_TOKENS",
    "LANG_CONFIG",
    "TAB_WIDTHS",
    "THEME_NAMES",
    "Document",
    "_Debouncer",
]
