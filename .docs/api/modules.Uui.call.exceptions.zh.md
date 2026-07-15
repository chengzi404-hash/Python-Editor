# `modules/Uui/call/exceptions.py`

源文件路径：`modules/Uui/call/exceptions.py`

`Uui.call` 子包的自定义异常层次。

## 类

### `CallError(Exception)`
所有 `Uui.call` 异常的基类。

### `CommandNotFoundError(CallError)`
命令（可执行文件）不存在。

### `SubcommandNotFoundError(CallError)`
子命令为空或未提供。

### `MissingArgumentError(CallError)`
调用子命令时缺少必填参数。

### `CommandExecutionError(CallError)`
子进程返回非零退出码。

构造：
```python
CommandExecutionError(message, returncode=None, stdout=None, stderr=None, cmd=None)
```
字段：`returncode` / `stdout` / `stderr` / `cmd`。