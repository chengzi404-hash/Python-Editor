# `modules/Uui/widgets/editor_suggestion.py`

源文件路径：`modules/Uui/widgets/editor_suggestion.py`

编辑器浮动补全框（基于 `tk.Toplevel` + 自绘行）。

## 数据类

### `CompletionItem`（`@dataclass`）
单条补全项。
- `label: str`
- `detail: str = ''`
- `description: str = ''`
- `insert: str = ''` — 插入文本，缺省等于 `label`（`__post_init__` 自动回填）。
- `kind: str = ''`
- `priority: int = 0`

## 类

### `UEditorSuggestion(tk.Toplevel)`
构造 `__init__(parent, items=(), on_select=None, *, max_visible=8, show_detail=True, show_description=True, grab_focus=False)`：
- 绑定到 `parent.winfo_toplevel()`，无系统装饰（`overrideredirect(True)`）。
- 类级 `_active: Optional[UEditorSuggestion]` 记录当前活动补全框，确保同时只有一个。

主要方法（节选）：
- `set_items(items)` / `set_position(x, y)`：替换候选项或移动浮层。
- `show() / hide()`：显示/隐藏并绑定/解绑 root `FocusOut`。
- `_select_index(idx)` / `_select_next() / _select_prev()`：上下选择。
- `_activate(item)`：回调 `on_select(item)` 并 `hide()`。
- 键盘绑定：上下方向键、Enter/Tab 接受、Esc 取消、字母数字滚动到匹配项。
- `_apply_theme()`：主题刷新（行/选中/footer 颜色）。