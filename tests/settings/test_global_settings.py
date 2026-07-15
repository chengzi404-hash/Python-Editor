import json
import os
import tempfile

import pytest

from modules.settings.global_settings import GlobalSettings, default_global_path


class TestGlobalSettings:
    def test_init_with_path(self, temp_dir):
        path = os.path.join(temp_dir, "settings.json")
        settings = GlobalSettings(path=path, auto_load=False)
        assert settings.path == path

    def test_init_default_path(self):
        settings = GlobalSettings(auto_load=False)
        assert settings.path is not None

    def test_scope(self):
        settings = GlobalSettings(auto_load=False)
        from modules.settings.base import SettingsScope
        assert settings.scope == SettingsScope.GLOBAL

    def test_get_default_value(self):
        settings = GlobalSettings(auto_load=False)
        result = settings.get("editor.tab_size", default=4)
        assert result == 4

    def test_get_with_schema_default(self):
        settings = GlobalSettings(auto_load=False)
        result = settings.get("editor.tab_size")
        assert result == 4

    def test_set_and_get(self):
        settings = GlobalSettings(auto_load=False)
        settings.set("editor.tab_size", 8)
        assert settings.get("editor.tab_size") == 8

    def test_has(self):
        settings = GlobalSettings(auto_load=False)
        settings.set("editor.tab_size", 8)
        assert settings.has("editor.tab_size") == True

    def test_has_not_set(self):
        settings = GlobalSettings(auto_load=False)
        assert settings.has("editor.tab_size") == False

    def test_reset_single(self):
        settings = GlobalSettings(auto_load=False)
        settings.set("editor.tab_size", 8)
        settings.reset("editor.tab_size")
        assert settings.get("editor.tab_size") == 4

    def test_reset_all(self):
        settings = GlobalSettings(auto_load=False)
        settings.set("editor.tab_size", 8)
        settings.reset()
        assert settings.get("editor.tab_size") == 4

    def test_save_and_load(self, temp_dir):
        path = os.path.join(temp_dir, "settings.json")
        settings = GlobalSettings(path=path)
        settings.set("editor.tab_size", 8)
        settings.save()

        settings2 = GlobalSettings(path=path)
        assert settings2.get("editor.tab_size") == 8

    def test_all(self):
        settings = GlobalSettings(auto_load=False)
        all_values = settings.all()
        assert isinstance(all_values, dict)
        assert "editor.tab_size" in all_values


class TestDefaultGlobalPath:
    def test_returns_path(self):
        path = default_global_path()
        assert isinstance(path, str)
        assert len(path) > 0
