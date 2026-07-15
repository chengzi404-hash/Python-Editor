# `modules/Uui/web/orm/__init__.py`

源文件路径：`modules/Uui/web/orm/__init__.py`

`Uui.web.orm` 子包公开入口。Django 风格声明式 ORM。

## 快速上手

```python
from Uui.web.orm import Model, fields

class Post(Model):
    title = fields.CharField(max_length=200)
    body = fields.TextField()
    published = fields.BooleanField(default=False)

    class Meta:
        app = 'blog'

Post.objects.filter(published=True).order_by('-id').all()
Post.objects.create(title='Hello', body='World')
```

## 重新导出

### 核心
- `Model` — 基类（来自 `models.py`）。
- `QuerySet` — 查询构建器（来自 `query.py`）。
- `configure(settings)` — 用 settings.DATABASES 初始化所有后端。
- `connection` / `fields` / `query` — 子模块。

### 字段（来自 `fields.py`）
- 基类：`Field` / `AutoField`。
- 文本：`CharField` / `TextField`。
- 数值：`IntegerField` / `BigIntegerField` / `SmallIntegerField` / `FloatField`。
- 其它：`BooleanField` / `DateField` / `DateTimeField`。
- 关系：`ForeignKey`。
- 关系动作：`CASCADE` / `SET_NULL` / `PROTECT`。

### 后端（来自 `backend/`）
- `SqliteBackend` / `MysqlBackend` / `PostgresqlBackend` / `OracleBackend`。
- 基类 `Backend`。

### 迁移（来自 `migration.py`）
- `MigrationEngine` / `generate_migration` / `run_migrations`。

### 模型注册表
- `_resolve_model_string(path)` / `_models` — 模型注册字典。

## `__all__`

```python
['Model', 'QuerySet', 'Field', 'AutoField', 'CharField', 'TextField',
 'IntegerField', 'BigIntegerField', 'SmallIntegerField', 'FloatField',
 'BooleanField', 'DateField', 'DateTimeField', 'ForeignKey',
 'CASCADE', 'SET_NULL', 'PROTECT', 'configure', 'connection', 'fields',
 'query', 'MigrationEngine', 'generate_migration', 'run_migrations',
 'SqliteBackend', 'MysqlBackend', 'PostgresqlBackend', 'OracleBackend']
```