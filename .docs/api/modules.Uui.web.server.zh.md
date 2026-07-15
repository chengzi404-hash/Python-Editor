# `modules/Uui/web/server.py`

源文件路径：`modules/Uui/web/server.py`

Uui.web 内置 HTTP 服务器（开发 wsgiref、生产 waitress）。

## 函数

### `make_server(host='127.0.0.1', port=8000, settings=None) -> (server, wsgi_app)`
创建基于 `wsgiref.simple_server.WSGIServer + ThreadingMixIn` 的多线程 WSGI 服务器（`daemon_threads=True`, `allow_reuse_address=True`）。返回 `(server, wsgi_app)`，`server.set_app(wsgi_app)` 已设置。

### `runserver(host='127.0.0.1', port=8000, settings=None, quiet=False) -> None`
启动开发服务器（阻塞）。`Ctrl+C` 时调用 `server.shutdown()` 与 `server.server_close()`。

### `serve(host='0.0.0.0', port=8000, settings=None, threads=4, quiet=False) -> None`
启动生产服务器（waitress）。缺失 waitress 包时抛 `ImproperlyConfigured('waitress is required for `web serve`; install via `pip install waitress`')`。