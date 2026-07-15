# `modules/env_manager/manager.py`

源文件路径：`modules/env_manager/manager.py`

Python 解释器环境的扫描、切换与包管理实现。

## 数据类

### `PythonEnvironment`
描述一个 Python 解释器环境。

字段：
- `name: str` — 环境显示名（如 `base (current)`、`conda: py39`）。
- `python_path: str` — 解释器可执行文件绝对路径。
- `version: str = ''` — `X.Y[.Z]` 形式的版本号。
- `env_type: str = 'venv'` — 类型，可选 `'venv'` / `'conda'` / `'system'` / `'custom'`。
- `prefix: str = ''` — 虚拟环境根目录（venv/conda 适用）。
- `packages: Dict[str, str]` — 已缓存的包列表 `{name: version}`。

属性：
- `display_name -> str` — `name` 与 `Python <version>` 用 `—` 拼接，便于 UI 展示。

## 模块级辅助函数

### `_probe_python(path: str) -> str`
调用 `<python> --version`，返回提取到的 `X.Y[.Z]` 版本号；失败返回空串。

### `_list_packages(python_path: str) -> Dict[str, str]`
通过 `pip list --format=json` 列出已安装包，映射为 `{name: version}`；失败返回空字典。

## 类

### `EnvironmentManager`
线程安全的多 Python 环境管理器。

#### 监听器
- `add_listener(callback: Callable[[str], None]) -> None`：注册环境变更回调，参数为新的环境 `name`。
- `remove_listener(callback) -> None`：注销回调，未找到时忽略。
- `_notify(env_name: str) -> None`：内部通知逻辑，复制监听器列表后在锁外调用。

#### 扫描 / 检测
- `scan() -> Dict[str, PythonEnvironment]`
  全量扫描并替换内部环境表，依次：当前解释器（`sys.executable`）→ 系统 `python`/`python3`/`py` → 通用 venv 目录（`.venv`/`venv`/`./.env` 及父目录）→ conda 默认目录 → `conda env list --json`。自动选择与当前解释器匹配的环境作为 `current`。返回 `{name: PythonEnvironment}` 副本。

- `_scan_venv_dirs(seen: set) -> None`：扫描工作目录与父目录的常见 venv 路径，以及 `~/anaconda3/envs`、`~/miniconda3/envs` 下的 conda 环境。

- `_scan_conda(seen: set) -> None`：通过 `conda env list --json` 获取 conda 环境列表，逐个解析。

- `list_environments() -> Dict[str, PythonEnvironment]`：若尚未扫描会先调用 `scan()`，否则返回内部字典的副本。

#### 当前环境
- `current_name: Optional[str]`（属性）：当前激活的环境名。
- `get_current() -> Optional[PythonEnvironment]`：返回当前环境对象，若未设置返回 `None`。
- `set_current(name: str) -> None`：切换当前环境（仅在已扫描集合中存在时生效），并触发监听器。
- `get_python_path() -> str`：返回当前环境的解释器路径，无当前环境时回退到 `sys.executable`。

#### 包管理
- `get_packages(name: Optional[str] = None) -> Dict[str, str]`：列出指定/当前环境的已安装包，结果会缓存到 `env.packages`。
- `install_package(package: str, name: Optional[str] = None, mirror: str = '') -> str`：通过 `pip install` 安装包；`mirror` 非空时附加 `-i <mirror>`。返回空串表示成功，否则返回错误信息字符串（超时/非零退出/异常）。
- `uninstall_package(package: str, name: Optional[str] = None) -> str`：通过 `pip uninstall -y` 卸载包；返回值含义同 `install_package`。

#### 搜索 PyPI
- `search_packages_on_pypi(query: str) -> List[Dict[str, str]]`
  在镜像（清华源 Simple Index）上枚举所有包名并按 `query` 过滤；命中前 15 个再向 `pypi.org/pypi/<name>/json` 拉取版本/简介。结果最多 50 条，按“是否以 query 开头”排序。每项形如 `{'name': ..., 'version': ..., 'summary': ...}`。

- `_get_all_package_names() -> List[str]`：抓取并缓存全量包名列表（`EnvironmentManager._package_names_cache` 类属性）。

- `_fetch_package_info(name: str) -> tuple[str, str]`：访问 PyPI JSON API，返回 `(version, summary)`；失败返回 `('', '')`。

#### 创建 venv
- `create_venv(path: str, python_path: Optional[str] = None, name: Optional[str] = None) -> str`
  使用指定或当前 Python 调用 `<python> -m venv <path>` 创建虚拟环境；成功后探测解释器与版本，并加入 `_environments`。返回空串表示成功，否则返回错误信息。

#### 内部辅助
- `_get_env(name: Optional[str] = None) -> Optional[PythonEnvironment]`：按名称或当前环境查找环境对象。
- `_resolve_python(path: str) -> Optional[str]`（静态）：`os.path.realpath` 解析符号链接。
- `_make_key(path: str) -> str`（静态）：生成内部唯一键。
- `_is_venv(python_path: str) -> bool`（静态）：通过 `sys.prefix != sys.base_prefix` 或向上 5 层查找 `pyvenv.cfg` 判断是否 venv。
- `_venv_prefix(python_path: str) -> str`（静态）：向上查找包含 `pyvenv.cfg` 的目录作为 venv 前缀。
- `_find_python_in_venv(venv_dir: str) -> Optional[str]`（静态）：跨平台定位 venv 中的解释器路径（Windows `Scripts\python.exe`，POSIX `bin/python` 或 `bin/python3`）。

## 模块级单例

### `get_env_manager() -> EnvironmentManager`
懒加载单例工厂，返回全局共享的 `EnvironmentManager` 实例。