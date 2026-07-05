"""Default settings for Uui.web projects."""


DEBUG = False

SECRET_KEY = 'change-me-in-production'

ALLOWED_HOSTS: list = ['*']

# Database (default: sqlite)
DATABASES: dict = {
    'default': {
        'ENGINE': 'Uui.web.orm.backend.sqlite',
        'NAME': 'db.sqlite3',
    },
}

# Apps registered for this project
INSTALLED_APPS: list = []

# Path to the root URLconf module
ROOT_URLCONF = 'urls'

# WSGI application callable
WSGI_APPLICATION = 'wsgi.application'

# Middleware pipeline (top-to-bottom on request, bottom-to-top on response)
MIDDLEWARE: list = [
    'Uui.web.middleware.CommonMiddleware',
]

# Templates (Jinja2 by default)
TEMPLATES: list = [
    {
        'BACKEND': 'Uui.web.templates.Jinja2Backend',
        'DIRS': ['templates'],
        'APP_DIRS': 'templates',
        'OPTIONS': {},
    },
]

# Static files
STATIC_URL = '/static/'
STATIC_ROOT = 'staticfiles'
STATICFILES_DIRS: list = []

# Sessions
SESSION_ENGINE = 'Uui.web.auth.session.DbSessionBackend'
SESSION_COOKIE_NAME = 'uui_sessionid'
SESSION_COOKIE_AGE = 60 * 60 * 24 * 14  # 2 weeks

# Auth
AUTH_USER_MODEL = 'auth.User'

# CSRF
CSRF_COOKIE_NAME = 'uui_csrftoken'
CSRF_HEADER_NAME = 'HTTP_X_CSRFTOKEN'
CSRF_COOKIE_SECURE = False
CSRF_TRUSTED_ORIGINS: list = []

# HTTP/2
HTTP2_MAX_CONCURRENT_STREAMS = 100
HTTP2_MAX_FRAME_SIZE = 16384
HTTP2_MAX_HEADER_LIST_SIZE = 65536
HTTP2_ENABLE_PUSH = False

# TLS
SSL_CERTFILE: str = ''
SSL_KEYFILE: str = ''
SSL_ALPN_PROTOCOLS: list = ['h2', 'http/1.1']

# Logging
LOGGING: dict = {}

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_TZ = True
