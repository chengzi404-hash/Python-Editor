"""In-process WSGI test client — similar to Django's test client.

Usage::

    from Uui.web.testing import UTestClient

    def test_home():
        c = UTestClient()
        r = c.get('/')
        assert r.status_code == 200
        assert 'Hello' in r.text

    def test_login():
        c = UTestClient()
        r = c.login(username='alice', password='secret')
        assert r.status_code == 302
        r = c.get('/dashboard/')
        assert r.status_code == 200
"""

import contextlib
import json as _json
from collections.abc import Mapping
from http.cookies import SimpleCookie
from typing import Any
from urllib.parse import urlencode

from ..app import get_application


class UResponse:
    """Lightweight response wrapper returned by :class:`UTestClient`."""

    def __init__(
        self,
        status_code: int,
        headers: list[tuple[str, str]],
        body: bytes,
        context: dict[str, Any] | None = None,
    ) -> None:
        self.status_code = status_code
        self.headers = dict(headers)
        self.body = body
        self.text = body.decode("utf-8", "replace") if body else ""
        self.context = context or {}

    @property
    def json(self) -> Any:
        return _json.loads(self.text) if self.text else None

    def __repr__(self) -> str:
        return f"<UResponse status={self.status_code} body={len(self.body)} bytes>"


class UTestClient:
    """A test client that calls the WSGI app directly without sockets.

    The client keeps a persistent cookie jar between requests so login
    state carries over.
    """

    def __init__(self, wsgi_app: Any | None = None, settings: str | None = None) -> None:
        if wsgi_app is None:
            app = get_application(settings)
            wsgi_app = app.wsgi()
        self.wsgi_app = wsgi_app
        self.cookies: dict[str, str] = {}
        self.defaults: dict[str, str] = {}

    def get(self, path: str, **kwargs) -> "UResponse":
        return self._request("GET", path, **kwargs)

    def post(
        self, path: str, data: Any | None = None, json: Any | None = None, **kwargs
    ) -> "UResponse":
        if json is not None:
            kwargs["data"] = _json.dumps(json)
            kwargs.setdefault("content_type", "application/json")
        elif data is not None:
            if isinstance(data, Mapping):
                kwargs["data"] = urlencode(list(self._flatten(data)))
                kwargs.setdefault("content_type", "application/x-www-form-urlencoded")
            else:
                kwargs["data"] = data
        return self._request("POST", path, **kwargs)

    def put(self, path: str, **kwargs) -> "UResponse":
        return self._request("PUT", path, **kwargs)

    def patch(self, path: str, **kwargs) -> "UResponse":
        return self._request("PATCH", path, **kwargs)

    def delete(self, path: str, **kwargs) -> "UResponse":
        return self._request("DELETE", path, **kwargs)

    def head(self, path: str, **kwargs) -> "UResponse":
        return self._request("HEAD", path, **kwargs)

    def options(self, path: str, **kwargs) -> "UResponse":
        return self._request("OPTIONS", path, **kwargs)

    def login(self, username: str, password: str, login_url: str = "/login/") -> "UResponse":
        """POST the login form with the given credentials. Returns the
        response from the server. The session cookie is stored automatically
        on success."""
        return self.post(login_url, data={"username": username, "password": password})

    def logout(self) -> None:
        """Forget the current session cookie."""
        self.cookies.clear()

    def set_cookie(self, name: str, value: str) -> None:
        self.cookies[name] = value

    def _request(
        self,
        method: str,
        path: str,
        *,
        data: Any | None = None,
        params: Mapping[str, str] | None = None,
        headers: Mapping[str, str] | None = None,
        content_type: str | None = None,
    ) -> "UResponse":
        environ = self._build_environ(
            method, path, data=data, params=params, headers=headers, content_type=content_type
        )
        captured: dict[str, Any] = {"status": None, "headers": [], "body": []}

        def start_response(status, response_headers, exc_info=None):
            captured["status"] = status
            captured["headers"] = list(response_headers)
            return lambda data: captured["body"].append(data)

        body_iter = self.wsgi_app(environ, start_response)
        if body_iter is not None:
            try:
                for chunk in body_iter:
                    captured["body"].append(chunk)
            finally:
                if hasattr(body_iter, "close"):
                    with contextlib.suppress(Exception):
                        body_iter.close()
        body = b"".join(captured["body"])
        status = captured["status"] or "500 Internal Server Error"
        try:
            code = int(status.split(" ", 1)[0])
        except (TypeError, ValueError):
            code = 500
        response = UResponse(code, captured["headers"], body)
        self._harvest_cookies(captured["headers"])
        return response

    def _build_environ(
        self,
        method: str,
        path: str,
        *,
        data: Any,
        params: Mapping[str, str] | None,
        headers: Mapping[str, str] | None,
        content_type: str | None,
    ) -> dict[str, Any]:
        if "?" in path:
            base, _, qs = path.partition("?")
        else:
            base, qs = path, ""
        if params:
            extra = urlencode(list(params.items()))
            qs = (qs + "&" + extra) if qs else extra
        if not base.startswith("/"):
            base = "/" + base

        body_bytes = b""
        if data is None:
            pass
        elif isinstance(data, (bytes, bytearray)):
            body_bytes = bytes(data)
        elif isinstance(data, str):
            body_bytes = data.encode("utf-8")
        else:
            body_bytes = str(data).encode("utf-8")

        environ: dict[str, Any] = {
            "REQUEST_METHOD": method.upper(),
            "SCRIPT_NAME": "",
            "PATH_INFO": base,
            "QUERY_STRING": qs,
            "CONTENT_TYPE": content_type or "",
            "CONTENT_LENGTH": str(len(body_bytes)),
            "SERVER_NAME": "testserver",
            "SERVER_PORT": "80",
            "SERVER_PROTOCOL": "HTTP/1.1",
            "wsgi.url_scheme": "http",
            "wsgi.input": _FakeInput(body_bytes),
            "wsgi.errors": _stderr(),
            "wsgi.multithread": True,
            "wsgi.multiprocess": False,
            "wsgi.run_once": False,
            "wsgi.version": (1, 0),
            "HTTP_HOST": "testserver",
        }
        if self.cookies:
            environ["HTTP_COOKIE"] = "; ".join(f"{k}={v}" for k, v in self.cookies.items())
        if headers:
            for k, v in headers.items():
                key = k.upper().replace("-", "_")
                if key in ("CONTENT_TYPE", "CONTENT_LENGTH"):
                    environ[key] = v
                else:
                    environ[f"HTTP_{key}"] = v
        return environ

    def _harvest_cookies(self, headers: list[tuple[str, str]]) -> None:
        for k, v in headers:
            if k.lower() == "set-cookie":
                cookie = SimpleCookie()
                try:
                    cookie.load(v)
                except Exception:
                    continue
                for name, morsel in cookie.items():
                    if (
                        morsel["max-age"] == "0"
                        or morsel["expires"] == "Thu, 01 Jan 1970 00:00:00 GMT"
                    ):
                        self.cookies.pop(name, None)
                    else:
                        self.cookies[name] = morsel.value

    @staticmethod
    def _flatten(d: Mapping[str, Any], prefix: str = "") -> list[tuple[str, str]]:
        items: list[tuple[str, str]] = []
        for k, v in d.items():
            key = f"{prefix}{k}" if not prefix else f"{prefix}[{k}]"
            if isinstance(v, Mapping):
                items.extend(UTestClient._flatten(v, key))
            elif isinstance(v, (list, tuple)):
                for i, item in enumerate(v):
                    items.extend(UTestClient._flatten({f"{key}[{i}]": item}))
            else:
                items.append((key, "" if v is None else str(v)))
        return items


class _FakeInput:
    """File-like object that yields a fixed byte buffer and supports ``len()``."""

    def __init__(self, data: bytes) -> None:
        self._data = data
        self._pos = 0

    def read(self, n: int = -1) -> bytes:
        if n < 0 or n > len(self._data) - self._pos:
            n = len(self._data) - self._pos
        chunk = self._data[self._pos : self._pos + n]
        self._pos += n
        return chunk

    def readline(self) -> bytes:
        idx = self._data.find(b"\n", self._pos)
        if idx < 0:
            chunk = self._data[self._pos :]
            self._pos = len(self._data)
            return chunk
        chunk = self._data[self._pos : idx + 1]
        self._pos = idx + 1
        return chunk

    def __iter__(self):
        return iter([self.read()])


def _stderr():
    import sys

    return sys.stderr
