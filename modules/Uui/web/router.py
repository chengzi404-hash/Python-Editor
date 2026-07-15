"""URL routing with regex-based path matching and path converters."""
from collections.abc import Callable
from typing import Any

from .exceptions import Http404, ImproperlyConfigured

PathConverter = tuple[str, Callable[[str], Any]]

CONVERTERS: dict[str, PathConverter] = {
    'str': (r'[^/]+', str),
    'int': (r'[0-9]+', int),
    'slug': (r'[-a-zA-Z0-9_]+', str),
    'uuid': (r'[0-9a-fA-F-]{36}', str),
    'path': (r'.+', str),
}

DEFAULT_CONVERTER = CONVERTERS['str']

try:
    import regex as _regex_lib
except ImportError:  # fall back to stdlib re
    import re as _regex_lib  # type: ignore


def _compile_pattern(pattern: str) -> tuple[Any, list[str], dict[str, Callable[[str], Any]]]:
    """Translate Django-style ``<int:id>`` patterns into a regex."""
    parts: list[str] = []
    param_names: list[str] = []
    converters: dict[str, Callable[[str], Any]] = {}
    i = 0
    escape_set = r'.+*?^$()[]{}|\'\\'
    while i < len(pattern):
        ch = pattern[i]
        if ch == '<':
            end = pattern.find('>', i)
            if end == -1:
                raise ImproperlyConfigured(f"Unterminated converter in {pattern!r}")
            inner = pattern[i + 1:end]
            if ':' in inner:
                cname, pname = inner.split(':', 1)
            else:
                cname, pname = 'str', inner
            if cname not in CONVERTERS:
                raise ImproperlyConfigured(f"Unknown converter {cname!r}")
            regex_part, parser = CONVERTERS[cname]
            parts.append(f'(?P<{pname}>{regex_part})')
            param_names.append(pname)
            converters[pname] = parser
            i = end + 1
        else:
            parts.append(_regex_lib.escape(ch) if ch in escape_set else ch)
            i += 1
    full = '^' + ''.join(parts) + '$'
    return _regex_lib.compile(full), param_names, converters



class Route:
    """A single URL pattern. Created by :func:`path` and :func:`include`."""

    __slots__ = ('_compiled', '_converters', '_params', 'name', 'pattern', 'view')

    def __init__(self, pattern: str, view: Callable, name: str | None = None) -> None:
        self.pattern = pattern
        self.view = view
        self.name = name
        if pattern == '':
            self._compiled = None
            self._params = []
            self._converters = {}
        else:
            self._compiled, self._params, self._converters = _compile_pattern(pattern)

    def match(self, path: str) -> dict[str, Any] | None:
        if self._compiled is None:
            return {} if path == '' else None
        m = self._compiled.match(path)
        if m is None:
            return None
        result: dict[str, Any] = {}
        for name, value in m.groupdict().items():
            if value is None:
                continue
            parser = self._converters.get(name, str)
            try:
                result[name] = parser(value)
            except Exception:
                result[name] = value
        return result

    def __repr__(self) -> str:
        return f'<Route {self.pattern!r} -> {getattr(self.view, "__name__", self.view)!r}>'


def path(pattern: str, view: Callable, name: str | None = None):
    """Register a URL pattern. ``view`` is either a callable or the result
    of :func:`include`. The returned object is a :class:`Route` (for a
    callable) or an :class:`Include` (for a sub-URLconf) with a ``_prefix``
    attribute set so the parent router can mount it correctly."""
    if not pattern.startswith('/'):
        pattern = '/' + pattern
    pattern = pattern.rstrip('/') or '/'
    if isinstance(view, Include):
        view._prefix = pattern
        return view
    return Route(pattern, view, name)


def include(module: str, namespace: str | None = None) -> 'Include':
    """Mount a sub-URLconf. ``module`` is a dotted path to a module exposing
    a top-level ``urlpatterns`` (and optionally ``app_name``)."""
    return Include(module, namespace)


class Include:
    def __init__(self, module: str, namespace: str | None = None) -> None:
        self.module = module
        self.namespace = namespace
        self._prefix: str = ''



class URLRouter:
    """Compiles a list of routes and sub-includes into a single resolver."""

    def __init__(self, routes: list[Any], prefix: str = '', namespace: str | None = None) -> None:
        self.prefix = prefix.rstrip('/')
        self.namespace = namespace
        self._exact: dict[str, list[Route]] = {}
        self._exact_single: dict[str, Route] = {}
        self._regex: list[Route] = []
        self._include_routes: list[tuple[str, URLRouter]] = []
        for r in routes:
            self._add(r)

    def _add(self, r: Any) -> None:
        if isinstance(r, Include):
            sub_prefix = r._prefix or ''
            full_prefix = (self.prefix + sub_prefix) if self.prefix else sub_prefix
            full_prefix = full_prefix.replace('//', '/') or '/'
            sub = _load_include(r, prefix=full_prefix, namespace=r.namespace or self.namespace)
            self._include_routes.append((r.module, sub))
            return
        if not isinstance(r, Route):
            raise ImproperlyConfigured(f'urlconf item must be Route or Include, got {type(r).__name__}')
        compiled, params, converters = _compile_pattern(r.pattern)
        r._compiled = compiled
        r._params = params
        r._converters = converters
        if not params:
            self._exact.setdefault(r.pattern, []).append(r)
            self._exact_single.setdefault(r.pattern, r)
        else:
            self._regex.append(r)

    def resolve(self, path: str) -> tuple[Callable, dict[str, Any], dict[str, Any]]:
        """Return (view, kwargs, namespace_info) for the given path or raise Http404."""
        if not path.startswith('/'):
            path = '/' + path
        if self.prefix:
            if not path.startswith(self.prefix + '/') and path != self.prefix:
                raise Http404(f'{path!r} not under prefix {self.prefix!r}')
            sub_path = path[len(self.prefix):] or '/'
        else:
            sub_path = path
        if not sub_path.startswith('/'):
            sub_path = '/' + sub_path
        if sub_path != '/':
            sub_path = sub_path.rstrip('/') or '/'

        try:
            route = self._exact_single[sub_path]
            return route.view, route.match(sub_path) or {}, {}
        except KeyError:
            pass
        candidates = self._exact.get(sub_path)
        if candidates:
            for route in candidates:
                kw = route.match(sub_path)
                if kw is None:
                    continue
                return route.view, kw, {}

        for route in self._regex:
            kw = route.match(sub_path)
            if kw is not None:
                return route.view, kw, {}

        for module_name, sub in self._include_routes:
            try:
                return sub.resolve(path)
            except Http404:
                continue

        raise Http404(f'No route matches {path!r}')



_INCLUDE_CACHE: dict[str, 'URLRouter'] = {}


def _load_include(include: Include, *, prefix: str, namespace: str | None) -> 'URLRouter':
    key = f'{include.module}|{prefix}|{namespace or ""}'
    if key in _INCLUDE_CACHE:
        return _INCLUDE_CACHE[key]
    import importlib
    try:
        module = importlib.import_module(include.module)
    except ImportError as exc:
        raise ImproperlyConfigured(f"Could not import URLconf '{include.module}': {exc}")
    urlpatterns = getattr(module, 'urlpatterns', None)
    if urlpatterns is None:
        raise ImproperlyConfigured(f"Module '{include.module}' has no urlpatterns")
    sub = URLRouter(urlpatterns, prefix=prefix, namespace=namespace)
    _INCLUDE_CACHE[key] = sub
    return sub


def clear_url_caches() -> None:
    _INCLUDE_CACHE.clear()
