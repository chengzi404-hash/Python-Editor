# `modules/highlighter/themes.py`

源文件路径：`modules/highlighter/themes.py`

高亮主题注册表与切换 API。

## 数据类

### `HighlightTheme`（`@dataclass`）
- `name: str` — 内部唯一键。
- `label: str = ''` — UI 显示名。
- `tokens: Dict[str, Dict[str, Any]] = {}` — token 类型 → 样式属性（如 `{'foreground': '#...', 'background': ..., 'font': ...}`）。
- `description: str = ''`

## 模块私有 token 工厂

- `_default_dark_tokens() -> Dict[str, Dict[str, Any]]`：VS Code Dark+ 风格。
- `_default_light_tokens() -> Dict[str, Dict[str, Any]]`：VS Code Light+ 风格。
- `_solarized_dark_tokens() -> Dict[str, Dict[str, Any]]`：Solarized Dark 风格。

> 三个工厂覆盖的 token 类型：`keyword` / `builtin` / `string` / `number` / `comment` / `identifier` / `operator` / `punctuation` / `function` / `class` / `struct` / `preprocessor` / `decorator` / `self` / `type` / `module` / `key` / `tag` / `timestamp` / `level_debug` / `level_info` / `level_warn` / `level_error` / `level_critical`。

## 模块状态

- `_themes: Dict[str, HighlightTheme]` — 主题注册表。
- `_current_name: str = 'Default Dark'` — 当前主题键。
- `_listeners: List[Callable[[str], None]]` — 主题变更监听器。

## 公开 API

- `register(theme: HighlightTheme) -> None`：按 `theme.name` 注册（覆盖已有）。
- `unregister(name: str) -> None`：从注册表移除。
- `get(name: str) -> Optional[HighlightTheme]`。
- `available() -> List[HighlightTheme]` — 当前所有主题。
- `available_names() -> List[str]`。
- `current_name() -> str`。
- `current() -> HighlightTheme` — 当前主题；若 `_current_name` 不在表中则退回到表中第一个，否则返回空的 `HighlightTheme(name='Default Dark', tokens={})`。
- `tokens(name: Optional[str] = None) -> Dict[str, Dict[str, Any]]` — 获取指定/当前主题的 tokens 字典。
- `set_theme(name: str) -> None` — 仅当主题存在且与当前不同时切换，并按注册顺序通知所有监听器（监听器异常被忽略）。
- `on_change(callback: Callable[[str], None]) -> None` — 注册监听器。
- `off_change(callback)` — 注销监听器，未找到时忽略。

## 启动时内置

模块导入时自动注册三个主题：`Default Dark`、`Default Light`、`Solarized Dark`。

## `__all__`

```python
[
    'HighlightTheme',
    'register', 'unregister', 'get', 'available', 'available_names',
    'current', 'current_name', 'tokens',
    'set_theme', 'on_change', 'off_change',
]
```