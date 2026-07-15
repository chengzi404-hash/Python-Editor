# `modules/Uui/web/testing/client.py`

源文件路径：`modules/Uui/web/testing/client.py`

进程内 WSGI 测试客户端（Django test client 风格）。

## 类

### `UResponse`
轻量响应包装。
- `__init__(status_code, headers, body, context=None)`
- 属性：`status_code` / `headers`（dict）/ `body` / `text`（utf-8 解码）/ `context`。
- `json`（属性）：`json.loads(self.text)`，空文本返回 `None`。

### `UTestClient`
直接调用 WSGI 应用，不经过 socket。

构造 `__init__(wsgi_app=None, settings=None)`：
- 未传 `wsgi_app` 时通过 `get_application(settings).wsgi()` 获取。
- 维护 `cookies: Dict[str, str]` 用于跨请求状态。
- `defaults: Dict[str, str]` — 默认 header。

方法：
- `get(path, **kwargs)` / `post(path, data=None, json=None, **kwargs)` / `put / patch / delete / head / options` — 全部转给 `_request(method, path, **kwargs)`。
- `post` 的 `data` 支持 `Mapping`（自动 urlencode）或原始字符串；`json` 自动 `json.dumps` 并设 `Content-Type`。
- `login(username, password, login_url='/login/') -> UResponse`：POST 登录表单并保存 cookie。
- `_request(...)`：构造 environ，附加 cookies / defaults headers，调用 `wsgi_app(environ, start_response)`，把响应体收集为 `bytes`，更新 cookies（`Set-Cookie`）。

辅助：
- `_flatten(data) -> Iterable[(key, value)]`：嵌套 dict 拍平为 `key=value` 元组（用于 form urlencoded）。