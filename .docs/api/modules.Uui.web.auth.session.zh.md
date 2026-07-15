# `modules/Uui/web/auth/session.py`

源文件路径：`modules/Uui/web/auth/session.py`

数据库会话后端与 middleware。

## 类

### `Session(Model)`
- `session_key = CharField(max_length=40, unique=True)`
- `session_data = TextField()`
- `expire_at = DateTimeField(null=True)`
- `Meta.app = 'auth'` / `Meta.table = 'auth_session'`

### `SessionStore`
字典式包装，自动持久化到 DB。

构造 `__init__(session_key=None, age_seconds=14天)`：
- `_key`、`_loaded`、`_data`、`_age`、`_modified`。

属性 / 方法：
- `session_key`（属性）
- `_load()`：按 `_key` 从 DB 读取并反序列化。
- `_ensure_loaded()`：懒加载。
- `__getitem__ / __setitem__ / __delitem__ / __contains__ / get / keys / values / items`：标记 `_modified`。
- `flush()`：清空 `_data`。
- `save() -> str`：若无 `_key` 用 `secrets.token_urlsafe(32)` 生成；upsert Session 行；返回 `_key`。
- `delete()`：从 DB 删除并清空本地。

### `SessionMiddleware`
WSGI middleware：
- 从 `settings.SESSION_COOKIE_NAME`（默认 `uui_sessionid`）读取 cookie，构造 `SessionStore`。
- 把 store 写入 `environ['uui.session']` 与 `environ['uui._session_old_key']`。
- 包装 `start_response`：当 store 被修改后自动 `save()`，必要时通过 `Set-Cookie` 更新 cookie（`HttpOnly; SameSite=Lax; Path=/; Max-Age=age`）。

## 内部辅助

- `_serialize(data) -> str` / `_unserialize(text) -> dict` / `_json_default(obj)` — JSON 序列化（支持 `isoformat`）。
- `_parse_cookies(cookie_header) -> Dict[str, str]`。