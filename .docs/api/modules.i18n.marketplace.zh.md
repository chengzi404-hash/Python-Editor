# `modules/i18n/marketplace.py`

源文件路径：`modules/i18n/marketplace.py`

语言包市场抽象与全局市场聚合器。结构与 `modules.highlighter.marketplace` 平行。

## 数据类

### `MarketplaceItem`（`@dataclass`）
通用市场条目。字段：
- `id: str` / `name: str` / `version: str` / `author: str` / `description: str`
- `tags: List[str] = []`
- `download_url: str = ''`
- `thumbnail_url: str = ''`
- `rating: float = 0.0`
- `download_count: int = 0`

### `LanguagePackage`（`@dataclass`）
语言包条目，附翻译内容。
- `item: MarketplaceItem`
- `locale_data: Dict[str, str] = {}` — 与 `Translator._tables` 兼容的 `{key: text}`。

### `MarketplaceSearchResult`
搜索结果包装。
- `__init__(items, total=0, page=1, page_size=20)`
- 字段：`items` / `total` / `page` / `page_size`
- `has_more`（属性）— `page * page_size < total`。

## 抽象 / 聚合

### `MarketplaceProvider`（`ABC`）
抽象方法：
- `name() -> str`
- `search(query='', tags=None, page=1, page_size=20) -> MarketplaceSearchResult`
- `get_item(item_id: str) -> Optional[MarketplaceItem]`
- `download(item: MarketplaceItem, target_dir: str) -> str`

### `LanguageMarketplace`
- `register_provider(provider)` / `unregister_provider(name)`
- `providers`（属性）：已注册名称列表。
- `search(query='', tags=None, page=1, page_size=20) -> Dict[str, MarketplaceSearchResult]`：按 provider 分组聚合（异常被忽略）。
- `download_and_install(item, install_dir) -> Optional[str]`：按注册顺序尝试下载，首个成功返回路径。
- `get_provider(name) -> Optional[MarketplaceProvider]`

## 模块级单例

- `_marketplace: LanguageMarketplace`
- `get_marketplace() -> LanguageMarketplace`

## `__all__`

```python
['MarketplaceItem', 'LanguagePackage', 'MarketplaceSearchResult',
 'MarketplaceProvider', 'LanguageMarketplace', 'get_marketplace']
```