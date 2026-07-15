# `modules/Uui/widgets/file_tree.py`

源文件路径：`modules/Uui/widgets/file_tree.py`

VS Code 风格的文件树组件。基于 `TreeCanvas` 渲染层，自身维护 `iid → 绝对路径` 的映射并懒加载子目录。

## 模块常量

- `_DEFAULT_IGNORE_DIRS = frozenset({'__pycache__', '.git', '.venv', 'venv', 'node_modules', '.idea', '.vscode', 'build', 'dist', '.mypy_cache', '.pytest_cache'})`
- `_IID_PREFIX = 'FILE:'`

## 内部辅助

### `_path_to_iid(path) -> str`
返回 `FILE:<abs_path>`。

### `_iid_to_path(iid) -> Optional[str]`
逆解析；不以 `FILE:` 前缀开头时返回 `None`。

## 类

### `UFileTree(UFrame)`
构造 `__init__(parent, ...)`：
- 标题头 + `TreeCanvas` + `UScrollBar`。
- 维护 `iid → abs path` 映射；首层立即展开，深层懒加载（`<<TreeviewOpen>>`/toggle 时 `scandir`）。

公开 API：
- `set_root(path) -> None`：切换项目根目录并 `refresh()`。
- `refresh() -> None`：重新扫描根目录。
- `set_on_activate(callback)`：`callback(abs_path)`，文件双击触发。
- `set_title(title) -> None`：修改标题头文本。
- `selected_path() -> Optional[str]`：当前选中节点的绝对路径。
- `_apply_theme()`：主题刷新（由 `apply_theme_recursive` 触发）。

行为细节：
- 双击目录 → 折叠/展开（与点击三角等价）。
- 双击文件 → 调用 `on_activate(path)`。