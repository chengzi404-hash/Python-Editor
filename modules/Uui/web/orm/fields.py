"""ORM field types."""
from datetime import date, datetime
from typing import Any, Optional


class Field:
    """Base class for all field types."""

    sql_type: str = 'TEXT'
    primary_key: bool = False
    auto: bool = False
    nullable: bool = True
    unique: bool = False
    default: Any = None
    has_default: bool = False

    def __init__(self, *,
                 null: bool = False,
                 unique: bool = False,
                 default: Any = None,
                 primary_key: bool = False,
                 db_column: Optional[str] = None,
                 verbose_name: Optional[str] = None) -> None:
        self.null = null
        self.nullable = null
        self.unique = unique
        self.has_default = default is not None or primary_key
        self.default = default
        self.primary_key = primary_key
        self.db_column = db_column
        self.verbose_name = verbose_name
        self.attname: str = ''
        self.column: str = ''

    def to_python(self, value: Any) -> Any:
        return value

    def to_db(self, value: Any) -> Any:
        return value

    def get_default(self) -> Any:
        return self.default

    def contribute_to_class(self, cls, name: str) -> None:
        self.attname = name
        self.column = self.db_column or name


class AutoField(Field):
    sql_type = 'INTEGER'
    primary_key = True
    auto = True
    nullable = False
    unique = True

    def __init__(self, **kwargs) -> None:
        kwargs.setdefault('primary_key', True)
        super().__init__(**kwargs)

    def to_python(self, value: Any) -> Any:
        return int(value) if value is not None else None


class CharField(Field):
    sql_type = 'VARCHAR'

    def __init__(self, max_length: int = 255, **kwargs) -> None:
        self.max_length = max_length
        super().__init__(**kwargs)
        self.sql_type = f'VARCHAR({max_length})'

    def to_python(self, value: Any) -> Any:
        return str(value) if value is not None else None


class TextField(Field):
    sql_type = 'TEXT'


class IntegerField(Field):
    sql_type = 'INTEGER'

    def to_python(self, value: Any) -> Any:
        return int(value) if value is not None else None


class BigIntegerField(IntegerField):
    sql_type = 'BIGINT'


class SmallIntegerField(IntegerField):
    sql_type = 'SMALLINT'


class FloatField(Field):
    sql_type = 'REAL'

    def to_python(self, value: Any) -> Any:
        return float(value) if value is not None else None


class BooleanField(Field):
    sql_type = 'BOOLEAN'

    def __init__(self, default: Any = False, **kwargs) -> None:
        kwargs.setdefault('default', default)
        kwargs.setdefault('null', False)
        super().__init__(**kwargs)
        self.has_default = True

    def to_python(self, value: Any) -> Any:
        if value is None:
            return None
        return bool(value)

    def to_db(self, value: Any) -> Any:
        if value is None:
            return None
        return 1 if value else 0


class DateTimeField(Field):
    sql_type = 'TIMESTAMP'

    def __init__(self, auto_now: bool = False, auto_now_add: bool = False, **kwargs) -> None:
        self.auto_now = auto_now
        self.auto_now_add = auto_now_add
        super().__init__(**kwargs)

    def pre_save(self, instance: Any, add: bool) -> Any:
        if self.auto_now or (self.auto_now_add and add):
            return datetime.now()
        return getattr(instance, self.attname, None)

    def to_python(self, value: Any) -> Any:
        if value is None or isinstance(value, datetime):
            return value
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value)
            except ValueError:
                return value
        return value

    def to_db(self, value: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        return value


class DateField(Field):
    sql_type = 'DATE'

    def to_python(self, value: Any) -> Any:
        if value is None or isinstance(value, date):
            return value
        if isinstance(value, str):
            try:
                return date.fromisoformat(value[:10])
            except ValueError:
                return value
        return value

    def to_db(self, value: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, date):
            return value
        return value


class ForeignKey(Field):
    sql_type = 'INTEGER'

    def __init__(self, to, on_delete: str = 'CASCADE', **kwargs) -> None:
        kwargs.setdefault('null', False)
        self.to = to if not isinstance(to, str) else to
        self.on_delete = on_delete
        super().__init__(**kwargs)
        self._related_name: Optional[str] = None
        self.is_relation = True

    def contribute_to_class(self, cls, name: str) -> None:
        super().contribute_to_class(cls, name)
        if cls is not None:
            cache_name = f'_{name}_cache'
            setattr(cls, cache_name, None)
        self._related_name = name + '_set'

    def get_related_model(self) -> Any:
        if isinstance(self.to, str):
            from .models import _resolve_model_string
            return _resolve_model_string(self.to)
        return self.to


# Shortcut constants
CASCADE = 'CASCADE'
SET_NULL = 'SET_NULL'
PROTECT = 'PROTECT'
