# Highlighter Module API 文档

## 模块概览

`highlighter` 模块提供对源代码进行语法高亮分析的能力。它将一段代码解析为带类别标签的 token 序列,以便上层 UI(例如编辑器)按类别着色。

---

## 目录结构

```
highlighter/
├── __init__.py        # 模块入口,导出公共 API
├── base.py            # 抽象基类与数据类
├── python.py          # Python 语言的 Highlighter 实现
└── API_DOCS.md        # 本文档
```

---

## 公开 API

### 数据类

#### `HighlightToken`

描述单个高亮 token。

| 字段 | 类型 | 说明 |
| ---- | ---- | ---- |
| `start` | `int` | 在源码字符串中的起始字符偏移(含) |
| `end` | `int` | 在源码字符串中的结束字符偏移(不含) |
| `type` | `str` | token 类型,可能取值见下表 |

**token 类型**:

| `type` | 含义 |
| ------ | ---- |
| `string` | 字符串字面量(单引号/双引号/三引号,支持前缀 r/b/u/f 等) |
| `comment` | 单行注释(`#` 开头) |
| `decorator` | 装饰器(`@xxx`) |
| `number` | 数值字面量(十进制/十六进制/二进制/八进制/浮点/复数) |
| `keyword` | Python 关键字 |
| `builtin` | Python 内建名称 |
| `function` | 由 `def` 声明的函数名 |
| `class` | 由 `class` 声明的类名 |
| `identifier` | 其他普通标识符 |
| `operator` | 运算符(含复合运算符如 `**=`、`<<=`) |
| `punctuation` | 标点符号(`()[]{}:;,.-`) |

#### `HighlightBlock`

描述一段待高亮(或已高亮)的代码块。

| 字段 | 类型 | 说明 |
| ---- | ---- | ---- |
| `code` | `str` | 源代码原文 |
| `tokens` | `list[HighlightToken] \| None` | 高亮 token 列表,`None` 表示未做高亮处理 |

### 抽象基类

#### `HighlighterExpert`

所有语言 Highlighter 的抽象基类,继承自 `abc.ABC`。

```python
class HighlighterExpert(ABC):
    @abstractmethod
    def highlight(self, block: HighlightBlock) -> HighlightBlock: ...

    @abstractmethod
    def get_languange_exts(self) -> list: ...
```

| 方法 | 返回值 | 说明 |
| ---- | ------ | ---- |
| `highlight(block)` | `HighlightBlock` | 对 `block.code` 进行分词,返回带有 `tokens` 的新 `HighlightBlock` |
| `get_languange_exts()` | `list` | 该 Highlighter 所支持的文件扩展名列表(无点号,小写) |

### Python 实现

#### `PythonHighlighterExpert`

基于正则表达式实现的 Python 高亮器。

- 关键字集合从 `data/keywords/python.json` 加载,若文件不存在或 JSON 解析失败,使用内置关键字列表作为后备。
- 内建名称集合硬编码在 `_BUILTINS` 中。
- 在解析到 `def` / `class` 之后,**紧跟其后的**标识符(中间无空行)分别被标记为 `function` / `class`。
- 字符串支持前缀组合(`r""`、`b''`、`rb""`、`u""`、`f""` 等)。

**支持的文件扩展名**: `['py']`

---

## 使用示例

```python
from modules.highlighter import PythonHighlighterExpert, HighlightBlock

expert = PythonHighlighterExpert()
print('支持的扩展名:', expert.get_languange_exts())

source = '''
def greet(name: str) -> str:
    """Say hello."""
    return f"hello, {name}"
'''

block = HighlightBlock(code=source, tokens=None)
result = expert.highlight(block)

for token in result.tokens:
    snippet = result.code[token.start:token.end]
    print(f'{token.type:10s} -> {snippet!r}')
```

输出示例:

```
keyword    -> 'def'
function   -> 'greet'
punctuation-> '('
identifier -> 'name'
...
string     -> '"""Say hello."""'
keyword    -> 'return'
string     -> 'f"hello, {name}"'
```

---

## 扩展指南

新增一种语言的高亮器:

1. 继承 `HighlighterExpert`。
2. 实现 `highlight(self, block: HighlightBlock) -> HighlightBlock`,返回填充好的 token 列表。
3. 实现 `get_languange_exts(self) -> list`,返回支持的扩展名。
4. 在 `__init__.py` 中导出新类,并加入 `__all__`。