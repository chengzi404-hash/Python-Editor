"""Migration engine — JSON-snapshot-based, applying one file at a time.

The format of a migration file (`apps/<name>/migrations/<id>_<slug>.json`):

    {
        "id": "0001_initial",
        "app": "home",
        "dependencies": [],
        "operations": [
            {"op": "create_table", "name": "home_post", "columns": [
                {"name": "id", "type": "INTEGER", "primary_key": true, "auto": true},
                {"name": "title", "type": "VARCHAR(200)", "null": false}
            ]}
        ]
    }

Operations supported in v1:
    * create_table
    * drop_table
    * add_column
    * drop_column
    * rename_table
"""
import json
from pathlib import Path
from typing import Any

from . import connection as _conn
from .models import Model, _models


class MigrationEngine:
    """Drives discovery and application of migrations."""

    def __init__(self, apps_dir: str = 'apps') -> None:
        self.apps_dir = apps_dir


    def list_migrations(self, app: str | None = None) -> list[tuple[str, str, Path]]:
        """Return ``(app, migration_id, path)`` tuples sorted by id."""
        out: list[tuple[str, str, Path]] = []
        for app_dir in self._app_dirs():
            if app and app_dir.name != app:
                continue
            mig_dir = app_dir / 'migrations'
            if not mig_dir.is_dir():
                continue
            for f in sorted(mig_dir.glob('*.json')):
                with f.open(encoding='utf-8') as fh:
                    data = json.load(fh)
                out.append((data.get('app', app_dir.name), data.get('id', f.stem), f))
        out.sort(key=lambda x: (x[0], x[1]))
        return out

    def applied_migrations(self) -> list[str]:
        backend = _conn.get_backend()
        self._ensure_table(backend)
        rows = backend.fetchall(
            'SELECT app, id FROM uui_migrations ORDER BY app, id'
        )
        return [f'{r[0]}.{r[1]}' for r in rows]

    def show_migrations(self, app: str | None = None) -> None:
        applied = set(self.applied_migrations())
        for a, mid, _ in self.list_migrations(app):
            marker = 'X' if f'{a}.{mid}' in applied else ' '
            print(f'  [{marker}] {a}.{mid}')


    def run(self, app: str | None = None) -> list[str]:
        backend = _conn.get_backend()
        self._ensure_table(backend)
        applied = set(self.applied_migrations())
        new: list[str] = []
        for a, mid, path in self.list_migrations(app):
            key = f'{a}.{mid}'
            if key in applied:
                continue
            with path.open(encoding='utf-8') as fh:
                data = json.load(fh)
            for op in data.get('operations', []):
                self._apply_op(backend, op)
            backend.execute(
                f'INSERT INTO uui_migrations (app, id, applied_at) VALUES ({backend.placeholder(1)}, {backend.placeholder(2)}, {backend.placeholder(3)})',
                (a, mid, _now()),
            )
            new.append(key)
        return new


    def _ensure_table(self, backend) -> None:
        backend.ensure_migrations_table()

    def _app_dirs(self) -> list[Path]:
        root = Path(self.apps_dir)
        if not root.is_dir():
            return []
        return [p for p in root.iterdir() if p.is_dir() and (p / '__init__.py').exists()]

    def _apply_op(self, backend, op: dict[str, Any]) -> None:
        kind = op.get('op')
        if kind == 'create_table':
            cols_sql = self._columns_sql(backend, op['columns'])
            sql = backend.create_table_sql(op['name'], cols_sql)
            backend.execute(sql)
        elif kind == 'drop_table':
            sql = backend.drop_table_sql(op['name'])
            if sql:
                backend.execute(sql)
        elif kind == 'add_column':
            col = dict(op['column'])
            col_sql = self._column_sql(backend, col)
            sql = f'ALTER TABLE {backend.quote_name(op["table"])} ADD COLUMN {col_sql}'
            backend.execute(sql)
        elif kind == 'drop_column':
            sql = f'ALTER TABLE {backend.quote_name(op["table"])} DROP COLUMN {backend.quote_name(op["name"])}'
            backend.execute(sql)
        elif kind == 'rename_table':
            sql = f'ALTER TABLE {backend.quote_name(op["old"])} RENAME TO {backend.quote_name(op["new"])}'
            backend.execute(sql)
        else:
            raise ValueError(f'Unknown migration operation: {kind!r}')

    def _columns_sql(self, backend, columns: list[dict[str, Any]]) -> str:
        return ', '.join(self._column_sql(backend, c) for c in columns)

    def _column_sql(self, backend, col: dict[str, Any]) -> str:
        col_type = backend.sql_type(col['type'])
        if col.get('primary_key') and col.get('auto'):
            return backend.auto_increment_sql(col['name'], col_type)
        parts = [backend.quote_name(col['name']), col_type]
        if col.get('primary_key'):
            parts.append('PRIMARY KEY')
        if col.get('null') is False and not col.get('primary_key'):
            parts.append('NOT NULL')
        if col.get('unique') and not col.get('primary_key'):
            parts.append('UNIQUE')
        if 'default' in col:
            parts.append(f"DEFAULT {_sql_value(col['default'], backend)}")
        return ' '.join(parts)


def generate_migration(app: str, name: str = 'initial') -> dict[str, Any]:
    """Generate a migration dict from the current state of registered models
    whose ``Meta.app`` matches ``app``. The matching models are looked up via
    the ORM registry — no project file is required.
    """
    import importlib
    try:
        importlib.import_module(f'apps.{app}.models')
    except ImportError:
        pass  # built-in app (e.g. Uui.web.auth) — OK, models are already registered

    operations: list[dict[str, Any]] = []
    seen: list[type] = []
    for mdl in _models.values():
        if not isinstance(mdl, type) or not issubclass(mdl, Model) or mdl is Model:
            continue
        meta = getattr(mdl, '_meta', None)
        if not meta:
            continue
        if meta.get('app') != app:
            continue
        seen.append(mdl)

    for mdl in seen:
        columns = []
        for _fname, fld in mdl._meta['fields'].items():
            columns.append({
                'name': fld.column,
                'type': fld.sql_type,
                'primary_key': fld.primary_key,
                'auto': getattr(fld, 'auto', False),
                'null': fld.nullable,
                'unique': fld.unique,
            })
        operations.append({
            'op': 'create_table',
            'name': mdl._meta['table'],
            'columns': columns,
        })

    return {
        'id': f'0001_{name}' if name == 'initial' else f'0001_{name}',
        'app': app,
        'dependencies': [],
        'operations': operations,
    }


def run_migrations(apps_dir: str = 'apps', app: str | None = None) -> list[str]:
    """Convenience wrapper to run migrations against the default database."""
    return MigrationEngine(apps_dir).run(app)


def _now() -> str:
    from datetime import datetime
    return datetime.now().isoformat(sep=' ', timespec='seconds')


def _sql_value(v: Any, backend) -> str:
    if v is None:
        return 'NULL'
    if isinstance(v, bool):
        if backend.boolean_sql_type().upper() == 'BOOLEAN':
            return 'TRUE' if v else 'FALSE'
        return '1' if v else '0'
    if isinstance(v, (int, float)):
        return str(v)
    return repr(str(v))
