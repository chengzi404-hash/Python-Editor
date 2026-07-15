# `modules/Uui/widgets/git_card.py`

源文件路径：`modules/Uui/widgets/git_card.py`

Git 源代码管理卡片：当前分支（含 ahead/behind 远程跟踪）、变更文件、内联提交编辑器，Commit / Push / Pull / Refresh。

## 模块常量

- `_TITLE_HEIGHT = 28` / `_COMPOSER_HEIGHT = 3` / `_STATUS_HEIGHT = 22` / `_SECTION_HEADER_HEIGHT = 26` / `_PANEL_PADDING_X = 10`

## 类

### `GitCard(UFrame)`
构造 `__init__(parent, *, title='SOURCE CONTROL', **kwargs)`：
- 顶部：当前分支 + ahead/behind 标签 + 操作按钮。
- 中部：Staged Changes / Changes 列表（用 `UListView`）。
- 底部：提交信息输入框 + Commit 按钮。
- 通过 `subprocess` 调用 `git` 命令（status / diff / add / commit / push / pull）。

公开 API：
- `set_workspace_root(path) -> None`：设置工作区根目录并 `refresh()`。
- `set_on_file_click(callback) -> None`：文件点击回调 `(filepath, status)`，status ∈ `'staged'` / `'unstaged'` / `'untracked'` 等。
- `refresh() -> None`：重新拉取 Git 状态。
- `get_branch() -> str` / `has_staged_changes() -> bool` / `get_staged_count() -> int` / `get_unstaged_count() -> int`：只读访问器。
- `commit(message)` / `push()` / `pull()`：便捷操作。
- `_apply_theme()`：主题刷新。