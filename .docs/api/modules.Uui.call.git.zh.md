# `modules/Uui/call/git.py`

源文件路径：`modules/Uui/call/git.py`

`Git` 命令封装。

## 类

### `Git(Command)`
继承 `Command`，提供针对 `git` 的选项映射与必填参数校验。

类属性：
- `_option_aliases = {'empty': 'allow-empty'}`
- `_required_args = {'commit': ('message',)}`

构造：
- `__init__(cwd=None)`：调用 `super().__init__('git', cwd=cwd)`。

#### 用法示例
```python
git = Git(cwd='/path/to/repo')
git.init()
git.add('.')
git.commit(message='initial commit')
git.commit(message='empty commit', empty=True)   # --allow-empty
```