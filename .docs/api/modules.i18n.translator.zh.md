# `modules/i18n/translator.py`

源文件路径：`modules/i18n/translator.py`

翻译器核心实现。翻译源为 `data/i18n/locales/<lang>.json`，内容形如 `{key: text}`。

## 模块级符号

- `_LOCALE_DIR = i18n_path("locales")` — 语言包目录。
- `AVAILABLE_LANGUAGES: tuple = ("zh_CN", "en_US")` — 内置支持的语言代码。
- `I18nListener = Callable[[str], None]` — 监听器类型别名，参数为新语言代码。

## 模块级函数

### `_load_locale(lang: str) -> Dict[str, str]`
读取 `<lang>.json` 并规范化为 `{key: text}` 字典。文件缺失、解析错误或顶层不是 dict 时返回空 dict；写入始终是 `str`。

### `get_translator() -> Translator`
返回模块级 `_TRANSLATOR` 单例。

### `t(key: str, default: Optional[str] = None, **kwargs: Any) -> str`
等价于 `get_translator().translate(key, default=default, **kwargs)`。

## 类

### `Translator`
全局翻译器。线程安全，支持语言切换监听、运行时重载与 `str.format` 占位符。

类属性：
- `_FALLBACK_LANG = "en_US"` — 当当前语言缺翻译时回退的目标。

实例字段（构造时初始化）：
- `_lock: threading.RLock` — 保护内部状态。
- `_current: str = _FALLBACK_LANG` — 当前语言。
- `_tables: Dict[str, Dict[str, str]]` — 语言包缓存。
- `_listeners: List[I18nListener]` — 监听器列表。
- `_changing: bool` — 防止重入的标志位。

构造时遍历 `AVAILABLE_LANGUAGES` 加载所有语言包。

#### 属性
- `current_language: str` — 当前语言代码。
- `available_languages: tuple` — 等于 `AVAILABLE_LANGUAGES`。

#### 方法
- `set_language(lang: str) -> bool`
  切换语言。仅当 `lang ∈ AVAILABLE_LANGUAGES`、非重入、且与当前不同时生效。切换成功后复制监听器列表并在锁外依次调用（异常被忽略）。返回 `True` 表示成功切换。

- `add_listener(callback: I18nListener) -> None`
  注册监听器；重复注册会被忽略。

- `remove_listener(callback: I18nListener) -> None`
  注销监听器；未找到时忽略。

- `reload() -> None`
  从磁盘重读所有语言包，便于开发期热更新。

- `has(key: str, locale: Optional[str] = None) -> bool`
  查询指定/当前语言下某 key 是否存在翻译。

- `translate(key: str, default: Optional[str] = None, locale: Optional[str] = None, **kwargs: Any) -> str`
  查询翻译：优先 `locale`（或当前语言）→ 缺翻译回退到 `en_US` → 仍无则用 `default` 否则用 `key` 本身。找到文本后若传入 `kwargs` 则执行 `text.format(**kwargs)`，占位符不匹配时返回原文本而非抛错。

## `__all__`

```python
["AVAILABLE_LANGUAGES", "I18nListener", "Translator", "get_translator", "t"]
```