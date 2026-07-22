"""``modules.plugins.widgets`` — Plugin management window.

Visual plugin management interface for users:

* List of loaded plugins (enable/disable toggle)
* List of discovered but not enabled plugins on disk
* Each plugin can "enable / disable / reload / view details"
* Shows plugin directory location, convenient for users writing new plugins
"""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox
from typing import Any

try:
    from ui.widgets import (
        UButton,
        UFrame,
        ULabel,
        UText,
        theme,
    )

    _UUI_AVAILABLE = True
except Exception:  # pragma: no cover
    _UUI_AVAILABLE = False

from core.settings.i18n import t

from .hooks import HOOK_SPECS

__all__ = ["UPluginManagerWindow"]


class UPluginManagerWindow:
    """Plugin management window (singleton style, but allows multiple windows — each creates a new window).

    Creates Toplevel immediately on construction; instance can be discarded after user closes.
    """

    def __init__(self, editor: Any, manager: Any) -> None:
        self._editor = editor
        self._manager = manager
        self._tk_vars: dict[str, tk.BooleanVar] = {}

        self._win = tk.Toplevel(editor.window)
        self._win.title(t("plugin.manager.title"))
        self._win.configure(bg=theme.BG_BASE)
        self._win.geometry("720x520+300+150")
        self._win.transient(editor.window)
        self._win.resizable(True, True)

        self._build()

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def _build(self) -> None:
        # Top: directory info
        top = UFrame(self._win, variant="title")
        top.pack(fill=tk.X)
        global_dir = self._manager._global_plugins_dir
        ULabel(
            top,
            text=(f"  {t('plugin.manager.from_label')} {global_dir}    <project>/plugins/"),
            variant="secondary",
            bg=theme.BG_TITLE,
        ).pack(side=tk.LEFT, padx=10, pady=4)

        # Middle: left and right columns
        body = UFrame(self._win, variant="base")
        body.pack(fill=tk.BOTH, expand=True)

        body.columnconfigure(0, weight=1, uniform="col")
        body.columnconfigure(1, weight=1, uniform="col")
        body.rowconfigure(0, weight=1)

        # Left column: loaded plugins
        left = UFrame(body, variant="panel")
        left.grid(row=0, column=0, sticky="nsew", padx=(4, 2), pady=4)
        ULabel(left, text=t("plugin.manager.loaded"), variant="primary", bg=theme.BG_PANEL).pack(
            anchor="w",
            padx=8,
            pady=4,
        )
        self._loaded_text = UText(left, width=40, height=18)
        self._loaded_text.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        self._loaded_text._text.config(state="disabled", wrap="word")

        # Right column: discovered but not enabled
        right = UFrame(body, variant="panel")
        right.grid(row=0, column=1, sticky="nsew", padx=(2, 4), pady=4)
        ULabel(
            right, text=t("plugin.manager.discovered"), variant="primary", bg=theme.BG_PANEL
        ).pack(
            anchor="w",
            padx=8,
            pady=4,
        )
        self._discovered_text = UText(right, width=40, height=18)
        self._discovered_text.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        self._discovered_text._text.config(state="disabled", wrap="word")

        # Bottom: button row + hook list
        bottom = UFrame(self._win, variant="title")
        bottom.pack(fill=tk.X)
        UButton(
            bottom,
            text=t("plugin.manager.btn.enable"),
            width=70,
            height=24,
            command=self._on_enable,
        ).pack(side=tk.LEFT, padx=4, pady=4)
        UButton(
            bottom,
            text=t("plugin.manager.btn.disable"),
            width=70,
            height=24,
            command=self._on_disable,
        ).pack(side=tk.LEFT, padx=4, pady=4)
        UButton(
            bottom,
            text=t("plugin.manager.btn.reload"),
            width=80,
            height=24,
            command=self._on_reload,
        ).pack(side=tk.LEFT, padx=4, pady=4)
        UButton(
            bottom,
            text=t("plugin.manager.btn.details"),
            width=80,
            height=24,
            command=self._on_info,
        ).pack(side=tk.LEFT, padx=4, pady=4)
        UButton(
            bottom,
            text=t("plugin.manager.btn.close"),
            width=70,
            height=24,
            variant="default",
            command=self._win.destroy,
        ).pack(side=tk.RIGHT, padx=4, pady=4)

        # Hook event reference
        hooks_frame = UFrame(self._win, variant="panel", height=80)
        hooks_frame.pack(fill=tk.X, padx=4, pady=4)
        hooks_frame.pack_propagate(False)
        ULabel(
            hooks_frame,
            text=t("plugin.manager.hooks_label"),
            variant="primary",
            bg=theme.BG_PANEL,
        ).pack(anchor="w", padx=8, pady=2)
        hooks_text = UText(hooks_frame, height=3)
        hooks_text.pack(fill=tk.BOTH, expand=True, padx=4, pady=2)
        hooks_text._text.config(state="disabled", wrap="word")
        for spec in HOOK_SPECS:
            params = ", ".join(spec.params) if spec.params else ""
            hook_key = f"hook.{spec.name}"
            hook_desc = t(hook_key, default=spec.description)
            hooks_text._text.insert(
                "end",
                f"  {spec.name}({params})  — {hook_desc}\n",
            )

        self._refresh()

    # ------------------------------------------------------------------
    # List rendering
    # ------------------------------------------------------------------

    def _refresh(self) -> None:
        """Re-render both lists."""

        loaded = self._manager.list_loaded()
        discovered = [
            d
            for d in self._manager.list_discovered()
            if d.manifest.id not in {r.manifest.id for r in loaded}
        ]

        on_mark = t("plugin.manager.on")
        off_mark = t("plugin.manager.off")
        warn = t("plugin.manager.warning")
        from_label = t("plugin.manager.from_label")

        loaded_lines: list[str] = []
        self._tk_vars = {}
        for i, rec in enumerate(loaded, 1):
            mark = on_mark if rec.enabled else off_mark
            err = f"  {warn} {rec.error}" if rec.error else ""
            loaded_lines.append(
                f"{i:2}. {mark} {rec.manifest.name}  ({rec.manifest.id}){err}\n"
                f"      {from_label} {rec.location}\n"
            )
        if not loaded_lines:
            loaded_lines = [f"{t('plugin.manager.loaded_empty')}\n"]
        self._loaded_text._text.config(state="normal")
        self._loaded_text._text.delete("1.0", "end")
        self._loaded_text._text.insert("1.0", "".join(loaded_lines))
        self._loaded_text._text.config(state="disabled")

        discovered_lines: list[str] = []
        no_desc = t("plugin.manager.no_desc")
        for i, d in enumerate(discovered, 1):
            desc = d.manifest.description or no_desc
            discovered_lines.append(
                f"{i:2}. {d.manifest.name}  ({d.manifest.id})\n"
                f"      {desc}\n"
                f"      {from_label} {d.location}\n"
            )
        if not discovered_lines:
            discovered_lines = [f"{t('plugin.manager.discovered_empty')}\n"]
        self._discovered_text._text.config(state="normal")
        self._discovered_text._text.delete("1.0", "end")
        self._discovered_text._text.insert("1.0", "".join(discovered_lines))
        self._discovered_text._text.config(state="disabled")

    def _selected_loaded_index(self) -> int | None:
        """Read the index corresponding to currently selected row in loaded list (1-based)."""

        try:
            sel = self._loaded_text._text.tag_ranges("sel")
            if not sel:
                return None
            line = int(str(sel[0]).split(".")[0])
        except Exception:
            return None
        loaded = self._manager.list_loaded()
        if 1 <= line <= len(loaded):
            # "Sequence numbers" in loaded list are on lines 1, 3, 5, ... (2 lines per item)
            return (line - 1) // 2
        return None

    def _selected_discovered_index(self) -> int | None:
        try:
            sel = self._discovered_text._text.tag_ranges("sel")
            if not sel:
                return None
            line = int(str(sel[0]).split(".")[0])
        except Exception:
            return None
        loaded_ids = {r.manifest.id for r in self._manager.list_loaded()}
        discovered = [d for d in self._manager.list_discovered() if d.manifest.id not in loaded_ids]
        if 1 <= line <= len(discovered):
            return (line - 1) // 3  # 3 lines per item (title/description/path)
        return None

    # ------------------------------------------------------------------
    # Button callbacks
    # ------------------------------------------------------------------

    def _on_enable(self) -> None:
        idx = self._selected_discovered_index()
        if idx is None:
            messagebox.showinfo(
                t("plugin.manager.msg.enable_title"),
                t("plugin.manager.msg.enable_select_discovered"),
                parent=self._win,
            )
            return
        loaded_ids = {r.manifest.id for r in self._manager.list_loaded()}
        discovered = [d for d in self._manager.list_discovered() if d.manifest.id not in loaded_ids]
        target = discovered[idx]
        try:
            self._manager.enable(target.manifest.id)
        except Exception as exc:
            messagebox.showerror(
                t("plugin.manager.msg.enable_title"),
                t("plugin.manager.msg.enable_failed") + f": {exc}",
                parent=self._win,
            )
            return
        self._editor._refresh_plugin_menu()
        self._editor._refresh_plugin_languages()
        self._refresh()

    def _on_disable(self) -> None:
        idx = self._selected_loaded_index()
        if idx is None:
            messagebox.showinfo(
                t("plugin.manager.msg.disable_title"),
                t("plugin.manager.msg.disable_select_loaded"),
                parent=self._win,
            )
            return
        loaded = self._manager.list_loaded()
        target = loaded[idx]
        try:
            self._manager.disable(target.manifest.id)
        except Exception as exc:
            messagebox.showerror(
                t("plugin.manager.msg.disable_title"),
                t("plugin.manager.msg.disable_failed") + f": {exc}",
                parent=self._win,
            )
            return
        self._editor._refresh_plugin_menu()
        self._editor._refresh_plugin_languages()
        self._refresh()

    def _on_reload(self) -> None:
        idx = self._selected_loaded_index()
        if idx is None:
            messagebox.showinfo(
                t("plugin.manager.msg.reload_title"),
                t("plugin.manager.msg.reload_select_loaded"),
                parent=self._win,
            )
            return
        loaded = self._manager.list_loaded()
        target = loaded[idx]
        try:
            self._manager.reload(target.manifest.id)
        except Exception as exc:
            messagebox.showerror(
                t("plugin.manager.msg.reload_title"),
                t("plugin.manager.msg.reload_failed") + f": {exc}",
                parent=self._win,
            )
            return
        self._editor._refresh_plugin_menu()
        self._editor._refresh_plugin_languages()
        self._refresh()

    def _on_info(self) -> None:
        idx = self._selected_loaded_index()
        if idx is not None:
            loaded = self._manager.list_loaded()
            self._editor._show_plugin_info(loaded[idx])
            return
        idx = self._selected_discovered_index()
        if idx is not None:
            loaded_ids = {r.manifest.id for r in self._manager.list_loaded()}
            discovered = [
                d for d in self._manager.list_discovered() if d.manifest.id not in loaded_ids
            ]
            d = discovered[idx]
            m = d.manifest
            text = t(
                "plugin.info.template_discovered",
                name=m.name,
                id=m.id,
                version=m.version or t("plugin.info.version_unknown"),
                author=m.author or t("plugin.info.author_unknown"),
                scope=m.scope,
                location=d.location,
                status=t("plugin.info.status.not_enabled"),
                description=m.description or t("plugin.info.description_none"),
            )
            messagebox.showinfo(t("dialog.title.plugin", name=m.name), text, parent=self._win)
            return
        messagebox.showinfo(
            t("plugin.manager.msg.details_title"),
            t("plugin.manager.msg.details_select"),
            parent=self._win,
        )
