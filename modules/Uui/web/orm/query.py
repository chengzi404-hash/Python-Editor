"""Lazy QuerySet supporting filter / exclude / order_by / slicing."""
from typing import TYPE_CHECKING, Any

from . import connection as _conn

if TYPE_CHECKING:
    pass


_LOOKUPS = {
    'exact': '=',
    'eq': '=',
    'ieq': '=',
    'gt': '>',
    'gte': '>=',
    'lt': '<',
    'lte': '<=',
    'in': 'IN',
    'contains': 'LIKE',
    'icontains': 'LIKE',
    'startswith': 'LIKE',
    'endswith': 'LIKE',
    'isnull': 'IS',
}


class QuerySet:
    """A lazy, chainable query builder."""

    def __init__(self, model: type) -> None:
        self._model = model
        self._filters: list[tuple[str, tuple[str, Any]]] = []
        self._exclude: list[tuple[str, tuple[str, Any]]] = []
        self._order: list[str] = []
        self._limit: int | None = None
        self._offset: int | None = None
        self._distinct: bool = False
        self._select: list[str] = []


    def filter(self, **kwargs) -> 'QuerySet':
        clone = self._clone()
        for key, value in kwargs.items():
            clone._filters.append(_parse_lookup(key, value))
        return clone

    def exclude(self, **kwargs) -> 'QuerySet':
        clone = self._clone()
        for key, value in kwargs.items():
            clone._exclude.append(_parse_lookup(key, value))
        return clone

    def order_by(self, *fields) -> 'QuerySet':
        clone = self._clone()
        clone._order = list(fields)
        return clone

    def limit(self, n: int) -> 'QuerySet':
        clone = self._clone()
        clone._limit = n
        return clone

    def offset(self, n: int) -> 'QuerySet':
        clone = self._clone()
        clone._offset = n
        return clone

    def distinct(self, on: bool = True) -> 'QuerySet':
        clone = self._clone()
        clone._distinct = on
        return clone

    def values(self, *fields) -> 'QuerySet':
        clone = self._clone()
        clone._select = list(fields)
        return clone


    def all(self) -> list[Any]:
        return self._fetch()

    def __iter__(self):
        return iter(self._fetch())

    def __len__(self) -> int:
        return self.count()

    def __getitem__(self, key):
        if isinstance(key, slice):
            clone = self._clone()
            if key.start is not None:
                clone._offset = key.start
            if key.stop is not None:
                clone._limit = key.stop - (key.start or 0)
            return list(clone._fetch())
        clone = self._clone()
        clone._limit = 1
        clone._offset = key
        rows = clone._fetch()
        return rows[0] if rows else None

    def get(self, **kwargs) -> Any:
        clone = self.filter(**kwargs)
        rows = clone._fetch()
        if not rows:
            from ..exceptions import Http404
            raise Http404(f'{self._model.__name__} matching query does not exist')
        if len(rows) > 1:
            raise ValueError(f'get() returned {len(rows)} rows; expected 1')
        return rows[0]

    def first(self) -> Any | None:
        clone = self._clone()
        clone._limit = 1
        rows = clone._fetch()
        return rows[0] if rows else None

    def last(self) -> Any | None:
        clone = self._clone()
        clone._order = ['-' + o if not o.startswith('-') else o[1:] for o in reversed(self._order or ['pk'])]
        clone._limit = 1
        rows = clone._fetch()
        return rows[0] if rows else None

    def create(self, **kwargs) -> Any:
        instance = self._model(**kwargs)
        instance.save()
        return instance

    def count(self) -> int:
        backend = _conn.get_backend()
        sql, params = self._build_sql(count=True)
        rows = backend.fetchall(sql, tuple(params))
        return int(rows[0][0]) if rows else 0

    def exists(self) -> bool:
        return self.count() > 0

    def delete(self) -> int:
        backend = _conn.get_backend()
        where, params = self._build_where()
        sql = f'DELETE FROM {backend.quote_name(self._model._meta["table"])}{where}'
        backend.execute(sql, tuple(params))
        return -1  # SQLite doesn't return affected row count by default

    def update(self, **kwargs) -> int:
        backend = _conn.get_backend()
        if not kwargs:
            return 0
        assignments = ', '.join(
            f'{backend.quote_name(_resolve_field(self._model, k).column)} = {backend.placeholder(i + 1)}'
            for i, k in enumerate(kwargs)
        )
        where, params = self._build_where(offset=len(kwargs))
        values = []
        for k, v in kwargs.items():
            field = _resolve_field(self._model, k)
            values.append(field.to_db(v) if hasattr(field, 'to_db') else v)
        sql = (f'UPDATE {backend.quote_name(self._model._meta["table"])} SET {assignments}{where}')
        backend.execute(sql, tuple(values) + tuple(params))
        return -1


    def _build_sql(self, count: bool = False) -> tuple[str, list]:
        backend = _conn.get_backend()
        if count:
            select = 'COUNT(*)'
        elif self._select:
            cols = ', '.join(backend.quote_name(_resolve_field(self._model, c).column) for c in self._select)
            select = cols
        else:
            select = '*'

        sql = f'SELECT {select} FROM {backend.quote_name(self._model._meta["table"])}'
        where, params = self._build_where()
        sql += where
        if self._order:
            order_parts = []
            for o in self._order:
                if o.startswith('-'):
                    col = _resolve_field(self._model, o[1:]).column
                    order_parts.append(f'{backend.quote_name(col)} DESC')
                elif o.startswith('+'):
                    col = _resolve_field(self._model, o[1:]).column
                    order_parts.append(f'{backend.quote_name(col)} ASC')
                else:
                    col = _resolve_field(self._model, o).column
                    order_parts.append(f'{backend.quote_name(col)} ASC')
            sql += ' ORDER BY ' + ', '.join(order_parts)
        sql = backend.limit_offset_sql(sql, self._limit, self._offset)
        return sql, params

    def _build_where(self, offset: int = 0) -> tuple[str, list]:
        backend = _conn.get_backend()
        clauses: list[str] = []
        params: list[Any] = []
        idx = offset + 1

        def _add_condition(field: str, op: str, value: Any, negated: bool = False):
            nonlocal idx
            col = backend.quote_name(_resolve_field(self._model, field).column)
            if op == 'IN':
                if not value:
                    clauses.append('1 = 1' if negated else '0 = 1')
                else:
                    placeholders = ', '.join(backend.placeholder(i) for i in range(idx, idx + len(value)))
                    not_ = 'NOT ' if negated else ''
                    clauses.append(f'{col} {not_}IN ({placeholders})')
                    params.extend(value)
                    idx += len(value)
            elif op == 'IS':
                if negated:
                    clauses.append(f'{col} IS {"NOT NULL" if value else "NULL"}')
                else:
                    clauses.append(f'{col} IS {"NULL" if value else "NOT NULL"}')
            elif op == 'LIKE':
                clauses.append(f'{col} {"NOT" if negated else ""} LIKE {backend.placeholder(idx)}')
                params.append(value)
                idx += 1
            else:
                clauses.append(f'{col} {"<>" if negated else op} {backend.placeholder(idx)}')
                params.append(value)
                idx += 1

        for field, (op, value) in self._filters:
            _add_condition(field, op, value)
        for field, (op, value) in self._exclude:
            _add_condition(field, op, value, negated=True)
        if not clauses:
            return '', []
        return ' WHERE ' + ' AND '.join(clauses), params

    def _fetch(self) -> list[Any]:
        backend = _conn.get_backend()
        sql, params = self._build_sql()
        rows = backend.fetchall(sql, tuple(params))
        results: list[Any] = []
        for row in rows:
            if self._select:
                results.append(dict(zip(self._select, row)))
            else:
                results.append(self._hydrate(row))
        return results

    def _hydrate(self, row) -> Any:
        instance = self._model()
        keys = row.keys() if hasattr(row, 'keys') else range(len(row))
        mapping = dict(zip(keys, row))
        for fname, fld in self._model._meta['fields'].items():
            value = mapping.get(fld.column)
            if hasattr(fld, 'to_python'):
                value = fld.to_python(value)
            setattr(instance, fname, value)
        return instance

    def _clone(self) -> 'QuerySet':
        clone = QuerySet(self._model)
        clone._filters = list(self._filters)
        clone._exclude = list(self._exclude)
        clone._order = list(self._order)
        clone._limit = self._limit
        clone._offset = self._offset
        clone._distinct = self._distinct
        clone._select = list(self._select)
        return clone

    def __repr__(self) -> str:
        return f'<QuerySet model={self._model.__name__}>'



def _parse_lookup(key: str, value: Any) -> tuple[str, tuple[str, Any]]:
    if '__' in key:
        field, op = key.rsplit('__', 1)
        sql_op = _LOOKUPS.get(op)
        if sql_op is None:
            raise ValueError(f'Unknown lookup {op!r}')
        if op in ('contains', 'icontains'):
            value = f'%{value}%'
        elif op == 'startswith':
            value = f'{value}%'
        elif op == 'endswith':
            value = f'%{value}'
        return field, (sql_op, value)
    return key, ('=', value)


def _resolve_field(model: type, name: str):
    fields = model._meta['fields']
    if name in fields:
        return fields[name]
    if name == 'pk':
        return fields[model._meta['pk']]
    raise AttributeError(f'{model.__name__} has no field {name!r}')
