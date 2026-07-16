"""``modules.settings.widgets`` — Visual UI wrappers for the settings module.

Depends on :mod:`modules.Uui.widgets` components from this repository, providing:

* :class:`USettingPanel` — Single-scope settings panel (suitable for "Global Settings" or "Project Settings").
* :class:`UProjectSettingsWindow` — Window managing both project and global settings,
  with :guilabel:`Apply` / :guilabel:`Save` / :guilabel:`Close` / :guilabel:`Reset Defaults` buttons at the bottom.

> These UI classes **are just convenient wrappers**, internally still read/write through
> :class:`SettingsManager` / :class:`Settings` abstraction, so business code does not
> need to be aware of the UI's existence.
"""

from __future__ import annotations

import contextlib
import tkinter as tk
from collections.abc import Callable
from tkinter import filedialog, messagebox
from typing import TYPE_CHECKING, Any

from modules.i18n import t

from .base import (
    Settings,
    SettingsChangeEvent,
    SettingsListener,
    SettingSpec,
    SettingsScope,
    SettingValueType,
)
from .manager import SettingsManager

if TYPE_CHECKING:
    # Types seen by type checkers - used for static analysis
    from modules.Uui.widgets import (
        NavSelection,
        UButton,
        UCheckButton,
        UComboBox,
        UEntry,
        UFrame,
        ULabel,
        USettingsNavBar,
        theme,
    )
else:
    # Runtime variables - imported from UUI package; degrades to None on failure
    UButton: Any = None  # type: ignore[assignment,misc]
    UCheckButton: Any = None  # type: ignore[assignment,misc]
    UComboBox: Any = None  # type: ignore[assignment,misc]
    UEntry: Any = None  # type: ignore[assignment,misc]
    UFrame: Any = None  # type: ignore[assignment,misc]
    ULabel: Any = None  # type: ignore[assignment,misc]
    USettingsNavBar: Any = None  # type: ignore[assignment,misc]
    NavSelection: Any = None  # type: ignore[assignment,misc]
    theme: Any = None  # type: ignore[assignment,misc]

try:
    from modules.Uui.widgets import (  # type: ignore[assignment]
        UButton,
        UCheckButton,
        UComboBox,
        UEntry,
        UFrame,
        ULabel,
        USettingsNavBar,
        theme,
    )

    _UUI_AVAILABLE = True
except Exception:  # pragma: no cover - allows import in non-tk environment
    _UUI_AVAILABLE = False


def _group_key(spec: SettingSpec) -> str:
    """Auto-group by ``key`` prefix, e.g., ``editor.tab_size`` → ``editor``."""

    if "." in spec.key:
        return spec.key.split(".", 1)[0]
    return "_"


class USettingPanel(UFrame if _UUI_AVAILABLE else object):  # type: ignore[misc]
    """Visual panel rendering a group of :class:`SettingSpec` for a scope.

    Each spec is displayed as a three-part row: ``label + control + description``;
    automatically grouped by ``key`` prefix.
    When the user edits a control, only the *local copy* is modified; you need to call
    :meth:`apply` or :meth:`revert` to actually write back to the underlying :class:`Settings`
    or discard changes.

    Args:
        parent —— Parent container.
        settings —— Underlying :class:`Settings` instance (global or project).
        on_change —— Callback when user changes a control (optional).
        show_only_keys —— If specified, only render these keys; defaults to all in schema.
        filter_group_keys —— If specified, only render keys belonging to these groups.
    """

    def __init__(
        self,
        parent,
        settings: Settings,
        *,
        on_change: Callable[[str, Any], None] | None = None,
        show_only_keys: list[str] | None = None,
        filter_group_keys: list[str] | None = None,
        **kwargs,
    ) -> None:
        if not _UUI_AVAILABLE:
            raise RuntimeError(
                "USettingPanel requires modules.Uui.widgets; "
                "tkinter is not available in this environment."
            )
        super().__init__(parent, variant="base", **kwargs)
        self._settings = settings
        self._on_change = on_change
        self._working: dict[str, Any] = dict(settings.defined())
        self._widgets: dict[str, Any] = {}
        self._vars: dict[str, tk.Variable] = {}
        self._listener: SettingsListener | None = None

        specs = list(settings.schema)
        if show_only_keys is not None:
            only = set(show_only_keys)
            specs = [s for s in specs if s.key in only]
        if filter_group_keys is not None:
            groups = set(filter_group_keys)
            specs = [s for s in specs if _group_key(s) in groups]

        self._specs: list[SettingSpec] = specs
        self._build()
        self._listener = self._on_settings_event
        settings.add_listener(self._listener)

    def _build(self) -> None:
        grouped: dict[str, list[SettingSpec]] = {}
        order: list[str] = []
        for spec in self._specs:
            g = _group_key(spec)
            if g not in grouped:
                grouped[g] = []
                order.append(g)
            grouped[g].append(spec)

        row = 0
        for group_key in order:
            ULabel(
                self,
                text=group_key,
                variant="secondary",
                font=theme.LABEL_FONT_BOLD,
            ).grid(
                row=row, column=0, columnspan=3, sticky="w", padx=8, pady=(8 if row > 0 else 4, 2)
            )
            row += 1
            for spec in grouped[group_key]:
                self._build_row(row, spec)
                row += 1

        # Column width strategy: column 1 (input control) takes remaining space with a minimum width
        # to ensure input boxes are not squeezed by description text;
        # columns 0/2 set minimum width to avoid labels or descriptions being clipped.
        self.columnconfigure(0, minsize=110)
        self.columnconfigure(1, weight=1, minsize=160)
        self.columnconfigure(2, minsize=180)

    def _build_row(self, row: int, spec: SettingSpec) -> None:
        label = ULabel(self, text=spec.label or spec.key, variant="primary")
        label.grid(row=row, column=0, sticky="w", padx=(12, 6), pady=4)

        widget = self._make_widget(spec)
        widget.grid(row=row, column=1, sticky="ew", padx=4, pady=4)
        self._widgets[spec.key] = widget

        if spec.type is SettingValueType.BUTTON:
            return

        desc = ULabel(
            self,
            text=spec.description or "",
            variant="tertiary",
            font=theme.LABEL_FONT_SMALL,
            width=30,
            wraplength=240,
            anchor="w",
            justify="left",
        )
        desc.grid(row=row, column=2, sticky="nw", padx=(4, 12), pady=4)

    def _make_widget(self, spec: SettingSpec):
        """Instantiate the corresponding control based on spec.type."""

        current = self._current_value(spec)

        if spec.type is SettingValueType.BOOLEAN:
            var = tk.BooleanVar(value=bool(current))
            widget = UCheckButton(self, text="", variable=var)
            widget._command = lambda v=var, k=spec.key: self._user_changed(k, v.get())  # type: ignore[attr-defined]
            self._vars[spec.key] = var
            return widget

        if spec.type is SettingValueType.CHOICE:
            widget = UComboBox(self, values=list(spec.choices))
            widget.set(str(current))
            widget._command = lambda v, k=spec.key: self._user_changed(k, v)  # type: ignore[attr-defined]
            return widget

        if spec.type is SettingValueType.BUTTON:
            widget = UButton(
                self,
                text=spec.label or spec.key,
                variant="primary",
                command=lambda k=spec.key: self._on_button(k),
                width=200,
                height=28,
            )
            return widget

        var = tk.StringVar(value=self._stringify(current))
        widget = UEntry(self, textvariable=var, width=24)
        var.trace_add("write", lambda *a, k=spec.key, v=var: self._user_changed(k, v.get()))
        self._vars[spec.key] = var
        return widget

    def _current_value(self, spec: SettingSpec) -> Any:
        """Read current effective value (prefers local working, then underlying settings)."""

        if spec.key in self._working:
            return self._working[spec.key]
        return self._settings.get(spec.key)

    @staticmethod
    def _stringify(value: Any) -> str:
        if isinstance(value, list):
            return ", ".join(str(x) for x in value)
        return "" if value is None else str(value)

    def _on_button(self, key: str) -> None:
        if self._on_change is not None:
            with contextlib.suppress(Exception):
                self._on_change(key, None)

    def _user_changed(self, key: str, value: Any) -> None:
        try:
            coerced = self._coerce(key, value)
        except ValueError as exc:
            self._last_error = exc
            return
        self._working[key] = coerced
        if self._on_change is not None:
            with contextlib.suppress(Exception):
                self._on_change(key, coerced)

    def _coerce(self, key: str, value: Any) -> Any:
        spec = self._settings.spec(key)
        if spec is None:
            return value
        if spec.type is SettingValueType.BUTTON:
            return value
        if spec.type is SettingValueType.INTEGER:
            if value == "" or value is None:
                return spec.default
            return spec.validate(int(value))
        if spec.type is SettingValueType.FLOAT:
            if value == "" or value is None:
                return spec.default
            return spec.validate(float(value))
        if spec.type is SettingValueType.LIST:
            if isinstance(value, list):
                return spec.validate(value)
            text = str(value)
            items = [s.strip() for s in text.split(",") if s.strip()]
            return spec.validate(items)
        return spec.validate(value)

    def apply(self) -> int:
        """Sync working copy to underlying :class:`Settings`. Returns number of entries written."""

        count = 0
        for key, value in self._working.items():
            spec = self._settings.spec(key)
            if spec is not None and spec.type is SettingValueType.BUTTON:
                continue
            try:
                self._settings.set(key, value)
                count += 1
            except (ValueError, KeyError):
                continue
        return count

    def revert(self) -> None:
        """Discard working copy and refresh all controls with underlying values."""

        self._working = dict(self._settings.defined())
        self._refresh_widgets()

    def last_error(self) -> Exception | None:
        return getattr(self, "_last_error", None)

    def _refresh_widgets(self) -> None:
        for spec in self._specs:
            self._refresh_single_widget(spec.key)

    def _refresh_single_widget(self, key: str) -> None:
        spec = self._settings.spec(key)
        widget = self._widgets.get(key)
        if spec is None or widget is None:
            return
        if spec.type is SettingValueType.BUTTON:
            return
        value = self._current_value(spec)
        if spec.type is SettingValueType.BOOLEAN:
            widget.set(bool(value))
        elif spec.type is SettingValueType.CHOICE:
            widget.set(str(value))
        else:
            var = self._vars.get(key)
            if var is not None:
                var.set(self._stringify(value))

    def _on_settings_event(self, event: SettingsChangeEvent) -> None:
        if event.scope is not self._settings.scope:
            return
        if event.key is not None:
            self._working.pop(event.key, None)
            self._refresh_single_widget(event.key)
        else:
            self._working.clear()
            self._refresh_widgets()

    def destroy(self) -> None:  # type: ignore[override]
        if self._listener is not None:
            with contextlib.suppress(Exception):
                self._settings.remove_listener(self._listener)
        super().destroy()  # type: ignore[misc]


class UProjectSettingsWindow:
    """Window presenting both "global / project" sets of settings.

    Usage::

        manager = SettingsManager()
        win = UProjectSettingsWindow(manager)
        win.show()

    Behavior:

    * Top two tabs switch between **Global** and **Project** (Project tab disabled if no project is mounted).
    * Switching tabs discards unsaved changes and reloads.
    * Click :guilabel:`Apply` to write current tab's changes back to :class:`Settings`.
    * Click :guilabel:`Save` to write back and call :meth:`SettingsManager.save_all` to persist.
    * Click :guilabel:`Close` to discard any unapplied changes.
    """

    def __init__(
        self,
        manager: SettingsManager,
        *,
        title: str = "Settings",
        parent: tk.Misc | None = None,
        geometry: str = "640x520",
        on_change: Callable[[str, Any], None] | None = None,
    ) -> None:
        if not _UUI_AVAILABLE:
            raise RuntimeError("UProjectSettingsWindow requires modules.Uui.widgets.")
        self._manager = manager
        self._parent = parent
        self._geometry = geometry
        self._title = title
        self._on_change = on_change

        self._root = tk.Toplevel(parent) if parent is not None else tk.Tk()
        self._root.title(title)
        self._root.geometry(geometry)
        self._root.configure(bg=theme.BG_BASE)

        self._build()

    def _build(self) -> None:
        header = UFrame(self._root, variant="title")
        header.pack(fill=tk.X)
        ULabel(header, text=self._title, variant="primary", font=theme.LABEL_FONT_BOLD).pack(
            side=tk.LEFT, padx=12, pady=8
        )

        # Middle: left navigation tree + right settings panel, separated by horizontal PanedWindow.
        # sashrelief / sashwidth makes the divider visible and draggable; completely isomorphic
        # to the project file tree PanedWindow in the main window.
        self._paned = tk.PanedWindow(
            self._root,
            orient=tk.HORIZONTAL,
            sashwidth=4,
            sashrelief="flat",
            bg=theme.BORDER,
            bd=0,
            showhandle=False,
        )
        self._paned.pack(fill=tk.BOTH, expand=True)
        self._paned.bind("<Map>", self._init_paned_position, add="+")

        self._nav: Any = USettingsNavBar(
            self._paned,
            title=t("settings.navbar.title"),
            on_select=self._on_nav_select,
        )
        self._paned.add(self._nav, minsize=160, stretch="never")

        self._body = UFrame(self._paned, variant="base")
        self._paned.add(self._body, minsize=200, stretch="always")

        footer = UFrame(self._root, variant="title")
        footer.pack(fill=tk.X)
        UButton(
            footer,
            text=t("settings.btn.reset"),
            variant="warning",
            command=self._on_reset_defaults,
            width=96,
            height=28,
        ).pack(side=tk.RIGHT, padx=4, pady=6)
        UButton(
            footer,
            text=t("settings.btn.close"),
            variant="default",
            command=self._on_close,
            width=80,
            height=28,
        ).pack(side=tk.RIGHT, padx=4, pady=6)
        UButton(
            footer,
            text=t("settings.btn.save"),
            variant="success",
            command=self._on_save,
            width=80,
            height=28,
        ).pack(side=tk.RIGHT, padx=4, pady=6)
        UButton(
            footer,
            text=t("settings.btn.apply"),
            variant="primary",
            command=self._on_apply,
            width=80,
            height=28,
        ).pack(side=tk.RIGHT, padx=4, pady=6)

        self._current_scope: SettingsScope = SettingsScope.GLOBAL
        self._panel: USettingPanel | None = None
        # First build the tree according to current manager state; set_roots will automatically
        # select the first leaf and trigger on_select, which completes the first screen's
        # right panel rendering.
        self._load_nav()

    def _init_paned_position(self, event=None) -> None:
        """After first display, place the sash at 220px, isomorphic to other PanedWindow in the project."""

        try:
            total = self._paned.winfo_width()
            if total <= 1:
                # Not yet truly laid out, postpone one frame
                self._root.after(10, self._init_paned_position)
                return
            self._paned.sash_place(0, max(220, 160), 0)
            self._paned.unbind("<Map>")
        except tk.TclError:
            pass

    def _load_nav(self) -> None:
        """Rebuild the navigation tree based on current :class:`SettingsManager` state.

        When project is not mounted, project_schema is not passed and the "Project" branch
        does not appear in the tree; subsequent ``_switch(PROJECT)`` will prompt the user
        to select a directory if it detects no project is mounted, and after selection,
        :meth:`_switch` calls this method again to refresh the tree.
        """

        project = self._manager.project_settings
        self._nav.set_roots(
            global_schema=self._manager.global_settings.schema,
            project_schema=project.schema if project is not None else None,
        )

    def _switch(self, scope: SettingsScope) -> None:
        """Navigate to the specified scope root node (compatible with old call patterns of
        :meth:`CodeEditor._open_global_settings` / :meth:`CodeEditor._open_project_settings`).

        Behavior:
            * If switching to PROJECT but no project is mounted, prompt user to select directory,
              then refresh the navigation tree to show the "Project" branch.
            * Otherwise, just let the left navigation tree follow to the corresponding scope root;
              actual rendering is handled by :meth:`_on_nav_select` (which rebuilds the right panel).
        """

        if scope is SettingsScope.PROJECT and self._manager.project_settings is None:
            if not messagebox.askyesno(
                t("settings.msg.project.no_attach.title"),
                t("settings.msg.project.no_attach.body"),
                parent=self._root,
            ):
                return
            chosen = filedialog.askdirectory(
                title=t("settings.msg.project.pick_dir.title"),
                parent=self._root,
            )
            if not chosen:
                return
            try:
                self._manager.attach_project(chosen)
            except Exception as exc:
                messagebox.showerror(
                    t("settings.msg.project.no_attach.title"),
                    t("settings.msg.project.mount_failed", exc=exc),
                    parent=self._root,
                )
                return
            # After successful mount, rebuild tree (make the "Project" branch appear).
            self._load_nav()

        self._current_scope = scope
        if self._nav is not None:
            self._nav.set_selected(scope)

    def _on_nav_select(self, selection: Any) -> None:
        """Navigation tree node selected: rebuild right :class:`USettingPanel` based on selection scope.

        * selection.group_key is ``None`` and keys is empty → scope root, display all
        * selection.keys is non-empty → leaf node, ``show_only_keys=keys`` exact filter
        * Other cases (group node) → ``filter_group_keys=[group_key]`` keeps the
          "group header" rendering that :class:`USettingPanel` has by default
        """

        if selection is None:
            return
        self._current_scope = selection.scope
        self._rebuild_panel(selection)

    def _rebuild_panel(self, selection: Any) -> None:
        """Rebuild right ``USettingPanel`` based on selection."""

        if self._panel is not None:
            with contextlib.suppress(Exception):
                self._panel.destroy()
            self._panel = None

        scope = selection.scope
        if scope is SettingsScope.GLOBAL:
            settings = self._manager.global_settings
        elif scope is SettingsScope.PROJECT:
            settings = self._manager.project_settings
        else:
            return
        if settings is None:
            return

        kwargs: dict[str, Any] = {}
        if self._on_change is not None:
            kwargs["on_change"] = self._on_change

        if selection.keys:
            panel = USettingPanel(
                self._body,
                settings=settings,
                show_only_keys=list(selection.keys),
                **kwargs,
            )
        elif selection.group_key is not None:
            panel = USettingPanel(
                self._body,
                settings=settings,
                filter_group_keys=[selection.group_key],
                **kwargs,
            )
        else:
            panel = USettingPanel(self._body, settings=settings, **kwargs)

        panel.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        self._panel = panel

    def _on_apply(self) -> None:
        if self._panel is None:
            return
        try:
            count = self._panel.apply()
        except Exception as exc:
            messagebox.showerror(t("settings.msg.apply.failed"), str(exc), parent=self._root)
            return
        messagebox.showinfo(
            t("settings.msg.apply.success.title"),
            t("settings.msg.apply.success.body", count=count),
            parent=self._root,
        )

    def _on_save(self) -> None:
        if self._panel is not None:
            try:
                self._panel.apply()
            except Exception as exc:
                messagebox.showerror(t("settings.msg.save.failed"), str(exc), parent=self._root)
                return
        try:
            self._manager.save_all()
        except Exception as exc:
            messagebox.showerror(t("settings.msg.save.failed"), str(exc), parent=self._root)
            return
        messagebox.showinfo(
            t("settings.msg.save.success.title"),
            t("settings.msg.save.success.body"),
            parent=self._root,
        )

    def _on_close(self) -> None:
        with contextlib.suppress(tk.TclError):
            self._root.destroy()

    def _on_reset_defaults(self) -> None:
        if self._panel is None:
            return
        if not messagebox.askyesno(
            t("settings.msg.reset.confirm.title"),
            t("settings.msg.reset.confirm.body"),
            parent=self._root,
        ):
            return
        self._manager.reset(self._current_scope)
        # Keep user at current node, only rebuild panel to show default values;
        # if navigation tree is not built yet (exceptional path), fall back to _switch.
        sel = self._nav.get_selected() if self._nav is not None else None
        if sel is not None:
            self._rebuild_panel(sel)
        else:
            self._switch(self._current_scope)

    def show(self) -> None:
        """Enter mainloop."""

        self._root.mainloop()

    @property
    def root(self) -> tk.Misc:
        return self._root


__all__ = ["UProjectSettingsWindow", "USettingPanel"]
