# `modules/Uui/web/orm/migration.py`

源文件路径：`modules/Uui/web/orm/migration.py`

JSON 快照格式的迁移引擎。每个迁移文件位于 `apps/<name>/migrations/<id>_<slug>.json`，结构：

```json
{
  "id": "0001_initial",
  "app": "home",
  "dependencies": [],
  "operations": [
    {"op": "create_table", "name": "home_post", "columns": [
      {"name": "id", "type": "INTEGER", "primary_key": true, "auto": true},
      {"name": "title", "type": "VARCHAR(200)", "null": false}
    ]}
  ]
}
```

支持的操作（v1）：`create_table` / `drop_table` / `add_column` / `drop_column` / `rename_table`。

## 类

### `MigrationEngine`
- `__init__(apps_dir='apps')`：扫描目录。
- `list_migrations(app=None) -> List[(app, id, path)]`：按 `(app, id)` 排序。
- `applied_migrations() -> List[str]`：返回 `app.id` 形式的列表（来源是 `uui_migrations` 表）。
- `show_migrations(app=None)`：用 `[X]/[ ]` 打印迁移状态。
- `run(app=None) -> List[str]`：按顺序应用未执行的迁移；通过 `backend.execute(...)` 写 `uui_migrations`。
- `_ensure_table(backend)` / `_app_dirs()` / `_apply_op(backend, op)` 等私有辅助。

## 函数

### `generate_migration(app, name='initial') -> dict`
根据当前 `_models` 注册表生成一个迁移 dict（`id` 用 `0001_<name>` 形式）。

### `run_migrations(app=None) -> List[str]`
便捷函数：构造 `MigrationEngine()` 并调用 `.run(app)`。