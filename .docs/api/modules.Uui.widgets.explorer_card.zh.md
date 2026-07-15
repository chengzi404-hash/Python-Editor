# `modules/Uui/widgets/explorer_card.py`

源文件路径：`modules/Uui/widgets/explorer_card.py`

Explorer 侧边栏卡片（标题头 + `UFileTree`）。

## 类

### `ExplorerCard(UFrame)`
构造 `__init__(parent, *, title='EXPLORER', on_activate=None, **kwargs)`：
- `title`：标题头文本。
- `on_activate(abs_path) -> None`：文件双击回调。
- 默认 `variant='panel'`。

方法：
- `set_root(path) -> None`：转给内部 `UFileTree`。
- `refresh() -> None`
- `set_on_activate(callback)`：运行时改回调。
- `set_title(title) -> None`
- `selected_path() -> Optional[str]`
- `_apply_theme()`：主题刷新。