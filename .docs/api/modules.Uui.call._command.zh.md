# `modules/Uui/call/_command.py`

源文件路径：`modules/Uui/call/_command.py`

`Command` 基类：通过方法调用映射到子命令（如 `git.commit(...)` → `git commit ...`），并校验必填参数。

## 类

### `Command`
命令行封装基类。

#### 类属性（子类可重写）
- `_option_aliases: dict[str, str]` — 把 Python 关键字参数名映射到 CLI 选项名（如 `empty -> allow-empty`）。
- `_required_args: dict[str, tuple[str, ...]]` — `{subcommand: (必需kwarg名, ...)}`。

#### 构造
- `__init__(program, cwd=None)`：若 `shutil.which(program) is None` 抛 `CommandNotFoundError`；保存 `program` 与 `cwd`。

#### 方法
- `_build_option(key) -> str`：把 kwarg 名转成 CLI 选项（`_` → `-`），单字符前缀 `-`，多字符前缀 `--`。

- `_append_options(cmd, kwargs)`：把 kwargs 序列化为选项。
  - `bool` 真值追加 flag；假值忽略。
  - `list`/`tuple` 逐项重复 `flag value`。
  - 其它：`flag value`。

- `_check_required_args(subcommand, kwargs)`：检查 `_required_args[subcommand]` 中的 kwarg 是否齐全，缺失抛 `MissingArgumentError`。

- `_run(cmd) -> subprocess.CompletedProcess`：执行命令。
  - `subprocess.run(..., cwd=self.cwd, check=True, capture_output=True, text=True)`。
  - `CalledProcessError` 转 `CommandExecutionError(returncode, stdout, stderr, cmd)`。
  - `FileNotFoundError` 转 `CommandNotFoundError`。

- `_validate_subcommand(subcommand)`：空子命令抛 `SubcommandNotFoundError`。

#### 动态方法
- `__getattr__(name)`：把属性名 `name` 中的 `_` 替换为 `-` 作为子命令；返回闭包 `method(*args, **kwargs)`：
  1. 检查必填参数。
  2. 构造 `[program, subcommand, ...options, ...args]`。
  3. 调用 `_run` 返回 `CompletedProcess`。

- `__call__(*args, **kwargs)`：直接调用 `program`（无子命令），如 `Git()(cwd=...)` 不常见，但 `Pip()(...)` 等价于 `pip ...`。