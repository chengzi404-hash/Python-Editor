# `modules/suggestion/__init__.py`

源文件路径：`modules/suggestion/__init__.py`

`modules.suggestion` 包的公开入口。汇总各语言补全专家以及 Python 内建符号集。

## 重新导出

### 基础类型
- `SuggestionBlock` — 待补全的代码块（`code` + `position`）。
- `DOMScope` — 用户代码的作用域树节点（begin/end/变量/函数/类/子作用域）。
- `SuggestionExpert` — 补全器抽象基类。
- `SuggestionItem` — 单条补全项（含 `label` / `priority` / `kind`）。

### 语言补全器
- `PythonSuggestionExpert`
- `CSuggestionExpert`
- `CppSuggestionExpert`

### Python 内建符号集
- `KEYWORDS` — Python 关键字集合。
- `BUILTIN_FUNCTIONS` — 内建函数集合。
- `BUILTIN_CLASSES` — 内建类集合。
- `BUILTIN_PROPERTIES` — 内建常量/属性集合（如 `True`/`None`/`__name__`）。
- `BUILTIN_ATTRS: dict[str, list[str]]` — 按类型映射的常用属性名（`str` / `list` / `dict` / `int` / `float` / `set` / `tuple` / `bytes` / `bool`）。

## `__all__`

```python
[
    'SuggestionBlock', 'DOMScope', 'SuggestionExpert', 'SuggestionItem',
    'PythonSuggestionExpert', 'CSuggestionExpert', 'CppSuggestionExpert',
    'KEYWORDS', 'BUILTIN_FUNCTIONS', 'BUILTIN_CLASSES',
    'BUILTIN_PROPERTIES', 'BUILTIN_ATTRS',
]
```