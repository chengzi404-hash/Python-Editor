# `modules/checker/__init__.py`

源文件路径：`modules/checker/__init__.py`

`modules.checker` 包的公开入口，重新导出基类与 Python 语言相关的检查器。

## 导出

- `OutputRow` — 单条诊断信息的数据类。
- `Output` — 一次检查产出的汇总对象。
- `Checker` — 检查器抽象基类。
- `Flake8Checker` — 调用 `flake8` 的 Python 检查器实现。
- `PyrightChecker` — 调用 `pyright` 的 Python 类型检查器实现。
- `CPythonChecker` — 直接执行 Python 源码以捕获运行时错误的检查器实现。

## `__all__`

```python
[
    'OutputRow',
    'Output',
    'Checker',
    'Flake8Checker',
    'PyrightChecker',
    'CPythonChecker',
]
```