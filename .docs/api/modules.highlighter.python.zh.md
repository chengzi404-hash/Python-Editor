# `modules/highlighter/python.py`

源文件路径：`modules/highlighter/python.py`

Python 高亮器。结合 `dom_cache` 在 `import` 语句中识别外部模块的成员类型。

## 模块常量

- `_KEYWORDS: set[str]` — Python 关键字集合，从 `data/keywords/python.json` 加载，失败时回退到内置列表。
- `_BUILTINS: set[str]` — 内建函数/类型集合（`abs`/`all`/`print`/`type` 等约 60 个）。
- `_STR_PREFIX`：字符串字面量前缀（`r/b/f/u` 及其组合，可选）。
- `_TOKEN_RE`：复合正则，命名组：`string` / `comment` / `decorator` / `number` / `module_attr`（含 `module_name` 与 `attr_name` 子组）/`identifier` / `operator` / `punctuation`。
- `_FROM_IMPORT_RE`：匹配 `from X import`。
- `_IMPORT_RE`：匹配 `import X`。

## 内部函数

### `_resolve_module_attr(module_name: str, attr_name: str, cached_libs: dict[str, LibraryDOM]) -> str | None`
尝试在缓存的 DOM 中解析 `module_name.attr_name`。
- 命中顶层类 → `'class'`；命中顶层函数 → `'function'`；命中子模块 → `'module'`；命中子模块中的类/函数 → `'class'` / `'function'`。
- 无法解析时返回 `None`。
- 解析期间按需通过 `get_or_load_lib_dom` 加载 DOM 并缓存。

### `_collect_imports(code: str) -> dict[str, LibraryDOM]`
扫描 `code` 中的 `import` / `from import`，对已存在缓存的顶层模块名预加载 DOM 并返回 `{name: LibraryDOM}`。

## 类

### `PythonHighlighterExpert(HighlighterExpert)`

#### 方法
- `get_languange_exts() -> list`：返回 `['py']`。
- `highlight(block: HighlightBlock) -> HighlightBlock`：调用 `_tokenize`。
- `_tokenize(code: str) -> list[HighlightToken]`：
  1. 字符串 → `'string'`；注释 → `'comment'`；装饰器 → `'decorator'`；数字 → `'number'`。
  2. `module_attr`：通过 `_resolve_module_attr` 决定 `class`/`function`/`module`，未解析则 `'identifier'`。
  3. `identifier`：关键字 → `'keyword'`；遇到 `def`/`class`/`from`/`import` 时记录 `pending_name`。
  4. 内建 → `'builtin'`。其他标识符若紧跟在 `def`/`class`/`from`/`import` 之后：
     - `def` 后 → 记入 `defined_functions`，标 `'function'`。
     - `class` 后 → 记入 `defined_classes`，标 `'class'`。
     - `from`/`import` 后 → 标 `'module'`。
  5. 后续遇到 `defined_functions`/`defined_classes` 中的名称分别标 `'function'` / `'class'`，否则 `'identifier'`。
  6. 操作符 → `'operator'`；标点 → `'punctuation'`。