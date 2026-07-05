"""Built-in middleware for Uui.web.

Each middleware class has signature ``__init__(app, inner) -> wsgi_callable``
where ``app`` is the :class:`UWSGIApp` (for accessing settings) and ``inner``
is the next WSGI callable in the chain. The ``__call__`` method is the
WSGI entry point.
"""
import os
from typing import Any, Dict

from .request import URequest
from .response import UResponse, error as error_response


class CommonMiddleware:
    """Set common headers and reject requests with bad Host header."""

    def __init__(self, app, inner) -> None:
        self.app = app
        self.inner = inner

    def __call__(self, environ, start_response):
        host = environ.get('HTTP_HOST', '')
        allowed = getattr(self.app.settings, 'ALLOWED_HOSTS', ['*']) or ['*']
        if allowed and allowed != ['*'] and '*' not in allowed:
            allowed_lower = {h.lower() for h in allowed}
            bare = host.split(':', 1)[0].lower()
            if bare and bare not in allowed_lower:
                resp = error_response(400, f'Invalid Host header: {host!r}')
                return resp(environ, start_response)

        def _start(status, headers, exc_info=None):
            new_headers = []
            seen = set()
            for k, v in headers:
                kl = k.lower()
                if kl == 'x-content-type-options':
                    seen.add(kl)
                new_headers.append((k, v))
            if 'x-content-type-options' not in seen:
                new_headers.append(('X-Content-Type-Options', 'nosniff'))
            return start_response(status, new_headers, exc_info)

        return self.inner(environ, _start)


class SessionMiddleware:
    """Stub kept for backwards compatibility. The real implementation lives
    in :class:`Uui.web.auth.session.SessionMiddleware`."""

    def __init__(self, app, inner) -> None:
        self.app = app
        self.inner = inner

    def __call__(self, environ, start_response):
        return self.inner(environ, start_response)


class AuthenticationMiddleware:
    """Resolves the request's user from the session key. Must come after
    :class:`Uui.web.auth.session.SessionMiddleware` so that ``uui.session``
    is set in environ. Attaches the user to environ as ``uui.user``; the
    :class:`URequest` constructor picks it up automatically."""

    def __init__(self, app, inner) -> None:
        self.app = app
        self.inner = inner

    def __call__(self, environ, start_response):
        from .auth.users import get_user_by_id, get_anonymous_user
        session = environ.get('uui.session')
        user = get_anonymous_user()
        if session is not None:
            uid = session.get('_user_id')
            if uid:
                found = get_user_by_id(int(uid))
                if found is not None and found.is_active:
                    user = found
        environ['uui.user'] = user
        return self.inner(environ, start_response)


class CsrfViewMiddleware:
    """Validate CSRF token on unsafe methods (POST, PUT, PATCH, DELETE)."""

    def __init__(self, app, inner) -> None:
        self.app = app
        self.inner = inner
        self.cookie_name = getattr(app.settings, 'CSRF_COOKIE_NAME', 'uui_csrftoken')
        self.header_name = getattr(app.settings, 'CSRF_HEADER_NAME', 'HTTP_X_CSRFTOKEN')

    def __call__(self, environ, start_response):
        method = environ.get('REQUEST_METHOD', 'GET').upper()
        if method in ('POST', 'PUT', 'PATCH', 'DELETE'):
            cookies = _cookies(environ.get('HTTP_COOKIE', ''))
            header_token = environ.get(self.header_name, '')
            cookie_token = cookies.get(self.cookie_name, '')
            if not cookie_token or not header_token or cookie_token != header_token:
                resp = error_response(403, 'CSRF verification failed.')
                return resp(environ, start_response)
        return self.inner(environ, start_response)


class StaticMiddleware:
    """Serve files under ``STATIC_URL`` directly from ``STATIC_ROOT`` and
    ``STATICFILES_DIRS``. Skipped if the path doesn't exist or the request
    method is not GET/HEAD."""

    def __init__(self, app, inner) -> None:
        self.app = app
        self.inner = inner
        self.url = getattr(app.settings, 'STATIC_URL', '/static/').rstrip('/')
        self.root = getattr(app.settings, 'STATIC_ROOT', 'staticfiles')
        self.dirs = list(getattr(app.settings, 'STATICFILES_DIRS', []) or [])

    def __call__(self, environ, start_response):
        method = environ.get('REQUEST_METHOD', 'GET').upper()
        if method in ('GET', 'HEAD'):
            path = environ.get('PATH_INFO', '')
            prefix = self.url + '/'
            if path.startswith(prefix):
                rel = path[len(prefix):]
                if rel and '..' not in rel.split('/'):
                    from .response import file as file_resp, error as err_resp
                    tried = []
                    for base in [self.root, *self.dirs]:
                        full = os.path.join(base, rel)
                        tried.append(full)
                        if os.path.isfile(full):
                            resp = file_resp(full)
                            return resp(environ, start_response)
                    resp = err_resp(404)
                    return resp(environ, start_response)
        return self.inner(environ, start_response)


def _cookies(cookie_header: str) -> dict:
    cookies: dict = {}
    for chunk in cookie_header.split(';'):
        chunk = chunk.strip()
        if not chunk or '=' not in chunk:
            continue
        k, _, v = chunk.partition('=')
        cookies[k.strip()] = v.strip()
    return cookies
