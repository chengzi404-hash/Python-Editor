# `modules/highlighter/marketplace.py`

源文件路径：`modules/highlighter/marketplace.py`

主题市场抽象与全局市场聚合器。

## 数据类

### `MarketplaceItem`（`@dataclass`）
一个市场条目。
- `id: str` / `name: str` / `version: str` / `author: str` / `description: str`
- `tags: List[str] = []`
- `download_url: str = ''`
- `thumbnail_url: str = ''`
- `rating: float = 0.0`
- `download_count: int = 0`

### `HighlightThemePackage`（`@dataclass`）
主题市场条目，附带 tokens。
- `item: MarketplaceItem`
- `tokens: Dict[str, Dict[str, Any]] = {}` — token 名 → 样式字典。

### `MarketplaceSearchResult`
搜索结果包装。
- `__init__(items, total=0, page=1, page_size=20)`
- 属性：`items`、`total`、`page`、`page_size`
- `has_more`（属性）— 是否还有下一页（`page * page_size < total`）。

## 抽象 / 聚合

### `MarketplaceProvider`（`ABC`）
市场提供者接口。
- `name() -> str`（抽象）：提供者唯一名称。
- `search(query='', tags=None, page=1, page_size=20) -> MarketplaceSearchResult`（抽象）。
- `get_item(item_id: str) -> Optional[MarketplaceItem]`（抽象）。
- `download(item: MarketplaceItem, target_dir: str) -> str`（抽象）：下载到目标目录，返回路径。

### `HighlightThemeMarketplace`
多提供者聚合器。
- `register_provider(provider)` — 按 `provider.name()` 注册。
- `unregister_provider(name)` — 注销提供者。
- `providers`（属性）：已注册提供者名称列表。
- `search(query='', tags=None, page=1, page_size=20) -> Dict[str, MarketplaceSearchResult]`：调用每个提供者的 `search`，异常被静默忽略，结果以提供者名分组。
- `download_and_install(item, install_dir) -> Optional[str]`：按注册顺序尝试各提供者的 `download`，首个成功的返回路径，全部失败返回 `None`。
- `get_provider(name) -> Optional[MarketplaceProvider]`。

## 模块级单例

- `_marketplace: HighlightThemeMarketplace` — 进程级实例。
- `get_marketplace() -> HighlightThemeMarketplace` — 返回上述单例。

## `__all__`

```python
[
    'MarketplaceItem', 'HighlightThemePackage',
    'MarketplaceSearchResult', 'MarketplaceProvider',
    'HighlightThemeMarketplace', 'get_marketplace',
]
```