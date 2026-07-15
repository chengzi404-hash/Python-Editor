# `modules/Uui/web/middleware.py`

源文件路径：`modules/Uui/web/middleware.py`

内置中间件。每个中间件类签名：`__init__(app, inner)`，其中 `app` 是 `UWSGIApp`、`inner` 是链中下一个 WSGI callable；`__call__(environ, start_response)` 是 WSGI 入口。

## 类

### `CommonMiddleware`
设置常见响应头，拒绝 `Host` 不在 `ALLOWED_HOSTS` 中的请求（`ALLOWED_HOSTS=['*']` 时放行）；自动追加 `X-Content-Type-Options: nosniff`。

### `SessionMiddleware`
为向后兼容保留的桩；实际实现见 `Uui.web.auth.session.SessionMiddleware`。

### `AuthenticationMiddleware`
从 `environ['uui.session']['_user_id']` 取出用户 ID，通过 `auth.users.get_user_by_id` 解析，存入 `environ['uui.user']`；未登录时存入 `get_anonymous_user()`。需要放在 `SessionMiddleware` 之后。

### `CsrfViewMiddleware`
校验非安全方法（`POST`/`PUT`/`PATCH`/`DELETE`）的 CSRF token：
- 比较 cookie（`settings.CSRF_COOKIE_NAME`，默认 `uui_csrftoken`）与 header（`settings.CSRF_HEADER_NAME` 默认 `HTTP_X_CSRFTOKEN`）。
- 不一致返回 `error_response(403, 'CSRF verification failed.')`。

### `StaticMiddleware`
（在文件后续位置提供）服务于 `settings.STATIC_URL` 下的静态文件。

## 内部辅助

- `_cookies(cookie_header: str) -> Dict[str, str]`：解析 Cookie 字符串。