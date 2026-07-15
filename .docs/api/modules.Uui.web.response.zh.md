# `modules/Uui/web/response.py`

源文件路径：`modules/Uui/web/response.py`

HTTP 响应对象与构造器。

## 类

### `UResponse`
表示 HTTP 响应。`__slots__ = ('status_code', 'status', 'headers', 'body')`。

构造 `__init__(body, status=200, headers=None, content_type=None)`：
- `body` 支持 `None`/`str`/`bytes`/`Iterable[bytes]`（会被规整为 `List[bytes]`）。
- `status` 支持 `int` 或 `"200 OK"` 字符串。
- 自动补齐 `content-length`（按 body 总字节数）；`content_type` 缺省时通过参数指定。

方法 / 属性：
- `set_header(name, value) -> UResponse` / `delete_header(name) -> UResponse`
- `__setitem__` / `__getitem__` — 按小写键访问 headers
- `__iter__` — 迭代 body chunks
- `__call__(environ, start_response)` — WSGI 入口：调用 `start_response(status, headers)`，返回 body 列表。
- `content`（属性）：所有 chunk 拼接后的 `bytes`
- `text`（属性）：`content.decode('utf-8', 'replace')`
- `__repr__`：`<UResponse status=... body=... bytes>`

## 构造器函数

- `text(content, status=200, headers=None) -> UResponse` — `text/plain; charset=utf-8`
- `html(content, status=200, headers=None) -> UResponse` — `text/html; charset=utf-8`
- `json(data, status=200, headers=None, encoder=None) -> UResponse` — `application/json; charset=utf-8`，未提供 `encoder` 时用 `_json_default`（支持 `isoformat` 与可迭代对象）。
- `empty(status=204, headers=None) -> UResponse`
- `redirect(location, status=302, headers=None) -> UResponse` — 设置 `location` header
- `file(path, status=200, headers=None, as_attachment=False, attachment_name=None) -> UResponse` — 按 `mimetypes.guess_type` 自动选 MIME；可选 `Content-Disposition: attachment`；流式读取 64KB chunk。文件不存在抛 `Http404`。
- `error(status, message=None) -> UResponse` — `text/plain; charset=utf-8`，默认消息按 `UWebError` 子类的 `status_code`/`default_message` 推断。

## 模板渲染

### `render(request, template_name, context=None, status=200, headers=None) -> UResponse`
按 `settings.TEMPLATES` 选模板后端，注入 `request` / `user`（若已认证），渲染并返回 `text/html`。

辅助：
- `_settings_from_request()`：若 `request` 没有 `settings`，回退到模块级 `_GLOBAL_APP`。
- `_get_template_backend(settings)`：缓存 backend 实例。
- `_json_default(obj)` — `isoformat()` / 可迭代 → 列表。

## 内部

- `_STATUS_LINE: Dict[int, str]` — 100~599 的 `"<code> <reason>"` 字典。
- `_new(body, status, content_type, headers)` — 内部构造辅助。