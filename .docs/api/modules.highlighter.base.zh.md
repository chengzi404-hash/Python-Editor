# `modules/highlighter/base.py`

源文件路径：`modules/highlighter/base.py`

高亮器抽象定义：token 数据结构与基类契约。

## 数据类

### `HighlightToken`（`@dataclass`）
单个高亮区间。
- `start: int` — 区间起始字符偏移。
- `end: int` — 区间结束字符偏移（不含）。
- `type: str` — token 类型名（如 `'keyword'`/`'string'`/`'function'` 等），由主题映射到具体样式。

### `HighlightBlock`（`@dataclass`）
待高亮的代码块。
- `code: str` — 原始文本。
- `tokens: list[HighlightToken] | None = None` — 高亮结果，未高亮前为 `None`。

## 类

### `HighlighterExpert`（`ABC`）
所有语言高亮器的抽象基类。

抽象方法：
- `highlight(block: HighlightBlock) -> HighlightBlock`：对 `block.code` 进行分词，返回填充了 `tokens` 的新 `HighlightBlock`。
- `get_languange_exts() -> list`：返回该专家支持的文件扩展名列表。