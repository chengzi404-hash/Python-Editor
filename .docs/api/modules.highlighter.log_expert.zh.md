# `modules/highlighter/log_expert.py`

源文件路径：`modules/highlighter/log_expert.py`

日志文件高亮器。基于 `_LOG_TOKEN_RE` 一次扫描识别时间戳、日志级别、数字、关键字和堆栈帧。

## 模块常量

- `_LOG_TOKEN_RE`：命名组：
  - `timestamp` — ISO/类 syslog/时分秒 三种形式。
  - `level` — `CRITICAL`/`FATAL`。
  - `level_error` — `ERROR`/`SEVERE`。
  - `level_warn` — `WARN`/`WARNING`。
  - `level_info` — `INFO`/`INFORMATION`。
  - `level_debug` — `DEBUG`/`TRACE`/`VERBOSE`。
  - `number` — `\d+`。
  - `keyword` — `at`/`in`/`line`/`file`/`raised`/`Traceback`/`traceback`。
  - `comment` — 堆栈帧与 `Traceback ...` 段。

## 类

### `LogHighlighterExpert(HighlighterExpert)`

#### 方法
- `get_languange_exts() -> list`：返回 `['log', 'txt', 'logs']`。
- `highlight(block: HighlightBlock) -> HighlightBlock`：将每个命名组映射到对应类型：
  - `level*` → `level_critical` / `level_error` / `level_warn` / `level_info` / `level_debug`。
  - `timestamp` → `'timestamp'`；`number` → `'number'`；`keyword` → `'keyword'`；`comment` → `'comment'`。