# `modules/Uui/widgets/frame.py`

源文件路径：`modules/Uui/widgets/frame.py`

主题感知 `tk.Frame`。

## 类

### `UFrame(tk.Frame)`
构造 `__init__(parent, variant='panel', bg_key=None, **kwargs)`：
- `variant`：预设背景（`title` / `base` / `panel` / `raised` / `input`）。
- `bg_key`：可选主题颜色名（如 `'BG_HOVER'`），优先于 `variant`。
- 显式 `bg=...` 优先级最高。
- 默认 `highlightthickness=0`、`bd=0`。

方法：
- `_variant_bg(variant) -> str`：按 variant 查表返回对应颜色，未命中回退 `BG_PANEL`。
- `_apply_theme()`：按当前主题重新设置背景。