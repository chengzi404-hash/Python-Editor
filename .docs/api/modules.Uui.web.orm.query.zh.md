# `modules/Uui/web/orm/query.py`

源文件路径：`modules/Uui/web/orm/query.py`

惰性 QuerySet。

## 模块常量

`_LOOKUPS`：字段 lookup → SQL 操作符映射：
- `exact` / `eq` / `ieq` → `=`
- `gt` / `gte` / `lt` / `lte` → `>` / `>=` / `<` / `<=`
- `in` → `IN`
- `contains` / `icontains` / `startswith` / `endswith` → `LIKE`
- `isnull` → `IS`

## 类

### `QuerySet`
惰性、可链式调用的查询构造器。

构造 `__init__(model)`：初始化 `_filters` / `_exclude` / `_order` / `_limit` / `_offset` / `_distinct` / `_select`。

链式方法（均返回新的 `QuerySet`）：
- `filter(**kwargs)`：每个 kwarg 通过 `_parse_lookup` 解析后加入 `_filters`。
- `exclude(**kwargs)`：同上但加入 `_exclude`。
- `order_by(*fields)`
- `limit(n)` / `offset(n)`
- `distinct(on=True)`
- `values(*fields)`

执行：
- `all() -> List[Any]`：调用 `_fetch()` 立即执行 SQL。
- `__iter__()`：迭代 `_fetch()`。
- `__len__()`：`count()`。
- `__getitem__(key)`：支持 `qs[10]`（取第 10 条，单值或 `None`）和切片。

辅助：
- `_clone()`：克隆当前 QuerySet。
- `_fetch()`：编译 SQL 并通过 backend fetchall。