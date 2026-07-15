# `modules/suggestion/python.py`

源文件路径：`modules/suggestion/python.py`

Python 代码补全器。包含关键字/内建补全、用户作用域树、点号属性补全、`from X import` 模块成员补全与 `self.xxx` 类内方法补全。

## 模块级常量

- 优先级常量：
  - `_PRIORITY_USER_FUNCTION = 5`
  - `_PRIORITY_USER_VARIABLE = 10`
  - `_PRIORITY_IMPORT_FROM = 12` — 来自 `from X import` 的成员。
  - `_PRIORITY_KEYWORD = 15`（其中 `lambda` 用 16）。
  - `_PRIORITY_USER_CLASS = 20`
  - `_PRIORITY_BUILTIN = 30`
- `_CACHED_LISTS: dict` — 已加载的语言/类别列表缓存。

## 公开常量

- `KEYWORDS: set[str]` — Python 关键字集合。
- `BUILTIN_FUNCTIONS: set[str]` — 内建函数集合。
- `BUILTIN_CLASSES: set[str]` — 内建类集合。
- `BUILTIN_PROPERTIES: set[str]` — 内建常量/属性集合（`True`/`None`/`__name__`/`__file__` 等）。
- `BUILTIN_ATTRS: dict[str, list[str]]` — 按类型映射的常用属性名（`str`/`list`/`dict`/`int`/`float`/`set`/`tuple`/`bytes`/`bool`）。

## 内部函数

### `_load_suggestion_list(lang, category) -> list[tuple[str, int]]`
读取 `data/suggestions/python/<category>_<lang>.json`，回退到 `en_US`，再回退到 `_FALLBACKS[category]`。下划线前缀优先级微调：
- `__` 前缀：+20
- `_` 前缀（不是 `__`）：+10

### `_adjust_underscore_priority(label, priority) -> int`

### 兜底列表

- `_FALLBACK_KEYWORDS` — Python 关键字（`class`/`def` 默认 20，`lambda` 用 16）。
- `_FALLBACK_BUILTINS` — 内建函数/类/常量（合并到一个列表，优先级 30）。
- `_FALLBACKS = {'keywords': ..., 'builtins': ...}`。

## 正则

- `CLASS_PATTERN` — 类声明 `class NAME(...):`。
- `FUNC_PATTERN` — 函数定义 `def NAME(...):`（支持 `async`/`->`）。

## 类

### `PythonSuggestionExpert(SuggestionExpert)`

#### 构造
- `__init__(lang: str = 'en_US')`。

#### 方法
- `get_languange_exts() -> list`：返回 `['py']`。

- `suggest(block: SuggestionBlock) -> list[SuggestionItem]`
  1. 找到光标所在行、列、当前词前缀 `prefix`。
  2. 若词前为 `.`：
     - 反向拼接整段点号路径为 `full_obj_name`。
     - 若是 `self` → 类内方法补全。
     - 否则调用 `_suggest_attributes`。
  3. 否则调用 `_suggest_names(block, line_no)`。
  4. 按 `prefix` 过滤（若 `prefix` 是关键字则不过滤，避免把 `import` 之类过滤掉）。
  5. 按 `(priority, label.lower())` 排序返回。

- `_suggest_names(block, line_no) -> list[SuggestionItem]`
  - 合并关键字与内建建议。
  - 调用 `_add_import_from_suggestions` 合并 `from X import` 引入的成员。
  - 构造用户作用域树 `_build_scope_tree` 并递归进入光标所在作用域，把其中的 `functions`/`classes`/`varibles` 与 `_extract_variables` 提取的局部变量加入建议。

- `_add_import_from_suggestions(block, line_no, suggestions) -> None`
  扫描整个文件的 `from <module> import` 行，使用 `get_lib_dom(module)`（只读缓存）合并其 `submodules`/`functions`/`classes`（仅在缓存中存在时使用，不在补全时扫描）。`os.path` 会被特殊处理为子模块名 `path`。

- `_suggest_attributes(block, line_no, obj_name, before_cursor='') -> list[SuggestionItem]`
  - `self` → 枚举所在类的方法列表 + 默认对象属性。
  - 内建类型 (`str/list/dict/...`) → `BUILTIN_ATTRS[type]`。
  - `os.path` 特殊处理：实时 `import os.path` 并枚举其公开属性（因为 `pkgutil` 无法发现）。
  - 形如 `pkg.sub` → 用 `cache_exists` + `parent_dom.submodule_contents` 解析；若命中则返回其函数/类。
  - 单层名 → `get_lib_dom(obj_name)` 命中则返回函数/类/子模块；`os` 特殊处理会补上 `path`。
  - 否则返回通用默认属性集合。

- `_enclosing_class_methods(block, line_no) -> list[str]`
  向上查找最近的 `class` 头，再向下收集缩进更大的 `def` 名；最后拼接通用对象属性。

- `_extract_variables(code, begin, end) -> list[str]`（静态）
  在 `[begin, end)` 行范围内匹配：
  - `name = ...` 形式的赋值（含 `name: type = ...`）。
  - `for name in` / `with ... as name` / `except ... as name`。
  - 函数定义形参列表（去掉 `: type` 和默认值，强制加入 `self` / `cls`）。

- `_collect_entries(code) -> list[tuple[int, int, str, str, int]]`（静态）
  用 `CLASS_PATTERN`/`FUNC_PATTERN` 扫描，返回 `(line_no, indent, kind, name, end_line)` 并按缩进推断结束行。

- `iter_classes(block) -> list[str]`（静态）
- `iter_function(block) -> list[str]`（静态）

- `_build_scope_tree(code) -> DOMScope`（静态）
  按缩进构建嵌套 `DOMScope`：class 进入 `classes`，function 进入 `functions`。

- `find_domin(block, position) -> DOMScope`（静态）
  沿 `subDOM.begin <= position < subDOM.end` 找到最深匹配的 `DOMScope`。