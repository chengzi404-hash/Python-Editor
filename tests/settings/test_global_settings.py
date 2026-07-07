# -*- coding: utf-8 -*-
"""针对 modules.settings.global_settings 模块的测试。"""

from __future__ import annotations

import os
import sys

import pytest

from modules.settings import (
    GLOBAL_SCHEMA,
    GlobalSettings,
    SettingsScope,
    default_global_path,
)
from modules.settings.storage import CURRENT_VERSION, JsonFileSettings


class TestGlobalSettingsMetadata:
    """GlobalSettings 的 scope 必须是 GLOBAL，schema 应为内置 GLOBAL_SCHEMA。"""

    def test_scope_is_global(self, tmp_path):
        gs = GlobalSettings(path=str(tmp_path / "global.json"))
        assert gs.scope == SettingsScope.GLOBAL

    def test_schema_is_global_schema(self, tmp_path):
        gs = GlobalSettings(path=str(tmp_path / "global.json"))
        assert gs.schema is GLOBAL_SCHEMA

    def test_inherits_json_file_settings(self, tmp_path):
        gs = GlobalSettings(path=str(tmp_path / "global.json"))
        assert isinstance(gs, JsonFileSettings)

    def test_path_returns_provided(self, tmp_path):
        target = str(tmp_path / "g.json")
        gs = GlobalSettings(path=target)
        assert gs.path == target


class TestGlobalSettingsCRUD:
    """GlobalSettings 的读写行为应与底层的 JsonFileSettings 一致。"""

    def test_default_when_unset(self, tmp_path):
        gs = GlobalSettings(path=str(tmp_path / "g.json"))
        assert gs.get("ui.theme") == "Dark"
        assert gs.get("editor.tab_size") == 4
        assert gs.has("ui.theme") is False

    def test_set_then_get(self, tmp_path):
        gs = GlobalSettings(path=str(tmp_path / "g.json"))
        gs.set("ui.theme", "Light")
        assert gs.get("ui.theme") == "Light"
        assert gs.has("ui.theme") is True

    def test_set_unknown_key_raises(self, tmp_path):
        gs = GlobalSettings(path=str(tmp_path / "g.json"))
        with pytest.raises(KeyError):
            gs.set("not.a.real.key", "v")

    def test_set_invalid_choice_raises(self, tmp_path):
        gs = GlobalSettings(path=str(tmp_path / "g.json"))
        with pytest.raises(ValueError):
            gs.set("ui.theme", "NotATheme")

    def test_reset_single_key(self, tmp_path):
        gs = GlobalSettings(path=str(tmp_path / "g.json"))
        gs.set("ui.theme", "Light")
        gs.reset("ui.theme")
        assert gs.has("ui.theme") is False
        assert gs.get("ui.theme") == "Dark"

    def test_reset_all_clears_user_values(self, tmp_path):
        gs = GlobalSettings(path=str(tmp_path / "g.json"))
        gs.set("ui.theme", "Light")
        gs.set("editor.tab_size", 8)
        gs.reset()
        assert gs.defined() == {}
        assert gs.all()["ui.theme"] == "Dark"

    def test_all_includes_defaults(self, tmp_path):
        gs = GlobalSettings(path=str(tmp_path / "g.json"))
        gs.set("ui.theme", "Light")
        snap = gs.all()
        assert snap["ui.theme"] == "Light"
        assert snap["editor.tab_size"] == 4
        assert snap["completion.enabled"] is True

    def test_defined_only_user_set(self, tmp_path):
        gs = GlobalSettings(path=str(tmp_path / "g.json"))
        gs.set("ui.theme", "Light")
        defs = gs.defined()
        assert defs == {"ui.theme": "Light"}
        assert "editor.tab_size" not in defs

    def test_set_triggers_change_event(self, tmp_path):
        """set() 应触发 listener 事件,事件 scope == GLOBAL,key/old/new 正确。"""
        gs = GlobalSettings(path=str(tmp_path / "g.json"))
        events = []
        gs.add_listener(lambda evt: events.append(evt))
        gs.set("ui.theme", "Light")
        assert len(events) == 1
        evt = events[0]
        assert evt.scope == SettingsScope.GLOBAL
        assert evt.key == "ui.theme"
        assert evt.old == "Dark"
        assert evt.new == "Light"


class TestDefaultGlobalPath:
    """default_global_path() 应返回包含应用名的字符串。"""

    def test_returns_non_empty_string(self):
        p = default_global_path()
        assert isinstance(p, str)
        assert len(p) > 0

    def test_path_is_absolute(self):
        """默认路径在 Windows 上应包含盘符,是绝对路径。"""
        p = default_global_path()
        assert os.path.isabs(p)

    def test_contains_python_editor_windows(self):
        """Windows 平台应包含 PythonEditor 子串。"""
        if sys.platform.startswith("win"):
            assert "PythonEditor" in default_global_path()

    def test_contains_python_editor_macos(self):
        """macOS 平台应包含 PythonEditor 子串。"""
        if sys.platform == "darwin":
            assert "PythonEditor" in default_global_path()

    def test_contains_python_editor_other(self):
        """Linux / 其他平台也应包含 PythonEditor 子串。"""
        if not sys.platform.startswith("win") and sys.platform != "darwin":
            assert "PythonEditor" in default_global_path()

    def test_ends_with_settings_json(self):
        """默认文件名应为 settings.json。"""
        assert default_global_path().endswith("settings.json")


class TestResolvePath:
    """未显式传 path 时,_resolve_path() 与 default_global_path() 应一致。"""

    def test_resolve_path_returns_default_when_path_cleared(self, tmp_path):
        """将 _path 置 None 后,_resolve_path() 应回落到 default_global_path()。"""
        gs = GlobalSettings(path=str(tmp_path / "forced.json"))
        gs._path = None
        assert gs._resolve_path() == default_global_path()

    def test_path_property_uses_provided_when_set(self, tmp_path):
        target = str(tmp_path / "explicit.json")
        gs = GlobalSettings(path=target)
        assert gs.path == target

    def test_resolved_default_contains_app_name(self, tmp_path):
        gs = GlobalSettings(path=str(tmp_path / "x.json"))
        gs._path = None
        assert "PythonEditor" in gs._resolve_path()

    def test_default_resolution_starts_with_win_dir(self, tmp_path):
        """Windows 默认路径应以 APPDATA 或 home 目录开头。"""
        gs = GlobalSettings(path=str(tmp_path / "x.json"))
        gs._path = None
        if sys.platform.startswith("win"):
            p = gs._resolve_path()
            assert p.startswith("C:") or os.path.isabs(p)


class TestSaveAndReload:
    """save() 后重新构造实例应能读到相同值。"""

    def test_save_writes_to_disk(self, tmp_path):
        path = tmp_path / "global.json"
        gs = GlobalSettings(path=str(path))
        gs.set("ui.theme", "Light")
        gs.set("ui.font_size", 14)
        gs.save()
        assert path.is_file()

    def test_reload_preserves_values(self, tmp_path):
        path = tmp_path / "global.json"
        gs1 = GlobalSettings(path=str(path))
        gs1.set("ui.theme", "Light")
        gs1.set("ui.font_size", 14)
        gs1.save()
        gs2 = GlobalSettings(path=str(path))
        assert gs2.get("ui.theme") == "Light"
        assert gs2.get("ui.font_size") == 14
        assert gs2.has("ui.theme")
        assert gs2.has("ui.font_size")

    def test_ui_theme_change_round_trip(self, tmp_path):
        """修改 ui.theme 后 save(),重新构造实例能读到相同值。"""
        path = tmp_path / "global.json"
        gs = GlobalSettings(path=str(path))
        gs.set("ui.theme", "Solarized Dark")
        gs.save()
        reloaded = GlobalSettings(path=str(path))
        assert reloaded.get("ui.theme") == "Solarized Dark"
        assert reloaded.has("ui.theme") is True

    def test_save_writes_valid_json(self, tmp_path):
        """save() 写入的文件应是合法 JSON,包含 version 与 scope 字段。"""
        import json
        path = tmp_path / "global.json"
        gs = GlobalSettings(path=str(path))
        gs.set("ui.theme", "Light")
        gs.save()
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["version"] == CURRENT_VERSION
        assert data["scope"] == "global"
        assert data["values"]["ui.theme"] == "Light"

    def test_load_no_op_when_file_missing(self, tmp_path):
        """load() 在文件不存在时不应抛错,值保持默认。"""
        gs = GlobalSettings(path=str(tmp_path / "nonexistent.json"))
        assert gs.get("ui.theme") == "Dark"

    def test_save_uses_provided_path(self, tmp_path):
        """save() 应把数据写入 path 属性指定的文件。"""
        target = tmp_path / "subdir" / "g.json"
        gs = GlobalSettings(path=str(target))
        gs.set("ui.theme", "Light")
        gs.save()
        assert target.is_file()
