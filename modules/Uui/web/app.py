"""WSGI application object."""
import importlib
import os
from collections.abc import Callable, Mapping
from typing import Any, Optional

from .exceptions import Http400, Http403, Http404, ImproperlyConfigured
from .request import URequest
from .response import UResponse, error
from .router import URLRouter, clear_url_caches

_SETTINGS_CACHE: dict[str, Any] = {}
_GLOBAL_APP: Optional['UWSGIApp'] = None


def get_settings(module_path: str | None = None) -> Any:
    """Return the project's settings module. ``module_path`` is auto-detected
    from ``UUI_SETTINGS`` env var or ``manage.py``'s import order."""
    if module_path is None:
        module_path = os.environ.get('UUI_SETTINGS')
    if module_path is None:
        raise ImproperlyConfigured(
            'UUI_SETTINGS env var must be set to a settings module (e.g. "config")'
        )
    if module_path in _SETTINGS_CACHE:
        return _SETTINGS_CACHE[module_path]
    try:
        mod = importlib.import_module(module_path)
    except ImportError as exc:
        raise ImproperlyConfigured(f"Could not import settings '{module_path}': {exc}")
    _SETTINGS_CACHE[module_path] = mod
    return mod


def get_application(settings_path: str | None = None) -> 'UWSGIApp':
    """Build a :class:`UWSGIApp` from a settings module path."""
    settings = get_settings(settings_path)
    return UWSGIApp(settings)



class UWSGIApp:
    """A WSGI-compliant application object. Wrap a :class:`UWSGIApp` with
    middleware by calling :meth:`add_middleware` or by listing
    ``MIDDLEWARE`` in the settings module."""

    def __init__(self, settings: Any) -> None:
        self.settings = settings
        self._router: URLRouter | None = None
        self._middleware: list[Callable] = []
        try:
            from .orm import connection as _db
            _db.configure(settings)
        except Exception:
            pass
        self._init_middleware()
        self._init_router()
        global _GLOBAL_APP
        _GLOBAL_APP = self


    def _init_middleware(self) -> None:
        for path in reversed(getattr(self.settings, 'MIDDLEWARE', []) or []):
            self._middleware.append(_import(path))

    def _init_router(self) -> None:
        urlconf = getattr(self.settings, 'ROOT_URLCONF', None)
        if not urlconf:
            raise ImproperlyConfigured('settings.ROOT_URLCONF must be set')
        clear_url_caches()
        module = importlib.import_module(urlconf)
        urlpatterns = getattr(module, 'urlpatterns', None)
        if urlpatterns is None:
            raise ImproperlyConfigured(f"URLconf '{urlconf}' has no urlpatterns")
        self._router = URLRouter(urlpatterns)

    def add_middleware(self, mw_class: Callable) -> None:
        """Append a middleware *class* to the stack. The class is instantiated
        with the inner WSGI app when :meth:`wsgi` is called."""
        self._middleware.append(mw_class)


    def __call__(self, environ: Mapping[str, Any], start_response: Callable) -> list[bytes]:
        try:
            request = URequest(environ)
            return self._handle(request, start_response)
        except Http404 as exc:
            return self._handle_404(exc, start_response)
        except Http403 as exc:
            return _respond(start_response, error(403, str(exc)))
        except Http400 as exc:
            return _respond(start_response, error(400, str(exc)))
        except Exception as exc:
            return self._handle_exception(exc, start_response)

    def _handle(self, request: URequest, start_response: Callable) -> list[bytes]:
        if self._router is None:
            raise ImproperlyConfigured('Router not initialised')
        view, kwargs, ns = self._router.resolve(request.path)
        result = view(request, **kwargs)
        if isinstance(result, UResponse):
            return _respond(start_response, result)
        if isinstance(result, str):
            return _respond(start_response, UResponse(result))
        if isinstance(result, (bytes, bytearray)):
            return _respond(start_response, UResponse(bytes(result)))
        if hasattr(result, '__iter__'):
            return _respond(start_response, UResponse(result))
        raise ImproperlyConfigured(f'View returned unexpected type: {type(result).__name__}')

    def _handle_exception(self, exc: Exception, start_response: Callable) -> list[bytes]:
        if getattr(self.settings, 'DEBUG', False):
            tb = _format_traceback(exc)
            return _respond(start_response, _debug_error(exc, tb))
        return _respond(start_response, error(500, str(exc)))

    def _handle_404(self, exc: Http404, start_response: Callable) -> list[bytes]:
        if getattr(self.settings, 'DEBUG', False):
            return _respond(start_response, error(404, str(exc)))
        try:
            from . import response as _r
            from .app import _GLOBAL_APP
            if _GLOBAL_APP is not None:
                return _respond(start_response,
                                _r.render(_FakeRequest(exc), '404.html', {'path': str(exc)}))
        except Exception:
            pass
        return _respond(start_response, error(404, str(exc)))


    def wsgi(self) -> Callable:
        """Return a fully-wrapped WSGI callable (middleware applied).

        Middleware is composed in the order specified in ``settings.MIDDLEWARE``,
        which is processed top-to-bottom: the first middleware in the list is
        the outermost layer (request flows through it first, response last).
        """
        handler: Callable = self._dispatch
        for mw_class in self._middleware:
            handler = mw_class(self, handler)
        return handler

    def _dispatch(self, environ: Mapping[str, Any], start_response: Callable) -> list[bytes]:
        return self.__call__(environ, start_response)



def _import(path: str) -> Any:
    try:
        module_path, _, attr = path.rpartition('.')
        module = importlib.import_module(module_path)
        return getattr(module, attr)
    except Exception as exc:
        raise ImproperlyConfigured(f"Could not import '{path}': {exc}")


def _respond(start_response: Callable, response: UResponse) -> list[bytes]:
    header_list: list[tuple[str, str]] = []
    for k, v in response.headers.items():
        header_list.append((k, v))
    start_response(response.status, header_list)
    return list(response.body)


def _format_traceback(exc: Exception) -> str:
    import traceback
    return ''.join(traceback.format_exception(type(exc), exc, exc.__traceback__))


def _debug_error(exc: Exception, tb: str) -> UResponse:
    from .response import html
    body = f'''<html><head><meta charset="utf-8"><title>{type(exc).__name__}</title>
<style>
body{{font-family:'SF Mono','Consolas',monospace;background:#1e1e1e;color:#d4d4d4;padding:24px;margin:0}}
h1{{color:#f48771;font-size:20px;margin:0 0 8px}}
pre{{background:#0d0d0d;border:1px solid #3a3a3a;border-radius:6px;padding:16px;
     white-space:pre-wrap;font-size:12px;line-height:1.5}}
.frame{{margin:0;padding:4px 8px}}
.frame.current{{background:#5a1d1d;border-left:3px solid #f48771}}
.file{{color:#9cdcfe}}
.line{{color:#ce9178}}
</style></head><body>
<h1>{type(exc).__name__}: {exc}</h1>
<pre>{_escape_html(tb)}</pre>
</body></html>'''
    return html(body, status=500)


def _escape_html(s: str) -> str:
    return (s.replace('&', '&amp;')
             .replace('<', '&lt;')
             .replace('>', '&gt;'))


class _FakeRequest:
    """Minimal stand-in passed to ``response.render`` for error pages so the
    Jinja2 template can call ``{{ STATIC_URL }}`` etc. without touching the
    WSGI environ."""

    def __init__(self, message: Any = '') -> None:
        from .app import _GLOBAL_APP
        self.settings = _GLOBAL_APP.settings if _GLOBAL_APP is not None else None
        self.message = str(message)
