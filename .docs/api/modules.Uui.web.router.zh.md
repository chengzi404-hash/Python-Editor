# `modules/Uui/web/router.py`

源文件路径：`modules/Uui/web/router.py`

URL 路由：基于正则的路径匹配 + Django 风格的 path converter + include 子 URLconf。

## 模块常量 / 类型

- `PathConverter = Tuple[str, Callable[[str], Any]]` — `(regex_part, parser)`
- `CONVERTERS` — 内置转换器：
  - `str` → `[^/]+` / `str`
  - `int` → `[0-9]+` / `int`
  - `slug` → `[-a-zA-Z0-9_]+` / `str`
  - `uuid` → `[0-9a-fA-F-]{36}` / `str`
  - `path` → `.+` / `str`
- `DEFAULT_CONVERTER = CONVERTERS['str']`
- 优先使用 `regex`（性能更好），回退 `re`。

## 函数

### `_compile_pattern(pattern) -> (compiled_regex, param_names, converters)`
把 `"hello/<int:id>"` 类模式编译为 `^(?P<id>[0-9]+)$`；遇到未闭合 `<` 或未知 converter 抛 `ImproperlyConfigured`。

### `path(pattern: str, view: Callable, name: Optional[str] = None)`
注册一个 URL pattern。
- 自动为 `pattern` 补前导 `/`，去尾 `/`（保留根 `/`）。
- `view` 是 `Include` 时设置其 `_prefix` 后返回它，否则返回 `Route(pattern, view, name)`。

### `include(module: str, namespace: Optional[str] = None) -> Include`
挂载子 URLconf。

### `clear_url_caches()`
清空 `_INCLUDE_CACHE`。

## 类

### `Route`
单个 URL 模式（`__slots__ = ('pattern', 'view', 'name', '_compiled', '_params', '_converters')`）。

构造 `__init__(pattern, view, name=None)`：
- `pattern == ''` 时不编译。
- 其它情况下编译并保存 `_compiled` / `_params` / `_converters`。

方法：
- `match(path) -> Optional[Dict[str, Any]]`：匹配 `path`，把命名组按 `_converters` 转换为 Python 对象；解析失败时保留原字符串。

### `Include`
子 URLconf 标记对象。`__init__(module, namespace=None)`，`_prefix` 在 `path(...)` 包装时设置。

### `URLRouter`
编译一组路由 + 子 include 为单一解析器。

构造 `__init__(routes, prefix='', namespace=None)`：
- 把 `prefix` 去尾 `/`。
- 内部表：`_exact` / `_exact_single`（无参数路由）、`_regex`（带参数路由）、`_include_routes`（子路由）。

方法：
- `resolve(path) -> (view, kwargs, namespace_info)`：按 `prefix` 缩放；优先匹配 `_exact_single`，回退 `_exact`，再回退 `_regex`，最后尝试 `_include_routes`（递归 `sub.resolve`）；都失败抛 `Http404`。

## 模块内部

- `_INCLUDE_CACHE: Dict[str, URLRouter]` — 子 URLconf 模块的缓存。
- `_load_include(include, *, prefix, namespace) -> URLRouter`：按 `module|prefix|namespace` 缓存；import 后构建 `URLRouter`。