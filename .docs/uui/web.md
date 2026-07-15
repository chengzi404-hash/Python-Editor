# `modules.Uui.web`

**Source**: [`modules/Uui/web/`](../../modules/Uui/web/)

A Django-inspired WSGI framework that ships inside the editor's vendored
`Uui` library. Includes ORM, auth, admin, sessions, templates, testing,
and HTTP/1.1 + HTTP/2 servers. **Not currently used by the editor
itself** — exposed for downstream apps.

```python
from modules.Uui.web import (
    UWSGIApp, get_application, get_settings,
    URequest,
    UResponse, text, html, json, empty, redirect, file, error,
    URLRouter, path, include, clear_url_caches,
    UWebError, Http404, Http405, Http400, Http403, Http500,
    ImproperlyConfigured,
)
```

> **Naming**: the package is imported as `modules.Uui.web` from inside
> the editor project, but internal imports use the bare name
> `Uui.web` (matching the canonical project name). The two are the same
> module.

## Application

### `get_settings(module_path=None)` `[app.py:17]`

Loads the project's settings module. Reads the `UUI_SETTINGS` env var
when `module_path` is omitted. Caches by module path. Raises
`ImproperlyConfigured` if not set or not importable.

### `get_application(settings_path=None)` `[app.py:36]`

Convenience: `get_settings(...) → UWSGIApp(...)`.

### `UWSGIApp` `[app.py:43]`

```python
class UWSGIApp:
    def __init__(self, settings): ...
    def add_middleware(self, mw_class): ...       # append to the middleware stack
    def route(self, pattern, *, methods=None): ...
    def render(self, template_name, context): ...
    def static_url(self, path): ...
    def wsgi(self) -> Callable: ...                # compose middleware, return callable
    def __call__(self, environ, start_response): ...
```

Construction:

1. Stores `settings`.
2. Configures ORM backends via `orm.connection.configure(settings)` (best-effort).
3. Loads middleware (reversed order from `settings.MIDDLEWARE`).
4. Loads the URLconf from `settings.ROOT_URLCONF` and builds a `URLRouter`.
5. Registers itself as `_GLOBAL_APP` so `response.render()` and friends
   can find the active app.

| Method | Description |
| --- | --- |
| `add_middleware(mw_class)` | Append a middleware class. Instantiated later when `wsgi()` is called. |
| `route(pattern, *, methods=None)` | Convenience for inline routes (typically you use `path()` in a URLconf). |
| `render(template_name, context)` | Render a template through the configured backend. |
| `static_url(path)` | Resolve a static URL (uses `settings.STATIC_URL`). |
| `wsgi()` | Returns a callable with middleware applied. Top-to-bottom in `settings.MIDDLEWARE` is outermost. |
| `__call__(environ, start_response)` | WSGI entry. Catches `Http404`, `Http403`, `Http400` and unhandled exceptions; renders 500 in DEBUG. |

A view may return: a `UResponse`, a `str` (200 text/html), `bytes`, or
any iterable of bytes. Returning anything else raises
`ImproperlyConfigured`.

## Request

### `URequest` `[request.py:6]`

Wraps a WSGI `environ` dict. Header keys normalised to lowercase. Body
parsing is lazy.

| Property | Type | Description |
| --- | --- | --- |
| `method` | `str` | HTTP verb (uppercased). |
| `path` | `str` | `PATH_INFO`. |
| `full_path` | `str` | `path + (?query_string)`. |
| `query_string` | `str` | Raw query. |
| `environ` | `Mapping[str, Any]` | The original environ. |
| `scheme` | `str` | `'http'` or `'https'`. |
| `host` | `str` | `HTTP_HOST` or `SERVER_NAME`. |
| `content_type` | `str` | From `CONTENT_TYPE`. |
| `content_length` | `int` | Parsed `CONTENT_LENGTH`, 0 on error. |
| `headers` | `Dict[str, str]` | Lower-cased headers (lazy). |
| `GET` | `Dict[str, object]` | `parse_qs` result. |
| `form` / `POST` | `Dict[str, object]` | Parsed form (lazy; urlencoded or multipart). |
| `files` | `dict` | Lazy file map (multipart only). |
| `json` | `Any` | Parsed JSON body if `Content-Type: application/json`. |
| `cookies` | `Dict[str, str]` | Parsed `HTTP_COOKIE`. |
| `body` | `bytes` | Raw body. |
| `is_secure` | `bool` | `scheme == 'https'`. |
| `remote_addr` | `str` | `REMOTE_ADDR`. |
| `session` | `Any` | Read/write through `state['session']`. |
| `user` | `Any` | Read/write through `state['user']`. |
| `state` | `Dict[str, Any]` | Free-form middleware scratch space. |

Methods:

| Method | Description |
| --- | --- |
| `get_header(name, default=None)` | Case-insensitive header lookup. |
| `query(key, default=None)` | First value for `?key=value`, else `default`. |

## Response

### `UResponse` `[response.py:17]`

```python
class UResponse:
    status_code: int
    status: str            # '200 OK'
    headers: Dict[str, str]
    body: List[bytes]      # captured chunks
```

Construct with `body`, `status` (int or string), optional `headers` dict
and `content_type`. Strings and bytes are auto-encoded; iterables of
bytes are captured into a list. `content-length` is auto-added.

| Method / property | Description |
| --- | --- |
| `set_header(name, value)` / `delete_header(name)` | Chainable. |
| `__setitem__` / `__getitem__` | Dict-style headers. |
| `__iter__` | Iterate body chunks (WSGI). |
| `__call__(environ, start_response)` | Act as a WSGI app (handy for tests). |
| `content` (property) | Concatenated body. |
| `text` (property) | Decoded `content`. |

### Helper constructors

| Function | Returns | Content-Type |
| --- | --- | --- |
| `text(body, status=200, headers=None)` | `UResponse` | `text/plain; charset=utf-8` |
| `html(body, status=200, headers=None)` | `UResponse` | `text/html; charset=utf-8` |
| `json(data, status=200, headers=None, encoder=None)` | `UResponse` | `application/json; charset=utf-8` |
| `empty(status=204, headers=None)` | `UResponse` | (no body) |
| `redirect(location, status=302, headers=None)` | `UResponse` | sets `Location` header |
| `file(path, status=200, headers=None, as_attachment=False, attachment_name=None)` | `UResponse` streaming the file in 64 KiB chunks; raises `Http404` if missing |
| `error(status, message=None)` | `UResponse` | text/plain; default message picked from exception class |
| `render(request, template_name, context=None, status=200, headers=None)` | `UResponse` | rendered through the project's template backend |

`json(data)` uses a permissive default that JSON-serialises `datetime`
(via `isoformat`) and arbitrary iterables.

## Routing

### `path(pattern, view, name=None)` `[router.py:94]`

Register a single route. Patterns use Django-style converters:

| Converter | Regex | Parser |
| --- | --- | --- |
| `str` (default) | `[^/]+` | `str` |
| `int` | `[0-9]+` | `int` |
| `slug` | `[-a-zA-Z0-9_]+` | `str` |
| `uuid` | `[0-9a-fA-F-]{36}` | `str` |
| `path` | `.+` | `str` |

```python
urlpatterns = [
    path('users/<int:id>', user_view, name='user-detail'),
    path('files/<path:rest>', file_view),
]
```

A leading `/` is added if missing. Trailing `/` is stripped (except the
empty root pattern).

### `include(module, namespace=None)` `[router.py:108]`

Mount a sub-URLconf from another module:

```python
urlpatterns = [
    path('api/v1/', include('myapp.urls')),
]
```

### `URLRouter` `[router.py:122]`

Compiles a flat list of `Route` and `Include` entries into a resolver.

| Method | Description |
| --- | --- |
| `resolve(path) -> (view, kwargs, namespace_info)` | Match `path`. Raises `Http404` if no match. |

Internal cache `_exact_single` provides O(1) lookups for static
patterns; dynamic patterns fall through to `_regex`.

### `clear_url_caches()` `[router.py:218]`

Clear the `Include` import cache. Call after changing `urlpatterns`.

## Exceptions `[exceptions.py]`

| Class | HTTP | Default message |
| --- | --- | --- |
| `UWebError` | 500 | `Internal server error` |
| `Http404` | 404 | `Not found` |
| `Http405` | 405 | `Method not allowed` |
| `Http400` | 400 | `Bad request` |
| `Http403` | 403 | `Forbidden` |
| `Http500` | 500 | `Server error` |
| `ImproperlyConfigured` | 500 | `Improperly configured` |
| `AppRegistryNotReady` | 500 | `Apps are not loaded yet` |

All carry `status_code` and `default_message` class attributes.

## Middleware `[middleware.py]`

| Class | Effect |
| --- | --- |
| `CommonMiddleware` | Validates `Host` header against `ALLOWED_HOSTS`; adds `X-Content-Type-Options: nosniff`. |
| `SessionMiddleware` | Real implementation in `Uui.web.auth.session`; re-exported here. |
| `CSRFMiddleware` | CSRF token enforcement. |
| `GZipMiddleware` | GZip response compression. |

Auth and session middleware are listed in
[`auth/`](../../modules/Uui/web/auth/) and [`auth/session.py`](../../modules/Uui/web/auth/session.py).

## Templates `[templates.py]`

```python
class TemplateBackend: ...         # abstract
class Jinja2Backend(TemplateBackend): ...

DEFAULT_TEMPLATES = [
    {"BACKEND": "Uui.web.templates.Jinja2Backend",
     "DIRS": ["templates"],
     "APP_DIRS": "templates",
     "OPTIONS": {}},
]
```

`Jinja2Backend` uses a single `jinja2.Environment` per project. Templates
are loaded from `DIRS` and (optionally) per-app `templates/` folders.
The render context automatically injects `request` and (if
authenticated) `user`.

## Servers

### `make_server(host, port, settings) -> wsgi.server` `[server.py]`

Builds a `wsgiref.simple_server`-style server.

### `runserver(host, port, settings, quiet=False)` `[server.py]`

Synchronous: blocks until shutdown.

### `serve(host, port, settings, threads=10, quiet=False)` `[server.py]`

Threaded variant.

### HTTP/2 `[server_http2.py]`

WSGI server with `h2` support. Accepts h2c (cleartext) and HTTPS with
ALPN `h2`. Pair with `tls.py` / `tls_pyfallback.py` for self-signed
cert generation.

```python
# Generate a self-signed cert
from modules.Uui.web.tls import openssl_available
from modules.Uui.web.tls_pyfallback import _generate_via_cryptography
if not openssl_available():
    cert, key = _generate_via_cryptography('localhost', 'cert.pem', 'key.pem', 365)
```

## CLI `[cli.py]`

`manage.py`-style entry point:

```bash
python -m Uui.web runserver
python -m Uui.web migrate
python -m Uui.web shell
python -m Uui.web createsuperuser
```

Run with `--help` to see the full subcommand list.

## Default settings (`modules.Uui.web.conf.default_settings`)

```python
DEBUG = False
SECRET_KEY = 'change-me-in-production'
ALLOWED_HOSTS = ['*']
DATABASES = {'default': {'ENGINE': 'Uui.web.orm.backend.sqlite', 'NAME': 'db.sqlite3'}}
INSTALLED_APPS = []
ROOT_URLCONF = 'urls'
WSGI_APPLICATION = 'wsgi.application'
MIDDLEWARE = ['Uui.web.middleware.CommonMiddleware']
TEMPLATES = [{'BACKEND': 'Uui.web.templates.Jinja2Backend', 'DIRS': ['templates'], ...}]
STATIC_URL = '/static/'
STATIC_ROOT = 'staticfiles'
STATICFILES_DIRS = []
SESSION_ENGINE = 'Uui.web.auth.session.DbSessionBackend'
SESSION_COOKIE_NAME = 'uui_sessionid'
SESSION_COOKIE_AGE = 60 * 60 * 24 * 14
AUTH_USER_MODEL = 'auth.User'
CSRF_COOKIE_NAME = 'uui_csrftoken'
CSRF_HEADER_NAME = 'HTTP_X_CSRFTOKEN'
CSRF_COOKIE_SECURE = False
CSRF_TRUSTED_ORIGINS = []
HTTP2_MAX_CONCURRENT_STREAMS = 100
HTTP2_MAX_FRAME_SIZE = 16384
HTTP2_MAX_HEADER_LIST_SIZE = 65536
HTTP2_ENABLE_PUSH = False
SSL_CERTFILE = ''
SSL_KEYFILE = ''
SSL_ALPN_PROTOCOLS = ['h2', 'http/1.1']
LOGGING = {}
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_TZ = True
```

## ORM (`modules.Uui.web.orm`)

```python
from modules.Uui.web.orm import (
    Model, QuerySet,
    Field, AutoField,
    CharField, TextField,
    IntegerField, BigIntegerField, SmallIntegerField,
    FloatField, BooleanField,
    DateField, DateTimeField, ForeignKey,
    CASCADE, SET_NULL, PROTECT,
    configure,
    connection,
    fields, query,
    MigrationEngine, generate_migration, run_migrations,
    SqliteBackend, MysqlBackend, PostgresqlBackend, OracleBackend,
)
```

### `Model`

Django-style declarative base. Subclass and add class attributes for
fields. `Meta.app` names the app for migrations.

```python
class Post(Model):
    title = fields.CharField(max_length=200)
    body = fields.TextField()
    published = fields.BooleanField(default=False)

    class Meta:
        app = 'blog'

Post.objects.filter(published=True).order_by('-id').all()
Post.objects.create(title='Hello', body='World')
```

`objects` returns a `QuerySet` (see below).

### `QuerySet` `[query.py]`

Lazy. Methods:

| Method | Description |
| --- | --- |
| `filter(**lookup)` | Add WHERE clauses. |
| `exclude(**lookup)` | Negate clauses. |
| `order_by(*fields)` | ORDER BY (prefix `-` for DESC). |
| `all()` | Return the whole queryset. |
| `get(**lookup)` | Return one row or raise. |
| `count()` | `SELECT COUNT(*)`. |
| `first()` / `last()` | First/last row. |
| `exists()` | Boolean shortcut. |
| `create(**fields)` | Insert and return the instance. |
| `update(**fields)` | Bulk update. |
| `delete()` | Bulk delete. |
| `__getitem__(slice)` | Pagination. |
| `__iter__` | Materialise rows. |

Lookups supported (from `_LOOKUPS`): `exact`, `iexact`, `contains`,
`icontains`, `gt`, `gte`, `lt`, `lte`, `in`, `startswith`, `endswith`,
`isnull`, `range`.

### `fields`

| Field | Notes |
| --- | --- |
| `Field` | Base. |
| `AutoField` | Auto-increment primary key. |
| `CharField(max_length=None)` | VARCHAR. |
| `TextField()` | TEXT. |
| `IntegerField()` / `BigIntegerField()` / `SmallIntegerField()` | Numeric. |
| `FloatField()` | REAL/DOUBLE. |
| `BooleanField()` | TINYINT/BOOLEAN. |
| `DateField()` / `DateTimeField()` | DATE / TIMESTAMP. |
| `ForeignKey(to, on_delete=CASCADE, related_name=None)` | Many-to-one. |

Constants: `CASCADE`, `SET_NULL`, `PROTECT`.

### Connection management `[connection.py]`

`configure(settings)` reads `settings.DATABASES` and instantiates a
backend per alias. `get_connection(alias='default')` returns the active
backend. Thread-local with simple pooling.

### Backends `[backend/]`

- `base.Backend` (abstract)
- `sqlite.SqliteBackend`
- `mysql.MysqlBackend`
- `postgresql.PostgresqlBackend`
- `oracle.OracleBackend`

### Migrations `[migration.py]`

- `MigrationEngine` — applies ops sequentially.
- `generate_migration(from_state, to_state) -> dict` — diff two model
  states into an op list.
- `run_migrations(app_name=None) -> int` — apply outstanding migrations
  for the given app (or all). Returns the count applied.

Supported ops: `create_table`, `drop_table`, `add_column`, `drop_column`,
`rename_table`.

## Auth (`modules.Uui.web.auth`)

```python
from modules.Uui.web.auth import (
    make_password, check_password, needs_rehash,
    User, AnonymousUser, get_anonymous_user, authenticate, get_user_by_id,
    login_required, permission_required, staff_member_required,
    Session, SessionStore, SessionMiddleware,
)
```

### Password hashing `[password.py]`

| Constant | Value |
| --- | --- |
| `ALGO` | `'pbkdf2_sha256'` |
| `ITERATIONS` | `320_000` |
| `SALT_LEN` | `16` |
| `HASH_LEN` | `32` |

| Function | Description |
| --- | --- |
| `make_password(password, *, iterations=ITERATIONS) -> str` | Returns `pbkdf2_sha256$<iters>$<salt>$<hash>`. |
| `check_password(password, encoded) -> bool` | Constant-time compare. `False` on any parse error. |
| `needs_rehash(encoded) -> bool` | `True` if iteration count is below `ITERATIONS`. |

### Users `[users.py]`

| Class / function | Description |
| --- | --- |
| `AnonymousUser` | Singleton `_ANONYMOUS` exposed via `get_anonymous_user()`. |
| `User(Model)` | Django-style user. |
| `authenticate(request, username, password) -> User` | Verify credentials; returns the user or `AnonymousUser`. |
| `get_user_by_id(uid) -> User \| AnonymousUser` | Fetch by primary key. |

### Decorators `[decorators.py]`

| Decorator | Effect |
| --- | --- |
| `@login_required` | Anonymous GET → 302 to `/login/?next=…`; other methods → 403. |
| `@permission_required('app.perm')` | Parametrized; checks `user.has_perm`. |
| `@staff_member_required` | Requires `user.is_staff`. |

### Sessions `[session.py]`

| Class | Description |
| --- | --- |
| `Session(Model)` | Persisted session row. |
| `SessionStore` | Dict-like API: `__getitem__/__setitem__/__contains__/__delitem__/get/setdefault/pop/keys/values/items/save/flush/clear`. |
| `SessionMiddleware` | WSGI middleware that loads + persists `SessionStore` keyed by cookie. |

## Admin (`modules.Uui.web.admin`)

```python
from modules.Uui.web.admin import (
    site, AdminSite, ModelAdmin,
    AlreadyRegistered, NotRegistered,
)
```

| Symbol | Description |
| --- | --- |
| `site` | Singleton `AdminSite`. |
| `AdminSite.register(model, admin_class=None)` | Register a model. |
| `AdminSite.unregister(model)` | Remove. |
| `AdminSite.get_urls()` | URL patterns for the admin UI. |
| `AdminSite.has_permission(request)` | Permission gate. |
| `ModelAdmin` | Customize `list_display`, `list_filter`, `search_fields`, `list_per_page`, `ordering`, `fields`, `exclude`, `readonly_fields`, `date_hierarchy`, `list_select_related`, `save_on_top`. |
| `views` | Index, app_index, change_list, add_form, change_form, delete. |
| `urls` | `urlpatterns = site.get_urls()`, `app_name = 'admin'`. |

## Testing (`modules.Uui.web.testing`)

```python
from modules.Uui.web.testing import UTestClient, UResponse

client = UTestClient(app)
resp = client.get('/api/items/')
assert resp.status_code == 200
assert resp.json() == [...]
```

| Class / method | Description |
| --- | --- |
| `UTestClient(app)` | In-process WSGI client. |
| `client.get(path, **kw)` | GET. |
| `client.post(path, data=None, **kw)` | POST. |
| `client.put` / `client.patch` / `client.delete` | Other verbs. |
| `client.login(username, password)` | Log in for subsequent requests. |
| `client.logout()` | Clear session. |
| `client.request(method, path, **kw)` | Generic request. |
| `UResponse.status_code` / `.text` / `.json()` / `.content` | Inspection. |