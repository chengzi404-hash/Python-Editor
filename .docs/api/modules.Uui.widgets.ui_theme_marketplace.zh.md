# `modules/Uui/widgets/ui_theme_marketplace.py`

源文件路径：`modules/Uui/widgets/ui_theme_marketplace.py`

UI 主题市场抽象。与其它 marketplace 平行的结构。

## 数据类

### `MarketplaceItem`（`@dataclass`）
- `id` / `name` / `version` / `author` / `description` / `tags` / `download_url` / `thumbnail_url` / `rating` / `download_count`。

### `UIThemePackage`（`@dataclass`）
- `item: MarketplaceItem`
- `theme_data: Dict[str, Any] = {}` — 主题颜色 / 字体字典（可直接喂给 `Theme` 子类）。

### `MarketplaceSearchResult`
- `__init__(items, total=0, page=1, page_size=20)`
- 属性：`items` / `total` / `page` / `page_size` / `has_more`。

## 抽象 / 聚合

### `MarketplaceProvider`（`ABC`）
- `name() -> str`
- `search(query='', tags=None, page=1, page_size=20) -> MarketplaceSearchResult`
- `get_item(item_id) -> Optional[MarketplaceItem]`
- `download(item, target_dir) -> str`

### `UIMarketplace`
- `register_provider(provider)` / `unregister_provider(name)`
- `providers`（属性）
- `search(query='', tags=None, page=1, page_size=20) -> Dict[str, MarketplaceSearchResult]`
- `download_and_install(item, install_dir) -> Optional[str]`
- `get_provider(name) -> Optional[MarketplaceProvider]`

## 模块级单例

- `_marketplace: UIMarketplace`
- `get_marketplace() -> UIMarketplace`

## `__all__`

```python
['MarketplaceItem', 'UIThemePackage', 'MarketplaceSearchResult',
 'MarketplaceProvider', 'UIMarketplace', 'get_marketplace']
```