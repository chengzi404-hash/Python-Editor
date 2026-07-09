"""ORM Model base and metaclass."""
from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING

from . import connection as _conn
from .fields import AutoField, Field, ForeignKey

if TYPE_CHECKING:
    from .query import QuerySet


_models: Dict[str, 'Model'] = {}


def _resolve_model_string(path: str) -> Any:
    if path in _models:
        return _models[path]
    import importlib
    mod_path, _, attr = path.rpartition('.')
    mod = importlib.import_module(mod_path)
    cls = getattr(mod, attr, None)
    if cls is None:
        raise LookupError(f'Cannot resolve model {path!r}')
    return cls


class ModelMeta(type):
    """Collects Field instances and creates the table schema."""

    def __new__(mcs, name, bases, attrs):
        if name == 'Model' and not bases:
            return super().__new__(mcs, name, bases, attrs)

        fields: Dict[str, Field] = {}
        pk_field: Optional[Field] = None
        for key, value in list(attrs.items()):
            if isinstance(value, Field):
                fields[key] = value
                del attrs[key]

        for base in bases:
            for key, value in getattr(base, '_meta', {}).get('fields', {}).items():
                fields.setdefault(key, value)

        if not any(f.primary_key for f in fields.values()):
            pk_field = AutoField()
            fields['id'] = pk_field
            attrs['id'] = pk_field

        meta = attrs.get('Meta')
        table = name.lower()
        app = ''
        if meta is not None:
            table = getattr(meta, 'table', table)
            app = getattr(meta, 'app', '')
        if app and '.' not in table:
            table = f'{app}_{table}'

        meta_dict = {
            'fields': fields,
            'table': table,
            'app': app,
            'pk': next((n for n, f in fields.items() if f.primary_key), 'id'),
        }

        for fname, fld in fields.items():
            fld.attname = fname
            fld.column = fld.db_column or fname
            attrs[fname] = fld

        cls = super().__new__(mcs, name, bases, attrs)
        cls._meta = meta_dict  # type: ignore[attr-defined]
        from .query import QuerySet as _QS
        cls.objects = _QS(cls)  # type: ignore[arg-type,attr-defined]

        model_path = f'{cls.__module__}.{name}'
        _models[model_path] = cls  # type: ignore[arg-type]
        _models[name] = cls  # type: ignore[arg-type]
        return cls


class Model(metaclass=ModelMeta):
    """Base class for all ORM models."""

    objects: 'QuerySet' = None  # type: ignore
    _meta: Dict[str, Any]

    def __init__(self, **kwargs) -> None:
        for fname, fld in self._meta['fields'].items():
            if fname in kwargs:
                value = kwargs[fname]
                if hasattr(fld, 'to_python'):
                    value = fld.to_python(value)
                setattr(self, fname, value)
            else:
                default = fld.get_default() if fld.has_default else None
                setattr(self, fname, default)

    def __repr__(self) -> str:
        pk_field = self._meta['pk']
        return f'<{type(self).__name__} {pk_field}={getattr(self, pk_field, None)!r}>'

    @classmethod
    def get_queryset(cls) -> 'QuerySet':
        return QuerySet(cls)

    def save(self) -> 'Model':
        backend = _conn.get_backend()
        fields = self._meta['fields']
        pk_field_name = self._meta['pk']
        pk_field = fields[pk_field_name]
        pk_value = getattr(self, pk_field_name, None)

        values: Dict[str, Any] = {}
        for fname, fld in fields.items():
            if fld.primary_key and pk_value is None and not fld.auto:
                continue
            if hasattr(fld, 'pre_save'):
                value = fld.pre_save(self, add=pk_value is None)
                setattr(self, fname, value)
            raw = getattr(self, fname, None)
            if hasattr(fld, 'to_db'):
                raw = fld.to_db(raw)
            if raw is None and fld.nullable:
                values[fld.column] = None
            elif raw is None and fld.has_default and not fld.primary_key:
                continue
            else:
                values[fld.column] = raw

        if pk_value is None:
            cols = ', '.join(backend.quote_name(c) for c in values)
            placeholders = ', '.join(backend.placeholder(i + 1) for i in range(len(values)))
            sql = f'INSERT INTO {backend.quote_name(self._meta["table"])} ({cols}) VALUES ({placeholders})'
            backend.execute(sql, tuple(values.values()))
            if pk_field.auto:
                new_pk = backend.last_insert_id(self._meta['table'], pk_field.column)
                setattr(self, pk_field_name, new_pk)
        else:
            assignments = ', '.join(
                f'{backend.quote_name(c)} = {backend.placeholder(i + 1)}'
                for i, c in enumerate(values)
            )
            sql = f'UPDATE {backend.quote_name(self._meta["table"])} SET {assignments} WHERE {backend.quote_name(pk_field.column)} = {backend.placeholder(len(values) + 1)}'
            backend.execute(sql, tuple(values.values()) + (pk_value,))
        return self

    def delete(self) -> int:
        backend = _conn.get_backend()
        pk_field_name = self._meta['pk']
        pk_value = getattr(self, pk_field_name, None)
        if pk_value is None:
            return 0
        sql = f'DELETE FROM {backend.quote_name(self._meta["table"])} WHERE {backend.quote_name(self._meta["fields"][pk_field_name].column)} = {backend.placeholder(1)}'
        backend.execute(sql, (pk_value,))
        return 1

    @classmethod
    def create(cls, **kwargs) -> 'Model':
        instance = cls(**kwargs)
        instance.save()
        return instance

    def to_dict(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {}
        for fname in self._meta['fields']:
            value = getattr(self, fname, None)
            if hasattr(value, 'isoformat'):
                value = value.isoformat()  # type: ignore[union-attr]
            result[fname] = value
        return result
