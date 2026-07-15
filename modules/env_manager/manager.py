from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import threading
from collections.abc import Callable
from dataclasses import dataclass, field


@dataclass
class PythonEnvironment:
    name: str
    python_path: str
    version: str = ''
    env_type: str = 'venv'  # 'venv' | 'conda' | 'system' | 'custom'
    prefix: str = ''
    packages: dict[str, str] = field(default_factory=dict)

    @property
    def display_name(self) -> str:
        parts = [self.name]
        if self.version:
            parts.append(f'Python {self.version}')
        return ' — '.join(parts)


def _probe_python(path: str) -> str:
    try:
        r = subprocess.run(
            [path, '--version'],
            capture_output=True, text=True, timeout=5,
        )
    except Exception:
        return ''
    out = (r.stdout or r.stderr or '').strip()
    if out.lower().startswith('python '):
        out = out[7:]
    m = re.search(r'\d+\.\d+(?:\.\d+)?', out)
    return m.group(0) if m else ''


def _list_packages(python_path: str) -> dict[str, str]:
    try:
        r = subprocess.run(
            [python_path, '-m', 'pip', 'list', '--format=json'],
            capture_output=True, text=True, timeout=30,
        )
        if r.returncode != 0:
            return {}
        import json
        items = json.loads(r.stdout)
        return {item['name']: item['version'] for item in items}
    except Exception:
        return {}


class EnvironmentManager:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._environments: dict[str, PythonEnvironment] = {}
        self._current: str | None = None
        self._listeners: list[Callable[[str], None]] = []
        self._scan_done: bool = False

    # ── listener ──────────────────────────────────────────────────────

    def add_listener(self, callback: Callable[[str], None]) -> None:
        with self._lock:
            self._listeners.append(callback)

    def remove_listener(self, callback: Callable[[str], None]) -> None:
        with self._lock:
            try:
                self._listeners.remove(callback)
            except ValueError:
                pass

    def _notify(self, env_name: str) -> None:
        with self._lock:
            listeners = list(self._listeners)
        for cb in listeners:
            try:
                cb(env_name)
            except Exception:
                pass

    # ── scan / detect ─────────────────────────────────────────────────

    def scan(self) -> dict[str, PythonEnvironment]:
        with self._lock:
            self._environments = {}
            self._scan_done = True

            seen: set = set()

            # 1. Current interpreter (sys.executable)
            current_python = self._resolve_python(sys.executable)
            if current_python:
                key = self._make_key(current_python)
                if key not in seen:
                    seen.add(key)
                    ver = _probe_python(current_python)
                    is_venv = self._is_venv(current_python)
                    self._environments[key] = PythonEnvironment(
                        name='base (current)' if not is_venv else os.path.basename(self._venv_prefix(current_python)),
                        python_path=current_python,
                        version=ver,
                        env_type='venv' if is_venv else 'system',
                        prefix=self._venv_prefix(current_python),
                    )

            # 2. System pythons (python, python3)
            for name in ('python', 'python3', 'py'):
                path = shutil.which(name)
                if not path:
                    continue
                resolved = self._resolve_python(path)
                if not resolved or resolved in seen:
                    continue
                seen.add(resolved)
                ver = _probe_python(resolved)
                self._environments[f'python ({ver})'] = PythonEnvironment(
                    name=f'python ({ver})',
                    python_path=resolved,
                    version=ver,
                    env_type='system',
                )

            # 3. Common venv locations
            self._scan_venv_dirs(seen)

            # 4. Conda
            self._scan_conda(seen)

            # Set current if not set
            current_python_resolved = self._resolve_python(sys.executable)
            if self._current is None or self._current not in self._environments:
                for key, env in self._environments.items():
                    if env.python_path == current_python_resolved:
                        self._current = key
                        break
                if self._current is None and self._environments:
                    self._current = next(iter(self._environments))

            return dict(self._environments)

    def _scan_venv_dirs(self, seen: set) -> None:
        candidates = [
            os.path.join(os.getcwd(), '.venv'),
            os.path.join(os.getcwd(), 'venv'),
            os.path.join(os.getcwd(), '.env'),
        ]
        parent = os.path.dirname(os.getcwd())
        if parent:
            candidates.append(os.path.join(parent, '.venv'))
        conda_defaults = [
            os.path.expanduser('~/anaconda3/envs'),
            os.path.expanduser('~/miniconda3/envs'),
        ]
        for d in conda_defaults:
            if os.path.isdir(d):
                for env_name in os.listdir(d):
                    env_dir = os.path.join(d, env_name)
                    py = self._find_python_in_venv(env_dir)
                    if py:
                        resolved = self._resolve_python(py)
                        if resolved and resolved not in seen:
                            seen.add(resolved)
                            ver = _probe_python(resolved)
                            self._environments[f'conda: {env_name}'] = PythonEnvironment(
                                name=f'conda: {env_name}',
                                python_path=resolved,
                                version=ver,
                                env_type='conda',
                                prefix=env_dir,
                            )

    def _scan_conda(self, seen: set) -> None:
        conda_path = shutil.which('conda')
        if not conda_path:
            return
        try:
            r = subprocess.run(
                [conda_path, 'env', 'list', '--json'],
                capture_output=True, text=True, timeout=15,
            )
            if r.returncode != 0:
                return
            import json
            data = json.loads(r.stdout)
            envs = data.get('envs', [])
            for env_dir in envs:
                if env_dir == 'base':
                    continue
                py = self._find_python_in_venv(env_dir)
                if not py:
                    continue
                resolved = self._resolve_python(py)
                if not resolved or resolved in seen:
                    continue
                seen.add(resolved)
                env_name = os.path.basename(env_dir)
                ver = _probe_python(resolved)
                self._environments[f'conda: {env_name}'] = PythonEnvironment(
                    name=f'conda: {env_name}',
                    python_path=resolved,
                    version=ver,
                    env_type='conda',
                    prefix=env_dir,
                )
        except Exception:
            pass

    # ── current environment ───────────────────────────────────────────

    @property
    def current_name(self) -> str | None:
        with self._lock:
            return self._current

    def get_current(self) -> PythonEnvironment | None:
        with self._lock:
            if self._current is None:
                return None
            return self._environments.get(self._current)

    def set_current(self, name: str) -> None:
        with self._lock:
            if name not in self._environments:
                return
            self._current = name
        self._notify(name)

    def get_python_path(self) -> str:
        env = self.get_current()
        if env:
            return env.python_path
        return sys.executable

    # ── package management ────────────────────────────────────────────

    def get_packages(self, name: str | None = None) -> dict[str, str]:
        env = self._get_env(name)
        if not env:
            return {}
        packages = _list_packages(env.python_path)
        env.packages = packages
        return packages

    def install_package(self, package: str, name: str | None = None,
                        mirror: str = '') -> str:
        env = self._get_env(name)
        if not env:
            return 'Environment not found'
        try:
            cmd = [env.python_path, '-m', 'pip', 'install', package]
            if mirror:
                cmd.extend(['-i', mirror])
            r = subprocess.run(
                cmd, capture_output=True, text=True, timeout=120,
            )
            if r.returncode == 0:
                env.packages = _list_packages(env.python_path)
                return ''
            return (r.stderr or r.stdout or 'Install failed').strip()
        except subprocess.TimeoutExpired:
            return 'Install timed out'
        except Exception as e:
            return str(e)

    def uninstall_package(self, package: str, name: str | None = None) -> str:
        env = self._get_env(name)
        if not env:
            return 'Environment not found'
        try:
            r = subprocess.run(
                [env.python_path, '-m', 'pip', 'uninstall', package, '-y'],
                capture_output=True, text=True, timeout=60,
            )
            if r.returncode == 0:
                env.packages = _list_packages(env.python_path)
                return ''
            return (r.stderr or r.stdout or 'Uninstall failed').strip()
        except subprocess.TimeoutExpired:
            return 'Uninstall timed out'
        except Exception as e:
            return str(e)

    # ── search packages ─────────────────────────────────────────────

    def search_packages_on_pypi(self, query: str) -> list[dict[str, str]]:
        """
        Search PyPI for packages matching the query.
        Uses the mirror's Simple Index API (PEP 503) to list all packages,
        then filters client-side. Results are cached for the session.
        Returns list of dicts with keys: name, version, summary.
        """
        try:
            names = self._get_all_package_names()
        except Exception:
            return []
        q = query.lower()
        matching = [n for n in names if q in n.lower()]
        matching.sort(key=lambda n: (0 if n.lower().startswith(q) else 1, n))
        results: list[dict[str, str]] = []
        for name in matching[:50]:
            ver, summary = '', ''
            if len(results) < 15:
                ver, summary = self._fetch_package_info(name)
            results.append({
                'name': name,
                'version': ver,
                'summary': summary[:200] if summary else '',
            })
        return results

    _package_names_cache: list[str] | None = None

    def _get_all_package_names(self) -> list[str]:
        if self._package_names_cache is not None:
            return self._package_names_cache
        import re
        import urllib.request
        url = 'https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple/'
        req = urllib.request.Request(url)
        req.add_header('User-Agent', 'PythonEditor/1.0')
        with urllib.request.urlopen(req, timeout=30) as resp:
            html = resp.read().decode('utf-8', errors='replace')
        names = re.findall(r'<a\s+href="[^"]*">([^<]+)</a>', html)
        EnvironmentManager._package_names_cache = names
        return names

    def _fetch_package_info(self, name: str) -> tuple:
        import json
        import urllib.request
        try:
            url = f'https://pypi.org/pypi/{name}/json'
            req = urllib.request.Request(url)
            req.add_header('User-Agent', 'PythonEditor/1.0')
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode())
            info = data.get('info', {})
            return info.get('version', ''), info.get('summary', '')
        except Exception:
            return '', ''

    # ── create environment ────────────────────────────────────────────

    def create_venv(self, path: str, python_path: str | None = None,
                    name: str | None = None) -> str:
        python = python_path or sys.executable
        if os.path.isdir(path):
            return f'Directory already exists: {path}'
        try:
            r = subprocess.run(
                [python, '-m', 'venv', path],
                capture_output=True, text=True, timeout=60,
            )
            if r.returncode != 0:
                return (r.stderr or 'venv creation failed').strip()
            py = self._find_python_in_venv(path)
            if not py:
                return 'Failed to find python in created venv'
            resolved = self._resolve_python(py)
            ver = _probe_python(resolved) if resolved else ''
            env_name = name or os.path.basename(path)
            with self._lock:
                self._environments[env_name] = PythonEnvironment(
                    name=env_name,
                    python_path=resolved or py,
                    version=ver,
                    env_type='venv',
                    prefix=path,
                )
            return ''
        except subprocess.TimeoutExpired:
            return 'venv creation timed out'
        except Exception as e:
            return str(e)

    # ── helpers ───────────────────────────────────────────────────────

    def _get_env(self, name: str | None = None) -> PythonEnvironment | None:
        with self._lock:
            key = name or self._current
            if key is None:
                return None
            return self._environments.get(key)

    @staticmethod
    def _resolve_python(path: str) -> str | None:
        try:
            return os.path.realpath(path)
        except Exception:
            return None

    @staticmethod
    def _make_key(path: str) -> str:
        ver = _probe_python(path)
        return f'python {ver}' if ver else os.path.basename(path)

    @staticmethod
    def _is_venv(python_path: str) -> bool:
        prefix = sys.prefix if python_path == sys.executable else None
        if prefix is None:
            # Try to determine from real prefix structure
            real = os.path.realpath(python_path)
            for _ in range(5):
                parent = os.path.dirname(real)
                if os.path.isdir(os.path.join(parent, 'pyvenv.cfg')):
                    return True
                if parent == real:
                    break
                real = parent
            return False
        return prefix != sys.base_prefix

    @staticmethod
    def _venv_prefix(python_path: str) -> str:
        if python_path == sys.executable and sys.prefix != sys.base_prefix:
            return sys.prefix
        real = os.path.realpath(python_path)
        for _ in range(5):
            parent = os.path.dirname(real)
            if os.path.isfile(os.path.join(parent, 'pyvenv.cfg')):
                return parent
            if parent == real:
                break
            real = parent
        return ''

    @staticmethod
    def _find_python_in_venv(venv_dir: str) -> str | None:
        if sys.platform == 'win32':
            candidates = [
                os.path.join(venv_dir, 'Scripts', 'python.exe'),
                os.path.join(venv_dir, 'bin', 'python.exe'),
            ]
        else:
            candidates = [
                os.path.join(venv_dir, 'bin', 'python'),
                os.path.join(venv_dir, 'bin', 'python3'),
            ]
        for c in candidates:
            if os.path.isfile(c):
                return c
        return None

    def list_environments(self) -> dict[str, PythonEnvironment]:
        if not self._scan_done:
            return self.scan()
        with self._lock:
            return dict(self._environments)


_env_manager: EnvironmentManager | None = None


def get_env_manager() -> EnvironmentManager:
    global _env_manager
    if _env_manager is None:
        _env_manager = EnvironmentManager()
    return _env_manager
