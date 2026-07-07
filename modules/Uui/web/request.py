"""WSGI request wrapper with lazy body parsing."""
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple
from urllib.parse import parse_qs, parse_qsl


class URequest:
    """Wraps a WSGI environ dict and provides ergonomic access to common fields.

    Header keys are normalised to lower case. Body parsing is deferred until
    ``form``, ``files`` or ``json`` is accessed. A mutable ``state`` dict is
    available for middleware to attach arbitrary data (``request.session``,
    ``request.user``, ...).
    """

    __slots__ = (
        '_environ', '_headers', '_form', '_files', '_json', '_body',
        '_path', '_method', '_query', 'state',
    )

    def __init__(self, environ: Mapping[str, Any]) -> None:
        self._environ = environ
        self._headers: Optional[Dict[str, str]] = None
        self._form: Optional[List[Tuple[str, str]]] = None
        self._files = None
        self._json: Any = None
        self._body: Optional[bytes] = None
        self._path: str = environ.get('PATH_INFO', '/')
        self._method: str = environ.get('REQUEST_METHOD', 'GET').upper()
        self._query: Optional[List[Tuple[str, str]]] = None
        self.state: Dict[str, Any] = {}
        if 'uui.user' in environ:
            self.state['user'] = environ['uui.user']
        if 'uui.session' in environ:
            self.state['session'] = environ['uui.session']


    @property
    def method(self) -> str:
        return self._method

    @property
    def path(self) -> str:
        return self._path

    @property
    def full_path(self) -> str:
        qs = self._environ.get('QUERY_STRING', '')
        return self._path + ('?' + qs if qs else '')

    @property
    def query_string(self) -> str:
        return self._environ.get('QUERY_STRING', '')

    @property
    def environ(self) -> Mapping[str, Any]:
        return self._environ

    @property
    def scheme(self) -> str:
        return 'https' if self._environ.get('wsgi.url_scheme') == 'https' else 'http'

    @property
    def host(self) -> str:
        return self._environ.get('HTTP_HOST', self._environ.get('SERVER_NAME', ''))

    @property
    def content_type(self) -> str:
        return self._environ.get('CONTENT_TYPE', '')

    @property
    def content_length(self) -> int:
        try:
            return int(self._environ.get('CONTENT_LENGTH') or 0)
        except (TypeError, ValueError):
            return 0


    @property
    def headers(self) -> Dict[str, str]:
        if self._headers is None:
            self._headers = _parse_headers(self._environ)
        return self._headers

    def get_header(self, name: str, default: Optional[str] = None) -> Optional[str]:
        return self.headers.get(name.lower(), default)


    @property
    def GET(self) -> Dict[str, object]:
        return dict(parse_qs(self._environ.get('QUERY_STRING', ''), keep_blank_values=True))

    def query(self, key: str, default: Optional[str] = None) -> Optional[str]:
        if self._query is None:
            self._query = parse_qsl(self._environ.get('QUERY_STRING', ''), keep_blank_values=True)
        for k, v in self._query:
            if k == key:
                return v
        return default


    @property
    def body(self) -> bytes:
        if self._body is None:
            self._body = _read_body(self._environ)
        return self._body

    @property
    def POST(self) -> Dict[str, object]:
        return self.form

    @property
    def form(self) -> Dict[str, object]:
        if self._form is None:
            self._form = _parse_form(self._environ, self.body, self.content_type)
        return dict(self._form)

    @property
    def json(self) -> Any:
        if self._json is None:
            self._json = _parse_json(self.body, self.content_type)
        return self._json


    @property
    def cookies(self) -> Dict[str, str]:
        return _parse_cookies(self._environ.get('HTTP_COOKIE', ''))


    @property
    def is_secure(self) -> bool:
        return self.scheme == 'https'

    @property
    def remote_addr(self) -> str:
        return self._environ.get('REMOTE_ADDR', '')

    def __repr__(self) -> str:
        return f'<URequest {self._method} {self._path!r}>'


    @property
    def session(self):
        return self.state.get('session')

    @session.setter
    def session(self, value) -> None:
        self.state['session'] = value

    @property
    def user(self):
        return self.state.get('user')

    @user.setter
    def user(self, value) -> None:
        self.state['user'] = value



def _parse_headers(environ: Mapping[str, Any]) -> Dict[str, str]:
    headers: Dict[str, str] = {}
    for key, value in environ.items():
        if not isinstance(value, str):
            continue
        if key.startswith('HTTP_') and len(key) > 5:
            header = key[5:].replace('_', '-').lower()
            headers[header] = value
        elif key in ('CONTENT_TYPE', 'CONTENT_LENGTH'):
            headers[key.replace('_', '-').lower()] = value
    return headers


def _read_body(environ: Mapping[str, Any]) -> bytes:
    try:
        length = int(environ.get('CONTENT_LENGTH') or 0)
    except (TypeError, ValueError):
        length = 0
    if length <= 0:
        return b''
    body = environ.get('wsgi.input')
    if body is None:
        return b''
    try:
        data = body.read(length)
    except Exception:
        return b''
    try:
        body.seek(0)
    except Exception:
        pass
    return data or b''


def _parse_form(environ: Mapping[str, Any], body: bytes, content_type: str) -> List[Tuple[str, str]]:
    if not body:
        return []
    ctype = content_type.split(';', 1)[0].strip().lower()
    if ctype == 'application/x-www-form-urlencoded':
        try:
            text = body.decode('utf-8', 'replace')
        except Exception:
            return []
        return parse_qsl(text, keep_blank_values=True)
    if ctype.startswith('multipart/'):
        return _parse_multipart(environ, body, content_type)
    return []


def _parse_multipart(environ: Mapping[str, Any], body: bytes,
                     content_type: str) -> List[Tuple[str, str]]:
    try:
        from multipart import parse_multipart  # type: ignore
    except ImportError:
        return []
    try:
        fields = parse_multipart(environ, {'CONTENT_LENGTH': str(len(body)),
                                            'CONTENT_TYPE': content_type})
        result: List[Tuple[str, str]] = []
        for key, values in fields.items():
            for v in values:
                if hasattr(v, 'decode'):
                    v = v.decode('utf-8', 'replace')
                result.append((key, v))
        return result
    except Exception:
        return []


def _parse_json(body: bytes, content_type: str) -> Any:
    ctype = content_type.split(';', 1)[0].strip().lower()
    if ctype and ctype != 'application/json':
        return None
    if not body:
        return None
    import json
    try:
        return json.loads(body.decode('utf-8'))
    except Exception:
        return None


def _parse_cookies(cookie_header: str) -> Dict[str, str]:
    cookies: Dict[str, str] = {}
    if not cookie_header:
        return cookies
    for chunk in cookie_header.split(';'):
        chunk = chunk.strip()
        if not chunk or '=' not in chunk:
            continue
        k, _, v = chunk.partition('=')
        cookies[k.strip()] = v.strip()
    return cookies
