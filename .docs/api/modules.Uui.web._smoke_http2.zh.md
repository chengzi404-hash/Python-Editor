# `modules/Uui/web/_smoke_http2.py`

源文件路径：`modules/Uui/web/_smoke_http2.py`

HTTP/1.1 + HTTP/2 端到端冒烟测试脚本。

## 模块常量

- `sys.path.insert(0, 'D:/Code')`：本地开发路径 hack。

## 函数

### `make_app() -> wsgi_app`
构造测试用 WSGI app：
- `/` → `b'Hello from Uui.web!\n'`
- `/echo/<x>` → `b'echo: <x>'`
- `/headers` → 把 `HTTP_*` environ 键按行输出
- 其它 → `404 Not Found`
- 响应头 `x-server: uui-web-h2`。

### `recv_all(sock, n, timeout=5.0) -> bytes`
从 socket 接收恰好 `n` 字节（超时 5s）。

### `http1_get(host, port, path, ssl_ctx=None) -> (status, body, headers)`
明文/HTTPS HTTP/1.1 GET。

### `h2c_get(host, port, path) -> (status, body)`
通过 `h2` 库发送 prior-knowledge h2c GET。

### `tls_h2_get(host, port, path, certfile) -> (status, body)`
通过 TLS+ALPN 协商 h2 后再 GET。

### `main()`
启动服务器并按顺序跑 `http1_get` / `h2c_get` / `tls_h2_get`，打印 PASS/FAIL。