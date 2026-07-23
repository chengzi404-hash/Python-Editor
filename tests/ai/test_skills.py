"""Tests for :mod:`core.ai.skills`."""

from __future__ import annotations

import json
import os
import tempfile

from core.ai import AISkill, AISkillRegistry, MCPServer


class TestAISkillSerialization:
    def test_roundtrip_minimal(self):
        skill = AISkill(id="x", name="X")
        d = skill.to_dict()
        rebuilt = AISkill.from_dict(d)
        assert rebuilt.id == "x"
        assert rebuilt.name == "X"

    def test_roundtrip_full(self):
        skill = AISkill(
            id="doc-writer",
            name="Doc Writer",
            version="1.2.3",
            author="alice",
            description="Writes docstrings.",
            system_prompt="You write docstrings.",
            model_override="gpt-4",
            mcp_servers=[
                MCPServer(name="fs", command="mcp-fs", args=["--stdio"], env={"A": "1"}),
            ],
            tags=["docs", "python"],
        )
        d = skill.to_dict()
        rebuilt = AISkill.from_dict(d)
        assert rebuilt.id == "doc-writer"
        assert rebuilt.name == "Doc Writer"
        assert rebuilt.model_override == "gpt-4"
        assert rebuilt.system_prompt == "You write docstrings."
        assert rebuilt.mcp_servers[0].name == "fs"
        assert rebuilt.mcp_servers[0].args == ["--stdio"]
        assert rebuilt.mcp_servers[0].env == {"A": "1"}
        assert rebuilt.tags == ["docs", "python"]

    def test_from_dict_handles_missing_keys(self):
        # No required keys → fallback defaults.
        rebuilt = AISkill.from_dict({})
        assert rebuilt.id == ""
        assert rebuilt.name == "Unnamed"


class TestAISkillRegistry:
    def _make_skill(self, root: str, skill_id: str, name: str | None = None) -> AISkill:
        return AISkill(
            id=skill_id,
            name=name or skill_id,
            system_prompt=f"prompt for {skill_id}",
        )

    def test_install_and_list(self):
        with tempfile.TemporaryDirectory() as tmp:
            reg = AISkillRegistry(tmp)
            assert reg.list() == []
            reg.install(self._make_skill(tmp, "alpha"))
            reg.install(self._make_skill(tmp, "beta"))
            ids = sorted(s.id for s in reg.list())
            assert ids == ["alpha", "beta"]

    def test_install_persists_to_disk(self):
        with tempfile.TemporaryDirectory() as tmp:
            reg = AISkillRegistry(tmp)
            reg.install(self._make_skill(tmp, "alpha"))
            on_disk = os.listdir(os.path.join(tmp, "ai", "skills"))
            assert "alpha.json" in on_disk

    def test_uninstall_removes_file_and_cache(self):
        with tempfile.TemporaryDirectory() as tmp:
            reg = AISkillRegistry(tmp)
            reg.install(self._make_skill(tmp, "alpha"))
            assert reg.uninstall("alpha") is True
            assert reg.get("alpha") is None
            # Second uninstall should still succeed (no file to remove).
            assert reg.uninstall("alpha") is True

    def test_activate_returns_skill(self):
        with tempfile.TemporaryDirectory() as tmp:
            reg = AISkillRegistry(tmp)
            reg.install(self._make_skill(tmp, "alpha"))
            activated = reg.activate("alpha")
            assert activated is not None
            assert activated.id == "alpha"
            assert reg.active_id == "alpha"

    def test_activate_unknown_returns_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            reg = AISkillRegistry(tmp)
            assert reg.activate("nope") is None

    def test_activate_none_clears(self):
        with tempfile.TemporaryDirectory() as tmp:
            reg = AISkillRegistry(tmp)
            reg.install(self._make_skill(tmp, "alpha"))
            reg.activate("alpha")
            assert reg.activate(None) is None
            assert reg.active_id is None

    def test_scan_picks_up_files_added_out_of_band(self):
        with tempfile.TemporaryDirectory() as tmp:
            reg = AISkillRegistry(tmp)
            # Drop a file directly into the registry root.
            skills_dir = os.path.join(tmp, "ai", "skills")
            os.makedirs(skills_dir, exist_ok=True)
            with open(os.path.join(skills_dir, "gamma.json"), "w", encoding="utf-8") as fh:
                json.dump({"id": "gamma", "name": "Gamma"}, fh)
            skills = reg.list()
            assert any(s.id == "gamma" for s in skills)
