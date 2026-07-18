"""Suggestion icon system - loads SVG icons for suggestion kinds from vscode-icons."""

from __future__ import annotations

import io
import tkinter as tk
from pathlib import Path

try:
    import cairosvg  # type: ignore[import]

    HAS_CAIRO = True
except (ImportError, OSError):
    HAS_CAIRO = False

try:
    from reportlab.graphics import renderPM
    from svglib.svglib import svg2rlg

    HAS_SVGLIB = True
except ImportError:
    HAS_SVGLIB = False


VSCODE_ICONS_DIR = Path(__file__).parent.parent.parent / "data" / "vscode-icons" / "icons"
ICON_SIZE = 18

_ICON_KINDS: dict[str, str] = {
    "keyword": "symbol-keyword",
    "builtin": "symbol-namespace",
    "function": "symbol-method",
    "class": "symbol-class",
    "variable": "symbol-variable",
    "attribute": "symbol-property",
    "module": "folder",
    "method": "symbol-method",
}

_SVG_CACHE: dict[str, tk.PhotoImage] = {}
_ICON_ROOT: tk.Tk | None = None


def _get_icon_root() -> tk.Tk:
    """Get or create a hidden Tk instance for icon generation."""
    global _ICON_ROOT
    if _ICON_ROOT is None:
        _ICON_ROOT = tk.Tk()
        _ICON_ROOT.withdraw()
    return _ICON_ROOT


def _get_icon_variant() -> str:
    """Get the current icon variant based on theme (dark or light)."""
    try:
        from . import theme

        theme_name = theme.current().name.lower()
        if "dark" in theme_name or theme_name == "default":
            return "dark"
        return "light"
    except Exception:
        return "dark"


def _make_background_transparent(img):
    """Make pure white background transparent in an RGBA image."""
    from PIL import Image

    if img.mode != "RGBA":
        img = img.convert("RGBA")
    mask = Image.new("L", img.size, 255)
    for y in range(img.height):
        for x in range(img.width):
            pixel = img.getpixel((x, y))
            if pixel[0] == 255 and pixel[1] == 255 and pixel[2] == 255:
                mask.putpixel((x, y), 0)
    img.putalpha(mask)
    return img


def _create_icon_image(kind: str, variant: str) -> tk.PhotoImage:
    """Create a PhotoImage for the given kind using vscode-icons."""

    icon_name = _ICON_KINDS.get(kind, "symbol-misc")
    cache_key = f"{kind}:{icon_name}:{variant}"
    if cache_key in _SVG_CACHE:
        return _SVG_CACHE[cache_key]

    icon: tk.PhotoImage | None = None
    svg_path = VSCODE_ICONS_DIR / variant / f"{icon_name}.svg"

    if HAS_CAIRO and svg_path.exists():
        try:
            svg_content = svg_path.read_text(encoding="utf-8")
            png_data = cairosvg.svg2png(
                bytestring=svg_content.encode("utf-8"),
                output_width=ICON_SIZE,
                output_height=ICON_SIZE,
            )
            icon = tk.PhotoImage(data=png_data)
        except Exception:
            pass

    if icon is None and HAS_SVGLIB and svg_path.exists():
        try:
            drawing = svg2rlg(svg_path)
            if drawing:
                png_data = renderPM.drawToString(drawing, fmt="PNG")
                from PIL import Image, ImageTk

                img = Image.open(io.BytesIO(png_data))
                if img.mode not in ("RGBA", "LA"):
                    img = img.convert("RGBA")
                img = _make_background_transparent(img)
                img = img.resize((ICON_SIZE, ICON_SIZE), Image.LANCZOS)
                icon = ImageTk.PhotoImage(img)
        except Exception:
            pass

    if icon is None:
        try:
            from PIL import Image, ImageDraw, ImageTk

            img = Image.new("RGBA", (ICON_SIZE, ICON_SIZE), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            draw.rectangle([0, 0, ICON_SIZE - 1, ICON_SIZE - 1], fill="#808080")
            icon = ImageTk.PhotoImage(img)
        except Exception:
            _get_icon_root()
            icon = tk.PhotoImage(width=ICON_SIZE, height=ICON_SIZE)

    _SVG_CACHE[cache_key] = icon  # type: ignore[arg-type]
    return icon  # type: ignore[return-value]


class SuggestionIconRenderer:
    """Renders suggestion kind icons for use in UI."""

    def __init__(self) -> None:
        self._icons: dict[str, tk.PhotoImage] = {}

    def get_icon(self, kind: str) -> tk.PhotoImage | None:
        """Get the icon PhotoImage for a suggestion kind."""
        if not kind:
            return None

        variant = _get_icon_variant()
        cache_key = f"{kind}:{variant}"

        if cache_key in self._icons:
            return self._icons[cache_key]

        icon = _create_icon_image(kind, variant)
        self._icons[cache_key] = icon
        return icon

    def clear_cache(self) -> None:
        """Clear the icon cache."""
        self._icons.clear()
        _SVG_CACHE.clear()


_icon_renderer: SuggestionIconRenderer | None = None


def get_icon_renderer() -> SuggestionIconRenderer:
    """Get the global SuggestionIconRenderer instance."""
    global _icon_renderer
    if _icon_renderer is None:
        _icon_renderer = SuggestionIconRenderer()
    return _icon_renderer


__all__ = ["ICON_SIZE", "SuggestionIconRenderer", "get_icon_renderer"]
