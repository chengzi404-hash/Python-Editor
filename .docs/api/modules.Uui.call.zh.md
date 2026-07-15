# `modules/Uui/call/__init__.py`

源文件路径：`modules/Uui/call/__init__.py`

`Uui.call` 子包公开入口，统一封装命令行调用。

## 重新导出

- `Command` — 命令基类（自动把方法名转成子命令，支持选项与必填参数校验）。
- `Git` — Git 命令封装。
- `Npm` — npm 命令封装。
- `Pip` — pip 命令封装。
- 异常：`CallError` / `CommandExecutionError` / `CommandNotFoundError` / `MissingArgumentError` / `SubcommandNotFoundError`。

## `__all__`

```python
['CallError', 'CommandExecutionError', 'CommandNotFoundError',
 'MissingArgumentError', 'SubcommandNotFoundError',
 'Command', 'Git', 'Npm', 'Pip']
```