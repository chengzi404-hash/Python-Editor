# Checker Module API 文档

## 模块概览

`checker` 模块提供对 Python 源文件的静态检查与运行时检查能力。它抽象了不同检查工具(Flake8、Pyright、CPython 执行),统一对外暴露 `Checker` 接口。

---

## 目录结构

```
checker/
├── __init__.py        # 模块入口,导出公共 API
├── base.py            # 抽象基类与数据类
├── python.py          # Python 专用 Checker 实现
└── API_DOCS.md        # 本文档
```

---

## 公开 API

### 数据类

#### `OutputRow`

表示单条检查结果。

| 字段 | 类型 | 说明 |
| ---- | ---- | ---- |
| `message` | `str` | 检查消息内容 |
| `level` | `str` | 级别,可选值:`error` / `warning` / `convention` / `notice` / `info` |

#### `Output`

表示一个文件的检查结果。

| 字段 | 类型 | 说明 |
| ---- | ---- | ---- |
| `file` | `str` | 被检查的文件路径 |
| `row` | `list[OutputRow]` | 该文件中所有检查结果行 |

### 抽象基类

#### `Checker`

所有 Checker 的抽象基类,继承自 `abc.ABC`。

```python
class Checker(ABC):
    @abstractmethod
    def check(self, file: str) -> Output: ...
```

| 方法 | 参数 | 返回值 | 说明 |
| ---- | ---- | ------ | ---- |
| `check(file)` | `file: str` — 待检查文件路径 | `Output` | 执行检查并返回结果 |

### Python Checker 实现

#### `Flake8Checker`

基于 [Flake8](https://flake8.pycqa.org/) 的静态检查器。

- 若系统已安装 `flake8`,使用 flake8 进行检查(超时 30 秒)。
- 若未安装 flake8,降级为 `ast` 语法检查,并在结果中追加一条 `info` 级别的提示 `FLAKE8_NOT_FOUND`。

**错误码 → 级别 映射**:

| 错误码前缀 | 级别 |
| ---------- | ---- |
| `E` / `F` | `error` |
| `W` | `warning` |
| `C` | `convention` |
| `N` | `notice` |
| 其他 | `info` |

#### `PyrightChecker`

基于 [Pyright](https://github.com/microsoft/pyright) 的静态类型检查器。

- 优先使用 JSON 输出解析(`--outputjson`)以获取 `summary` 与 `generalDiagnostics`。
- 若解析失败,回退到文本格式并尽量解析。
- 若未安装 pyright,在结果中追加 `info` 级别提示 `PYRIGHT_NOT_FOUND`。

**严重性 → 级别 映射**:

| Pyright severity | 级别 |
| ---------------- | ---- |
| `error` | `error` |
| `warning` | `warning` |
| `information` | `info` |

#### `CPythonChecker`

通过 `subprocess` 执行 CPython 来检查脚本是否能正常运行的运行时检查器。

- 使用 `sys.executable -c <source>` 执行源码,超时 30 秒。
- 若 `returncode != 0`,捕获 `stderr` 中的错误行(过滤 `Traceback` 与 `File "..."` 行)。
- 若发生超时,追加 `execution timed out` 错误消息。
- 文件不存在或读取失败时,追加对应的 `error` 消息并直接返回。

---

## 常量

| 常量 | 来源 | 值 |
| ---- | ---- | -- |
| `FLAKE8_NOT_FOUND` | `python.py` | `'flake8 is not installed, using basic syntax check only'` |
| `PYRIGHT_NOT_FOUND` | `python.py` | `'pyright is not installed, type checking skipped'` |
| `CPYTHON_CHECK_FAILED` | `python.py` | `'python execution check failed'` |

---

## 使用示例

```python
from modules.checker import Flake8Checker, PyrightChecker, CPythonChecker

file_path = 'example.py'

# 静态风格检查
result = Flake8Checker().check(file_path)
for row in result.row:
    print(f'[{row.level}] {row.message}')

# 类型检查
type_result = PyrightChecker().check(file_path)

# 运行时检查
run_result = CPythonChecker().check(file_path)
```

也可以将不同检查器的结果合并:

```python
from modules.checker import Output, OutputRow

combined = Output(file=file_path, row=[])
for checker in (Flake8Checker(), PyrightChecker(), CPythonChecker()):
    combined.row.extend(checker.check(file_path).row)
```

---

## 扩展指南

要新增一种语言或检查器,只需:

1. 继承 `Checker` 并实现 `check(self, file: str) -> Output`。
2. 在该语言的子目录(例如 `checker/python.py`)中实现。
3. 在 `__init__.py` 中导出新类,并加入 `__all__`。