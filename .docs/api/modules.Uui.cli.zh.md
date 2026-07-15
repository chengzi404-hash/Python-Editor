# `modules/Uui/cli.py`

源文件路径：`modules/Uui/cli.py`

Uui 的命令行脚手架工具，可通过 `python -m Uui.cli <subcmd>` 调用。

## 模块常量

- `CONFIG_DIR = Path.home() / '.uui'`
- `CONFIG_FILE = CONFIG_DIR / 'config.py'`
- `DEFAULT_CONFIG` — 默认全局配置源码（FOLLOW_SYSTEM_THEME/DEFAULT_THEME/DEFAULT_GEOMETRY/PRELOAD/FOLLOW_OS_THEME）。
- `PROJECT_TEMPLATE` — `uui new` 生成的项目 `main.py` 模板。
- `THEME_TEMPLATE` — `uui theme <Name>` 生成的 theme 类模板。
- `GITIGNORE_TEMPLATE` — `uui new` 写入的 `.gitignore` 内容。

## 模块内部工具函数

- `_ensure_parent(path)` / `_write_file(path, content, *, force=False)` — 写文件辅助（已存在且未传 `force` 时跳过）。
- `_ensure_config()` — 若 `~/.uui/` 不存在则创建，并写入默认 `config.py`。
- `_load_config(quiet=True)` — 通过 `importlib.util.spec_from_file_location` 加载 `~/.uui/config.py`。
- `_py_repr(value)` — 直接调用 `repr`。
- `_ansi_supported()` / `_ansi_supported` / `_c(code, text)` — ANSI 颜色支持检测与加色。
- `_hr()` / `_banner()` / `_step()` / `_summary()` / `_success()` / `_info()` / `_warn()` / `_error()` — CLI 排版工具。
- `_is_interactive()` / `_prompt()` / `_prompt_choice()` / `_prompt_yes_no()` — 交互式问答（仅在 stdin 是 TTY 且支持 ANSI 时启用）。
- `_validate_identifier(value)` / `_validate_geometry(value)` — 输入校验。
- `_detect_vcs_tools()` — 检测 `git`/`svn`。
- `_probe_python(path) -> str` — 调用 `<py> --version` 返回 `X.Y.Z`。
- `_conda_flavor(conda_path)` — 通过 `conda info --root` 与 `python --version` 推断 anaconda/miniconda/conda 与默认 Python 版本。
- `_detect_python_envs()` — 探测当前 venv、系统 python/python3/py、conda。
- `_create_python_env(project_dir, choice)` / `_create_venv(...)` / `_create_conda(...)` / `_activate_hint(...)` — 创建并提示激活虚拟环境。
- `_init_git(project_dir)` / `_init_svn(project_dir)` — 初始化版本控制（写 .gitignore、commit、svnadmin）。

## 内部类

### `_C`
ANSI 转义码常量（RESET / BOLD / DIM / CYAN / GREEN / YELLOW / BLUE / MAGENTA / RED / GRAY）。

## 命令实现

### `cmd_new(args) -> int`
- 有 `name` → `_new_noninteractive`；否则若非 TTY 直接报错；否则 `_new_interactive`。
- 两路径最终调用 `_new_apply`。

### `cmd_theme(args) -> int`
校验 name 为合法 Python 标识符；生成 `<name>_theme.py`，类名取 `Name` + `Theme` 后缀。

### `cmd_info(args) -> int`
列出内置主题、组件名、OS 主题 follow 映射、当前主题与 OS 主题。

### `cmd_demo(args) -> int`
调用 `.demo.main()` 启动组件画廊。

### `cmd_designer(args) -> int`
调用 `.tool.designer.main(args.file)` 启动可视化设计器。

### `cmd_config(args) -> int`
子命令：`--init` / `--reset` / `--path` / `--edit`，默认显示当前配置。

### `_dispatch_web(args) -> int`
`uui web ...` 子命令，转发到 `.web.cli.main(...)`。

## argparse

### `build_parser() -> argparse.ArgumentParser`
构建顶层 parser 与子命令：`new` / `theme` / `info` / `demo` / `designer` / `config` / `web`。

## 入口

### `main(argv=None) -> int`
解析 argv 并调用对应 `cmd_*`；`KeyboardInterrupt` 返回 `130`。