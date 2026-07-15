# `modules/Uui/web/orm/backend/mysql.py`

源文件路径：`modules/Uui/web/orm/backend/mysql.py`

MySQL 后端实现。基于 `pymysql` 或 `mysqlclient`（具体驱动以源码为准）。

## 主要公开类

### `MysqlBackend(Backend)`
连接 `cfg['HOST']/['PORT']/['USER']/['PASSWORD']/['NAME']`，实现 `execute/fetchall` 等。