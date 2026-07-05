# Suggestion Module API 文档

## 模块概览

`suggestion` 模块为代码编辑器提供**自动补全建议**功能。它根据光标位置、上下文(类/函数作用域)以及语言内置符号,生成候选词列表。

---

## 目录结构

```
suggestion/
├── __init__.py        # 模块入口,导出公共 API
├── base.py            # 抽象基类与数据类
├── python.py          # Python 语言的 Suggestion 实现
├── c.py               # C 语言(占位)
├── cpp.py             # C++ 语言(占位)
└── API_DOCS.md        # 本文档
```

---

## 公开 API

### 数据类

#### `SuggestionBlock`

描述一段需要补全建议的代码块。

| 字段 | 类型 | 说明 |
| ---- | ---- | ---- |
| `code` | `str` | 整段源代码 |
| `position` | `int` | 光标在 `code` 中的字符偏移 |

#### `DOMScope`

描述一个作用域的静态结构信息。

| 字段 | 类型 | 说明 |
| ---- | ---- | ---- |
| `begin` | `int` | 作用域起始行(从 0 开始) |
| `end` | `int` | 作用域结束行(不含) |
| `varibles` | `list` | 该作用域内的变量名 |
| `functions` | `list` | 该作用域内的函数名 |
| `classes` | `list` | 该作用域内的类名 |
| `subDOM` | `list[DOMScope]` | 嵌套的子作用域 |

> ⚠️ 拼写说明:`varibles` 是源码中已存在的拼写,如需修复请同步修改 `base.py` 与所有引用方。

### 抽象基类

#### `SuggestionExpert`

所有语言 Suggestion 的抽象基类,继承自 `abc.ABC`。

```python
class SuggestionExpert(ABC):
    @abstractmethod
    def suggest(self, block: SuggestionBlock) -> list: ...

    @abstractmethod
    def get_languange_exts(self) -> list: ...
```

| 方法 | 返回值 | 说明 |
| ---- | ------ | ---- |
| `suggest(block)` | `list` | 根据 `block.position` 生成候选词列表 |
| `get_languange_exts()` | `list` | 该 Suggestion 所支持的文件扩展名列表 |

---

## Python 实现

### `PythonSuggestionExpert`

#### 公开方法

| 方法 | 说明 |
| ---- | ---- |
| `suggest(block)` | 主入口。返回按 `prefix` 过滤并去重排序的候选词列表。 |
| `get_languange_exts()` | 返回 `['py']`。 |

#### 静态工具方法

| 方法 | 说明 |
| ---- | ---- |
| `iter_classes(block)` | 返回 `block.code` 中所有 `class` 名(扁平)。 |
| `iter_function(block)` | 返回 `block.code` 中所有 `def` 名(扁平)。 |
| `find_domin(block, position)` | 返回光标位置 `position` 所在的**最深** `DOMScope`。 |

#### 私有方法(以 `_` 开头)

| 方法 | 说明 |
| ---- | ---- |
| `_suggest_names(block, line_no)` | 汇总内建名 + 关键字 + 作用域内的变量/函数/类,返回候选集。 |
| `_suggest_attributes(block, line_no, obj_name)` | 处理 `obj.<cursor>` 的属性补全(支持 `self.*` 与内建类型属性)。 |
| `_enclosing_class_methods(block, line_no)` | 向上回溯找到光标所在类,并列出其中定义的方法。 |
| `_extract_variables(code, begin, end)` | 通过正则从代码段中提取变量名(赋值、`for ... in`、`with ... as`、`except ... as`、函数参数)。 |
| `_collect_entries(code)` | 扫描代码,收集所有 `class` / `def` 条目及其行号、缩进、范围。 |
| `_build_scope_tree(code)` | 由 `_collect_entries` 的结果构建出 `DOMScope` 树(根作用域涵盖整个文件)。 |

#### 内置常量(在 `python.py` 中)

| 常量 | 说明 |
| ---- | ---- |
| `BUILTIN_FUNCTIONS` | Python 内建函数列表 |
| `BUILTIN_CLASSES` | Python 内建类型列表 |
| `BUILTIN_PROPERTIES` | 内建常量与 dunder 名(`True`, `None`, `__name__` 等) |
| `KEYWORDS` | Python 关键字列表 |
| `BUILTIN_ATTRS` | 字典,键为内建类型,值为该类型的常用属性/方法名列表 |

#### 建议逻辑概览

1. 根据光标位置 `position` 计算所在行、列。
2. 取光标所在行中**当前正在输入的前缀**(`prefix`),由字母数字与下划线组成。
3. 若光标紧跟在 `.` 之后,则切换到 **属性补全**:
   - `self.` → 列出所在类的方法 + 通用 dunder。
   - 已知内建类型 → 返回 `BUILTIN_ATTRS` 中的对应属性。
   - 其他对象 → 返回通用 dunder 集合。
4. 否则进入 **标识符补全**:
   - 合并关键字、内建函数/类/常量。
   - 调用 `_build_scope_tree` 构建作用域树。
   - 深度优先遍历,加入当前作用域与外层作用域的变量、函数、类。
5. 用 `prefix` 过滤并返回排序去重后的结果。

---

## C / C++ 实现

`c.py` 与 `cpp.py` 当前为占位文件,尚未提供具体实现。未来计划:

- 引入 `CSuggestionExpert` / `CppSuggestionExpert`,继承 `SuggestionExpert`。
- 支持 `CSuggestionExpert.get_languange_exts() -> ['c', 'h']`。
- 支持 `CppSuggestionExpert.get_languange_exts() -> ['cpp', 'cxx', 'cc', 'hpp', 'hh', 'hxx']`。
- 完成后在 `__init__.py` 中导出,并加入 `__all__`。

---

## 使用示例

```python
from modules.suggestion import PythonSuggestionExpert, SuggestionBlock

expert = PythonSuggestionExpert()
print('支持扩展名:', expert.get_languange_exts())

source = '''
import os

class Greeter:
    def __init__(self, name):
        self.name = name

    def greet(self):
        return f"hi {self."

g = Greeter("world")
print(g.greet)
'''

# 假设光标停在 self.| 的位置
pos = source.index('self.') + len('self.')
block = SuggestionBlock(code=source, position=pos)
print('属性建议:', expert.suggest(block))

# 标识符补全
pos2 = source.index('print(') + len('print(')
block2 = SuggestionBlock(code=source, position=pos2)
print('标识符建议:', expert.suggest(block2))
```

---

## 扩展指南

新增一种语言的补全器:

1. 继承 `SuggestionExpert`。
2. 实现 `suggest(self, block: SuggestionBlock) -> list`。
3. 实现 `get_languange_exts(self) -> list`。
4. 在 `__init__.py` 中导出新类,并加入 `__all__`。