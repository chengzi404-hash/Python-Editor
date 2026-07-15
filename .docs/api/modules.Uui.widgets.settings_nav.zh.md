# `modules/Uui/widgets/settings_nav.py`

源文件路径：`modules/Uui/widgets/settings_nav.py`

设置导航树。基于 `TreeCanvas`，把两个 `SettingsSchema` 拆成 `scope → group → leaf` 三层并喂给 `TreeCanvas`。

## 纯函数（不依赖 Tk，便于测试）

### `group_key(spec_key: str) -> str`
按 `key` 前缀自动归类：`editor.tab_size` → `editor`；无前缀 → `'_'`。

### `node_id(scope_value: str, group_key: Optional[str] = None, key: Optional[str] = None) -> str`
- `node_id('global')` → `'global'`（scope 根）
- `node_id('global', 'ui')` → `'global:ui'`（分组）
- `node_id('global', 'ui', 'ui.theme')` → `'global:ui:ui.theme'`（叶子）

### `parse_node_id(iid) -> (scope_value, group_key, key)`
逆向解析。

## 数据类

### `NavSelection`
当前选中节点的反查结果：
- `scope: SettingsScope`
- `group_key: Optional[str]`
- `keys: List[str]` — 叶子 keys（叶子节点）或空（分组节点 / scope 根）。

## 类

### `USettingsNavBar(UFrame)`
构造 `__init__(parent, *, title='Settings', on_select=None)`：
- 标题头 + `TreeCanvas`。

公开 API：
- `set_roots(global_schema, project_schema=None) -> None`：用两个 schema 重建整棵树；`project_schema=None` 时不显示"项目"分支。
- `set_selected(scope=None, group_key=None, key=None) -> None`：程序式跳到指定节点。
- `get_selected() -> Optional[NavSelection]`：当前选中的 `NavSelection`。
- `set_on_select(callback)`：回调签名 `(NavSelection) -> None`。
- `set_title(title) -> None`：修改标题文本。
- `_apply_theme()`：主题刷新。