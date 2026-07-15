# `modules/highlighter/__init__.py`

源文件路径：`modules/highlighter/__init__.py`

`modules.highlighter` 包的公开入口。汇总各语言高亮器、主题、市场与 Python 库 DOM 缓存。

## 重新导出

### 基础数据结构 / 抽象类
- `HighlightToken` — `(start, end, type)` 描述一个高亮区间。
- `HighlightBlock` — 待高亮的代码块及其 token 列表。
- `HighlighterExpert` — 高亮器抽象基类。

### 语言高亮器
- `PythonHighlighterExpert` — Python（`.py`）。
- `CcppHighlighterExpert` — C/C++（`.c`/`.cpp`/`.cc`/`.cxx`/`.h`/`.hpp`/`.hh`）。
- `JsonHighlighterExpert` — JSON（`.json`）。
- `XmlHighlighterExpert` — XML/HTML/XHTML/XSD/XSL/SVG。
- `YamlHighlighterExpert` — YAML（`.yaml`/`.yml`）。
- `LogHighlighterExpert` — 日志（`.log`/`.txt`/`.logs`）。

### 子模块
- `highlight_themes` — 内置主题集合与切换 API。
- `highlight_marketplace` — 主题市场接口与全局单例。

### Python 库 DOM 缓存（来自 `dom_cache.py`）
- `LibraryDOM` — 表示已安装库的公开结构（类/函数/子模块）。
- `ensure_lib_cache(name)` — 扫描并写入单个库的缓存。
- `get_lib_dom(name)` — 读取已缓存的 `LibraryDOM`，缺失返回 `None`。
- `get_or_load_lib_dom(name)` — 优先缓存，否则扫描。
- `build_full_cache(progress_callback=None)` — 全量扫描所有可见包。
- `cache_exists(name)` — 判断缓存是否存在。
- `invalidate_lib_cache(name)` — 删除某库的缓存。

## `__all__`

```python
[
    'HighlightToken', 'HighlightBlock', 'HighlighterExpert',
    'PythonHighlighterExpert', 'CcppHighlighterExpert',
    'JsonHighlighterExpert', 'XmlHighlighterExpert',
    'YamlHighlighterExpert', 'LogHighlighterExpert',
    'highlight_themes', 'highlight_marketplace',
    'LibraryDOM', 'ensure_lib_cache', 'get_lib_dom',
    'get_or_load_lib_dom', 'build_full_cache',
    'cache_exists', 'invalidate_lib_cache',
]
```