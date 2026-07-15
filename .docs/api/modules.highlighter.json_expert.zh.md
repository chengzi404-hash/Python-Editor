# `modules/highlighter/json_expert.py`

源文件路径：`modules/highlighter/json_expert.py`

JSON 高亮器。基于 `_JSON_KEY_VALUE_RE` 组合正则一次扫描完成。

## 模块常量

- `_JSON_KEY_VALUE_RE`：命名组：`string` / `number` / `keyword`（`true|false|null`）/`punctuation`（`[]{}`）/`operator`（`:,`）/`comment`（`//...\n` 或 `/* ... */`）。

## 类

### `JsonHighlighterExpert(HighlighterExpert)`

#### 方法
- `get_languange_exts() -> list`：返回 `['json']`。
- `highlight(block: HighlightBlock) -> HighlightBlock`：使用 `is_key_position` 辅助判断字符串是否处于键名位置（紧跟 `{` 或 `,` 后），若是则标记为 `'key'`，否则 `'string'`；数字 `'number'`；关键字 `'keyword'`；标点 `'punctuation'`；`:,` `'operator'`；注释 `'comment'`。