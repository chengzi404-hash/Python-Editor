"""ANSI SGR (Select Graphic Rendition) escape sequence parser for terminals.

This module turns a stream of bytes containing ANSI colour codes into a
list of ``(style, text)`` segments where ``style`` carries foreground,
background, and attribute flags. ``UTerminal`` consumes these segments
to render coloured output.

Coverage:
* SGR ``\\x1b[...m`` sequences — the only ones worth supporting for a
  shell terminal. CSI cursor / clear sequences are passed through (text
  preserved, sequences dropped) so other tools that emit them (e.g.
  progress bars) don't completely break the display.
* 8 standard colours, 8 bright colours (16-colour palette).
* 256-colour ``\\x1b[38;5;N m`` foreground and ``\\x1b[48;5;N m``
  background.
* 24-bit truecolour ``\\x1b[38;2;R;G;B m`` and ``\\x1b[48;2;R;G;B m``.
* Bold / dim / italic / underline attributes (italic has wide font support
  variance — included for completeness).
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from dataclasses import dataclass
from typing import NamedTuple

# --------------------------------------------------------------------------
# Style + parser
# --------------------------------------------------------------------------


@dataclass
class AnsiStyle:
    """Mutable accumulator for SGR state."""

    fg: str | None = None
    bg: str | None = None
    bold: bool = False
    dim: bool = False
    italic: bool = False
    underline: bool = False
    inverse: bool = False

    def copy(self) -> AnsiStyle:
        return AnsiStyle(
            fg=self.fg,
            bg=self.bg,
            bold=self.bold,
            dim=self.dim,
            italic=self.italic,
            underline=self.underline,
            inverse=self.inverse,
        )


# CSI sequences end with a final byte in the range ``@``..``~`` (0x40-0x7E).
# SGR sequences always end in ``m``; everything else (cursor moves, clears,
# etc.) gets dropped. We keep the two patterns separate for readability
# rather than splitting on the final byte in a single regex.
_ANSI_SGR_RE = re.compile(r"\x1b\[([\d;?]*)m")
# Final byte class excludes ``M``/``m`` so we never accidentally strip SGR
# sequences along with the cursor/clear ones.
_ANSI_OTHER_CSI_RE = re.compile(r"\x1b\[[\d;?]*[ -/]*[A-LN-Za-ln-z]")

# Standard 16-colour palette, tuned for dark backgrounds. Light variants
# pull from theme tokens where they exist; everything else is a fixed
# palette that mirrors what real terminals use.
_STD_PALETTE: dict[int, str] = {
    0: "#000000",  # black
    1: "#ff5f57",  # red
    2: "#28c840",  # green
    3: "#febc2e",  # yellow
    4: "#0a84ff",  # blue
    5: "#bf5af2",  # magenta
    6: "#5ac8fa",  # cyan
    7: "#d4d4d4",  # white (light gray on dark bg)
    8: "#505050",  # bright black (dark gray)
    9: "#ff7f77",  # bright red
    10: "#4ae060",  # bright green
    11: "#ffcc4e",  # bright yellow
    12: "#3a9eff",  # bright blue
    13: "#d28aff",  # bright magenta
    14: "#7ee0ff",  # bright cyan
    15: "#ffffff",  # bright white
}


def _xterm256_to_rgb(idx: int) -> str:
    """Convert an 8-bit xterm colour index to a ``#rrggbb`` string."""
    if idx in _STD_PALETTE:
        return _STD_PALETTE[idx]
    if 16 <= idx <= 231:
        # 6 x 6 x 6 cube
        idx -= 16
        r = idx // 36
        g = (idx // 6) % 6
        b = idx % 6
        levels = [0, 95, 135, 175, 215, 255]
        return f"#{levels[r]:02x}{levels[g]:02x}{levels[b]:02x}"
    if 232 <= idx <= 255:
        level = 8 + (idx - 232) * 10
        return f"#{level:02x}{level:02x}{level:02x}"
    return "#d4d4d4"


def _apply_sgr(style: AnsiStyle, params: list[int]) -> None:
    """Mutate ``style`` by applying a single SGR parameter list (``m`` body)."""

    if not params:
        params = [0]
    i = 0
    while i < len(params):
        p = params[i]
        if p == 0:
            style.fg = None
            style.bg = None
            style.bold = False
            style.dim = False
            style.italic = False
            style.underline = False
            style.inverse = False
        elif p == 1:
            style.bold = True
        elif p == 2:
            style.dim = True
        elif p == 3:
            style.italic = True
        elif p == 4:
            style.underline = True
        elif p == 7:
            style.inverse = True
        elif p == 22:
            style.bold = False
            style.dim = False
        elif p == 23:
            style.italic = False
        elif p == 24:
            style.underline = False
        elif p == 27:
            style.inverse = False
        elif 30 <= p <= 37:
            style.fg = _STD_PALETTE[p - 30]
        elif p == 38:
            # Extended foreground: 38;5;N  (256 colour) or 38;2;R;G;B (truecolour)
            if i + 1 < len(params):
                if params[i + 1] == 5 and i + 2 < len(params):
                    style.fg = _xterm256_to_rgb(params[i + 2])
                    i += 2
                elif params[i + 1] == 2 and i + 4 < len(params):
                    r, g, b = params[i + 2], params[i + 3], params[i + 4]
                    style.fg = f"#{r & 0xFF:02x}{g & 0xFF:02x}{b & 0xFF:02x}"
                    i += 4
        elif p == 39:
            style.fg = None
        elif 40 <= p <= 47:
            style.bg = _STD_PALETTE[p - 40]
        elif p == 48:
            if i + 1 < len(params):
                if params[i + 1] == 5 and i + 2 < len(params):
                    style.bg = _xterm256_to_rgb(params[i + 2])
                    i += 2
                elif params[i + 1] == 2 and i + 4 < len(params):
                    r, g, b = params[i + 2], params[i + 3], params[i + 4]
                    style.bg = f"#{r & 0xFF:02x}{g & 0xFF:02x}{b & 0xFF:02x}"
                    i += 4
        elif p == 49:
            style.bg = None
        elif 90 <= p <= 97:
            style.fg = _STD_PALETTE[p - 90 + 8]
        elif 100 <= p <= 107:
            style.bg = _STD_PALETTE[p - 100 + 8]
        i += 1


class AnsiSegment(NamedTuple):
    """A piece of text with a snapshot of SGR style at that point."""

    style: AnsiStyle
    text: str


def _blank_style() -> AnsiStyle:
    return AnsiStyle()


def parse_ansi(text: str) -> list[AnsiSegment]:
    """Split ``text`` into ``AnsiSegment`` records, dropping CSI sequences.

    Cursor / clear / scroll CSI sequences (anything ending in a non-``m``
    final byte) are stripped entirely. SGR (``m``-terminated) sequences
    update the running style before the next text run begins.
    """

    style = _blank_style()
    out: list[AnsiSegment] = []

    # Strip non-SGR CSI sequences first (cursor moves, clears, etc.).
    text = _ANSI_OTHER_CSI_RE.sub("", text)

    pos = 0
    for match in _ANSI_SGR_RE.finditer(text):
        if match.start() > pos:
            chunk = text[pos : match.start()]
            out.append(AnsiSegment(style=style.copy(), text=chunk))
        param_str = match.group(1)
        try:
            params = [int(x) if x else 0 for x in param_str.split(";")] if param_str else [0]
        except ValueError:
            params = [0]
        _apply_sgr(style, params)
        pos = match.end()
    if pos < len(text):
        out.append(AnsiSegment(style=style.copy(), text=text[pos:]))
    return out


def style_key(style: AnsiStyle) -> str:
    """Return a stable hashable key so Tk tags can be shared per style."""

    return "|".join(
        [
            f"fg={style.fg or ''}",
            f"bg={style.bg or ''}",
            f"b={int(style.bold)}",
            f"d={int(style.dim)}",
            f"i={int(style.italic)}",
            f"u={int(style.underline)}",
            f"v={int(style.inverse)}",
        ]
    )


def iter_styled_chars(text: str) -> Iterator[tuple[AnsiStyle, str]]:
    """Flatten parse_ansi() into per-character (style, char) tuples.

    Useful for terminals that want to apply styling character-by-character
    (e.g. when supporting text selection / clipboard). Most UIs prefer the
    coarser segment list.
    """

    for seg in parse_ansi(text):
        for ch in seg.text:
            yield seg.style, ch


# --------------------------------------------------------------------------
# Convenience: render a sequence of segments by joining the raw text back.
# Useful for tests.
# --------------------------------------------------------------------------


def strip_ansi(text: str) -> str:
    """Return ``text`` with every ANSI CSI sequence removed."""

    return _ANSI_SGR_RE.sub("", _ANSI_OTHER_CSI_RE.sub("", text))
