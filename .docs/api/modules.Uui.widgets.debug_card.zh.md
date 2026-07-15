# `modules/Uui/widgets/debug_card.py`

源文件路径：`modules/Uui/widgets/debug_card.py`

调试侧边栏卡片：变量、调用栈、断点视图，以及调试控制（运行/暂停/单步等）。源文件 ~590 行。

## 数据类

### `DebugLocation`（`@dataclass`）
调试位置：`file` / `line` / `function`。

### `VariableInfo`（`@dataclass`）
变量信息：`name` / `value` / `type`。

## 类

### `DebugSession`
调试会话管理器：负责与外部调试器（如 debugpy）的连接、事件分发、状态维护。方法集通常包括：
- `start() / stop() / pause() / continue() / step_over() / step_into() / step_out()`
- `set_breakpoint(file, line) / clear_breakpoint(file, line)`
- `get_stack()` / `get_variables(scope)` / `evaluate(expr)`
- 事件回调：`on_paused` / `on_resumed` / `on_output` / `on_terminated`

### `DebugCard(UFrame)`
UI 卡片：把 `DebugSession` 的数据呈现到 UI。
- 构造 `__init__(parent, session, *, title='DEBUG', **kwargs)`。
- 内部使用 `UListView` 渲染 Variables / Call Stack / Breakpoints。
- `set_session(session)` / `refresh()` / `_apply_theme()` 等。

> 具体方法名以源文件为准（建议查阅源码 590 行的完整实现）。