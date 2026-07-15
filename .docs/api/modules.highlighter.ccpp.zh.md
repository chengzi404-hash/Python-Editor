# `modules/highlighter/ccpp.py`

源文件路径：`modules/highlighter/ccpp.py`

C/C++ 高亮器。基于一个组合正则 `_TOKEN_RE`（字符串/注释/预处理器/数字/标识符/操作符/标点）进行分词。

## 模块常量

- `_KEYWORDS: set[str]` — C++ 关键字集合，从 `data/keywords/c&cpp/cpp.json` 加载，失败时回退到内置列表。
- `_C_KEYWORDS: set[str]` — C 关键字集合，从 `data/keywords/c&cpp/c.json` 加载。
- `_BUILTINS: set[str]` — 常用内建标识符（`sizeof`/`offsetof`/`NULL`/`true`/`false`）。
- `_PP_KEYWORDS: set[str]` — 预处理器关键字（以 `#` 开头的指令）。
- `_STR_PREFIX`：字符串字面量前缀的可选部分（`u`/`U`/`L` 及其组合）。
- `_TOKEN_RE`：单一组合正则，按以下命名组匹配：`string` / `comment` / `multiline` / `preprocessor` / `number` / `identifier` / `operator` / `punctuation`。

## 类

### `CcppHighlighterExpert(HighlighterExpert)`

#### 方法
- `get_languange_exts() -> list`：返回 `['c', 'cpp', 'cc', 'cxx', 'h', 'hpp', 'hh']`。
- `highlight(block: HighlightBlock) -> HighlightBlock`：调用 `_tokenize` 并返回填充后的 `HighlightBlock`。
- `_tokenize(code: str) -> list[HighlightToken]`：
  - 字符串 → `'string'`；`//` 注释与 `/* */` 注释 → `'comment'`；预处理器指令 → `'preprocessor'`。
  - 标识符：若命中 C++ 或 C 关键字 → `'keyword'`；遇到 `struct`/`class`/`enum` 时记录位置；接着的下一个紧邻标识符被识别为 `'class'` 或 `'struct'`。
  - 命中 `_BUILTINS` → `'builtin'`；命中 `_PP_KEYWORDS` → `'preprocessor'`；否则 → `'identifier'`。
  - 操作符 → `'operator'`；标点（`()[]{},.;-`）→ `'punctuation'`。