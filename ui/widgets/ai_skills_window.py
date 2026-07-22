"""``modules.Uui.widgets.ai_skills_window`` — AI Skills marketplace window.

Lists installed + available skills. User can install/uninstall. Installed
skills live under ``<settings_dir>/ai/skills/<id>.json`` (see
:class:`core.ai.skills.AISkillRegistry`).
"""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from typing import TYPE_CHECKING

from core.ai import (
    AISkill,
    AISkillMarketplaceProvider,
    AISkillRegistry,
    install_skill_from_marketplace,
)
from core.plugins.marketplace import MarketplaceItem
from core.settings.i18n import t

from . import theme
from .button import UButton
from .frame import UFrame
from .label import ULabel
from .list_view import UListView
from .text import UText

if TYPE_CHECKING:
    pass


class AISkillsWindow:
    """Window for browsing and managing installed AI skills."""

    def __init__(
        self,
        editor,
        *,
        registry: AISkillRegistry,
        provider: AISkillMarketplaceProvider,
        on_skill_activated: Callable[[AISkill | None], None] | None = None,
    ) -> None:
        self._editor = editor
        self._registry = registry
        self._provider = provider
        self._on_activated = on_skill_activated

        self._win = tk.Toplevel(editor.window)
        self._win.title(t("ai.skills.title"))
        self._win.configure(bg=theme.BG_BASE)
        self._win.geometry("780x560+220+140")
        self._win.transient(editor.window)
        self._win.resizable(True, True)

        self._current_section = "installed"
        self._installed_items: list[AISkill] = []
        self._available_items: list = []

        self._build()

    # ---- Construction ----------------------------------------------------

    def _build(self) -> None:
        header = UFrame(self._win, variant="title")
        header.pack(fill=tk.X)

        self._search_var = tk.StringVar()
        search_entry = tk.Entry(
            header,
            textvariable=self._search_var,
            bg=theme.BG_INPUT,
            fg=theme.FG_PRIMARY,
            insertbackground=theme.FG_PRIMARY,
            relief="flat",
            font=theme.LABEL_FONT,
        )
        search_entry.pack(fill=tk.X, padx=8, pady=6, ipady=4)
        self._search_var.set("")
        self._search_var.trace_add("write", lambda *_: self._reload_lists())

        body = UFrame(self._win, variant="base")
        body.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)

        left = UFrame(body, variant="panel", width=200)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=(4, 2), pady=4)
        left.pack_propagate(False)

        ULabel(left, text=t("marketplace.categories"), variant="primary", bg=theme.BG_PANEL).pack(
            anchor="w", padx=8, pady=(8, 4)
        )

        self._section_view = UListView(
            left,
            columns=[""],
            column_widths={"": 180},
            show_header=False,
            on_select=self._on_section_select,
        )
        self._section_view.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        self._section_view.set_data(
            [
                {"": t("ai.skills.installed_section"), "section": "installed"},
                {"": t("ai.skills.browse_section"), "section": "available"},
            ]
        )

        right = UFrame(body, variant="panel")
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(2, 4), pady=4)

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

        detail_frame = UFrame(self._win, variant="title", height=140)
        detail_frame.pack(fill=tk.X, padx=0, pady=0)
        detail_frame.pack_propagate(False)

        self._detail_text = UText(detail_frame, width=40, height=6, wrap="word", show_line_numbers=False)
        self._detail_text.pack(fill=tk.BOTH, expand=True, padx=8, pady=6)
        self._detail_text.config(state="disabled")

        bottom = UFrame(self._win, variant="title")
        bottom.pack(fill=tk.X)

        self._action_btn = UButton(
            bottom,
            text=t("ai.skills.detail.install"),
            width=100,
            height=24,
            variant="primary",
            command=self._on_action_clicked,
        )
        self._action_btn.pack(side=tk.LEFT, padx=8, pady=4)

        self._activate_btn = UButton(
            bottom,
            text="Activate",
            width=90,
            height=24,
            variant="default",
            command=self._on_activate_clicked,
        )
        self._activate_btn.pack(side=tk.LEFT, padx=4, pady=4)

        self._info_label = ULabel(bottom, text="", variant="secondary", bg=theme.BG_TITLE)
        self._info_label.pack(side=tk.LEFT, padx=10, pady=4)

        UButton(
            bottom,
            text=t("settings.button.close"),
            width=80,
            height=24,
            variant="default",
            command=self._win.destroy,
        ).pack(side=tk.RIGHT, padx=4, pady=4)

        self._reload_lists()

    # ---- Loading ---------------------------------------------------------

    def _reload_lists(self) -> None:
        self._installed_items = self._registry.list()
        col_name = t("marketplace.col.name")
        col_author = t("marketplace.col.author")
        col_version = t("marketplace.col.version")

        if self._current_section == "installed":
            data = [
                {
                    col_name: s.name,
                    col_author: s.author,
                    col_version: s.version,
                    "_skill_id": s.id,
                    "_skill": s,
                    "_type": "installed",
                }
                for s in self._installed_items
            ]
        else:
            query = self._search_var.get().strip()
            result = self._provider.search(query=query)
            self._available_items = result.items
            data = [
                {
                    col_name: item.name,
                    col_author: item.author,
                    col_version: item.version,
                    "_item": item,
                    "_type": "available",
                }
                for item in self._available_items
            ]
        self._items_view.set_data(data)
        self._info_label.config(
            text=f"{len(data)} {t('marketplace.items_count')}"
            if data
            else t("marketplace.no_items")
        )
        self._update_action_button()

    # ---- Selection -------------------------------------------------------

    def _on_section_select(self, _index: int, row: dict) -> None:
        self._current_section = row.get("section", "installed")
        self._reload_lists()

    def _on_item_select(self, _index: int, row: dict) -> None:
        if not row:
            return
        if row.get("_type") == "installed":
            skill = row.get("_skill")
            if skill is None:
                return
            self._render_detail_installed(skill)
        else:
            item = row.get("_item")
            if item is None:
                return
            self._render_detail_available(item)
        self._update_action_button()

    def _render_detail_installed(self, skill: AISkill) -> None:
        lines = [f"{skill.name} ({skill.version})", f"by {skill.author or '—'}"]
        if skill.description:
            lines.append("")
            lines.append(skill.description)
        if skill.tags:
            lines.append("")
            lines.append(t("ai.skills.detail.tags", tags=", ".join(skill.tags)))
        if skill.system_prompt:
            lines.append("")
            lines.append(f"{t('ai.skills.system_prompt')}:")
            lines.append(skill.system_prompt)
        if skill.mcp_servers:
            lines.append("")
            lines.append(f"{t('ai.skills.mcp_servers')}:")
            for server in skill.mcp_servers:
                lines.append(f"  • {server.name} ({server.transport}): {server.command}")
        self._set_detail("\n".join(lines))

    def _render_detail_available(self, item) -> None:
        lines = [f"{item.name} ({item.version})", f"by {item.author or '—'}"]
        if item.description:
            lines.append("")
            lines.append(item.description)
        if item.tags:
            lines.append("")
            lines.append(t("ai.skills.detail.tags", tags=", ".join(item.tags)))
        self._set_detail("\n".join(lines))

    def _set_detail(self, text: str) -> None:
        self._detail_text.config(state="normal")
        self._detail_text.clear()
        self._detail_text._text.insert("1.0", text)
        self._detail_text.config(state="disabled")

    # ---- Action button ---------------------------------------------------

    def _update_action_button(self) -> None:
        if self._current_section == "installed":
            self._action_btn.config(text=t("ai.skills.detail.uninstall"))
            installed = bool(self._get_selected_skill_id())
            self._action_btn.config(state="normal" if installed else "disabled")
            self._activate_btn.config(
                state="normal" if self._get_selected_skill_id() != self._registry.active_id else "disabled"
            )
        else:
            self._action_btn.config(text=t("ai.skills.detail.install"))
            self._action_btn.config(state="normal" if self._get_selected_item() is not None else "disabled")
            self._activate_btn.config(state="disabled")

    def _get_selected_skill_id(self) -> str | None:
        row = self._items_view.selected_value()
        if not row:
            return None
        if row.get("_type") != "installed":
            return None
        return row.get("_skill_id")

    def _get_selected_item(self) -> MarketplaceItem | None:
        row = self._items_view.selected_value()
        if not row:
            return None
        if row.get("_type") != "available":
            return None
        item = row.get("_item")
        if isinstance(item, MarketplaceItem):
            return item
        return None

    def _on_action_clicked(self) -> None:
        if self._current_section == "installed":
            self._uninstall_selected()
        else:
            self._install_selected()

    def _install_selected(self) -> None:
        item = self._get_selected_item()
        if item is None:
            return
        skill = install_skill_from_marketplace(self._provider, self._registry, item.id)
        if skill is None:
            self._info_label.config(text=t("ai.skills.installed", name=item.name))
        else:
            self._info_label.config(text=t("ai.skills.installed", name=skill.name))
        self._reload_lists()

    def _uninstall_selected(self) -> None:
        skill_id = self._get_selected_skill_id()
        if skill_id is None:
            return
        skill = self._registry.get(skill_id)
        name = skill.name if skill else skill_id
        if self._registry.uninstall(skill_id):
            self._info_label.config(text=t("ai.skills.removed", name=name))
        self._reload_lists()

    def _on_activate_clicked(self) -> None:
        skill_id = self._get_selected_skill_id()
        if skill_id is None:
            return
        activated = self._registry.activate(skill_id)
        if self._on_activated is not None:
            self._on_activated(activated)
        self._reload_lists()


__all__ = ["AISkillsWindow"]
