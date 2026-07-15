# `modules/Uui/web/server_http2.py`

源文件路径：`modules/Uui/web/server_http2.py`

HTTP/2-capable WSGI 服务器：底层用 `h2` 库实现 HTTP/2 帧，并把 WSGI 应用当作 HTTP/1.1 处理（应用本身无需修改）。

## 模块常量

- `H2_AVAILABLE = True/False`：导入 `h2` 成功与否。

## 支持的传输

- **h2c（明文）**：通过 HTTP/1.1 Upgrade 协商；若客户端 prior-knowledge 则假定 HTTP/2。
- **HTTPS + ALPN**：TLS 握手协商 `h2` 或 `http/1.1`，按连接选择。

## 模块级常量

- `_STATUS_REASONS`：HTTP code → reason phrase。
- `_build_http2_headers(status, headers) -> List[Tuple[bytes, bytes]]`：把 WSGI 状态行 + headers 转成 HTTP/2 伪头部（`:status`）+ `(k, v)` 字节对。

## 主要 API

### `run_http2(host, port, settings, *, ssl_certfile='', ssl_keyfile='')`
启动 h2c 或 HTTPS+ALPN 服务器；使用 `h2.connection.H2Connection` 与每连接线程模型。

### `_h2_config(settings) -> h2.config.H2Configuration`
服务器端配置（`client_side=False`，`header_encoding='utf-8'`）；`h2` 缺失时抛 `ImproperlyConfigured`。

## 其它

- 基于 `ThreadingMixIn` + 自定义 `WSGIServer`；通过 `wsgiref.simple_server.WSGIRequestHandler` 处理 HTTP/1.1 子集。
- WSGI 应用由调用方传入，文件本身只负责传输层与 HTTP/2 帧。