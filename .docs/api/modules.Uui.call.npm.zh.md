# `modules/Uui/call/npm.py`

源文件路径：`modules/Uui/call/npm.py`

`Npm` 命令封装。

## 类

### `Npm(Command)`
继承 `Command`，针对 `npm`。

构造：
- `__init__(cwd=None)`：调用 `super().__init__('npm', cwd=cwd)`。

不重写 `_option_aliases` / `_required_args`；任何 npm 子命令（如 `install` / `run` / `test`）均可直接通过属性访问：`npm.install(...)` / `npm.run(build=...)` 等。