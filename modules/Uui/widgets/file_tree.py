"""``modules.Uui.widgets.file_tree`` — VS-style directory tree component.

Based on :class:`TreeCanvas` (Canvas rendering layer), itself only responsible for:

* Maintaining ``iid -> absolute path`` mapping, decoupling TreeCanvas's iid from filesystem paths;
* Scanning directories and feeding nodes to TreeCanvas; **first level expands immediately, deep levels lazy-load on demand**
  — the first ``<<TreeviewOpen>>`` equivalent event (i.e., :meth:`TreeCanvas.toggle`)
  triggers ``scandir`` on that directory;
* Distinguishing "directory" vs "file" in :meth:`on_activate` callback — double-clicking directory is equivalent
  to clicking the triangle (expand/collapse), double-clicking file truly invokes user's ``on_activate``.

API is fully consistent with ttk.Treeview era:

* :meth:`set_root` / :meth:`refresh` —— switch or rebuild project root;
* :meth:`set_on_activate` / :meth:`set_title` —— change callback/title at runtime;
* :meth:`selected_path` —— absolute path of currently selected node;
* :meth:`_apply_theme` —— theme switch, triggered recursively by
  :func:`modules.Uui.widgets.theme.apply_theme_recursive`.
"""

from __future__ import annotations

import contextlib
import os
import tkinter as tk
from collections.abc import Callable, Iterable

from . import theme
from .frame import UFrame
from .label import ULabel
from .tree_canvas import TreeCanvas

# These directories should never appear in file tree for any project; explicit hiding avoids node explosion.
_DEFAULT_IGNORE_DIRS = frozenset(
    {
        "__pycache__",
        ".git",
        ".venv",
        "venv",
        "node_modules",
        ".idea",
        ".vscode",
        "build",
        "dist",
        ".mypy_cache",
        ".pytest_cache",
    }
)


# iid encoding: ``FILE:\\\\absolute path``; using ``FILE:`` prefix avoids conflicts with
# potentially non-file nodes introduced in the future (e.g., setting item nodes).
_IID_PREFIX = "FILE:"


def _path_to_iid(path: str) -> str:
    return _IID_PREFIX + os.path.abspath(path)


def _iid_to_path(iid: str) -> str | None:
    if not iid.startswith(_IID_PREFIX):
        return None
    return iid[len(_IID_PREFIX) :]


class UFileTree(UFrame):
    """File tree: header title + Canvas tree + vertical Scrollbar."""

    def __init__(
        self,
        parent,
        *,
        title: str = "Project",
        ignore_dirs: Iterable[str] | None = None,
        width: int = 240,
        on_activate: Callable[[str], None] | None = None,
        **kwargs,
    ) -> None:
        # Self as outer panel, isomorphic with output_panel (``variant='panel'``).
        kwargs.setdefault("variant", "panel")
        super().__init__(parent, **kwargs)

        self._title_text = title
        self._on_activate = on_activate
        self._ignore_dirs = (
            set(ignore_dirs) if ignore_dirs is not None else set(_DEFAULT_IGNORE_DIRS)
        )
        self._root_path: str | None = None
        # iid -> absolute path (TreeCanvas doesn't care about business, we maintain reverse lookup table ourselves).
        self._iid_to_path: dict[str, str] = {}

        self._build()

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    def _build(self) -> None:
        # Title header: isomorphic with _build_output_panel: UFrame(title) + ULabel(secondary).
        header = UFrame(self, variant="title", height=26)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        self._title_label = ULabel(
            header,
            text=f"  {self._title_text}",
            variant="secondary",
            bg=theme.BG_TITLE,
        )
        self._title_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self._tree = TreeCanvas(
            self,
            row_text=self._row_label,
            on_select=self._on_select,
            on_activate=self._on_activate_dispatch,
            on_toggle=self._on_toggle,
        )
        self._tree.pack(fill=tk.BOTH, expand=True)

    def _row_label(self, iid: str) -> str:
        """TreeCanvas uses this callback to get display text for each row."""

        path = self._iid_to_path.get(iid)
        if path is None:
            return ""
        return os.path.basename(path) or path

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_on_activate(
        self,
        callback: Callable[[str], None] | None,
    ) -> None:
        self._on_activate = callback

    def set_title(self, text: str) -> None:
        self._title_text = text
        self._title_label.config(text=f"  {text}")

    def set_root(self, path: str | None) -> None:
        """Set root directory, ``None`` means clear tree."""

        self._root_path = os.path.abspath(path) if path else None
        # Header shows only project name; without root directory, revert to default title.
        if self._root_path:
            display = os.path.basename(self._root_path) or self._root_path
        else:
            display = self._title_text
        self._title_label.config(text=f"  {display}")
        self._rebuild()

    def refresh(self) -> None:
        """Externally triggered rebuild (e.g., just attached a project)."""
        self._rebuild()

    def selected_path(self) -> str | None:
        iid = self._tree.get_selected()
        if iid is None:
            return None
        return self._iid_to_path.get(iid)

    # ------------------------------------------------------------------
    # Internal: tree rebuild
    # ------------------------------------------------------------------

    def _rebuild(self) -> None:
        self._tree.clear()
        self._iid_to_path.clear()

        if not self._root_path or not os.path.isdir(self._root_path):
            return

        root_iid = _path_to_iid(self._root_path)
        self._iid_to_path[root_iid] = self._root_path
        # Root node always expands; once TreeCanvas's add_node has is_open=True,
        # it immediately renders child nodes in _relayout, which is the entry point for first-level scan.
        self._tree.add_node(root_iid, None, is_open=True)
        try:
            self._populate(root_iid, self._root_path)
        except OSError:
            # Permission issues etc: attach an error node under root to alert user.
            err_iid = root_iid + "::err"
            self._iid_to_path[err_iid] = ""
            self._tree.add_node(err_iid, root_iid)

    def _populate(self, parent_iid: str, dir_path: str) -> None:
        """Recursively populate one level of child nodes under ``dir_path`` into ``parent_iid``.

        Same level sorted by "directories first, alphabetical order" for stable browsing experience.
        """

        try:
            entries = list(os.scandir(dir_path))
        except OSError:
            return

        dirs = []
        files = []
        for e in entries:
            name = e.name
            if name.startswith(".") and name not in (".gitignore", ".env") and e.is_dir():
                continue
            try:
                is_dir = e.is_dir(follow_symlinks=False)
            except OSError:
                continue
            if is_dir:
                if name in self._ignore_dirs:
                    continue
                dirs.append(e)
            else:
                try:
                    is_file = e.is_file(follow_symlinks=False)
                except OSError:
                    is_file = False
                if is_file:
                    files.append(e)

        dirs.sort(key=lambda d: d.name.lower())
        files.sort(key=lambda f: f.name.lower())

        for d in dirs:
            self._add_dir(d, parent_iid)
        for f in files:
            self._add_file(f, parent_iid)

    def _add_dir(self, entry: os.DirEntry, parent_iid: str) -> None:
        """Add a directory node; collapsed by default, scandir on first expand."""

        iid = _path_to_iid(entry.path)
        self._iid_to_path[iid] = entry.path
        # is_open=False: don't immediately populate children, lazy load when on_toggle triggers.
        self._tree.add_node(iid, parent_iid, is_open=False, data=entry.path)

    def _add_file(self, entry: os.DirEntry, parent_iid: str) -> None:
        iid = _path_to_iid(entry.path)
        self._iid_to_path[iid] = entry.path
        # Leaf nodes don't need triangle; is_open is ignored in TreeCanvas.
        self._tree.add_node(iid, parent_iid, data=entry.path)

    # ------------------------------------------------------------------
    # Internal: events
    # ------------------------------------------------------------------

    def _on_select(self, iid: str) -> None:
        # TreeCanvas has already switched highlight to iid; we don't need to do anything extra here,
        # selection is only for :meth:`selected_path` reverse lookup.
        return

    def _on_activate_dispatch(self, iid: str) -> None:
        """TreeCanvas double-click/Enter entry; distinguish file vs directory."""

        path = self._iid_to_path.get(iid)
        if path is None or not path:
            return
        if os.path.isdir(path):
            # Double-click directory = expand/collapse, consistent with original Treeview behavior.
            self._tree.toggle(iid)
            return
        if self._on_activate is not None:
            with contextlib.suppress(Exception):
                self._on_activate(path)

    def _on_toggle(self, iid: str, is_open: bool) -> None:
        """On directory first expand, lazy load its child nodes.

        Reverse lookup the real path of this directory via :attr:`_iid_to_path`, then
        call :meth:`_populate` once. Subsequent expand/collapse is just state switching, no
        repeated scandir (TreeCanvas already knows the node's current open/close state,
        won't repeatedly trigger on_toggle).
        """

        if not is_open:
            return
        path = self._iid_to_path.get(iid)
        if path is None or not path or not os.path.isdir(path):
            return
        # Check if this iid already has real child nodes; prevent "close then open" from being
        # misidentified as "first expand" causing duplicate insertions.
        # TreeCanvas doesn't expose children list for now — go through data layer:
        # in _iid_to_path, child nodes' iids all use "<this path>" as
        # prefix (after abspath); use iid_to_path reverse lookup to see if child already exists.
        prefix = _path_to_iid(path) + os.sep
        already = any(k != iid and k.startswith(prefix) for k in self._iid_to_path)
        if already:
            return
        try:
            self._populate(iid, path)
        except OSError:
            err_iid = iid + "::err"
            self._iid_to_path[err_iid] = ""
            self._tree.add_node(err_iid, iid)

    # ------------------------------------------------------------------
    # Theme refresh
    # ------------------------------------------------------------------

    def _apply_theme(self) -> None:
        """Called by upper layer when switching theme, refresh all colors.

        UFrame._apply_theme only updates its own bg; here recursively refresh sub-controls to ensure
        title / body / TreeCanvas all follow theme switch.
        """

        with contextlib.suppress(tk.TclError):
            super()._apply_theme()
        with contextlib.suppress(tk.TclError, AttributeError):
            self._title_label.config(
                bg=theme.BG_TITLE,
                fg=theme.FG_SECONDARY,
            )
        # TreeCanvas implements _apply_theme itself, through super()._apply_theme's
        # recursion (in UFrame) it will already be hit, but _apply_theme actually only
        # refreshes when receiving _apply_theme call. UFrame._apply_theme is not recursive,
        # explicitly trigger TreeCanvas's theme refresh here.
        if hasattr(self._tree, "_apply_theme"):
            with contextlib.suppress(tk.TclError):
                self._tree._apply_theme()


__all__ = ["UFileTree"]
