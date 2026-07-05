"""Uui.web ORM.

Django-style declarative models:

    from Uui.web.orm import Model, fields

    class Post(Model):
        title = fields.CharField(max_length=200)
        body = fields.TextField()
        published = fields.BooleanField(default=False)

        class Meta:
            app = 'blog'

    Post.objects.filter(published=True).order_by('-id').all()
    Post.objects.create(title='Hello', body='World')
"""
from . import connection, fields, query
from .models import Model, _resolve_model_string, _models
from .fields import (
    Field, AutoField,
    CharField, TextField,
    IntegerField, BigIntegerField, SmallIntegerField,
    FloatField, BooleanField,
    DateField, DateTimeField,
    ForeignKey,
    CASCADE, SET_NULL, PROTECT,
)
from .query import QuerySet
from . import backend  # noqa: F401  (register backend subclasses)
from .backend.sqlite import SqliteBackend
from .backend.mysql import MysqlBackend
from .backend.postgresql import PostgresqlBackend
from .backend.oracle import OracleBackend
from .migration import MigrationEngine, generate_migration, run_migrations


def configure(settings) -> None:
    """Initialise all backends from ``settings.DATABASES``."""
    connection.configure(settings)


__all__ = [
    'Model', 'QuerySet',
    'Field', 'AutoField',
    'CharField', 'TextField',
    'IntegerField', 'BigIntegerField', 'SmallIntegerField',
    'FloatField', 'BooleanField',
    'DateField', 'DateTimeField',
    'ForeignKey',
    'CASCADE', 'SET_NULL', 'PROTECT',
    'configure',
    'connection',
    'fields',
    'query',
    'MigrationEngine', 'generate_migration', 'run_migrations',
    'SqliteBackend', 'MysqlBackend', 'PostgresqlBackend', 'OracleBackend',
]
