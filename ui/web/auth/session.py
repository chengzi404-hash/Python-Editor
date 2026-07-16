"""Session backends. The default stores sessions in the database."""

import contextlib
import datetime as _dt
import secrets
from typing import Any

from ..orm import Model, fields


class Session(Model):  # type: ignore[misc]
    """Database-backed session record."""

    session_key = fields.CharField(max_length=40, unique=True)
    session_data = fields.TextField()
    expire_at = fields.DateTimeField(null=True)

    class Meta:
        app = "auth"
        table = "auth_session"


class SessionStore:
    """Wraps a session dictionary and persists changes back to the DB.

    The session is loaded lazily on first access. ``save()`` is called on
    request completion by the middleware. ``flush()`` discards the session.
    """

    def __init__(
        self, session_key: str | None = None, age_seconds: int = 60 * 60 * 24 * 14
    ) -> None:
        self._key = session_key
        self._loaded = session_key is None
        self._data: dict[str, Any] = {}
        self._age = age_seconds
        self._modified = False
        if session_key:
            self._load()

    @property
    def session_key(self) -> str | None:
        return self._key

    def _load(self) -> None:
        if not self._key:
            return
        try:
            row = Session.objects.get(session_key=self._key)
        except Exception:
            return
        self._data = _unserialize(row.session_data or "")
        self._loaded = True

    def _ensure_loaded(self) -> None:
        if not self._loaded:
            self._load()

    def __getitem__(self, key: str) -> Any:
        self._ensure_loaded()
        return self._data[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self._ensure_loaded()
        self._data[key] = value
        self._modified = True

    def __delitem__(self, key: str) -> None:
        self._ensure_loaded()
        del self._data[key]
        self._modified = True

    def __contains__(self, key: str) -> bool:
        self._ensure_loaded()
        return key in self._data

    def get(self, key: str, default: Any = None) -> Any:
        self._ensure_loaded()
        return self._data.get(key, default)

    def keys(self):
        self._ensure_loaded()
        return self._data.keys()

    def values(self):
        self._ensure_loaded()
        return self._data.values()

    def items(self):
        self._ensure_loaded()
        return self._data.items()

    def flush(self) -> None:
        self._data = {}
        self._modified = True

    def save(self) -> str:
        if not self._key:
            self._key = secrets.token_urlsafe(32)
            self._modified = True
        expire = _dt.datetime.now() + _dt.timedelta(seconds=self._age)
        payload = _serialize(self._data)
        try:
            existing = Session.objects.get(session_key=self._key)
            existing.session_data = payload
            existing.expire_at = expire
            existing.save()
        except Exception:
            Session.objects.create(
                session_key=self._key,
                session_data=payload,
                expire_at=expire,
            )
        self._modified = False
        return self._key

    def delete(self) -> None:
        if not self._key:
            return
        with contextlib.suppress(Exception):
            Session.objects.filter(session_key=self._key).delete()
        self._key = None
        self._data = {}
        self._modified = False


def _serialize(data: dict[str, Any]) -> str:
    import json

    return json.dumps(data, default=_json_default, ensure_ascii=False)


def _unserialize(text: str) -> dict[str, Any]:
    import json

    try:
        return json.loads(text)
    except Exception:
        return {}


def _json_default(obj: Any) -> Any:
    if hasattr(obj, "isoformat"):
        return obj.isoformat()
    raise TypeError(f"Not JSON serialisable: {type(obj).__name__}")


class SessionMiddleware:
    """WSGI middleware that attaches a :class:`SessionStore` to every request
    as ``request.session``. The session cookie name and age are taken from
    ``settings.SESSION_COOKIE_NAME`` and ``settings.SESSION_COOKIE_AGE``."""

    def __init__(self, app, inner) -> None:
        self.app = app
        self.inner = inner
        self.cookie_name = getattr(app.settings, "SESSION_COOKIE_NAME", "uui_sessionid")
        self.age = getattr(app.settings, "SESSION_COOKIE_AGE", 60 * 60 * 24 * 14)

    def __call__(self, environ, start_response):
        cookies = _parse_cookies(environ.get("HTTP_COOKIE", ""))
        key = cookies.get(self.cookie_name)
        store = SessionStore(session_key=key, age_seconds=self.age)
        environ["uui.session"] = store
        environ["uui._session_old_key"] = key

        def _start(status, headers, exc_info=None):
            if store._modified or (store._key is None and bool(store._data)):
                new_key = store.save()
                old_key = environ.get("uui._session_old_key")
                if new_key != old_key:
                    headers = [
                        *list(headers),
                        (
                            "Set-Cookie",
                            f"{self.cookie_name}={new_key}; Path=/; Max-Age={self.age}; HttpOnly; SameSite=Lax",
                        ),
                    ]
                store._modified = False
            return start_response(status, headers, exc_info)

        return self.inner(environ, _start)


def _parse_cookies(cookie_header: str) -> dict[str, str]:
    cookies: dict[str, str] = {}
    if not cookie_header:
        return cookies
    for chunk in cookie_header.split(";"):
        chunk = chunk.strip()
        if not chunk or "=" not in chunk:
            continue
        k, _, v = chunk.partition("=")
        cookies[k.strip()] = v.strip()
    return cookies
