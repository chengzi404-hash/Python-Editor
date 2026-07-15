# `modules/Uui/web/request.py`

源文件路径：`modules/Uui/web/request.py`

WSGI 请求包装，支持懒解析。

## 类

### `URequest`
包装 `environ` 并提供常用字段访问。

构造 `__init__(environ)`：
- 保存 `_environ`，延迟初始化 `_headers` / `_form` / `_files` / `_json` / `_body` / `_query`。
- 缓存 `_path` / `_method`。
- `state: Dict[str, Any]`，从 `environ['uui.user']` / `environ['uui.session']` 同步到 `state`。

属性 / 方法：
- `method` / `path` / `full_path` / `query_string`
- `environ` / `scheme` / `host` / `content_type` / `content_length`
- `headers -> Dict[str, str]`：懒解析；`get_header(name, default=None)`
- `GET -> Dict[str, object]`：`parse_qs(..., keep_blank_values=True)` 结果
- `query(key, default=None) -> Optional[str]`：按出现顺序返回第一个匹配值
- `body -> bytes`：懒读 `wsgi.input`
- `POST` / `form`：根据 `content-type` 解析 form-urlencoded / multipart
- `json`：解析 `application/json` body
- `cookies -> Dict[str, str]`
- `is_secure`（属性）— `scheme == 'https'`
- `remote_addr`（属性）
- `session` / `user`：从 `state` 读写
- `__repr__`：`<URequest {METHOD} {path}>`

## 模块内部辅助

### `_parse_headers(environ) -> Dict[str, str]`
从 `HTTP_*` / `CONTENT_*` 构建小写键字典。

### `_read_body(environ) -> bytes`
读 `CONTENT_LENGTH` 长度的 `wsgi.input`，读后尝试 `seek(0)`。

### `_parse_form(environ, body, content_type) -> List[Tuple[str, str]]`
按 content-type 分发到 urlencoded 或 multipart 解析。

### `_parse_multipart(environ, body, content_type) -> List[Tuple[str, str]]`
依赖第三方 `multipart` 包；缺失时返回 `[]`。

### `_parse_json(body, content_type) -> Any`
仅当 content-type 是 `application/json` 才解析；其它情况返回 `None`。

### `_parse_cookies(cookie_header) -> Dict[str, str]`
把 `Cookie` 头解析成字典。