# `modules/suggestion/cpp.py`

源文件路径：`modules/suggestion/cpp.py`

C++ 代码补全器。与 `c.py` 结构平行，多了 `::` 作用域解析与更丰富的正则（模板/命名空间/enum）。

## 模块级常量

- 优先级常量：
  - `_PRIORITY_USER_FUNCTION = 5`
  - `_PRIORITY_USER_VARIABLE = 10`
  - `_PRIORITY_KEYWORD = 15`
  - `_PRIORITY_USER_CLASS = 20`
  - `_PRIORITY_BUILTIN = 30`
  - `_PRIORITY_HEADER = 35`
- `_CACHED_LISTS: dict` — 已加载的语言/类别列表缓存。

## 内部函数

### `_load_suggestion_list(lang, category) -> list[tuple[str, int]]`
读取 `data/suggestions/cpp/<category>_<lang>.json`，回退到 `en_US`，再回退到 `_FALLBACKS[category]`。下划线前缀优先级微调同 `c.py`。

### `_adjust_underscore_priority(label, priority) -> int`

### 兜底列表

- `_FALLBACK_KEYWORDS` — C++ 关键字（含 `alignas`/`co_await`/`requires` 等）；`class`/`enum`/`namespace`/`operator`/`struct`/`template`/`typedef`/`union` 优先级 20，其余 15。
- `_FALLBACK_BUILTINS` — `nullptr`/`printf`/`string`/`vector`/`make_shared` 等。
- `_FALLBACK_HEADERS` — `<algorithm>`/`<vector>`/`<iostream>` 等（35）。
- `_FALLBACKS = {'keywords': ..., 'builtins': ..., 'headers': ...}`。

## 正则

- `_CLASS_PATTERN` — 类/结构声明（含 `template <>`、`export`、`A::B` 限定、继承列表）。
- `_FUNC_PATTERN` — 函数定义（带 `template`/修饰符/返回类型/常量性/`override`/`noexcept`）。
- `_NAMESPACE_PATTERN` — 命名空间声明。
- `_ENUM_PATTERN` — `enum [class] NAME`。

## 类

### `CppSuggestionExpert(SuggestionExpert)`

#### 构造
- `__init__(lang: str = 'en_US')`。

#### 方法
- `get_languange_exts() -> list`：返回 `['cpp', 'cc', 'cxx', 'hpp', 'hh']`。

- `suggest(block: SuggestionBlock) -> list[SuggestionItem]`
  按上下文分派：
  - 光标前为 `::`（直接出现在词前）→ `_suggest_scope`。
  - 词前为 `::` → `_suggest_scope`。
  - 词前为 `.` → `_suggest_attributes(obj_name)`。
  - 词前为 `->` → `_suggest_attributes(obj_name)`。
  - 其余 → `_suggest_names(block)`。
  按 `prefix` 过滤后按 `(priority, label.lower())` 排序。

- `_suggest_names(block) -> list[SuggestionItem]`
  合并关键字/内建/头文件建议，并加入从作用域树提取的用户函数/类/变量。

- `_suggest_attributes(block, line_no, obj_name) -> list[SuggestionItem]`
  返回 C++ 常用容器/字符串方法（`begin`/`end`/`size`/`push_back`/`insert`/`find`/`substr` 等）。

- `_suggest_scope(block, line_no) -> list[SuggestionItem]`
  `::` 触发的命名空间补全：合并作用域树中的类/函数，再加上常见 C++ 名字（`std`/`cout`/`cin`/`endl`/`string`/`vector`/`map`/`set`）。

- `_collect_entries(code)`（静态）：扫描 4 个正则，过滤掉 `if/while/for/switch/catch/sizeof` 等关键字名；按缩进层次推断结束行。

- `_build_scope_tree(code)`（静态）：构建嵌套 `DOMScope` 树；`class`/`namespace` 进入 `classes`，其余进入 `functions`。