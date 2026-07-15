# `modules/suggestion/c.py`

源文件路径：`modules/suggestion/c.py`

C 语言的代码补全器。基于 `data/suggestions/c/<category>_<lang>.json` 加载建议列表（`keywords` / `builtins` / `headers` / `preprocessor`），结合用户代码中的作用域树和点号/箭头触发。

## 模块级常量

- 优先级常量（数值越小越靠前）：
  - `_PRIORITY_USER_FUNCTION = 5`
  - `_PRIORITY_USER_VARIABLE = 10`
  - `_PRIORITY_KEYWORD = 15`
  - `_PRIORITY_USER_CLASS = 20`
  - `_PRIORITY_BUILTIN = 30`
  - `_PRIORITY_HEADER = 35`
- `_CACHED_LISTS: dict` — 已加载的语言/类别列表缓存（`"<lang>:<category>"` → `[(label, priority), ...]`）。

## 内部函数

### `_load_suggestion_list(lang, category) -> list[tuple[str, int]]`
读取 `data/suggestions/c/<category>_<lang>.json`，缺失时回退 `en_US`，再缺失则使用 `_FALLBACKS[category]`。每个 item 可以是 dict（`label` + 可选 `priority`）或裸字符串（默认 `_PRIORITY_KEYWORD`）。读取后会调用 `_adjust_underscore_priority`：
- `'__'` 前缀：`priority + 20`
- `'_'` 前缀（不是 `__`）：`priority + 10`

### `_adjust_underscore_priority(label, priority) -> int`
按前缀下划线数量微调优先级。

### 兜底列表

- `_FALLBACK_KEYWORDS` / `_FALLBACK_BUILTINS` / `_FALLBACK_HEADERS` / `_FALLBACK_PREPROCESSOR`（统一进入 `_FALLBACKS` 字典）。
  - `keywords`：标准 C 关键字（部分 `struct`/`union`/`enum`/`typedef` 用 20）。
  - `builtins`：`printf`/`malloc`/`memcpy`/`fopen` 等。
  - `headers`：`stdio.h`/`stdlib.h`/`string.h` 等（`35`）。
  - `preprocessor`：`#define`/`#include`/`#ifdef` 等（`15`）。

## 正则

- `_STRUCT_CLASS_PATTERN` — `struct`/`union`/`enum` 声明（含可选 typedef）。
- `_FUNC_PATTERN` — 函数定义（含修饰符前缀）。
- `_TYPEDEF_PATTERN` — `typedef ...`。

## 类

### `CSuggestionExpert(SuggestionExpert)`

#### 构造
- `__init__(lang: str = 'en_US')` — 记录当前语言，影响建议列表加载。

#### 方法
- `get_languange_exts() -> list`：返回 `['c', 'h']`。

- `suggest(block: SuggestionBlock) -> list[SuggestionItem]`
  根据光标上下文分派：
  - 光标前为 `.` → `_suggest_attributes(obj_name)`。
  - 光标前为 `->` → `_suggest_attributes(obj_name)`。
  - 其余 → `_suggest_names(block)`。
  全部结果按 `prefix`（大小写不敏感前缀）过滤，再按 `(priority, label.lower())` 排序。

- `_suggest_names(block) -> list[SuggestionItem]`
  加载当前语言的 4 类建议列表（keyword/builtin/header/preprocessor），按优先级合并；遍历用户作用域树 `_build_scope_tree`，把其中 `functions`/`classes`/`varibles` 加入用户级条目。

- `_suggest_attributes(block, line_no, obj_name) -> list[SuggestionItem]`
  返回一组常用属性名（`x`/`y`/`width`/`data`/`next`/`size` 等），全部 `_PRIORITY_BUILTIN`。

- `_collect_entries(code) -> list[tuple[int, int, str, str, int]]`（静态）
  用三个正则扫描整篇代码，返回 `(line_no, indent, kind, name, end_line)` 列表，并按缩进层次为每条记录推断结束行。

- `_build_scope_tree(code) -> DOMScope`（静态）
  基于 `_collect_entries` 按缩进构建嵌套 `DOMScope` 树；`class`/`typedef` 进入 `classes`，否则进入 `functions`。