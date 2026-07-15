# `modules/Uui/widgets/theme.py`

源文件路径：`modules/Uui/widgets/theme.py`

Uui 的主题系统（颜色 + 字体 + 切换 + OS 主题跟随）。

## 类

### `Theme`（基类）
- 类属性：`name = 'Base'`。
- 颜色：`BG_TITLE` / `BG_BASE` / `BG_PANEL` / `BG_RAISED` / `BG_HOVER` / `BG_ACTIVE` / `BG_INPUT` / `BG_DROPDOWN`；`FG_PRIMARY` / `FG_SECONDARY` / `FG_TERTIARY` / `FG_DISABLED`；`BORDER` / `BORDER_STRONG` / `BORDER_FOCUS`；`RED` / `RED_HOVER` / `RED_DARK`；`YELLOW` / `YELLOW_HOVER` / `YELLOW_DARK`；`GREEN` / `GREEN_HOVER` / `GREEN_DARK`；`BLUE` / `BLUE_HOVER` / `BLUE_DARK`；`PURPLE`。
- 标题强调条：`TITLE_ACCENT_WIDTH = 3` / `TITLE_ACCENT`。
- 字体：`TITLE_FONT` / `MENU_FONT` / `LABEL_FONT` / `LABEL_FONT_BOLD` / `LABEL_FONT_SMALL` / `BUTTON_FONT` / `ICON_FONT` / `MONO_FONT`。

### `DarkTheme(Theme)` / `LightTheme(Theme)` / `SolarizedDarkTheme(Theme)`
具体主题。`LightTheme` 把背景整体改为浅色、文字深色；`SolarizedDarkTheme` 使用 Solarized Dark 调色板。

## 模块状态

- `_themes: List[Theme]` — 当前已注册主题列表（默认 `[Dark, Light, SolarizedDark]`）。
- `_current: Theme` — 当前主题（默认 Dark）。
- `_listeners: List[Callable[[Theme], None]]` — 主题变更监听器。

## 函数

- `available() -> List[Theme]`：返回主题副本。
- `by_name(name) -> Optional[Theme]`：按名字查找主题。
- `current() -> Theme`：返回当前主题。
- `on_change(cb) / off_change(cb)`：注册 / 注销变更监听。
- `set_theme(theme_obj, *, refresh_root=None)`：切换主题；可选对 `refresh_root`（Tk 根）递归调用 `apply_theme_recursive`；触发监听器。
- `apply_theme_recursive(widget)`：深度优先调用所有带 `_apply_theme` 的子控件。
- `follow_system(root=None, *, mapping=None, poll_interval_ms=1500) -> bool`：启动 OS 主题轮询；`mapping` 形如 `{'dark': 'Dark', 'light': 'Light'}`；返回是否立刻应用。
- `stop_following()`：取消轮询。
- `_read_os_theme() -> Optional[str]`：通过 Windows 注册表或 macOS `defaults` 探测 `'dark'` / `'light'`。
- `_resolve_target_name(os_theme)`：从 `_follow_mapping` / `_DEFAULT_FOLLOW_SYSTEM_THEME` 解析目标主题名。
- `_schedule_poll(root, interval_ms)` / `_poll(root, interval_ms)`：内部轮询。

## 模块常量

- `FOLLOW_SYSTEM_THEME: dict` — 默认 OS → 主题映射（`'dark'`/`'light'`/`'default'` → `'Dark'`/`'Light'`/`'Dark'`）。
- `_DEFAULT_FOLLOW_SYSTEM_THEME = dict(FOLLOW_SYSTEM_THEME)`。

## `__getattr__(name)`
通过 `getattr(_current, name)` 实现 `theme.BG_BASE` 这类访问；`_` 开头属性仍按常规抛 `AttributeError`。