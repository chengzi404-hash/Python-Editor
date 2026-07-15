# `modules/Uui/web/orm/backend/sqlite.py`

源文件路径：`modules/Uui/web/orm/backend/sqlite.py`

SQLite 后端实现。具体行为请参考源文件：
- 通过 `sqlite3` 标准库连接 `cfg['NAME']`。
- 占位符风格 `'?'`，自动 commit/rollback 与 `row_factory` 配置。

## 主要公开类

### `SqliteBackend(Backend)`
继承 `Backend`，实现 `connection / close / execute / executemany / fetchall / fetchone` 等。