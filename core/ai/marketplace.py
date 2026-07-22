"""``modules.ai.marketplace`` — :class:`AISkillMarketplace` provider.

Implements :class:`core.plugins.marketplace.MarketplaceProvider` so AI skills
can flow through the existing :class:`UMarketplaceWindow` UI without a new
abstraction.

Two data sources are supported:

* **Online index** — fetched from ``ai.skills_marketplace_url``. We expect a
  JSON document shaped like::

      {
        "version": 1,
        "skills": [
          {"id": "...", "name": "...", "version": "...", "author": "...",
           "description": "...", "tags": [...], "download_url": "..."},
          ...
        ]
      }

* **Offline index** — bundled in :data:`_OFFLINE_INDEX`. Always merged in,
  even when the online URL is unreachable, so users have something to play
  with out of the box.
"""

from __future__ import annotations

import json
import os
import tempfile
import urllib.error
import urllib.request

from core.plugins.marketplace import (
    MarketplaceItem,
    MarketplaceProvider,
    MarketplaceSearchResult,
)

from .skills import AISkill, AISkillRegistry

# A small offline catalogue — always available, even without network.
_OFFLINE_INDEX: list[dict] = [
    {
        "id": "python-expert",
        "name": "Python Expert",
        "version": "1.0.0",
        "author": "Python Editor",
        "description": "Answers Python questions with PEP 8 / type-hint awareness.",
        "tags": ["python", "coding", "beginner-friendly"],
        "system_prompt": (
            "You are a senior Python developer. Always give idiomatic, "
            "type-annotated answers. Prefer the standard library; only reach "
            "for third-party packages when they meaningfully reduce code size."
        ),
    },
    {
        "id": "code-reviewer",
        "name": "Code Reviewer",
        "version": "1.0.0",
        "author": "Python Editor",
        "description": "Reviews code for correctness, performance, and readability.",
        "tags": ["review", "quality"],
        "system_prompt": (
            "You are a meticulous code reviewer. For every snippet you receive, "
            "list (1) bugs, (2) performance issues, (3) readability issues. "
            "Order by severity. Never rewrite the code unless explicitly asked."
        ),
    },
    {
        "id": "git-helper",
        "name": "Git Helper",
        "version": "1.0.0",
        "author": "Python Editor",
        "description": "Suggests git commands and explains diffs.",
        "tags": ["git", "vcs"],
        "system_prompt": (
            "You are a git power-user. Suggest the safest command for the "
            "user's intent and warn about destructive operations."
        ),
    },
    {
        "id": "doc-writer",
        "name": "Doc Writer",
        "version": "1.0.0",
        "author": "Python Editor",
        "description": "Writes Sphinx / NumPy-style docstrings from code.",
        "tags": ["docs", "python"],
        "system_prompt": (
            "When given a function or class, return a complete Google-style "
            "docstring with Args, Returns, Raises sections. Output ONLY the "
            "docstring, surrounded by triple double quotes."
        ),
    },
    {
        "id": "test-author",
        "name": "Test Author",
        "version": "1.0.0",
        "author": "Python Editor",
        "description": "Writes pytest unit tests from code.",
        "tags": ["testing", "pytest"],
        "system_prompt": (
            "Given a function, produce a pytest module that covers the happy "
            "path, edge cases and error paths. Use parametrize for matrix "
            "cases. Output only the test module code."
        ),
    },
]


def bundled_skills() -> list[dict]:
    """Return the offline skill index as a list of plain dicts (for tests)."""

    return [dict(s) for s in _OFFLINE_INDEX]


class AISkillMarketplaceProvider(MarketplaceProvider):
    """A :class:`MarketplaceProvider` that serves the AI Skills index.

    Args:
        index_url: URL of the JSON catalogue. Empty string = offline-only.
        timeout_s: HTTP timeout for the index fetch.
    """

    def __init__(self, index_url: str = "", *, timeout_s: float = 10.0) -> None:
        self._index_url = index_url.strip()
        self._timeout_s = float(timeout_s)

    def set_index_url(self, url: str) -> None:
        self._index_url = url.strip()

    # ---- MarketplaceProvider --------------------------------------------

    def name(self) -> str:
        return "ai_skills"

    def search(
        self,
        query: str = "",
        tags: list[str] | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> MarketplaceSearchResult:
        all_items = self._load()
        filtered = _filter_items(all_items, query, tags)
        start = max(0, (page - 1) * page_size)
        end = start + page_size
        return MarketplaceSearchResult(
            items=filtered[start:end],
            total=len(filtered),
            page=page,
            page_size=page_size,
        )

    def get_item(self, item_id: str) -> MarketplaceItem | None:
        for item in self._load():
            if item.id == item_id:
                return item
        return None

    def download(self, item: MarketplaceItem, target_dir: str) -> str:
        """Persist the skill JSON to *target_dir* and return the file path."""

        os.makedirs(target_dir, exist_ok=True)
        raw = self._fetch_raw(item.id)
        if raw is None:
            # Fall back to a stub built from the marketplace item.
            raw = _stub_from_item(item)
        skill = AISkill.from_dict(raw if isinstance(raw, dict) else {})
        if not skill.id:
            skill.id = item.id
        if not skill.name:
            skill.name = item.name
        if not skill.author:
            skill.author = item.author
        if not skill.description:
            skill.description = item.description
        if not skill.tags:
            skill.tags = list(item.tags)
        path = os.path.join(target_dir, f"{_safe_id(skill.id)}.json")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(skill.to_dict(), fh, indent=2, ensure_ascii=False)
        return path

    # ---- Internal -------------------------------------------------------

    def _load(self) -> list[MarketplaceItem]:
        """Merge offline + online index into a list of :class:`MarketplaceItem`."""

        seen: dict[str, MarketplaceItem] = {}
        for raw in _OFFLINE_INDEX:
            item = _item_from_dict(raw)
            seen[item.id] = item
        if self._index_url:
            try:
                req = urllib.request.Request(
                    self._index_url,
                    headers={"User-Agent": "PythonEditor/1.0 (ai-skills)"},
                )
                with urllib.request.urlopen(req, timeout=self._timeout_s) as resp:
                    payload = json.loads(resp.read().decode("utf-8", errors="replace"))
                for raw in (payload.get("skills") or []):
                    if not isinstance(raw, dict):
                        continue
                    item = _item_from_dict(raw)
                    # Online wins for collisions.
                    seen[item.id] = item
            except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError, OSError):
                pass
        return sorted(seen.values(), key=lambda i: i.name.lower())

    def _fetch_raw(self, skill_id: str) -> dict | None:
        """Fetch a single skill JSON from the online index by id.

        Tries ``<index_url-without-trailing-name>.json`` style URLs by replacing
        the filename portion. Falls back to ``None`` if nothing is reachable.
        """

        if not self._index_url:
            return None
        # The index itself does not embed skill bodies — derive a URL by
        # replacing the file portion with ``<id>.json``.
        try:
            base, _ = self._index_url.rsplit("/", 1)
        except ValueError:
            return None
        candidate = f"{base}/{_safe_id(skill_id)}.json"
        try:
            req = urllib.request.Request(
                candidate,
                headers={"User-Agent": "PythonEditor/1.0 (ai-skills)"},
            )
            with urllib.request.urlopen(req, timeout=self._timeout_s) as resp:
                return json.loads(resp.read().decode("utf-8", errors="replace"))
        except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError, OSError):
            return None


def install_skill_from_marketplace(
    provider: AISkillMarketplaceProvider,
    registry: AISkillRegistry,
    skill_id: str,
) -> AISkill | None:
    """High-level helper: download *skill_id* and persist via *registry*."""

    item = provider.get_item(skill_id)
    if item is None:
        return None
    with tempfile.TemporaryDirectory() as tmp:
        path = provider.download(item, tmp)
        try:
            with open(path, encoding="utf-8") as fh:
                raw = json.load(fh)
        except (OSError, json.JSONDecodeError):
            return None
    skill = AISkill.from_dict(raw if isinstance(raw, dict) else {})
    if not skill.id:
        skill.id = item.id
    registry.install(skill)
    return skill


# ---- Pure helpers --------------------------------------------------------


def _filter_items(
    items: list[MarketplaceItem],
    query: str,
    tags: list[str] | None,
) -> list[MarketplaceItem]:
    q = query.strip().lower()

    def matches(item: MarketplaceItem) -> bool:
        if q:
            hay = " ".join(
                [
                    item.name,
                    item.description,
                    item.author,
                    " ".join(item.tags),
                ]
            ).lower()
            if q not in hay:
                return False
        if tags:
            tag_set = {t.lower() for t in tags}
            if not tag_set.intersection({t.lower() for t in item.tags}):
                return False
        return True

    return [it for it in items if matches(it)]


def _item_from_dict(raw: dict) -> MarketplaceItem:
    return MarketplaceItem(
        id=str(raw.get("id", "")),
        name=str(raw.get("name", raw.get("id", "Unnamed"))),
        version=str(raw.get("version", "1.0.0")),
        author=str(raw.get("author", "")),
        description=str(raw.get("description", "")),
        tags=[str(t) for t in (raw.get("tags") or [])],
        download_url=str(raw.get("download_url", "")),
    )


def _stub_from_item(item: MarketplaceItem) -> dict:
    """Build a minimal skill dict from a :class:`MarketplaceItem`."""

    return {
        "id": item.id,
        "name": item.name,
        "version": item.version,
        "author": item.author,
        "description": item.description,
        "tags": list(item.tags),
        "system_prompt": "",
    }


def _safe_id(skill_id: str) -> str:
    return "".join(c if c.isalnum() or c in "._-" else "_" for c in skill_id)


__all__ = [
    "AISkillMarketplaceProvider",
    "bundled_skills",
    "install_skill_from_marketplace",
]
