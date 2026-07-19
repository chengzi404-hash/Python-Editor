"""``modules.Uui.widgets.marketplace_window`` — Marketplace window.

Displays marketplace categories: plugins, themes, languages.
"""

from __future__ import annotations

import tkinter as tk

from core.language.highlighter import highlight_marketplace
from core.plugins import plugin_marketplace
from core.settings.i18n import language_marketplace, t

from . import theme
from .button import UButton
from .frame import UFrame
from .label import ULabel
from .list_view import UListView


class UMarketplaceWindow:
    """Marketplace window showing available extensions."""

    def __init__(self, editor) -> None:
        self._editor = editor

        self._win = tk.Toplevel(editor.window)
        self._win.title(t("marketplace.title"))
        self._win.configure(bg=theme.BG_BASE)
        self._win.geometry("800x600+200+100")
        self._win.transient(editor.window)
        self._win.resizable(True, True)

        self._current_category = "all"
        self._build()

    def _build(self) -> None:
        top = UFrame(self._win, variant="title")
        top.pack(fill=tk.X)

        search_frame = tk.Frame(top, bg=theme.BG_TITLE)
        search_frame.pack(fill=tk.X, padx=8, pady=4)

        self._search_var = tk.StringVar()
        search_entry = tk.Entry(
            search_frame,
            textvariable=self._search_var,
            bg=theme.BG_INPUT,
            fg=theme.FG_PRIMARY,
            insertbackground=theme.FG_PRIMARY,
            relief="flat",
            font=theme.LABEL_FONT,
        )
        search_entry.pack(fill=tk.X, ipady=4)
        self._search_var.set("")
        self._search_var.trace_add("write", lambda *_: self._on_search())

        body = UFrame(self._win, variant="base")
        body.pack(fill=tk.BOTH, expand=True)

        left = UFrame(body, variant="panel", width=200)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=(4, 2), pady=4)
        left.pack_propagate(False)

        ULabel(
            left,
            text=t("marketplace.categories"),
            variant="primary",
            bg=theme.BG_PANEL,
        ).pack(anchor="w", padx=8, pady=(8, 4))

        self._category_view = UListView(
            left,
            columns=[""],
            column_widths={"": 180},
            show_header=False,
            on_select=self._on_category_select,
        )
        self._category_view.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        categories = [
            {"": t("marketplace.category.all"), "cat_id": "all"},
            {"": t("marketplace.category.plugins"), "cat_id": "plugins"},
            {"": t("marketplace.category.themes"), "cat_id": "themes"},
            {"": t("marketplace.category.languages"), "cat_id": "languages"},
        ]
        self._category_view.set_data(categories)

        right = UFrame(body, variant="panel")
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(2, 4), pady=4)

        self._detail_label = ULabel(
            right,
            text=t("marketplace.select_category"),
            variant="secondary",
            bg=theme.BG_PANEL,
        )
        self._detail_label.pack(anchor="w", padx=8, pady=(8, 4))

        col_name = t("marketplace.col.name")
        col_author = t("marketplace.col.author")
        col_version = t("marketplace.col.version")
        self._items_view = UListView(
            right,
            columns=[col_name, col_author, col_version],
            column_widths={col_name: 200, col_author: 120, col_version: 80},
            show_header=True,
            on_select=self._on_item_select,
        )
        self._items_view.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        bottom = UFrame(self._win, variant="title")
        bottom.pack(fill=tk.X)

        self._info_label = ULabel(
            bottom,
            text="",
            variant="secondary",
            bg=theme.BG_TITLE,
        )
        self._info_label.pack(side=tk.LEFT, padx=10, pady=4)

        UButton(
            bottom,
            text=t("settings.button.close"),
            width=80,
            height=24,
            variant="default",
            command=self._win.destroy,
        ).pack(side=tk.RIGHT, padx=4, pady=4)

    def _load_items(self) -> None:
        items: list[dict] = []
        query = self._search_var.get().strip()

        if self._current_category == "all":
            items.extend(self._load_plugins(query))
            items.extend(self._load_themes(query))
            items.extend(self._load_languages(query))
        elif self._current_category == "plugins":
            items.extend(self._load_plugins(query))
        elif self._current_category == "themes":
            items.extend(self._load_themes(query))
        elif self._current_category == "languages":
            items.extend(self._load_languages(query))

        self._items_view.set_data(items)

        if items:
            self._info_label.config(text=f"{t('marketplace.items_count')}: {len(items)}")
        else:
            self._info_label.config(text=t("marketplace.no_items"))

    def _load_plugins(self, query: str) -> list[dict]:
        marketplace = plugin_marketplace.get_plugin_marketplace()
        results = marketplace.search(query=query)
        col_name = t("marketplace.col.name")
        col_author = t("marketplace.col.author")
        col_version = t("marketplace.col.version")

        items = []
        for provider_name, result in results.items():
            for item in result.items:
                items.append(
                    {
                        col_name: item.name,
                        col_author: item.author,
                        col_version: item.version,
                        "_item": item,
                        "_provider": provider_name,
                        "_type": "plugin",
                    }
                )
        return items

    def _load_themes(self, query: str) -> list[dict]:
        marketplace = highlight_marketplace.get_marketplace()
        results = marketplace.search(query=query)
        col_name = t("marketplace.col.name")
        col_author = t("marketplace.col.author")
        col_version = t("marketplace.col.version")

        items = []
        for provider_name, result in results.items():
            for item in result.items:
                items.append(
                    {
                        col_name: item.name,
                        col_author: item.author,
                        col_version: item.version,
                        "_item": item,
                        "_provider": provider_name,
                        "_type": "theme",
                    }
                )
        return items

    def _load_languages(self, query: str) -> list[dict]:
        marketplace = language_marketplace.get_marketplace()
        results = marketplace.search(query=query)
        col_name = t("marketplace.col.name")
        col_author = t("marketplace.col.author")
        col_version = t("marketplace.col.version")

        items = []
        for provider_name, result in results.items():
            for item in result.items:
                items.append(
                    {
                        col_name: item.name,
                        col_author: item.author,
                        col_version: item.version,
                        "_item": item,
                        "_provider": provider_name,
                        "_type": "language",
                    }
                )
        return items

    def _on_search(self) -> None:
        self._load_items()

    def _on_category_select(self, index: int, row: dict) -> None:
        cat_id = row.get("cat_id", "all")
        self._current_category = cat_id
        self._detail_label.config(text=f"{t('marketplace.category.selected')}: {row.get('', '')}")
        self._load_items()

    def _on_item_select(self, index: int, row: dict) -> None:
        col_name = t("marketplace.col.name")
        item_name = row.get(col_name, "")
        item = row.get("_item")
        if item:
            desc = getattr(item, "description", "")
            self._info_label.config(text=f"{item_name}: {desc}" if desc else item_name)
        else:
            self._info_label.config(text=item_name)


__all__ = ["UMarketplaceWindow"]
