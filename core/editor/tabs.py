"""Multi-document / tab management for the CodeEditor.

The :class:`TabManager` owns the documents map, the active document id,
the next untitled sequence number, and the :class:`TabBar` widget. It
forwards notifications (status updates, hook emission, language switches)
back to the host editor through a small ``host`` interface so this module
stays decoupled from the giant :class:`CodeEditor` class.
"""

from __future__ import annotations

import contextlib
import os
import tkinter as tk
from typing import Protocol

from core.editor.document import Document
from core.editor.helpers import detect_lang_from_path
from core.plugins import HookEvents
from core.settings.i18n import t
from ui.widgets import Tab, TabBar, UContextMenu


class TabHost(Protocol):
    """A minimal contract the :class:`TabManager` needs from its host editor."""

    window: tk.Tk
    text_widget: tk.Text
    current_file: str | None
    current_language: str

    def refresh_status(self) -> None: ...
    def apply_highlight(self) -> None: ...
    def switch_language(self, lang: str, *, from_doc_switch: bool = False) -> None: ...
    def emit(self, hook: str, *args, **kwargs) -> None: ...
    def confirm_unsaved_discard(self) -> bool: ...


class TabManager:
    """Owns the multi-document state and the tab bar UI."""

    def __init__(self, host: TabHost) -> None:
        self._host = host
        self._documents: dict[str, Document] = {}
        self._active_id: str | None = None
        self._next_seq = 1
        self._tab_bar: TabBar | None = None
        self._dirty = False

    # ------------------------------------------------------------------
    # Properties so the host editor can keep its public surface stable
    # ------------------------------------------------------------------

    @property
    def documents(self) -> dict[str, Document]:
        return self._documents

    @property
    def active_id(self) -> str | None:
        return self._active_id

    @property
    def dirty(self) -> bool:
        return self._dirty

    @property
    def tab_bar(self) -> TabBar | None:
        return self._tab_bar

    def bind_tab_bar(self, bar: TabBar) -> None:
        """Attach a :class:`TabBar` instance and seed it with the initial tabs."""
        self._tab_bar = bar
        self._update_tab_bar()

    # ------------------------------------------------------------------
    # Document lifecycle
    # ------------------------------------------------------------------

    def init_first_document(self) -> None:
        doc_id = self._new_doc_id()
        self._documents[doc_id] = Document(
            path=None, content="", dirty=False, lang=self._host.current_language, seq=1
        )
        self._active_id = doc_id
        self._next_seq = 2
        self._update_tab_bar()

    def new_file(self, *, emit: bool = True) -> bool:
        """Create a new untitled document.

        Returns ``True`` if a new document was created, ``False`` if the user
        cancelled at the unsaved-changes confirmation.
        """
        if self._active_id and self._documents.get(self._active_id):
            curr = self._documents[self._active_id]
            if curr.dirty and not self._host.confirm_unsaved_discard():
                return False

        seq = self._next_seq
        doc_id = self._new_doc_id()
        self._documents[doc_id] = Document(
            path=None, content="", dirty=False, lang=self._host.current_language, seq=seq
        )
        self._next_seq += 1
        self._active_id = doc_id

        text = self._host.text_widget
        text.config(state="normal")
        text.delete("1.0", tk.END)
        self._host.current_file = None
        self._dirty = False
        self._update_tab_bar()
        if emit:
            with contextlib.suppress(Exception):
                self._host.emit(HookEvents.EDITOR_FILE_CREATED)
        return True

    def switch_to(self, doc_id: str) -> None:
        """Switch the active document to ``doc_id``. Idempotent if missing."""
        if doc_id not in self._documents or doc_id == self._active_id:
            return
        self._flush_active_into_document()
        self._active_id = doc_id
        self._load_active_into_widget()
        with contextlib.suppress(Exception):
            self._host.emit(HookEvents.EDITOR_TAB_CHANGED, doc_id)

    def close(self, doc_id: str) -> None:
        """Close the tab with id ``doc_id``. Spawns a fresh empty doc when last one closes."""
        if doc_id not in self._documents:
            return
        doc = self._documents[doc_id]
        if doc.dirty and not self._host.confirm_unsaved_discard():
            return

        was_active = self._active_id == doc_id
        del self._documents[doc_id]
        self._tab_bar_remove(doc_id)

        if not self._documents:
            self.init_first_document()
        elif was_active:
            other_id = next(iter(self._documents.keys()))
            self._active_id = other_id
            self._load_active_into_widget()

        self._update_tab_bar()

    def close_others(self, keep_id: str) -> None:
        for did in [d for d in self._documents if d != keep_id]:
            self.close(did)

    def close_all(self) -> None:
        if len(self._documents) <= 1:
            self.new_file()
            return
        for did in list(self._documents.keys()):
            self.close(did)

    def close_active(self) -> None:
        if self._active_id is not None:
            self.close(self._active_id)

    def next_tab(self) -> None:
        if not self._documents:
            return
        ids = list(self._documents.keys())
        if self._active_id in ids:
            idx = ids.index(self._active_id)
            self.switch_to(ids[(idx + 1) % len(ids)])

    def prev_tab(self) -> None:
        if not self._documents:
            return
        ids = list(self._documents.keys())
        if self._active_id in ids:
            idx = ids.index(self._active_id)
            self.switch_to(ids[(idx - 1) % len(ids)])

    def mark_active_dirty(self) -> None:
        if self._active_id and self._active_id in self._documents:
            self._documents[self._active_id].dirty = True
            self._dirty = True
            self._update_tab_bar()

    def reset_active(
        self,
        *,
        dirty: bool = False,
        content: str = "",
        path: str | None = None,
        lang: str | None = None,
        seq: int = 0,
    ) -> None:
        """Replace the active document with a fresh state.

        Used by file openers after they have computed the new document
        metadata and inserted the right id into ``documents``.
        """
        if self._active_id and self._active_id in self._documents:
            doc = self._documents[self._active_id]
            doc.dirty = dirty
            doc.content = content
            if path is not None:
                doc.path = path
            if lang is not None:
                doc.lang = lang
            if seq:
                doc.seq = seq
        self._dirty = dirty
        self._update_tab_bar()

    def sync_dirty(self, dirty: bool) -> None:
        """Mirror the editor's dirty flag onto the active document."""
        self._dirty = dirty
        if self._active_id and self._active_id in self._documents:
            self._documents[self._active_id].dirty = dirty

    def flush_active_into_document(self) -> None:
        """Persist the current text-widget contents into the active document."""
        if self._active_id and self._active_id in self._documents:
            doc = self._documents[self._active_id]
            try:
                doc.content = self._host.text_widget.get("1.0", "end-1c")
            except tk.TclError:
                doc.content = ""
            doc.lang = self._host.current_language

    def language_for_path(self, path: str) -> str:
        return detect_lang_from_path(path)

    def register_opened(self, path: str, lang: str) -> None:
        """Insert a brand new document entry for ``path`` and mark it active."""
        doc_id = path
        detected = lang
        doc = Document(path=path, content="", dirty=False, lang=detected, seq=0)
        self._documents[doc_id] = doc
        self._active_id = doc_id
        self._update_tab_bar()

    def show_tab_context_menu(self, doc_id: str, x_root: int, y_root: int) -> None:
        menu = UContextMenu(self._host.window)
        menu.add_command(
            label=t("sidebar.tab.close"),
            command=lambda: self.close(doc_id),
        )
        menu.add_command(
            label=t("sidebar.tab.close_others"),
            command=lambda: self.close_others(doc_id),
        )
        menu.add_command(
            label=t("sidebar.tab.close_all"),
            command=self.close_all,
        )
        menu.show(x_root, y_root)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _new_doc_id(self) -> str:
        return f"__untitled_{self._next_seq}__"

    def _tab_title(self, doc: Document) -> str:
        if doc.path:
            return os.path.basename(doc.path)
        return f"{t('tab.title.untitled')}-{doc.seq}"

    def _update_tab_bar(self) -> None:
        if self._tab_bar is None:
            return
        tabs = []
        for doc_id, doc in self._documents.items():
            title = self._tab_title(doc)
            closeable = len(self._documents) > 1
            tabs.append(Tab(id=doc_id, title=title, dirty=doc.dirty, closeable=closeable))
        self._tab_bar.set_tabs(tabs, self._active_id)

    def _flush_active_into_document(self) -> None:
        self.flush_active_into_document()

    def _load_active_into_widget(self) -> None:
        doc = self._documents[self._active_id]
        text = self._host.text_widget
        text.config(state="normal")
        text.delete("1.0", tk.END)
        if doc.content:
            text.insert("1.0", doc.content)
        self._dirty = doc.dirty
        self._host.switch_language(doc.lang, from_doc_switch=True)
        if self._tab_bar is not None:
            self._tab_bar.set_active(self._active_id)
        self._host.apply_highlight()
        self._host.refresh_status()

    def _tab_bar_remove(self, doc_id: str) -> None:
        bar = self._tab_bar
        if bar is not None:
            with contextlib.suppress(Exception):
                bar.remove_tab(doc_id)
