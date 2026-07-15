# `modules/Uui/__init__.py`

源文件路径：`modules/Uui/__init__.py`

Uui 是基于 Tkinter 的窗口小部件工具集（含 web 框架 `call`、`tool` 工具与 `widgets`）。

## 公开导出

- `Window` — 主窗口类（来自 `.widgets.window`）。
- `widgets` — 子模块，提供所有 `U*` 控件、主题等。
- `call` — 子模块，统一封装 `git`/`npm`/`pip` 等命令行调用。

## `__all__`

```python
['Window', 'widgets', 'call']
```