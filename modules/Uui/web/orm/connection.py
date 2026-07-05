"""Database connection management — thread-local with simple pooling."""
import importlib
import threading
from typing import Any, Dict

from .backend.base import Backend
from .backend.sqlite import SqliteBackend


_connections: Dict[str, Backend] = {}
_lock = threading.Lock()
_active_alias: str = 'default'


def configure(settings: Any) -> None:
    """Initialise all database backends from ``settings.DATABASES``."""
    databases = getattr(settings, 'DATABASES', {}) or {}
    for alias, cfg in databases.items():
        if alias in _connections:
            continue
        engine = cfg.get('ENGINE', 'Uui.web.orm.backend.sqlite')

        if engine.endswith('sqlite'):
            _connections[alias] = SqliteBackend(alias, cfg)
            continue

        module_path = engine
        try:
            module = importlib.import_module(module_path)
        except ImportError as exc:
            raise ImportError(
                f'Could not import database backend {module_path!r}: {exc}'
            ) from exc

        backend_class = getattr(module, 'Backend', None)
        if backend_class is None:
            for attr in dir(module):
                if attr.endswith('Backend'):
                    backend_class = getattr(module, attr)
                    break

        if backend_class is None:
            raise ImportError(
                f'Database backend module {module_path!r} does not define a Backend class'
            )

        if not isinstance(backend_class, type) or not issubclass(backend_class, Backend):
            raise ImportError(
                f'Database backend class {backend_class.__name__} must inherit from Backend'
            )

        _connections[alias] = backend_class(alias, cfg)


def get_backend(alias: str = 'default') -> Backend:
    return _connections[alias]


def get_connection(alias: str = 'default') -> Any:
    """Return the raw connection (sqlite3.Connection for SQLite)."""
    return get_backend(alias).connection()


def close_all() -> None:
    for backend in _connections.values():
        backend.close()
    _connections.clear()


def using(alias: str):
    """Return a thread-local alias context. Currently a no-op (we use thread-local)."""
    return _ConnectionContext(alias)


class _ConnectionContext:
    def __init__(self, alias: str) -> None:
        self.alias = alias

    def __enter__(self) -> Backend:
        global _active_alias
        self._prev = _active_alias
        _active_alias = self.alias
        return get_backend(self.alias)

    def __exit__(self, exc_type, exc, tb) -> None:
        global _active_alias
        _active_alias = self._prev
