# `modules/Uui/widgets/line_number.py`

源文件路径：`modules/Uui/widgets/line_number.py`

基于 `tk.Canvas` 的代码行号栏，被 `UText(show_line_numbers=True)` 挂载。

## 协议

- 构造时拿到被观察的 `tk.Text`。
- 把 `redraw` 挂到 text 的 `yscrollcommand` 钩子上 → 滚动时重画。
- 监听 `<<Modified>>` 事件 → 清掉 modified flag 后触发重画。
- 监听 `<ButtonRelease-1>` / `<KeyRelease>` / `<Configure>` → 重新计算行高 / 当前行 / 可见区。

行号宽度按最大行号位数自动留白，"多加 1 位的策略" 防止 gutter 突然变宽把光标左右推动。

## 类

### `LineNumberCanvas(tk.Canvas)`
构造 `__init__(parent_text: tk.Text, **kwargs)`：
- 直接绑定到 `parent_text`（作为兄弟挂到 `tk.Frame` 容器）。

主要方法：
- `redraw() -> None`：重绘画布。
- `_on_text_configure(event)`：处理父 text 尺寸变化。
- `_on_modified(event)`：响应 `<<Modified>>`。
- `_on_release(event)` / `_on_keyrelease(event)`：更新当前行高亮。
- `_apply_theme()`：主题刷新。