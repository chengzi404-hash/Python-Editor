# `modules/suggestion/base.py`

源文件路径：`modules/suggestion/base.py`

补全器抽象定义。

## 数据类

### `SuggestionBlock`（`@dataclass`）
- `code: str` — 待补全代码原文。
- `position: int` — 光标在 `code` 中的偏移。

### `DOMScope`（`@dataclass`）
基于用户代码的简易作用域树节点（按缩进划分）。
- `begin: int` / `end: int` — 行号区间（含 begin，不含 end）。
- `varibles: list` — 该作用域内的变量名（注意：字段名拼写为 `varibles`，沿用源码）。
- `functions: list` / `classes: list` — 函数/类名列表。
- `subDOM: list[DOMScope]` — 子作用域列表。

### `SuggestionItem`（`@dataclass`）
单条补全项。
- `label: str` — 显示文本。
- `priority: int = 0` — 数值越小优先级越高。
- `kind: str = ''` — 分类（`'keyword'` / `'builtin'` / `'function'` / `'class'` / `'variable'` 等）。

## 类

### `SuggestionExpert(ABC)`
所有语言补全器的抽象基类。

抽象方法：
- `suggest(block: SuggestionBlock) -> List[SuggestionItem]`：根据 `block.code` 与 `block.position` 给出补全列表。
- `get_languange_exts() -> list`：返回支持的文件扩展名列表。