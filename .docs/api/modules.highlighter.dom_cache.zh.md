# `modules/highlighter/dom_cache.py`

源文件路径：`modules/highlighter/dom_cache.py`

Python 库的 DOM（公开类/函数/子模块）缓存。缓存位置由 `modules.data.cache_path('python_libs')` 提供，每个包一个 JSON 文件。

## 数据类

### `LibraryDOM`（`@dataclass`）
描述已安装 Python 库的公开结构。
- `name: str` — 包名。
- `version: str = ''` — 通过 `importlib.metadata` 探测到的版本。
- `classes: list[str]` — 顶层公开类名列表。
- `functions: list[str]` — 顶层公开可调用对象名列表。
- `submodules: list[str]` — 顶层子模块名列表。
- `submodule_contents: dict[str, dict]` — 子模块属性表，形如 `{'sub_name': {'classes': [...], 'functions': [...]}}`。

## 缓存路径辅助

- `_cache_dir() -> str`：返回 `cache/python_libs` 目录路径。
- `_cache_file(lib_name: str) -> str`：返回某库的 JSON 缓存文件路径（`.` 替换为 `_`）。

## 公开 API

### `get_lib_dom(lib_name: str) -> Optional[LibraryDOM]`
读取已缓存的 DOM；缺失或解析失败返回 `None`。

### `ensure_lib_cache(lib_name: str) -> Optional[LibraryDOM]`
扫描库并写入缓存；返回新建的 `LibraryDOM`，不可解析时返回 `None`。缓存写入失败被静默忽略。

### `get_or_load_lib_dom(lib_name: str) -> Optional[LibraryDOM]`
缓存命中则直接返回；否则调用 `ensure_lib_cache`。

### `build_full_cache(progress_callback=None) -> int`
扫描所有可见顶层包并缓存。
- 包来源：`sys.modules` 顶层模块名 + 通过 `pkgutil.iter_modules` 枚举的 `site.getsitepackages()` 与 `getusersitepackages()`。
- 过滤掉以下划线开头的名称、`sys.stdlib_module_names`、包含 `tests`/`test_`/`_pytest`/`pytest`/`.venv`/`venv` 的项。
- `progress_callback(current, total)` 在每个包处理完后调用一次。
- 返回成功缓存的包数量。

### `cache_exists(lib_name: str) -> bool`
判断指定库的缓存文件是否存在。

### `invalidate_lib_cache(lib_name: str) -> None`
删除指定库的缓存文件；不存在时静默忽略。

## 内部实现要点

### `_scan_library(lib_name: str) -> Optional[LibraryDOM]`
1. `__import__(lib_name)`，失败返回 `None`。
2. 收集公开名：优先 `__all__`，否则 `dir(mod)` 去掉下划线开头项；用 `getattr` 判断是 `type`、可调用对象，或视作子模块。
3. 用 `pkgutil.iter_modules(mod.__path__, lib_name + '.')` 补全子模块名。
4. 对每个子模块尝试导入并递归收集其 `classes` / `functions`。
5. 通过 `importlib.metadata.version` 探测版本号（多层 `try` 兜底）。