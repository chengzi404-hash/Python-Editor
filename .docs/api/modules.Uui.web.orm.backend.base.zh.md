# `modules/Uui/web/orm/backend/base.py`

源文件路径：`modules/Uui/web/orm/backend/base.py`

后端抽象基类。

## 类

### `Row(dict)`
Dict 风格的行；`__iter__` 直接 yield 值，方便 `zip(keys, row)` 解构。

### `Backend`
数据库后端抽象。

类属性：
- `engine_name: str = ''`
- `param_style: str = '?'`（`'?'` / `'%s'` / `':n'`）

构造 `__init__(alias, config)`：保存 `alias` 与 `config`。

抽象方法（各后端实现）：
- `connection() -> Any`
- `close()`
- `execute(sql, params=()) -> Any`
- `executemany(sql, seq)`
- `fetchall(sql, params=()) -> List[Any]`
- `fetchone(sql, params=()) -> Any`
- `last_insert_id(table, pk) -> int`

通用辅助：
- `placeholder(index) -> str`：`param_style == ':n'` 时返回 `f':{index}'`，否则用 `param_style`。
- `quote_name(name) -> str`：双引号转义包裹。
- `auto_increment_sql(column_name, column_type) -> str`：默认 `"<col>" <type> PRIMARY KEY AUTOINCREMENT`。
- `limit_offset_sql(sql, limit, offset) -> str`：追加 `LIMIT/OFFSET`。
- `boolean_sql_type() -> str`：`'BOOLEAN'`。
- `sql_type(generic_type) -> str`：`BOOLEAN` 走 `boolean_sql_type()`，其余原样。
- `create_table_sql(table_name, columns_sql) -> str`：`CREATE TABLE IF NOT EXISTS "<table>" (<columns_sql>)`。
- `drop_table_sql(table_name) -> str`：默认 `DROP TABLE IF EXISTS "<table>"`。