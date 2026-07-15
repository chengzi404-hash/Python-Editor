# `modules/Uui/widgets/label.py`

源文件路径：`modules/Uui/widgets/label.py`

主题感知 `tk.Label`。

## 类

### `ULabel(tk.Label)`
构造 `__init__(parent, text='', variant='primary', font=None, bg=None, **kwargs)`：
- `variant` 决定 `fg`，可用值：`primary` / `secondary` / `tertiary` / `disabled` / `blue` / `red` / `green` / `yellow`（其它回退 `FG_PRIMARY`）。
- `bg=None` 时从父控件的 `cget('bg')` 取（若失败回退 `BG_BASE`）。

属性 / 方法：
- `_VARIANT_FG_KEYS`：variant → 主题颜色键映射。
- `_variant_fg(variant) -> str`：返回对应 `fg`。
- `_parent_bg(parent) -> str`：父控件背景色探测。
- `_apply_theme()`：刷新 `fg`。