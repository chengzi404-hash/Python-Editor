"""Default settings for Uui.web projects."""

DEBUG = False

SECRET_KEY = "change-me-in-production"

ALLOWED_HOSTS: list = ["*"]

DATABASES: dict = {
    "default": {
        "ENGINE": "Uui.web.orm.backend.sqlite",
        "NAME": "db.sqlite3",
    },
}

INSTALLED_APPS: list = []

ROOT_URLCONF = "urls"

WSGI_APPLICATION = "wsgi.application"

MIDDLEWARE: list = [
    "Uui.web.middleware.CommonMiddleware",
]

TEMPLATES: list = [
    {
        "BACKEND": "Uui.web.templates.Jinja2Backend",
        "DIRS": ["templates"],
        "APP_DIRS": "templates",
        "OPTIONS": {},
    },
]

STATIC_URL = "/static/"
STATIC_ROOT = "staticfiles"
STATICFILES_DIRS: list = []

SESSION_ENGINE = "Uui.web.auth.session.DbSessionBackend"
SESSION_COOKIE_NAME = "uui_sessionid"
SESSION_COOKIE_AGE = 60 * 60 * 24 * 14  # 2 weeks

AUTH_USER_MODEL = "auth.User"

CSRF_COOKIE_NAME = "uui_csrftoken"
CSRF_HEADER_NAME = "HTTP_X_CSRFTOKEN"
CSRF_COOKIE_SECURE = False
CSRF_TRUSTED_ORIGINS: list = []

HTTP2_MAX_CONCURRENT_STREAMS = 100
HTTP2_MAX_FRAME_SIZE = 16384
HTTP2_MAX_HEADER_LIST_SIZE = 65536
HTTP2_ENABLE_PUSH = False

SSL_CERTFILE: str = ""
SSL_KEYFILE: str = ""
SSL_ALPN_PROTOCOLS: list = ["h2", "http/1.1"]

LOGGING: dict = {}

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_TZ = True
