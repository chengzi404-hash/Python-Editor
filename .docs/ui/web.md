# `ui.web`

**Source**: [`ui/web/`](../../ui/web/) — full reference in
[`ui/web/README.md`](../../ui/web/README.md) (Chinese).

> Minimalist Django-style WSGI framework, packaged inside the editor so
> editor extensions can ship as web apps.

The Python Editor does **not** import `ui.web` at startup. The package
is exposed as a public API for plugin authors and for ad-hoc use via
`python -m ui.web`.

## Public API

```python
from ui.web import (
    UWSGIApp, get_application, get_settings,
    URequest, UResponse,
    text, html, json, redirect, file, error, empty,
    URLRouter, path, include, clear_url_caches,
)
from ui.web import (
    UWebError, Http400Error, Http403Error, Http404Error,
    Http405Error, Http500Error, ImproperlyConfiguredError,
)
```

| Symbol | Description |
| --- | --- |
| `UWSGIApp` | The WSGI application object. |
| `get_application()` | Process-wide app accessor. |
| `get_settings()` | Lazy settings accessor (reads `ui/web/conf/default_settings.py`). |
| `URequest` | Request wrapper. |
| `UResponse` | Response object. |
| `text`, `html`, `json`, `redirect`, `file`, `error`, `empty` | Response factory helpers. |
| `URLRouter` | Low-level URL router. |
| `path`, `include` | URL routing helpers (Django-style). |
| `clear_url_caches` | Reset the routing cache (used in tests). |

## Features

- **WSGI-first** with a thin ASGI adapter
- **No web-framework dependency** — only `regex` (faster `re`) and
  `jinja2` (templates); production deploys can also use `waitress`
- **Built-in ORM** with SQLite / MySQL / PostgreSQL / Oracle backends
- **Declarative models** + Django-style `QuerySet`
- **JSON-format migrations** + automatic generation
- **Built-in Auth** (pbkdf2 password hashing, sessions, decorators)
- **Built-in Admin UI** (auto-CRUD over registered models)
- **In-process test client** (`UTestClient`, Django-style)

## Running

```bash
python -m ui.web new mysite
python -m ui.web runserver mysite
```

Or programmatically:

```python
from ui.web import UWSGIApp, path, text

def hello(request):
    return text("Hello, world!")

app = UWSGIApp(routes=[path("", hello)])
```

## Layout

```
ui/web/
├── __init__.py
├── app.py            — UWSGIApp
├── cli.py            — `python -m ui.web` commands
├── conf/             — default settings module
├── request.py
├── response.py
├── router.py
├── middleware.py
├── exceptions.py
├── templates.py
├── server.py         — WSGI server
├── server_http2.py   — HTTP/2 server (experimental)
├── testing/          — in-process test client
├── auth/             — sessions, users, password hashing, decorators
├── admin/            — admin UI
└── orm/              — Django-style ORM with multi-backend support
```

For the full module-by-module reference (signatures, options, examples)
read [`ui/web/README.md`](../../ui/web/README.md).