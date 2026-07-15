import contextlib
import sys
from collections.abc import Callable


class Theme:
    name: str = 'Base'

    BG_TITLE: str = '#000000'
    BG_BASE: str = '#1e1e1e'
    BG_PANEL: str = '#2a2a2a'
    BG_RAISED: str = '#3a3a3a'
    BG_HOVER: str = '#4a4a4a'
    BG_ACTIVE: str = '#5a5a5a'
    BG_INPUT: str = '#161616'
    BG_DROPDOWN: str = '#2a2a2a'

    FG_PRIMARY: str = '#ffffff'
    FG_SECONDARY: str = '#a0a0a0'
    FG_TERTIARY: str = '#707070'
    FG_DISABLED: str = '#505050'

    BORDER: str = '#3a3a3a'
    BORDER_STRONG: str = '#5a5a5a'
    BORDER_FOCUS: str = '#0a84ff'

    RED: str = '#ff5f57'
    RED_HOVER: str = '#ff7f77'
    RED_DARK: str = '#d94540'

    YELLOW: str = '#febc2e'
    YELLOW_HOVER: str = '#ffcc4e'
    YELLOW_DARK: str = '#cf9a10'

    GREEN: str = '#28c840'
    GREEN_HOVER: str = '#4ae060'
    GREEN_DARK: str = '#1caa30'

    BLUE: str = '#0a84ff'
    BLUE_HOVER: str = '#3a9eff'
    BLUE_DARK: str = '#0066cc'

    PURPLE: str = '#bf5af2'

    # 卡片标题栏左侧 accent 条(蓝色宽度 3px)
    TITLE_ACCENT_WIDTH: int = 3
    TITLE_ACCENT: str = '#0a84ff'

    TITLE_FONT: tuple = ('Comic Sans MS', 10)
    MENU_FONT: tuple = ('Arial', 10)
    LABEL_FONT: tuple = ('Arial', 10)
    LABEL_FONT_BOLD: tuple = ('Arial', 10, 'bold')
    LABEL_FONT_SMALL: tuple = ('Arial', 9)
    BUTTON_FONT: tuple = ('Arial', 10)
    ICON_FONT: tuple = ('Arial Black', 9)
    MONO_FONT: tuple = ('Consolas', 10)


class DarkTheme(Theme):
    name = 'Dark'


class LightTheme(Theme):
    name = 'Light'
    BG_TITLE = '#e8e8e8'
    BG_BASE = '#fafafa'
    BG_PANEL = '#f0f0f0'
    BG_RAISED = '#e0e0e0'
    BG_HOVER = '#d8d8d8'
    BG_ACTIVE = '#c0c0c0'
    BG_INPUT = '#ffffff'
    BG_DROPDOWN = '#ffffff'

    FG_PRIMARY = '#1a1a1a'
    FG_SECONDARY = '#555555'
    FG_TERTIARY = '#888888'
    FG_DISABLED = '#b0b0b0'

    BORDER = '#d0d0d0'
    BORDER_STRONG = '#a8a8a8'
    BORDER_FOCUS = '#0066cc'

    RED = '#dc3545'
    RED_HOVER = '#e85565'
    RED_DARK = '#a02a37'

    YELLOW = '#d99700'
    YELLOW_HOVER = '#e9a710'
    YELLOW_DARK = '#a07000'

    GREEN = '#2da745'
    GREEN_HOVER = '#4dc765'
    GREEN_DARK = '#1e8a37'

    BLUE = '#0066cc'
    BLUE_HOVER = '#1a80e0'
    BLUE_DARK = '#004a99'

    # 与本主题 BLUE 同色
    TITLE_ACCENT = '#0066cc'

class SolarizedDarkTheme(Theme):
    name = 'Solarized Dark'
    BG_TITLE = '#002b36'
    BG_BASE = '#002b36'
    BG_PANEL = '#073642'
    BG_RAISED = '#0a4452'
    BG_HOVER = '#0d5263'
    BG_ACTIVE = '#106274'
    BG_INPUT = '#01313d'
    BG_DROPDOWN = '#073642'

    FG_PRIMARY = '#fdf6e3'
    FG_SECONDARY = '#93a1a1'
    FG_TERTIARY = '#657b83'
    FG_DISABLED = '#586e75'

    BORDER = '#0a4452'
    BORDER_STRONG = '#0d5263'
    BORDER_FOCUS = '#268bd2'

    RED = '#dc322f'
    RED_HOVER = '#ec4240'
    RED_DARK = '#a8221f'

    YELLOW = '#b58900'
    YELLOW_HOVER = '#c59910'
    YELLOW_DARK = '#8a6900'

    GREEN = '#859900'
    GREEN_HOVER = '#95a910'
    GREEN_DARK = '#657900'

    BLUE = '#268bd2'
    BLUE_HOVER = '#369be2'
    BLUE_DARK = '#066ba2'

    # 与本主题 BLUE 同色
    TITLE_ACCENT = '#268bd2'


_themes: list[Theme] = [DarkTheme(), LightTheme(), SolarizedDarkTheme()]
_current: Theme = _themes[0]
_listeners: list[Callable[[Theme], None]] = []


def available() -> list[Theme]:
    return list(_themes)


def by_name(name: str) -> Theme | None:
    for t in _themes:
        if t.name == name:
            return t
    return None


def current() -> Theme:
    return _current


def on_change(callback: Callable[[Theme], None]) -> None:
    _listeners.append(callback)


def off_change(callback: Callable[[Theme], None]) -> None:
    with contextlib.suppress(ValueError):
        _listeners.remove(callback)


def set_theme(theme_obj: Theme, *, refresh_root=None) -> None:
    global _current
    if _current is theme_obj:
        return
    _current = theme_obj
    if refresh_root is not None:
        apply_theme_recursive(refresh_root)
    for cb in list(_listeners):
        with contextlib.suppress(Exception):
            cb(theme_obj)


def apply_theme_recursive(widget) -> None:
    """Walk the widget tree and call _apply_theme() on every themed widget."""
    apply_fn = getattr(widget, '_apply_theme', None)
    if apply_fn is not None:
        with contextlib.suppress(Exception):
            apply_fn()
    try:
        children = widget.winfo_children()
    except Exception:
        children = []
    for child in children:
        apply_theme_recursive(child)


def __getattr__(name: str):
    if name.startswith('_'):
        raise AttributeError(name)
    try:
        return getattr(_current, name)
    except AttributeError:
        raise AttributeError(f"theme has no attribute {name!r}")


FOLLOW_SYSTEM_THEME: dict = {
    'dark': 'Dark',
    'light': 'Light',
    'default': 'Dark',
}

_DEFAULT_FOLLOW_SYSTEM_THEME: dict = dict(FOLLOW_SYSTEM_THEME)

_follow_root = None
_follow_after_id = None
_follow_enabled = False
_follow_mapping: dict | None = None


def _read_os_theme() -> str | None:
    """Return 'dark', 'light', or None if not detectable."""
    if not sys.platform.startswith('win'):
        try:
            from subprocess import run
            r = run(['defaults', 'read', '-g', 'AppleInterfaceStyle'],
                    capture_output=True, text=True, timeout=2)
            if r.returncode == 0 and r.stdout.strip().lower() == 'dark':
                return 'dark'
            if r.returncode == 0:
                return 'light'
        except Exception:
            pass
        return None
    try:
        import winreg
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r'Software\Microsoft\Windows\CurrentVersion\Themes\Personalize',
        ) as key:
            value, _ = winreg.QueryValueEx(key, 'AppsUseLightTheme')
            return 'light' if value == 1 else 'dark'
    except Exception:
        return None


def _resolve_target_name(os_theme: str) -> str | None:
    mapping = _follow_mapping if _follow_mapping is not None else _DEFAULT_FOLLOW_SYSTEM_THEME
    return mapping.get(os_theme) or mapping.get('default')


def follow_system(root=None, *, mapping: dict | None = None,
                  poll_interval_ms: int = 1500) -> bool:
    """Start following the OS appearance. Pass the Tk root for live polling.

    Returns True if the OS theme was applied immediately, False otherwise.
    """
    global _follow_root, _follow_after_id, _follow_enabled, _follow_mapping

    if mapping is not None:
        merged = dict(_DEFAULT_FOLLOW_SYSTEM_THEME)
        merged.update(mapping)
        _follow_mapping = merged
    elif _follow_mapping is None:
        _follow_mapping = dict(_DEFAULT_FOLLOW_SYSTEM_THEME)

    applied = False
    os_theme = _read_os_theme()
    if os_theme is not None:
        target_name = _resolve_target_name(os_theme)
        if target_name:
            target = by_name(target_name)
            if target is not None and target is not _current:
                set_theme(target)
                applied = True
                if root is not None:
                    apply_theme_recursive(root)

    _follow_enabled = True
    _follow_root = root

    if root is not None:
        _schedule_poll(root, poll_interval_ms)
    return applied


def _schedule_poll(root, interval_ms: int) -> None:
    global _follow_after_id
    if not _follow_enabled or root is None:
        return
    with contextlib.suppress(Exception):
        _follow_after_id = root.after(interval_ms, _poll, root, interval_ms)


def _poll(root, interval_ms: int) -> None:
    global _follow_after_id, _follow_enabled
    if not _follow_enabled:
        return
    os_theme = _read_os_theme()
    if os_theme is not None:
        target_name = _resolve_target_name(os_theme)
        if target_name:
            target = by_name(target_name)
            if target is not None and target is not _current:
                set_theme(target)
                apply_theme_recursive(root)
    _schedule_poll(root, interval_ms)


def stop_following() -> None:
    global _follow_enabled, _follow_root, _follow_after_id, _follow_mapping
    _follow_enabled = False
    if _follow_root is not None and _follow_after_id is not None:
        with contextlib.suppress(Exception):
            _follow_root.after_cancel(_follow_after_id)
    _follow_root = None
    _follow_after_id = None
    _follow_mapping = None
