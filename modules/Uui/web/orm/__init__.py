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
from . import (
    backend,
    connection,
    fields,
    query,
)
from .backend.mysql import MysqlBackend
from .backend.oracle import OracleBackend
from .backend.postgresql import PostgresqlBackend
from .backend.sqlite import SqliteBackend
from .fields import (
    CASCADE,
    PROTECT,
    SET_NULL,
    AutoField,
    BigIntegerField,
    BooleanField,
    CharField,
    DateField,
    DateTimeField,
    Field,
    FloatField,
    ForeignKey,
    IntegerField,
    SmallIntegerField,
    TextField,
)
from .migration import MigrationEngine, generate_migration, run_migrations
from .models import Model, _models, _resolve_model_string
from .query import QuerySet


def configure(settings) -> None:
    """Initialise all backends from ``settings.DATABASES``."""
    connection.configure(settings)


__all__ = [
    'CASCADE',
    'PROTECT',
    'SET_NULL',
    'AutoField',
    'BigIntegerField',
    'BooleanField',
    'CharField',
    'DateField',
    'DateTimeField',
    'Field',
    'FloatField',
    'ForeignKey',
    'IntegerField',
    'MigrationEngine',
    'Model',
    'MysqlBackend',
    'OracleBackend',
    'PostgresqlBackend',
    'QuerySet',
    'SmallIntegerField',
    'SqliteBackend',
    'TextField',
    'configure',
    'connection',
    'fields',
    'generate_migration',
    'query',
    'run_migrations',
]
