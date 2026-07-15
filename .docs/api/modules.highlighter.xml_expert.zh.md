# `modules/highlighter/xml_expert.py`

源文件路径：`modules/highlighter/xml_expert.py`

XML / HTML 系列语言高亮器。

## 模块常量

- `_XML_TOKEN_RE`：命名组：`comment`（`<!--...-->`）/ `tag`（`<tagname ...>` 或 `</tagname>` 或 `<tagname/>`）/ `string`（双/单引号字符串）/ `entity`（`&name;` / `&#nn;` / `&#xhh;`）/ `operator`（`=`）/ `punctuation`（`<`/`>`/`/`）。

## 类

### `XmlHighlighterExpert(HighlighterExpert)`

#### 方法
- `get_languange_exts() -> list`：返回 `['xml', 'html', 'xhtml', 'xsd', 'xsl', 'svg']`。
- `highlight(block: HighlightBlock) -> HighlightBlock`：根据命名组生成 token，类型映射：
  - `comment` → `'comment'`；`tag` → `'tag'`；`string` → `'string'`；`entity` → `'keyword'`；`operator` → `'operator'`；`punctuation` → `'punctuation'`。