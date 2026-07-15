# `modules/Uui/web/orm/fields.py`

源文件路径：`modules/Uui/web/orm/fields.py`

ORM 字段类型。

## 类

### `Field`（基类）
- 类属性：`sql_type='TEXT'` / `primary_key=False` / `auto=False` / `nullable=True` / `unique=False` / `default=None` / `has_default=False`。
- 构造 `__init__(null=False, unique=False, default=None, primary_key=False, db_column=None, verbose_name=None)`。
- 方法：`to_python(value)` / `to_db(value)` / `get_default()` / `contribute_to_class(cls, name)`。

### `AutoField(Field)`
`sql_type='INTEGER'`、`primary_key=True`、`auto=True`、`nullable=False`、`unique=True`。`to_python` 转为 `int`。

### `CharField(Field)`
`sql_type='VARCHAR(<max_length>)'`。`to_python` 转为 `str`。

### `TextField(Field)`
`sql_type='TEXT'`。

### `IntegerField(Field)`
`sql_type='INTEGER'`。`to_python` 转为 `int`。

### `BigIntegerField(IntegerField)`
`sql_type='BIGINT'`。

### `SmallIntegerField(IntegerField)`
`sql_type='SMALLINT'`。

### `FloatField(Field)`
`sql_type='REAL'`。`to_python` 转为 `float`。

### `BooleanField(Field)`
`sql_type='BOOLEAN'`；默认 `null=False, default=False`。`to_python` 转 `bool`，`to_db` 转 `0/1`。

## 关系字段与动作（仅占位展示）

- `ForeignKey` / `DateField` / `DateTimeField` 及 `CASCADE` / `SET_NULL` / `PROTECT` 见同文件后续内容（典型关系字段会构造外键列并支持 `on_delete=`）。