# `modules/Uui/web/orm/models.py`

源文件路径：`modules/Uui/web/orm/models.py`

Model 基类与元类。

## 模块级

### `_models: Dict[str, Model]`
- 同时按 `'app.ModelName'` 与 `'ModelName'` 索引。

### `_resolve_model_string(path) -> Any`
先在 `_models` 中查 `path`；否则按 `mod.attr` import；找不到抛 `LookupError`。

## 类

### `ModelMeta(type)`
元类：构造 Model 子类时收集字段、推断主键与表名、安装 `QuerySet` 并注册到 `_models`。

- 收集类属性中的 `Field` 实例并从 attrs 中删除。
- 合并所有 base 的 `_meta['fields']`。
- 若无主键字段，自动添加 `id = AutoField()`。
- 推断表名：`<meta.table>` 或 `<class.lower()>`；当 `meta.app` 存在时前缀 `<app>_`。
- `cls._meta = {'fields': fields, 'table': table, 'app': app, 'pk': pk_name}`。
- 给 `cls` 挂 `objects: QuerySet`。

### `Model(metaclass=ModelMeta)`
- 类属性 `objects: QuerySet` / `_meta: Dict[str, Any]`。
- `__init__(**kwargs)`：遍历 `meta['fields']`，用 `kwargs.get(fname, default)` 填充；必要时通过 `fld.to_python(value)` 转换。
- `__repr__()`：`<ClassName pk=...>`。

其余方法（`save` / `delete` / `refresh_from_db` 等）在同文件后续定义。