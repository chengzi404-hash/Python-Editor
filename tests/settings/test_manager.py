import os
import tempfile

import pytest

from modules.settings.manager import SettingsManager


class TestSettingsManager:
    def test_init(self):
        manager = SettingsManager()
        assert manager is not None

    def test_global_settings(self):
        manager = SettingsManager()
        assert manager.global_settings is not None

    def test_project_settings_initially_none(self):
        manager = SettingsManager()
        assert manager.project_settings is None

    def test_project_root_initially_none(self):
        manager = SettingsManager()
        assert manager.project_root is None

    def test_attach_project(self, temp_dir):
        manager = SettingsManager()
        project = manager.attach_project(temp_dir)
        assert project is not None
        assert manager.project_settings is not None
        assert manager.project_root == os.path.abspath(temp_dir)

    def test_detach_project(self, temp_dir):
        manager = SettingsManager()
        manager.attach_project(temp_dir)
        manager.detach_project()
        assert manager.project_settings is None

    def test_get_global(self):
        manager = SettingsManager()
        result = manager.get(manager.global_settings.scope, "editor.tab_size")
        assert result == 4

    def test_set_global(self):
        manager = SettingsManager()
        from modules.settings.base import SettingsScope
        manager.set(SettingsScope.GLOBAL, "editor.tab_size", 8)
        result = manager.get(SettingsScope.GLOBAL, "editor.tab_size")
        assert result == 8

    def test_effective_global_only(self):
        manager = SettingsManager()
        from modules.settings.base import SettingsScope
        manager.set(SettingsScope.GLOBAL, "editor.tab_size", 8)
        result = manager.effective("editor.tab_size")
        assert result == 8

    def test_effective_project_overrides_global(self, temp_dir):
        manager = SettingsManager()
        from modules.settings.base import SettingsScope
        manager.set(SettingsScope.GLOBAL, "editor.tab_size", 4)
        manager.attach_project(temp_dir)
        manager.set(SettingsScope.PROJECT, "project.tab_size", 8)
        result = manager.effective("project.tab_size")
        assert result == 8

    def test_effective_fallback_to_global(self, temp_dir):
        manager = SettingsManager()
        from modules.settings.base import SettingsScope
        manager.set(SettingsScope.GLOBAL, "editor.tab_size", 4)
        manager.attach_project(temp_dir)
        result = manager.effective("editor.tab_size")
        assert result == 4

    def test_reset_global(self):
        manager = SettingsManager()
        from modules.settings.base import SettingsScope
        manager.set(SettingsScope.GLOBAL, "editor.tab_size", 8)
        manager.reset(SettingsScope.GLOBAL, "editor.tab_size")
        result = manager.get(SettingsScope.GLOBAL, "editor.tab_size")
        assert result == 4

    def test_add_listener(self):
        manager = SettingsManager()
        events = []
        def listener(event):
            events.append(event)
        manager.add_listener(listener)
        assert len(manager._user_listeners) == 1

    def test_save_all(self, temp_dir):
        manager = SettingsManager()
        from modules.settings.base import SettingsScope
        manager.set(SettingsScope.GLOBAL, "editor.tab_size", 8)
        manager.attach_project(temp_dir)
        manager.set(SettingsScope.PROJECT, "project.tab_size", 8)
        manager.save_all()

    def test_context_manager(self, temp_dir):
        from modules.settings.base import SettingsScope
        from modules.settings.global_settings import GlobalSettings
        settings_path = os.path.join(temp_dir, "settings.json")
        gs1 = GlobalSettings(path=settings_path)
        with SettingsManager(global_settings=gs1) as manager:
            manager.set(SettingsScope.GLOBAL, "editor.tab_size", 8)
        gs2 = GlobalSettings(path=settings_path)
        manager2 = SettingsManager(global_settings=gs2)
        assert manager2.get(SettingsScope.GLOBAL, "editor.tab_size") == 8

    def test_global_all(self):
        manager = SettingsManager()
        result = manager.global_all()
        assert isinstance(result, dict)

    def test_project_all_empty(self):
        manager = SettingsManager()
        result = manager.project_all()
        assert result == {}

    def test_project_all_with_project(self, temp_dir):
        manager = SettingsManager()
        manager.attach_project(temp_dir)
        result = manager.project_all()
        assert isinstance(result, dict)

    def test_effective_all(self):
        manager = SettingsManager()
        result = manager.effective_all()
        assert isinstance(result, dict)
