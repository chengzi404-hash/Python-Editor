# `modules/Uui/web/conf/default_settings.py`

源文件路径：`modules/Uui/web/conf/default_settings.py`

Uui.web 项目的默认 settings 集合（被 `config.py` 用 `from Uui.web.conf.default_settings import *` 加载）。

## 默认值

- `DEBUG = False`
- `SECRET_KEY = 'change-me-in-production'`
- `ALLOWED_HOSTS = ['*']`
- `DATABASES` — `default` 引擎 `Uui.web.orm.backend.sqlite`，DB 名 `db.sqlite3`。
- `INSTALLED_APPS = []`
- `ROOT_URLCONF = 'urls'`
- `WSGI_APPLICATION = 'wsgi.application'`
- `MIDDLEWARE = ['Uui.web.middleware.CommonMiddleware']`
- `TEMPLATES` — 默认 Jinja2 后端，DIRS=`['templates']`，APP_DIRS=`'templates'`。
- `STATIC_URL = '/static/'`、`STATIC_ROOT = 'staticfiles'`、`STATICFILES_DIRS = []`
- `SESSION_ENGINE = 'Uui.web.auth.session.DbSessionBackend'`、`SESSION_COOKIE_NAME = 'uui_sessionid'`、`SESSION_COOKIE_AGE = 14天`
- `AUTH_USER_MODEL = 'auth.User'`
- `CSRF_COOKIE_NAME = 'uui_csrftoken'`、`CSRF_HEADER_NAME = 'HTTP_X_CSRFTOKEN'`、`CSRF_COOKIE_SECURE = False`、`CSRF_TRUSTED_ORIGINS = []`
- HTTP/2：`HTTP2_MAX_CONCURRENT_STREAMS=100` / `HTTP2_MAX_FRAME_SIZE=16384` / `HTTP2_MAX_HEADER_LIST_SIZE=65536` / `HTTP2_ENABLE_PUSH=False`
- TLS：`SSL_CERTFILE=''` / `SSL_KEYFILE=''` / `SSL_ALPN_PROTOCOLS=['h2', 'http/1.1']`
- `LOGGING = {}`
- `LANGUAGE_CODE = 'en-us'`、`TIME_ZONE = 'UTC'`、`USE_TZ = True`