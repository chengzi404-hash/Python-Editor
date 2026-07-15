# `modules/checker/python.py`

源文件路径：`modules/checker/python.py`

针对 Python 源码的三种 `Checker` 实现。

## 模块常量

- `FLAKE8_NOT_FOUND = 'flake8 is not installed, using basic syntax check only'` — flake8 缺失时插入的提示信息。
- `PYRIGHT_NOT_FOUND = 'pyright is not installed, type checking skipped'` — pyright 缺失时插入的提示信息。
- `CPYTHON_CHECK_FAILED = 'python execution check failed'` — 预留常量（实际未直接使用）。

## 类

### `Flake8Checker(Checker)`
通过 `python -m flake8` 执行静态分析。失败或未安装时回退到 `ast.parse` 语法检查。

#### 方法

- `check(file: str) -> Output`
  入口方法。优先尝试调用 flake8；若 flake8 未安装或输出提示 `No module named flake8`，追加 `FLAKE8_NOT_FOUND` 并执行本地语法检查。返回填充好的 `Output`。

- `_try_flake8(file: str, output: Output) -> bool`
  同步执行 flake8 子进程（`timeout=30s`），将每条结果解析为 `OutputRow` 并写入 `output.row`。flake8 错误码到 `level` 的映射：E/F → error，W → warning，C → convention，N → notice。返回 `True` 表示已成功运行 flake8（无论是否有错误）。

- `_code_to_level(code: str) -> str`（静态）
  flake8 代码到严重级别的映射函数。

- `_syntax_check(file: str, output: Output) -> None`（静态）
  使用 `ast.parse` 对文件做语法检查；若失败则向 `output` 追加 `SyntaxError` 信息。

### `PyrightChecker(Checker)`
通过 `pyright --outputjson` 做类型检查。

#### 方法

- `check(file: str) -> Output`
  入口方法。尝试调用 pyright；缺失时回退并追加 `PYRIGHT_NOT_FOUND` 信息。

- `_try_pyright(file: str, output: Output) -> bool`
  同步执行 pyright 子进程（`timeout=60s`）。优先解析 `--outputjson` 输出；若 stdout 不是 JSON 则按行解析纯文本输出（识别 `error`/`warning`/`information` 前缀）。返回 `True` 表示已成功执行 pyright。

### `CPythonChecker(Checker)`
直接用当前解释器执行文件源码（`python -c <source>`），通过捕获非零退出码与 stderr 来发现运行时错误。

#### 方法

- `check(file: str) -> Output`
  读取源码后用 `subprocess.run([sys.executable, '-c', source], timeout=30)` 执行；超时返回 `'execution timed out'` 错误；非零退出码时将 stderr（去掉 `Traceback` 与 `  File` 行）逐行写入 `output.row`，level 均为 `'error'`。