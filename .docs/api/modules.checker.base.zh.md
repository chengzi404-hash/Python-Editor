# `modules/checker/base.py`

源文件路径：`modules/checker/base.py`

定义了检查器抽象基类与输出数据结构。

## 类

### `OutputRow`（`@dataclass`）
一行诊断信息。

字段：
- `message: str` — 人类可读的诊断消息文本。
- `level: str` — 严重级别（`'error'` / `'warning'` / `'convention'` / `'notice'` / `'info'` 等）。

### `Output`（`@dataclass`）
单次检查的结果汇总。

字段：
- `file: str` — 被检查文件的绝对路径。
- `row: list[OutputRow]` — 产出的诊断信息列表。

### `Checker`（`ABC`）
所有检查器的抽象基类。

方法：
- `check(file: str) -> Output`（抽象）：对指定文件执行检查并返回 `Output`。子类必须实现。