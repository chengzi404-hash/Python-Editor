# `modules/plugins/marketplace.py`

源文件路径：`modules/plugins/marketplace.py`

插件市场抽象与全局市场聚合器。结构与 `modules.highlighter.marketplace` / `modules.i18n.marketplace` 平行。

## 数据类

### `MarketplaceItem`（`@dataclass`）
- `id: str` / `name: str` / `version: str` / `author: str` / `description: str`
- `tags: List[str] = []`
- `download_url: str = ''`
- `thumbnail_url: str = ''`
- `rating: float = 0.0`
- `download_count: int = 0`

### `PluginMarketplacePackage`（`@dataclass`）
- `item: MarketplaceItem`
- `plugin_data: Optional[Dict[str, Any]] = None` — 与具体市场协议相关的附加数据。

### `MarketplaceSearchResult`
- `__init__(items, total=0, page=1, page_size=20)`
- 属性：`items` / `total` / `page` / `page_size` / `has_more`

## 抽象 / 聚合

### `MarketplaceProvider`（`ABC`）
- `name() -> str`
- `search(query='', tags=None, page=1, page_size=20) -> MarketplaceSearchResult`
- `get_item(item_id) -> Optional[MarketplaceItem]`
- `download(item, target_dir) -> str`

### `PluginMarketplace`
- `register_provider(provider)` / `unregister_provider(name)`
- `providers`（属性）
- `search(query='', tags=None, page=1, page_size=20) -> Dict[str, MarketplaceSearchResult]`
- `download_and_install(item, install_dir) -> Optional[str]`
- `get_provider(name) -> Optional[MarketplaceProvider]`

## 模块级单例

- `_marketplace: PluginMarketplace`
- `get_plugin_marketplace() -> PluginMarketplace`

## `__all__`

```python
['MarketplaceItem', 'PluginMarketplacePackage', 'MarketplaceSearchResult',
 'MarketplaceProvider', 'PluginMarketplace', 'get_plugin_marketplace']
```