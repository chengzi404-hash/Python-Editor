# `modules/Uui/widgets/scrollbar.py`

源文件路径：`modules/Uui/widgets/scrollbar.py`

主题感知滚动条（自绘 Canvas，跨平台）。

## 类

### `UScrollBar(tk.Frame)`
`tk.Frame` 内嵌 `tk.Canvas` 自绘。提供与 `tk.Scrollbar` 一致的接口。

类属性：
- `_theme_key_bg = 'BG_PANEL'` — 滑块颜色键。
- `_theme_key_trough = 'BG_INPUT'` — 滑道颜色键。
- `_theme_key_active = 'BG_HOVER'` — hover/拖动颜色键。
- `_MIN_SLIDER_PX = 20` — 滑块最小像素。

构造 `__init__(parent, *, bg='', autohidden=False, command=None, orient='vertical', troughcolor='', activebackground='', width=None, **kwargs)`：
- `bg=''` 时取 `theme._theme_key_bg`；显式非空则锁定为给定颜色。
- `troughcolor=''` 时取 `theme._theme_key_trough`。
- `activebackground=''` 时取 `theme._theme_key_active`。
- `autohidden=True`：当 `set(0.0, 1.0)` 时自动 `pack_forget`，非满区间时用缓存的 `pack_info()` 还原。
- 支持鼠标拖拽滑块、点击滑道 page scroll、滚轮 unit scroll。
- `command('moveto', first)` 等兼容 `tk.Scrollbar` 用法。

方法（节选）：
- `set(first, last)`：更新滑块位置与可见性。
- `_draw()`：按当前 `first` / `last` 在 canvas 上画滑道与滑块。
- `_on_press/_on_drag/_on_release`：滑块拖拽。
- `_on_trough_click(event)`：点击滑道 → page 滚动。
- `_on_mouse_wheel(event)`：滚轮 → unit 滚动（绑定 `bind_all`）。
- `_apply_theme()`：主题刷新。