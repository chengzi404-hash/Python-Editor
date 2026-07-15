# `modules/Uui/web/app.py`

源文件路径：`modules/Uui/web/app.py`

WSGI 应用对象与全局应用缓存。

## 模块级缓存

- `_SETTINGS_CACHE: Dict[str, Any]` — 已加载的 settings 模块。
- `_GLOBAL_APP: Optional[UWSGIApp]` — 最近构建的全局应用，供 `response.render` 解析 settings。

## 函数

### `get_settings(module_path: Optional[str] = None) -> Any`
返回项目的 settings 模块。`module_path` 未传时从环境变量 `UUI_SETTINGS` 读取；缺失抛 `ImproperlyConfigured`。已加载的模块会被缓存。

### `get_application(settings_path: Optional[str] = None) -> UWSGIApp`
构造并返回一个新的 `UWSGIApp(settings)`。

## 类

### `UWSGIApp`
WSGI 应用对象。

构造 `__init__(settings)`：
- 缓存 `settings`；初始化 `_router`、`_middleware`。
- 尝试用 settings 配置 ORM（`from .orm import connection as _db; _db.configure(settings)`）。
- 调用 `_init_middleware()` 与 `_init_router()`；设置全局 `_GLOBAL_APP`。

内部方法：
- `_init_middleware()`：从 `settings.MIDDLEWARE`（按反序）导入并加入栈。
- `_init_router()`：从 `settings.ROOT_URLCONF` 导入 `urlpatterns`，清空 URL 缓存后构建 `URLRouter`；缺失时抛 `ImproperlyConfigured`。
- `_import(path)`（模块内）：按 `module.path.Class` 形式导入。
- `_handle(request, start_response)`：调用 `router.resolve(request.path)` → 调用 `view(request, **kwargs)`，把返回值包装为 `UResponse`；返回值若是 `str`/`bytes`/可迭代也自动包装。
- `_handle_exception(exc, start_response)`：DEBUG 时返回带堆栈的调试响应，否则 `error(500, str(exc))`。
- `_handle_404(exc, start_response)`：DEBUG 时返回 404 详情。
- `wsgi(environ=None, start_response=None)`：返回带中间件链的 WSGI 可调用；无参时返回 curry 形式。

公开方法：
- `add_middleware(mw_class: Callable)`：把 middleware 类追加到栈（在 `__init__` 之后追加）。

WSGI 入口：`__call__(environ, start_response) -> List[bytes]`，按以下顺序处理异常：`Http404` → `Http403`/`Http400` → `Exception`。