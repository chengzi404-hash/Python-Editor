"""Built-in HTTP servers for Uui.web projects."""
from typing import Any

from .app import get_application
from .exceptions import ImproperlyConfigured


def make_server(host: str = '127.0.0.1', port: int = 8000,
                settings: str | None = None) -> tuple[Any, Any]:
    """Create a wsgiref-based threaded WSGI server."""
    from socketserver import ThreadingMixIn
    from wsgiref.simple_server import WSGIRequestHandler, WSGIServer

    class ThreadingWSGIServer(ThreadingMixIn, WSGIServer):
        daemon_threads = True
        allow_reuse_address = True

    app = get_application(settings)
    wsgi_app = app.wsgi()

    server = ThreadingWSGIServer((host, port), WSGIRequestHandler)
    server.set_app(wsgi_app)
    return server, wsgi_app


def runserver(host: str = '127.0.0.1', port: int = 8000,
              settings: str | None = None, quiet: bool = False) -> None:
    """Start the dev server (wsgiref, threaded). Blocks until interrupted."""
    server, _ = make_server(host, port, settings)
    if not quiet:
        url = f'http://{host}:{port}/'
        print(f'  Uui.web dev server listening on {url}', flush=True)
        print('  (use Ctrl+C to stop)', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        if not quiet:
            print('\n  Shutting down...', flush=True)
        server.shutdown()
        server.server_close()


def serve(host: str = '0.0.0.0', port: int = 8000,
          settings: str | None = None, threads: int = 4,
          quiet: bool = False) -> None:
    """Start the production server (waitress)."""
    try:
        from waitress import serve as _waitress_serve
    except ImportError as exc:
        raise ImproperlyConfigured(
            'waitress is required for `web serve`; install via `pip install waitress`'
        ) from exc
    app = get_application(settings).wsgi()
    if not quiet:
        url = f'http://{host}:{port}/'
        print(f'  Uui.web prod server (waitress) listening on {url}', flush=True)
    _waitress_serve(app, host=host, port=port, threads=threads)
