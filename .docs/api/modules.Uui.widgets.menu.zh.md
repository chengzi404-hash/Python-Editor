# `modules/Uui/widgets/menu.py`

源文件路径：`modules/Uui/widgets/menu.py`

主题感知菜单栏与下拉菜单。

## 类

### `UMenu`
数据模型：菜单项列表。

构造 `__init__()`：内部维护 `_items: List[Tuple]`。

方法：
- `add_command(label, command=None, shortcut='') -> None`
- `add_separator() -> None`
- `add_checkbutton(label, variable=None, command=None, shortcut='') -> None`
- `add_radiobutton(label, value, variable=None, command=None, shortcut='') -> None`
- `add_cascade(label) -> UMenu`：添加子菜单并返回该子菜单。

### `UMenuBar`
构造 `UMenuBar(parent)`：在顶部构建 `_menu_frame`（`BG_TITLE` 背景），通过 `add_cascade(label)` 返回可填充的 `UMenu`。

#### 内部实现（节选）
- `_MenuItemRow`：单行菜单项（24px 高），分隔符 9px 高。
- `_MenuDropdown`：下拉浮层容器；`_open_submenu(row, submenu)` 弹出子菜单。
- 主题切换由 `apply_theme_recursive` 触发 `_apply_theme`。

每个 `UMenuBar` 内部把 `UMenu` 渲染为下拉浮层，与 Tk 菜单系统解耦。