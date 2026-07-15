# `modules/Uui/web/__init__.py`

源文件路径：`modules/Uui/web/__init__.py`

`Uui.web` 公开入口 —— Django 风格的极简 WSGI 框架。

## 公开 API

- `UWSGIApp` — WSGI 应用对象。
- `get_application(settings_path=None)` — 工厂函数。
- `get_settings(module_path=None)` — 加载项目设置模块。
- `URequest` — 请求包装。
- `UResponse` 与构造器：`text` / `html` / `json` / `empty` / `redirect` / `file` / `error`。
- 路由：`URLRouter` / `path` / `include` / `clear_url_caches`。
- 异常：`UWebError` / `Http404` / `Http405` / `Http400` / `Http403` / `Http500` / `ImproperlyConfigured`。

## `__all__`

```python
['UWSGIApp', 'get_application', 'get_settings', 'URequest',
 'UResponse', 'text', 'html', 'json', 'empty', 'redirect', 'file', 'error',
 'URLRouter', 'path', 'include', 'clear_url_caches',
 'UWebError', 'Http404', 'Http405', 'Http400', 'Http403', 'Http500',
 'ImproperlyConfigured']
```

CLI 入口见 `Uui.web.cli`，开发/生产服务器见 `Uui.web.server` / `server_http2`。