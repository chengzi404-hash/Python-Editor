# `modules/Uui/widgets/tab_bar.py`

源文件路径：`modules/Uui/widgets/tab_bar.py`

多文件标签栏（基于 Canvas 自绘）。

## 数据类

### `Tab`（`@dataclass`）
- `id: str`
- `title: str`
- `dirty: bool = False`
- `closeable: bool = True`

## 类

### `TabBar(tk.Frame)`
构造 `__init__(parent, on_select, on_close, on_context_menu, **kwargs)`：
- `on_select(tab_id)` / `on_close(tab_id)` / `on_context_menu(tab_id, x, y)` 三个回调。
- 类常量：`TAB_HEIGHT=28` / `TAB_PADDING=14` / `CLOSE_SIZE=16` / `CLOSE_OFFSET=6` / `TAB_GAP=4`。

主要方法：
- `add_tab(tab_id, title, *, closeable=True) -> None`
- `remove_tab(tab_id) -> None`
- `set_active(tab_id) -> None`
- `set_title(tab_id, title) / set_dirty(tab_id, dirty) -> None`
- `clear() -> None`
- `set_on_select(cb)` / `set_on_close(cb)` / `set_on_context_menu(cb)`：运行时改回调。
- 内部 `tk.Canvas` 绘制标签按钮，支持活动高亮 / dirty `*` / 关闭按钮 / 右键上下文菜单 / 横向滚动。
- `_apply_theme()`：主题刷新。