from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class MarketplaceItem:
    id: str
    name: str
    version: str
    author: str
    description: str
    tags: list[str] = field(default_factory=list)
    download_url: str = ''
    thumbnail_url: str = ''
    rating: float = 0.0
    download_count: int = 0


@dataclass
class PluginMarketplacePackage:
    item: MarketplaceItem
    plugin_data: dict[str, Any] | None = None


class MarketplaceSearchResult:
    def __init__(
        self,
        items: list[MarketplaceItem],
        total: int = 0,
        page: int = 1,
        page_size: int = 20,
    ):
        self.items = items
        self.total = total
        self.page = page
        self.page_size = page_size

    @property
    def has_more(self) -> bool:
        return self.page * self.page_size < self.total


class MarketplaceProvider(ABC):
    @abstractmethod
    def name(self) -> str:
        ...

    @abstractmethod
    def search(
        self,
        query: str = '',
        tags: list[str] | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> MarketplaceSearchResult:
        ...

    @abstractmethod
    def get_item(self, item_id: str) -> MarketplaceItem | None:
        ...

    @abstractmethod
    def download(self, item: MarketplaceItem, target_dir: str) -> str:
        ...


class PluginMarketplace:
    def __init__(self):
        self._providers: dict[str, MarketplaceProvider] = {}

    def register_provider(self, provider: MarketplaceProvider) -> None:
        self._providers[provider.name()] = provider

    def unregister_provider(self, name: str) -> None:
        self._providers.pop(name, None)

    @property
    def providers(self) -> list[str]:
        return list(self._providers.keys())

    def search(
        self,
        query: str = '',
        tags: list[str] | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, MarketplaceSearchResult]:
        results: dict[str, MarketplaceSearchResult] = {}
        for name, provider in self._providers.items():
            try:
                results[name] = provider.search(query, tags, page, page_size)
            except Exception:
                pass
        return results

    def download_and_install(
        self,
        item: MarketplaceItem,
        install_dir: str,
    ) -> str | None:
        for provider in self._providers.values():
            try:
                pkg_path = provider.download(item, install_dir)
                return pkg_path
            except Exception:
                continue
        return None

    def get_provider(self, name: str) -> MarketplaceProvider | None:
        return self._providers.get(name)


_marketplace: PluginMarketplace = PluginMarketplace()


def get_plugin_marketplace() -> PluginMarketplace:
    return _marketplace


__all__ = [
    'MarketplaceItem',
    'MarketplaceProvider',
    'MarketplaceSearchResult',
    'PluginMarketplace',
    'PluginMarketplacePackage',
    'get_plugin_marketplace',
]
