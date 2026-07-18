"""``core.editor`` — Editor core module.

Provides document model, language configuration, UI constants and other basic data structures.
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
