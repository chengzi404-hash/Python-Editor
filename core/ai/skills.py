"""``modules.ai.skills`` — AI Skills (a.k.a. MCP-style skill bundles).

A *skill* is a small JSON document that bundles together:

* a **system prompt** prepended to every chat/compaction/FIM call when the
  skill is active;
* an optional list of **MCP server descriptors** (the marketplace doesn't have
  to actually launch the servers — it just records them so the editor can
  surface them and a future runtime can spawn them);
* optional model hints (override ``ai.model`` while the skill is active).

Skills live as JSON files under ``<settings_dir>/ai/skills/<id>.json``. The
:class:`AISkillRegistry` loads them on demand and tracks which one is active.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field

# ---- Data types ----------------------------------------------------------


@dataclass
class MCPServer:
    """Description of a Model Context Protocol server the skill wants to use."""

    name: str
    command: str = ""
    args: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)
    transport: str = "stdio"  # "stdio" | "http" | "sse"


@dataclass
class AISkill:
    """One skill bundle."""

    id: str
    name: str
    version: str = "1.0.0"
    author: str = ""
    description: str = ""
    system_prompt: str = ""
    model_override: str = ""
    mcp_servers: list[MCPServer] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Return a JSON-serializable representation."""

        return {
            "id": self.id,
            "name": self.name,
            "version": self.version,
            "author": self.author,
            "description": self.description,
            "system_prompt": self.system_prompt,
            "model_override": self.model_override,
            "mcp_servers": [
                {
                    "name": s.name,
                    "command": s.command,
                    "args": list(s.args),
                    "env": dict(s.env),
                    "transport": s.transport,
                }
                for s in self.mcp_servers
            ],
            "tags": list(self.tags),
        }

    @classmethod
    def from_dict(cls, data: dict) -> AISkill:
        """Build a skill from its JSON dict (best-effort: unknown keys ignored)."""

        try:
            servers_raw = data.get("mcp_servers") or []
            servers = [
                MCPServer(
                    name=str(s.get("name", "")),
                    command=str(s.get("command", "")),
                    args=[str(a) for a in s.get("args", []) or []],
                    env={str(k): str(v) for k, v in (s.get("env") or {}).items()},
                    transport=str(s.get("transport", "stdio")),
                )
                for s in servers_raw
                if isinstance(s, dict)
            ]
            return cls(
                id=str(data.get("id", "")),
                name=str(data.get("name", data.get("id", "Unnamed"))),
                version=str(data.get("version", "1.0.0")),
                author=str(data.get("author", "")),
                description=str(data.get("description", "")),
                system_prompt=str(data.get("system_prompt", "")),
                model_override=str(data.get("model_override", "")),
                mcp_servers=servers,
                tags=[str(t) for t in (data.get("tags") or [])],
            )
        except Exception:
            # Malformed → return a minimal stub so the registry keeps loading.
            return cls(id=str(data.get("id", "unknown")), name=str(data.get("id", "unknown")))


# ---- Registry ------------------------------------------------------------


class AISkillRegistry:
    """On-disk registry of installed AI skills.

    Skills are stored as individual JSON files in a single directory:

        <root>/ai/skills/<id>.json

    The registry never deletes a file when ``uninstall`` is called — it just
    removes the entry from the in-memory cache. Use :meth:`remove_file` for a
    full filesystem cleanup.
    """

    def __init__(self, root_dir: str) -> None:
        self._root = os.path.join(root_dir, "ai", "skills")
        self._cache: dict[str, AISkill] = {}
        self._active_id: str | None = None

    @property
    def root_dir(self) -> str:
        return self._root

    @property
    def active_id(self) -> str | None:
        return self._active_id

    @property
    def active(self) -> AISkill | None:
        if self._active_id is None:
            return None
        return self._cache.get(self._active_id)

    # -- CRUD --------------------------------------------------------------

    def list(self) -> list[AISkill]:
        """Return all installed skills (cached + on-disk)."""

        self._scan()
        return sorted(self._cache.values(), key=lambda s: s.name.lower())

    def get(self, skill_id: str) -> AISkill | None:
        self._scan()
        return self._cache.get(skill_id)

    def install(self, skill: AISkill) -> str:
        """Persist *skill* to disk and update the cache. Returns the file path."""

        if not skill.id:
            raise ValueError("skill.id is required")
        os.makedirs(self._root, exist_ok=True)
        path = self._path_for(skill.id)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(skill.to_dict(), fh, indent=2, ensure_ascii=False)
        os.replace(tmp, path)
        self._cache[skill.id] = skill
        return path

    def uninstall(self, skill_id: str) -> bool:
        """Remove the on-disk JSON file and forget the cached entry."""

        path = self._path_for(skill_id)
        try:
            os.remove(path)
        except FileNotFoundError:
            pass
        except OSError:
            return False
        self._cache.pop(skill_id, None)
        if self._active_id == skill_id:
            self._active_id = None
        return True

    def activate(self, skill_id: str | None) -> AISkill | None:
        """Mark *skill_id* as the active skill (or clear with ``None``)."""

        if skill_id is not None and skill_id not in self.list_ids():
            return None
        self._active_id = skill_id
        return self.active

    def list_ids(self) -> list[str]:
        return [s.id for s in self.list()]

    # -- Internal ----------------------------------------------------------

    def _path_for(self, skill_id: str) -> str:
        safe = "".join(c if c.isalnum() or c in "._-" else "_" for c in skill_id)
        return os.path.join(self._root, f"{safe}.json")

    def _scan(self) -> None:
        if not os.path.isdir(self._root):
            return
        # Discover files on disk; add new ones to cache; drop cache entries
        # whose file disappeared.
        try:
            on_disk = {
                os.path.splitext(fn)[0] for fn in os.listdir(self._root) if fn.endswith(".json")
            }
        except OSError:
            return
        # Drop cached entries that no longer exist on disk.
        for cached_id in list(self._cache):
            if cached_id not in on_disk:
                self._cache.pop(cached_id, None)
        # Load any new files.
        for skill_id in on_disk:
            if skill_id in self._cache:
                continue
            path = self._path_for(skill_id)
            try:
                with open(path, encoding="utf-8") as fh:
                    raw = json.load(fh)
            except (OSError, json.JSONDecodeError):
                continue
            skill = AISkill.from_dict(raw if isinstance(raw, dict) else {})
            if not skill.id:
                skill.id = skill_id
            self._cache[skill_id] = skill


__all__ = [
    "AISkill",
    "AISkillRegistry",
    "MCPServer",
]
