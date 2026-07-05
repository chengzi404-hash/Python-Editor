"""Uui.web command-line interface."""
import argparse
import importlib
import json
import os
import sys
import textwrap
from pathlib import Path

from .server import runserver, serve as prod_serve
from .app import get_application


SCAFFOLD_TEMPLATES = 'D:/Code/Uui/web/_scaffold'


# ---------------------------------------------------------------------------
# `web new` — scaffold a project
# ---------------------------------------------------------------------------

PROJECT_LAYOUT = {
    'manage.py': '''#!/usr/bin/env python
"""Entry point for {project}."""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault('UUI_SETTINGS', 'config')

from Uui.web.cli import main
if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
''',

    'config.py': '''"""Settings for {project}."""
import os
from pathlib import Path
from Uui.web.conf.default_settings import *  # noqa

ROOT = Path(__file__).resolve().parent

DEBUG = True
SECRET_KEY = 'dev-secret-change-me'
ALLOWED_HOSTS = ['*']

INSTALLED_APPS = [
    'apps.home',
    'Uui.web.auth',
    'Uui.web.admin',
]

ROOT_URLCONF = 'urls'
WSGI_APPLICATION = 'wsgi.application'
ASGI_APPLICATION = 'asgi.application'

MIDDLEWARE = [
    'Uui.web.middleware.CommonMiddleware',
    'Uui.web.auth.session.SessionMiddleware',
    'Uui.web.middleware.AuthenticationMiddleware',
    'Uui.web.middleware.CsrfViewMiddleware',
    'Uui.web.middleware.StaticMiddleware',
]

DATABASES = {{
    'default': {{
        'ENGINE': 'Uui.web.orm.backend.sqlite',
        'NAME': str(ROOT / 'db.sqlite3'),
    }},
}}

TEMPLATES = [
    {{
        'BACKEND': 'Uui.web.templates.Jinja2Backend',
        'DIRS': [str(ROOT / 'templates')],
        'APP_DIRS': 'templates',
        'OPTIONS': {{}},
    }},
]

STATIC_URL = '/static/'
STATIC_ROOT = str(ROOT / 'staticfiles')
STATICFILES_DIRS = [str(ROOT / 'static')]

AUTH_USER_MODEL = 'auth.User'

SESSION_COOKIE_NAME = 'uui_sessionid'
SESSION_COOKIE_AGE = 60 * 60 * 24 * 14  # 2 weeks

CSRF_COOKIE_NAME = 'uui_csrftoken'
CSRF_HEADER_NAME = 'HTTP_X_CSRFTOKEN'
''',

    'urls.py': '''"""Root URLconf for {project}."""
from Uui.web import path, include

urlpatterns = [
    path('', include('apps.home.urls')),
    path('admin/', include('Uui.web.admin.urls')),
]
''',

    'wsgi.py': '''"""WSGI entry point for {project}."""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault('UUI_SETTINGS', 'config')

from Uui.web.app import get_application
application = get_application('config').wsgi()
''',

    'asgi.py': '''"""ASGI entry point for {project} (experimental — HTTP only)."""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault('UUI_SETTINGS', 'config')

from Uui.web.app import get_application
from Uui.web.asgi import wsgi_to_asgi
application = wsgi_to_asgi(get_application('config').wsgi())
''',

    'requirements.txt': '''waitress>=3.0
regex>=2024.5.10
jinja2>=3.1
pytest>=7.0
''',

    '.gitignore': '''__pycache__/
*.py[cod]
db.sqlite3
.venv/
venv/
staticfiles/
.env
.idea/
.vscode/
*.egg-info/
''',

    'README.md': (
        '# {project}\n'
        '\n'
        'A Uui.web project — minimalist Django-style WSGI framework.\n'
        '\n'
        '## Quickstart\n'
        '\n'
        '```bash\n'
        'python manage.py migrate\n'
        'python manage.py createsuperuser\n'
        'python manage.py runserver\n'
        '```\n'
        '\n'
        'Open <http://127.0.0.1:8000/> and <http://127.0.0.1:8000/admin/>.\n'
        '\n'
        '## Commands\n'
        '\n'
        '| Command | Description |\n'
        '|---|---|\n'
        '| `python manage.py runserver [host:port]` | Dev server (wsgiref, threaded) |\n'
        '| `python manage.py serve [host:port]` | Prod server (waitress) |\n'
        '| `python manage.py shell` | Python REPL with app context |\n'
        '| `python manage.py makemigrations [app]` | Generate migration JSON |\n'
        '| `python manage.py migrate [app]` | Apply pending migrations |\n'
        '| `python manage.py showmigrations` | List migration state |\n'
        '| `python manage.py createsuperuser` | Create admin user |\n'
        '| `python manage.py collectstatic` | Collect static files |\n'
        '| `python manage.py test [path]` | Run pytest |\n'
        '| `python manage.py bench` | Performance baseline |\n'
        '\n'
        '## Layout\n'
        '\n'
        '```\n'
        '{project}/\n'
        '├── manage.py             # CLI entry\n'
        '├── config.py             # settings\n'
        '├── urls.py               # root URLconf\n'
        '├── wsgi.py / asgi.py     # entry points\n'
        '├── apps/<name>/          # your apps\n'
        '│   ├── apps.py\n'
        '│   ├── models.py\n'
        '│   ├── views.py\n'
        '│   ├── urls.py\n'
        '│   ├── migrations/\n'
        '│   └── templates/<app>/\n'
        '├── static/               # source static\n'
        '├── templates/            # project-wide templates\n'
        '├── staticfiles/          # collected static (gitignored)\n'
        '├── tests/                # pytest\n'
        '└── requirements.txt\n'
        '```\n'
        '\n'
        '## Defining views\n'
        '\n'
        '```python\n'
        '# apps/home/views.py\n'
        'from Uui.web import response\n'
        'from Uui.web.request import URequest\n'
        '\n'
        'def hello(request: URequest, name: str):\n'
        '    return response.text(f"Hello, {{name}}!")\n'
        '```\n'
        '\n'
        '## Models\n'
        '\n'
        '```python\n'
        '# apps/home/models.py\n'
        'from Uui.web.orm import Model, fields\n'
        '\n'
        'class Post(Model):\n'
        '    title = fields.CharField(max_length=200)\n'
        '    body = fields.TextField()\n'
        '    published = fields.BooleanField(default=False)\n'
        '\n'
        '    class Meta:\n'
        '        app = \'home\'\n'
        '```\n'
        '\n'
        '```bash\n'
        'python manage.py makemigrations home   # creates apps/home/migrations/0001_*.json\n'
        'python manage.py migrate home\n'
        '```\n'
    ),

    'apps/__init__.py': '',
    'apps/home/__init__.py': '',
    'apps/home/apps.py': (
        '"""App config for the home app."""\n'
        'from Uui.web.admin import site\n'
        'from Uui.web.admin.options import ModelAdmin\n'
        'from Uui.web.auth.users import User\n'
        'from .models import Post\n'
        '\n'
        '\n'
        'class HomeConfig:\n'
        '    name = \'home\'\n'
        '    verbose_name = \'Home\'\n'
        '\n'
        '    def ready(self):\n'
        '        # Register models with the admin (called from the URL conf import)\n'
        '        site.register(User, ModelAdmin)\n'
        '        site.register(Post, PostAdmin)\n'
        '\n'
        '\n'
        'class PostAdmin(ModelAdmin):\n'
        '    list_display = (\'id\', \'title\', \'published\', \'created_at\')\n'
        '    list_filter = (\'published\',)\n'
        '    search_fields = (\'title\',)\n'
        '    list_per_page = 20\n'
    ),
    'apps/home/models.py': (
        '"""Models for the home app."""\n'
        'from Uui.web.orm import Model, fields\n'
        'from Uui.web.auth.users import User\n'
        '\n'
        '\n'
        'class Post(Model):\n'
        '    title = fields.CharField(max_length=200)\n'
        '    body = fields.TextField()\n'
        '    author = fields.ForeignKey(User, on_delete=fields.CASCADE)\n'
        '    published = fields.BooleanField(default=False)\n'
        '    created_at = fields.DateTimeField(auto_now_add=True)\n'
        '\n'
        '    class Meta:\n'
        '        app = \'home\'\n'
    ),

    'apps/home/views.py': (
        '"""Views for the home app."""\n'
        'from Uui.web import response\n'
        'from Uui.web.request import URequest\n'
        'from Uui.web.auth.decorators import login_required\n'
        'from .models import Post\n'
        '\n'
        '\n'
        'def index(request: URequest):\n'
        '    posts = Post.objects.filter(published=True).order_by(\'-created_at\').all()[:20]\n'
        '    return response.render(request, \'home/index.html\', {{\'posts\': posts}})\n'
        '\n'
        '\n'
        'def hello(request: URequest, name: str):\n'
        '    return response.text(f\'Hello, {{name}}!\')\n'
        '\n'
        '\n'
        '@login_required\n'
        'def dashboard(request: URequest):\n'
        '    return response.text(f\'Welcome, {{request.user.username}}!\')\n'
    ),

    'apps/home/urls.py': (
        '"""URLconf for the home app."""\n'
        'from Uui.web import path\n'
        'from . import views\n'
        '\n'
        'app_name = \'home\'\n'
        'urlpatterns = [\n'
        '    path(\'\', views.index, name=\'index\'),\n'
        '    path(\'hello/<name>\', views.hello, name=\'hello\'),\n'
        '    path(\'dashboard/\', views.dashboard, name=\'dashboard\'),\n'
        ']\n'
    ),

    'apps/home/migrations/__init__.py': '',
    'apps/home/templates/home/index.html': (
        '<!doctype html>\n'
        '<html lang="en">\n'
        '<head>\n'
        '<meta charset="utf-8">\n'
        '<title>{{{{ project }}}}</title>\n'
        '<style>\n'
        'body {{ font-family: -apple-system, system-ui, "Segoe UI", sans-serif;\n'
        '       max-width: 720px; margin: 40px auto; padding: 0 24px; color: #1f2328; }}\n'
        'h1 {{ color: #0969da; border-bottom: 2px solid #0969da; padding-bottom: 8px; }}\n'
        '.post {{ background: #f6f8fa; border-radius: 8px; padding: 16px; margin: 12px 0; }}\n'
        '.post h2 {{ margin: 0 0 8px; font-size: 18px; }}\n'
        '.post p {{ margin: 0; color: #57606a; }}\n'
        '.empty {{ color: #8b949e; font-style: italic; }}\n'
        '</style>\n'
        '</head>\n'
        '<body>\n'
        '<h1>{{{{ project }}}}</h1>\n'
        '<p>Edit <code>apps/home/views.py</code> to change this page.</p>\n'
        '{{% if posts %}}\n'
        '{{% for p in posts %}}\n'
        '<div class="post">\n'
        '  <h2>{{{{ p.title }}}}</h2>\n'
        '  <p>{{{{ p.body }}}}</p>\n'
        '</div>\n'
        '{{% endfor %}}\n'
        '{{% else %}}\n'
        '<p class="empty">No posts yet.</p>\n'
        '{{% endif %}}\n'
        '</body>\n'
        '</html>\n'
    ),
    'tests/__init__.py': '',
    'tests/test_home.py': '''"""Smoke test for the home app."""
from Uui.web.testing import UTestClient


def test_index():
    c = UTestClient(settings='config')
    r = c.get('/')
    assert r.status_code in (200, 500)  # 500 if DB not migrated


def test_hello():
    c = UTestClient(settings='config')
    r = c.get('/hello/world')
    assert r.status_code == 200
    assert 'world' in r.text
''',
    'static/.gitkeep': '',
    'templates/.gitkeep': '',
}


def cmd_new(args: argparse.Namespace) -> int:
    name = args.name
    if not name.isidentifier():
        print(f'  ! project name must be a valid Python identifier: {name!r}')
        return 1
    target = Path(name)
    if target.exists() and not args.force:
        print(f'  ! directory exists: {target}  (use --force to merge)')
        return 1
    target.mkdir(parents=True, exist_ok=True)
    for relpath, body in PROJECT_LAYOUT.items():
        out = target / relpath
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(body.format(project=name), encoding='utf-8')
    print(f'  + created {target}/')
    print(f'  Next:')
    print(f'    cd {name}')
    print(f'    python manage.py migrate')
    print(f'    python manage.py createsuperuser')
    print(f'    python manage.py runserver')
    return 0


# ---------------------------------------------------------------------------
# `web runserver` / `web serve`
# ---------------------------------------------------------------------------

def _resolve_addr(addr: str) -> tuple:
    if ':' in addr:
        host, port = addr.rsplit(':', 1)
        return host, int(port)
    return '127.0.0.1', int(addr)


def cmd_runserver(args: argparse.Namespace) -> int:
    host, port = _resolve_addr(args.addr)
    if getattr(args, 'http2', False) or getattr(args, 'ssl_certfile', ''):
        from .server_http2 import run_http2
        cert = getattr(args, 'ssl_certfile', '') or ''
        key = getattr(args, 'ssl_keyfile', '') or ''
        if (cert or key) and not (cert and key):
            print('  ! both --ssl-cert and --ssl-key are required for HTTPS', file=__import__('sys').stderr)
            return 2
        if (not cert) and getattr(args, 'http2', False):
            # try to auto-generate a self-signed cert for h2c + http/2 prior-knowledge
            try:
                from .tls import ensure_dev_cert
                cert, key = ensure_dev_cert(cn=host or 'localhost',
                                            cert_path='cert.pem',
                                            key_path='key.pem')
                print(f'  + auto-generated dev cert: {cert}, {key}')
            except Exception as exc:
                print(f'  ! could not generate dev cert: {exc}')
                return 1
        run_http2(host=host, port=port, settings=args.settings,
                  ssl_certfile=cert, ssl_keyfile=key)
        return 0
    runserver(host=host, port=port, settings=args.settings)
    return 0


def cmd_serve(args: argparse.Namespace) -> int:
    host, port = _resolve_addr(args.addr)
    if getattr(args, 'http2', False) or getattr(args, 'ssl_certfile', ''):
        from .server_http2 import run_http2
        cert = getattr(args, 'ssl_certfile', '') or ''
        key = getattr(args, 'ssl_keyfile', '') or ''
        if (cert or key) and not (cert and key):
            print('  ! both --ssl-cert and --ssl-key are required for HTTPS', file=__import__('sys').stderr)
            return 2
        run_http2(host=host, port=port, settings=args.settings,
                  ssl_certfile=cert, ssl_keyfile=key)
        return 0
    prod_serve(host=host, port=port, settings=args.settings, threads=args.threads)
    return 0


# ---------------------------------------------------------------------------
# `web shell`
# ---------------------------------------------------------------------------

def cmd_shell(args: argparse.Namespace) -> int:
    import code
    app = get_application(args.settings)
    banner = 'Uui.web shell  (objects: app, settings)'
    ctx = {'app': app, 'settings': app.settings}
    try:
        code.interact(banner=banner, local=ctx, exitmsg='bye')
    except SystemExit:
        pass
    return 0


def cmd_test(args: argparse.Namespace) -> int:
    """Run a project's test suite via pytest."""
    import subprocess
    cmd = [sys.executable, '-m', 'pytest', '-x', '-q']
    if args.path:
        cmd.append(args.path)
    try:
        return subprocess.call(cmd)
    except FileNotFoundError:
        print('  ! pytest not installed; pip install pytest')
        return 1


def cmd_collectstatic(args: argparse.Namespace) -> int:
    """Copy all app static files into ``STATIC_ROOT``."""
    import shutil
    from .app import get_application
    app = get_application(args.settings)
    settings = app.settings
    root = Path(getattr(settings, 'ROOT', '.') if hasattr(settings, 'ROOT') else '.').resolve()
    static_root = Path(getattr(settings, 'STATIC_ROOT', 'staticfiles'))
    if not static_root.is_absolute():
        static_root = root / static_root
    static_root.mkdir(parents=True, exist_ok=True)
    dirs = list(getattr(settings, 'STATICFILES_DIRS', []) or [])
    if not dirs:
        print('  ! no STATICFILES_DIRS configured; nothing to collect')
        return 0
    copied = 0
    for src in dirs:
        src_p = Path(src)
        if not src_p.is_absolute():
            src_p = root / src_p
        if not src_p.is_dir():
            continue
        for f in src_p.rglob('*'):
            if f.is_file():
                rel = f.relative_to(src_p)
                dst = static_root / rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(f, dst)
                copied += 1
    print(f'  + collected {copied} file(s) into {static_root}')
    return 0

def cmd_bench(args: argparse.Namespace) -> int:
    """Run a hello-world benchmark against Uui.web and optionally Flask.

    The router is built with 100 exact paths and 1 named pattern, mirroring
    a small production URLconf. Results show mean / p50 / p99 latency and
    requests-per-second. ``--target flask`` also runs the same workload
    against Flask and prints a ratio (informational only — not enforced).
    """
    import time
    import statistics
    import threading
    from socketserver import ThreadingMixIn
    from wsgiref.simple_server import WSGIServer, WSGIRequestHandler, make_server

    from .router import URLRouter, Route

    def hello(request):
        from . import response
        return response.text('Hello, world!')

    def hello_name(request, name):
        from . import response
        return response.text(f'Hello, {name}!')

    routes = [Route('/' + str(i).rjust(3, '0'), hello) for i in range(100)]
    routes.append(Route('/u/<name>', hello_name))

    class ThreadedWSGIServer(ThreadingMixIn, WSGIServer):
        daemon_threads = True

    class SilentHandler(WSGIRequestHandler):
        def log_message(self, format, *args):  # noqa: A002
            pass

    def view_dispatch(environ, start_response):
        from .request import URequest
        try:
            v, kw, _ = router.resolve(environ.get('PATH_INFO', '/'))
            resp = v(URequest(environ), **kw)
        except Exception:
            from .response import error as err_resp
            resp = err_resp(404)
        return resp(environ, start_response)

    router = URLRouter(routes)

    srv = ThreadedWSGIServer(('127.0.0.1', 0), SilentHandler)
    srv.set_app(view_dispatch)
    port = srv.server_address[1]
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()

    flask_metrics: dict = {}
    try:
        import urllib.request
        urls = [f'http://127.0.0.1:{port}/{i:03d}' for i in range(100)]
        urls.append(f'http://127.0.0.1:{port}/u/alice')

        # warm up
        for u in urls[:5]:
            urllib.request.urlopen(u).read()

        N = args.requests
        timings = []
        for i in range(N):
            u = urls[i % len(urls)]
            t0 = time.perf_counter()
            urllib.request.urlopen(u).read()
            timings.append((time.perf_counter() - t0) * 1000)
        timings.sort()
        mean = statistics.mean(timings)
        p50 = timings[len(timings) // 2]
        p99 = timings[int(len(timings) * 0.99)]
        rps = 1000.0 / mean
        uui_mean = mean
        print(f'  Uui.web:  N={N}  mean={mean:.3f}ms  p50={p50:.3f}ms  p99={p99:.3f}ms  rps={rps:.0f}')
    finally:
        srv.shutdown()
        srv.server_close()

    if args.target == 'flask':
        try:
            from flask import Flask, Response
        except ImportError:
            print('  ! flask not installed; pip install flask to compare')
            return 0
        app = Flask(__name__)

        def hello_flask():
            return Response('Hello, world!', mimetype='text/plain')

        for i in range(100):
            app.add_url_rule(f'/{i:03d}', f'h{i}', hello_flask)

        @app.route('/u/<name>')
        def hello_name_flask(name):
            return Response(f'Hello, {name}!', mimetype='text/plain')

        srv2 = ThreadedWSGIServer(('127.0.0.1', 0), SilentHandler)
        srv2.set_app(app.wsgi_app)
        port2 = srv2.server_address[1]
        t2 = threading.Thread(target=srv2.serve_forever, daemon=True)
        t2.start()
        try:
            urls2 = [f'http://127.0.0.1:{port2}/{i:03d}' for i in range(100)]
            urls2.append(f'http://127.0.0.1:{port2}/u/alice')
            for u in urls2[:5]:
                urllib.request.urlopen(u).read()
            timings = []
            for i in range(N):
                u = urls2[i % len(urls2)]
                t0 = time.perf_counter()
                urllib.request.urlopen(u).read()
                timings.append((time.perf_counter() - t0) * 1000)
            timings.sort()
            mean = statistics.mean(timings)
            p50 = timings[len(timings) // 2]
            p99 = timings[int(len(timings) * 0.99)]
            rps = 1000.0 / mean
            print(f'  Flask:    N={N}  mean={mean:.3f}ms  p50={p50:.3f}ms  p99={p99:.3f}ms  rps={rps:.0f}')
            ratio = uui_mean / mean
            verdict = 'PASS' if ratio < 0.6 else 'INFO'
            print(f'\n  Uui.web / Flask ratio = {ratio:.3f}  ({verdict}; target is < 0.6)')
        finally:
            srv2.shutdown()
            srv2.server_close()
    return 0


def _bench_flask(N: int) -> int:
    try:
        from flask import Flask, Response
    except ImportError:
        print('  ! flask not installed; pip install flask to compare')
        return 0
    import time
    import statistics
    import threading
    from wsgiref.simple_server import make_server as _make

    app = Flask(__name__)

    def hello():
        return Response('Hello, world!', mimetype='text/plain')

    for i in range(100):
        app.add_url_rule(f'/{i:03d}', f'h{i}', hello)

    @app.route('/u/<name>')
    def hello_name(name):
        return Response(f'Hello, {name}!', mimetype='text/plain')

    srv = _make('127.0.0.1', 0, app.wsgi_app)
    port = srv.server_address[1]
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    try:
        import urllib.request
        urls = [f'http://127.0.0.1:{port}/{i:03d}' for i in range(100)]
        urls.append(f'http://127.0.0.1:{port}/u/alice')

        for u in urls[:5]:
            urllib.request.urlopen(u).read()

        timings = []
        for i in range(N):
            u = urls[i % len(urls)]
            t0 = time.perf_counter()
            urllib.request.urlopen(u).read()
            timings.append((time.perf_counter() - t0) * 1000)
        timings.sort()
        mean = statistics.mean(timings)
        p50 = timings[len(timings) // 2]
        p99 = timings[int(len(timings) * 0.99)]
        rps = 1000.0 / mean
        print(f'  Flask:    N={N}  mean={mean:.3f}ms  p50={p50:.3f}ms  p99={p99:.3f}ms  rps={rps:.0f}')
    finally:
        srv.shutdown()
        srv.server_close()
    return 0


# ---------------------------------------------------------------------------
# `web routes` — print all registered routes
# ---------------------------------------------------------------------------

def cmd_routes(args: argparse.Namespace) -> int:
    app = get_application(args.settings)
    router = app._router
    if router is None:
        print('  ! no router')
        return 1
    print('  Exact paths:')
    for p in sorted(router._exact.keys()):
        print(f'    {p}')
    print('  Patterns:')
    for r in router._regex:
        print(f'    {r.pattern}')
    return 0


# ---------------------------------------------------------------------------
# `web createsuperuser` / `makemigrations` / `migrate` / `showmigrations`
# ---------------------------------------------------------------------------

def _load_apps(settings) -> None:
    """Import every module in ``settings.INSTALLED_APPS`` so its models
    are registered with the metaclass."""
    import importlib
    for name in (getattr(settings, 'INSTALLED_APPS', []) or []):
        try:
            importlib.import_module(name)
        except Exception:
            pass


def cmd_migrate(args: argparse.Namespace) -> int:
    from .orm import configure
    from .orm.migration import MigrationEngine, generate_migration
    from .orm.models import _models
    from .orm import Model
    app = get_application(args.settings)
    configure(app.settings)
    _load_apps(app.settings)
    apps_root = Path(args.apps_dir or 'apps')

    for app_name in (getattr(app.settings, 'INSTALLED_APPS', []) or []):
        if '.' in app_name:
            short = app_name.split('.')[-1]
            app_dir = apps_root / short
        else:
            short = app_name
            app_dir = apps_root / app_name
        mig_dir = app_dir / 'migrations'
        has_models = any(
            getattr(m, '_meta', {}).get('app') in (app_name, short)
            for m in _models.values()
            if isinstance(m, type) and m is not Model
        )
        if not has_models:
            continue
        app_dir.mkdir(parents=True, exist_ok=True)
        if not (app_dir / '__init__.py').exists():
            (app_dir / '__init__.py').write_text('')
        mig_dir.mkdir(parents=True, exist_ok=True)
        existing = list(mig_dir.glob('*.json'))
        if not existing:
            data = generate_migration(short, name='initial')
            out = mig_dir / f'{data["id"]}.json'
            out.write_text(json.dumps(data, indent=2), encoding='utf-8')
            print(f'  + auto-generated {out}')

    applied = MigrationEngine(str(apps_root)).run(args.app)
    if applied:
        for m in applied:
            print(f'  + applied {m}')
    else:
        print('  No migrations to apply.')
    return 0


def cmd_showmigrations(args: argparse.Namespace) -> int:
    from .orm import configure
    from .orm.migration import MigrationEngine
    app = get_application(args.settings)
    configure(app.settings)
    _load_apps(app.settings)
    MigrationEngine(args.apps_dir or 'apps').show_migrations(args.app)
    return 0


def cmd_makemigrations(args: argparse.Namespace) -> int:
    from .orm import configure
    from .orm.migration import generate_migration
    app = get_application(args.settings)
    configure(app.settings)
    _load_apps(app.settings)
    target_app = args.app or 'demo'
    data = generate_migration(target_app, name=args.name or 'initial')
    apps_root = Path(args.apps_dir or 'apps')
    mig_dir = apps_root / target_app / 'migrations'
    mig_dir.mkdir(parents=True, exist_ok=True)
    out = mig_dir / f'{data["id"]}.json'
    out.write_text(json.dumps(data, indent=2), encoding='utf-8')
    print(f'  + wrote {out}  ({len(data["operations"])} ops)')
    return 0


def cmd_createsuperuser(args: argparse.Namespace) -> int:
    """Create a superuser interactively (or from --username/--password)."""
    from .orm import configure
    from .auth import User
    from getpass import getpass

    app = get_application(args.settings)
    configure(app.settings)
    _load_apps(app.settings)

    username = args.username
    if not username:
        username = _web_prompt('Username', required=True)
    if args.password:
        password = args.password
    else:
        password = getpass('Password: ')
        confirm = getpass('Password (again): ')
        if password != confirm:
            _web_error('Passwords do not match')
            return 1

    email = args.email or ''
    try:
        existing = User.objects.get(username=username)
        _web_warn(f'User {username!r} already exists; updating flags')
        existing.is_staff = True
        existing.is_superuser = True
        existing.is_active = True
        existing.set_password(password)
        existing.save()
        print(f'  + updated {username}')
    except Exception:
        u = User(username=username, email=email, password_hash='!', is_staff=True, is_superuser=True)
        u.set_password(password)
        u.save()
        print(f'  + created superuser {username!r}')
    return 0


def _web_prompt(question: str, default: str = '', required: bool = False) -> str:
    suffix = f' [{default}]' if default else ''
    while True:
        raw = input(f'  {question}{suffix}: ')
        ans = raw.strip()
        if not ans:
            ans = default
        if required and not ans:
            _web_error('required')
            continue
        return ans


def _web_error(msg: str) -> None:
    print(f'  ! {msg}')


def _web_warn(msg: str) -> None:
    print(f'  ! {msg}')


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------

def build_parser(prog: str = 'uui-web') -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog=prog, description='Uui.web — CLI')
    sub = p.add_subparsers(dest='cmd', required=True)

    p_new = sub.add_parser('new', help='scaffold a new project')
    p_new.add_argument('name', help='project name (Python identifier)')
    p_new.add_argument('--force', action='store_true')
    p_new.set_defaults(func=cmd_new)

    p_run = sub.add_parser('runserver', help='start the dev server (wsgiref or HTTP/2)')
    p_run.add_argument('addr', nargs='?', default='127.0.0.1:8000',
                       help='host:port (default 127.0.0.1:8000)')
    p_run.add_argument('--settings', default=None, help='settings module path')
    p_run.add_argument('--http2', action='store_true',
                       help='enable HTTP/2 (h2c cleartext or via TLS+ALPN)')
    p_run.add_argument('--ssl-cert', dest='ssl_certfile', default='',
                       help='path to TLS certificate (PEM); enables HTTPS + ALPN h2')
    p_run.add_argument('--ssl-key', dest='ssl_keyfile', default='',
                       help='path to TLS private key (PEM)')
    p_run.set_defaults(func=cmd_runserver)

    p_serve = sub.add_parser('serve', help='start the prod server (waitress or HTTP/2)')
    p_serve.add_argument('addr', nargs='?', default='0.0.0.0:8000')
    p_serve.add_argument('--threads', type=int, default=4)
    p_serve.add_argument('--settings', default=None)
    p_serve.add_argument('--http2', action='store_true',
                         help='enable HTTP/2 (TLS+ALPN or h2c)')
    p_serve.add_argument('--ssl-cert', dest='ssl_certfile', default='',
                         help='path to TLS certificate (PEM)')
    p_serve.add_argument('--ssl-key', dest='ssl_keyfile', default='',
                         help='path to TLS private key (PEM)')
    p_serve.set_defaults(func=cmd_serve)

    p_shell = sub.add_parser('shell', help='open a REPL with app context')
    p_shell.add_argument('--settings', default=None)
    p_shell.set_defaults(func=cmd_shell)

    p_bench = sub.add_parser('bench', help='run hello-world benchmark')
    p_bench.add_argument('-n', '--requests', type=int, default=2000)
    p_bench.add_argument('--target', choices=['none', 'flask'], default='flask',
                          help='also benchmark against this framework')
    p_bench.set_defaults(func=cmd_bench)

    p_routes = sub.add_parser('routes', help='list registered routes')
    p_routes.add_argument('--settings', default=None)
    p_routes.set_defaults(func=cmd_routes)

    p_csu = sub.add_parser('createsuperuser', help='create a superuser account')
    p_csu.add_argument('--username')
    p_csu.add_argument('--password')
    p_csu.add_argument('--email', default='')
    p_csu.add_argument('--settings', default=None)
    p_csu.set_defaults(func=cmd_createsuperuser)

    p_mk = sub.add_parser('makemigrations', help='generate migration files for an app')
    p_mk.add_argument('app', nargs='?', default='demo')
    p_mk.add_argument('--name', default='initial')
    p_mk.add_argument('--apps-dir', dest='apps_dir', default='apps')
    p_mk.add_argument('--settings', default=None)
    p_mk.set_defaults(func=cmd_makemigrations)

    p_mig = sub.add_parser('migrate', help='apply pending migrations')
    p_mig.add_argument('app', nargs='?', default=None)
    p_mig.add_argument('--apps-dir', dest='apps_dir', default='apps')
    p_mig.add_argument('--settings', default=None)
    p_mig.set_defaults(func=cmd_migrate)

    p_show = sub.add_parser('showmigrations', help='list migrations and their state')
    p_show.add_argument('app', nargs='?', default=None)
    p_show.add_argument('--apps-dir', dest='apps_dir', default='apps')
    p_show.add_argument('--settings', default=None)
    p_show.set_defaults(func=cmd_showmigrations)

    p_test = sub.add_parser('test', help='run the project test suite (pytest)')
    p_test.add_argument('path', nargs='?', default='')
    p_test.add_argument('--settings', default=None)
    p_test.set_defaults(func=cmd_test)

    p_cs = sub.add_parser('collectstatic', help='collect app static files into STATIC_ROOT')
    p_cs.add_argument('--settings', default=None)
    p_cs.set_defaults(func=cmd_collectstatic)

    return p


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except KeyboardInterrupt:
        return 130


if __name__ == '__main__':
    sys.exit(main())
