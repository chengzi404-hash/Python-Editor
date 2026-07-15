# `modules/i18n/__init__.py`

源文件路径：`modules/i18n/__init__.py`

`modules.i18n` 包的公开入口。零依赖（仅 `json` + 标准库）的轻量级国际化支持，翻译源为 JSON 文件，可被运行时切换并通知监听器。

## 公开 API

```python
from modules.i18n import t, translator, get_translator

translator.set_language("en_US")
print(t("menu.file.new"))          # -> "New"
print(t("greeting", name="Alice")) # -> "Hello, Alice!"

def on_change(lang):
    print("language switched to", lang)
translator.add_listener(on_change)
```

## 重新导出

- `AVAILABLE_LANGUAGES` — 支持的语言代码元组。
- `I18nListener` — 监听器类型别名。
- `Translator` — 翻译器类。
- `get_translator()` — 获取全局翻译器实例。
- `t(key, default=None, **kwargs)` — 模块级快捷翻译函数。
- `language_marketplace` — 语言包市场子模块（提供 `MarketplaceItem`/`LanguagePackage`/`MarketplaceProvider`/`LanguageMarketplace`/`get_marketplace`）。

## `__all__`

```python
[
    "AVAILABLE_LANGUAGES",
    "I18nListener",
    "Translator",
    "get_translator",
    "t",
    "language_marketplace",
]
```