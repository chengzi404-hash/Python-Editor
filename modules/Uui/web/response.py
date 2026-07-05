"""HTTP response objects and helpers."""
from http.client import responses as _status_text
import json as _json
import mimetypes
import os
from typing import Any, Dict, Iterable, Iterator, List, Optional, Tuple, Union
from .exceptions import ImproperlyConfigured


_STATUS_TEXT = _status_text

# Pre-computed "STATUS_CODE STATUS_TEXT" strings for the common cases
_STATUS_LINE: Dict[int, str] = {
    code: f'{code} {_STATUS_TEXT.get(code, "")}' for code in range(100, 600)
}


class UResponse:
    """Represents an HTTP response.

    The response can be iterated to yield the body chunks in WSGI format. The
    body is captured as a list of ``bytes`` chunks to keep the instance
    inspectable (status_code, headers, content).
    """

    __slots__ = ('status_code', 'status', 'headers', 'body')

    def __init__(self,
                 body: Union[str, bytes, Iterable[bytes], None] = b'',
                 status: Union[int, str] = 200,
                 headers: Optional[Dict[str, str]] = None,
                 content_type: Optional[str] = None) -> None:
        if isinstance(status, int):
            self.status_code = status
            self.status = _STATUS_LINE.get(status, f'{status} {_STATUS_TEXT.get(status, "")}')
        else:
            self.status = status
            try:
                self.status_code = int(status.split(' ', 1)[0])
            except (TypeError, ValueError):
                self.status_code = 0

        hdrs: Dict[str, str] = {}
        if headers:
            for k, v in headers.items():
                hdrs[str(k).lower()] = str(v)
        if content_type is not None and 'content-length' not in hdrs and 'content-type' not in hdrs:
            hdrs['content-type'] = content_type
        self.headers = hdrs

        if body is None:
            self.body = [b'']
        elif isinstance(body, str):
            self.body = [body.encode('utf-8')]
        elif isinstance(body, (bytes, bytearray)):
            self.body = [bytes(body)]
        elif isinstance(body, Iterable):
            chunks: List[bytes] = []
            for chunk in body:
                if isinstance(chunk, str):
                    chunks.append(chunk.encode('utf-8'))
                else:
                    chunks.append(bytes(chunk))
            self.body = chunks
        else:
            self.body = [b'']

        if 'content-length' not in hdrs:
            hdrs['content-length'] = str(sum(len(c) for c in self.body))

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def set_header(self, name: str, value: str) -> 'UResponse':
        self.headers[name.lower()] = str(value)
        return self

    def delete_header(self, name: str) -> 'UResponse':
        self.headers.pop(name.lower(), None)
        return self

    def __setitem__(self, key: str, value: str) -> None:
        self.headers[key.lower()] = str(value)

    def __getitem__(self, key: str) -> str:
        return self.headers[key.lower()]

    def __iter__(self) -> Iterator[bytes]:
        return iter(self.body)

    # ------------------------------------------------------------------
    # WSGI
    # ------------------------------------------------------------------

    def __call__(self, environ: Dict[str, Any], start_response) -> Iterable[bytes]:
        header_list: List[Tuple[str, str]] = []
        for k, v in self.headers.items():
            header_list.append((k, v))
        start_response(self.status, header_list)
        return list(self.body)

    @property
    def content(self) -> bytes:
        return b''.join(self.body)

    @property
    def text(self) -> str:
        return self.content.decode('utf-8', 'replace')

    def __repr__(self) -> str:
        return f'<UResponse status={self.status_code!r} body={len(self.content)} bytes>'


# ---------------------------------------------------------------------------
# Constructors
# ---------------------------------------------------------------------------

def _new(body: Union[str, bytes],
         status: int = 200,
         content_type: str = 'text/plain; charset=utf-8',
         headers: Optional[Dict[str, str]] = None) -> UResponse:
    return UResponse(body=body, status=status, headers=headers, content_type=content_type)


def text(content: str, status: int = 200, headers: Optional[Dict[str, str]] = None) -> UResponse:
    return _new(content, status=status,
                content_type='text/plain; charset=utf-8', headers=headers)


def html(content: str, status: int = 200, headers: Optional[Dict[str, str]] = None) -> UResponse:
    return _new(content, status=status,
                content_type='text/html; charset=utf-8', headers=headers)


def json(data: Any,
         status: int = 200,
         headers: Optional[Dict[str, str]] = None,
         encoder: Any = None) -> UResponse:
    if encoder is not None:
        body = encoder.encode(data)
    else:
        body = _json.dumps(data, ensure_ascii=False, default=_json_default)
    if isinstance(body, str):
        body = body.encode('utf-8')
    return UResponse(body=body, status=status, headers=headers,
                     content_type='application/json; charset=utf-8')


def empty(status: int = 204, headers: Optional[Dict[str, str]] = None) -> UResponse:
    return UResponse(body=b'', status=status, headers=headers)


def redirect(location: str, status: int = 302, headers: Optional[Dict[str, str]] = None) -> UResponse:
    hdrs = {'location': location}
    if headers:
        hdrs.update({k.lower(): v for k, v in headers.items()})
    return UResponse(body=b'', status=status, headers=hdrs)


def file(path: str,
         status: int = 200,
         headers: Optional[Dict[str, str]] = None,
         as_attachment: bool = False,
         attachment_name: Optional[str] = None) -> UResponse:
    if not os.path.isfile(path):
        from .exceptions import Http404
        raise Http404(f'No such file: {path}')
    ctype, _ = mimetypes.guess_type(path)
    ctype = ctype or 'application/octet-stream'

    def _iter_file() -> Iterator[bytes]:
        with open(path, 'rb') as fh:
            while True:
                chunk = fh.read(64 * 1024)
                if not chunk:
                    break
                yield chunk

    hdrs = dict(headers or {})
    hdrs.setdefault('content-type', ctype)
    if as_attachment:
        name = attachment_name or os.path.basename(path)
        hdrs.setdefault('content-disposition', f'attachment; filename="{name}"')
    return UResponse(body=_iter_file(), status=status, headers=hdrs)


def error(status: int, message: Optional[str] = None) -> UResponse:
    from .exceptions import UWebError
    if message is None:
        message = UWebError.default_message
        for cls in UWebError.__subclasses__():
            if cls.status_code == status:
                message = cls.default_message
                break
    body = f'{status} {message}\n'.encode('utf-8')
    return UResponse(body=body, status=status,
                     content_type='text/plain; charset=utf-8')


def _json_default(obj: Any) -> Any:
    if hasattr(obj, 'isoformat'):
        return obj.isoformat()
    if hasattr(obj, '__iter__'):
        return list(obj)
    raise TypeError(f'Object of type {type(obj).__name__} is not JSON serializable')


def render(request: Any, template_name: str, context: Optional[Dict[str, Any]] = None,
           status: int = 200, headers: Optional[Dict[str, str]] = None) -> UResponse:
    """Render a template through the project's template backend. The
    ``request`` must carry a ``settings`` attribute (any object exposing
    ``TEMPLATES``). The chosen backend is cached so subsequent renders in
    the same request avoid re-importing jinja2."""
    settings = getattr(request, 'settings', None)
    if settings is None:
        settings = _settings_from_request()
    backend = _get_template_backend(settings)
    if context is None:
        context = {}
    ctx = dict(context)
    if 'request' not in ctx:
        ctx['request'] = request
    if 'user' not in ctx:
        user = getattr(request, 'user', None)
        if user is not None and getattr(user, 'is_authenticated', False):
            ctx['user'] = user
    body = backend.render(template_name, ctx)
    return _new(body, status=status,
                content_type='text/html; charset=utf-8', headers=headers)


def _settings_from_request() -> Any:
    from .app import _GLOBAL_APP
    if _GLOBAL_APP is not None:
        return _GLOBAL_APP.settings
    raise ImproperlyConfigured(
        'render() needs a UWSGIApp context. Set Uui.web.app._GLOBAL_APP or pass request.settings.'
    )


def _get_template_backend(settings: Any) -> Any:
    import importlib
    from . import templates as _tpl
    backends = getattr(settings, 'TEMPLATES', None) or _tpl.DEFAULT_TEMPLATES
    cfg = backends[0] if backends else None
    if cfg is None:
        raise ImproperlyConfigured('No TEMPLATES configured')
    backend_path = cfg.get('BACKEND', 'Uui.web.templates.Jinja2Backend')
    if backend_path not in _tpl._BACKEND_CACHE:
        mod_path, _, attr = backend_path.rpartition('.')
        mod = importlib.import_module(mod_path)
        cls = getattr(mod, attr)
        _tpl._BACKEND_CACHE[backend_path] = cls(cfg, settings)
    return _tpl._BACKEND_CACHE[backend_path]
