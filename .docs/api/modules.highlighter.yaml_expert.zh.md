# `modules/highlighter/yaml_expert.py`

源文件路径：`modules/highlighter/yaml_expert.py`

YAML 高亮器。

## 模块常量

- `_YAML_TOKEN_RE`：命名组：
  - `comment` — `#...` 到行尾。
  - `keyword` — `true/false/yes/no/on/off/null/~`（含大小写变体）。
  - `number` — 有符号整数/浮点/科学计数。
  - `anchor` — `&name` / `*name`。
  - `tag` — `!!str` 等显式类型标签。
  - `operator` — `:` / `- ` / `? `。
  - `punctuation` — `[]{}|>,`。
  - `key` — 后面紧跟 `:` 的标识符（前瞻）。

## 类

### `YamlHighlighterExpert(HighlighterExpert)`

#### 方法
- `get_languange_exts() -> list`：返回 `['yaml', 'yml']`。
- `highlight(block: HighlightBlock) -> HighlightBlock`：按命名组生成 token，类型映射：
  - `comment` → `'comment'`；`keyword` → `'keyword'`；`number` → `'number'`；`anchor` → `'preprocessor'`；`tag` → `'type'`；`operator` → `'operator'`；`punctuation` → `'punctuation'`；`key` → `'key'`。