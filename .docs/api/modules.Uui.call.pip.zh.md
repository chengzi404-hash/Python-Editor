# `modules/Uui/call/pip.py`

源文件路径：`modules/Uui/call/pip.py`

`Pip` 命令封装。

## 类

### `Pip(Command)`
继承 `Command`，针对 `pip`。

构造：
- `__init__(cwd=None)`：调用 `super().__init__('pip', cwd=cwd)`。

用法示例：
```python
pip = Pip()
pip.install('requests')
pip.install('.', editable=True, no_deps=True)
pip.uninstall('requests', yes=True)
pip.list()
```