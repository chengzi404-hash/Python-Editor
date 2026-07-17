import os
import tempfile

import pytest

from core.settings import (
    GlobalSettings,
    ProjectSettings,
    SettingsManager,
    SettingsScope,
)


class TestSettingsManager:
    def test_init_default(self):
        manager = SettingsManager()
        assert manager.global_settings is not None

    def test_init_with_global_settings(self, temp_dir):
        path = os.path.join(temp_dir, "global.json")
        global_settings = GlobalSettings(path=path, auto_load=False)
        manager = SettingsManager(global_settings=global_settings)
        assert manager.global_settings is global_settings

    def test_init_with_project_settings(self, temp_dir):
        path = os.path.join(temp_dir, "project.json")
        project_settings = ProjectSettings(root=temp_dir, path=path, auto_load=False)
        manager = SettingsManager(project_settings=project_settings)
        assert manager.project_settings is project_settings

    def test_global_settings_property(self):
        manager = SettingsManager()
        assert isinstance(manager.global_settings, GlobalSettings)

    def test_project_settings_property_no_project(self):
        manager = SettingsManager()
        assert manager.project_settings is None

    def test_project_settings_property_with_project(self, temp_dir):
        manager = SettingsManager()
        manager.attach_project(temp_dir)
        assert manager.project_settings is not None

    def test_project_root_no_project(self):
        manager = SettingsManager()
        assert manager.project_root is None

    def test_project_root_with_project(self, temp_dir):
        manager = SettingsManager()
        manager.attach_project(temp_dir)
        assert manager.project_root == os.path.abspath(temp_dir)

    def test_attach_project(self, temp_dir):
        manager = SettingsManager()
        project = manager.attach_project(temp_dir)
        assert isinstance(project, ProjectSettings)
        assert manager.project_settings is project

    def test_detach_project(self, temp_dir):
        manager = SettingsManager()
        manager.attach_project(temp_dir)
        manager.detach_project()
        assert manager.project_settings is None

    def test_detach_project_no_project(self):
        manager = SettingsManager()
        manager.detach_project()
        assert manager.project_settings is None

    def test_get_global(self):
        manager = SettingsManager()
        result = manager.get(SettingsScope.GLOBAL, "editor.tab_size")
        assert result == 4

    def test_get_project(self, temp_dir):
        manager = SettingsManager()
        manager.attach_project(temp_dir)
        result = manager.get(SettingsScope.PROJECT, "project.tab_size")
        assert result == 4

    def test_get_project_no_project_raises(self):
        manager = SettingsManager()
        with pytest.raises(LookupError):
            manager.get(SettingsScope.PROJECT, "project.tab_size")

    def test_set_global(self):
        manager = SettingsManager()
        manager.set(SettingsScope.GLOBAL, "editor.tab_size", 8)
        assert manager.get(SettingsScope.GLOBAL, "editor.tab_size") == 8

    def test_set_project(self, temp_dir):
        manager = SettingsManager()
        manager.attach_project(temp_dir)
        manager.set(SettingsScope.PROJECT, "project.tab_size", 8)
        assert manager.get(SettingsScope.PROJECT, "project.tab_size") == 8

    def test_set_project_no_project_raises(self):
        manager = SettingsManager()
        with pytest.raises(LookupError):
            manager.set(SettingsScope.PROJECT, "project.tab_size", 8)

    def test_effective_no_project(self):
        manager = SettingsManager()
        manager.set(SettingsScope.GLOBAL, "editor.tab_size", 8)
        assert manager.effective("editor.tab_size") == 8

    def test_effective_project_overrides_global(self, temp_dir):
        manager = SettingsManager()
        manager.set(SettingsScope.GLOBAL, "editor.tab_size", 4)
        manager.attach_project(temp_dir)
        manager.set(SettingsScope.PROJECT, "project.tab_size", 8)
        assert manager.effective("project.tab_size") == 8

    def test_effective_fallback_to_global(self, temp_dir):
        manager = SettingsManager()
        manager.set(SettingsScope.GLOBAL, "editor.tab_size", 8)
        manager.attach_project(temp_dir)
        assert manager.effective("editor.tab_size") == 8

    def test_effective_with_default(self):
        manager = SettingsManager()
        result = manager.effective("nonexistent.key", default="default")
        assert result == "default"

    def test_reset_global(self):
        manager = SettingsManager()
        manager.set(SettingsScope.GLOBAL, "editor.tab_size", 8)
        manager.reset(SettingsScope.GLOBAL, "editor.tab_size")
        assert manager.get(SettingsScope.GLOBAL, "editor.tab_size") == 4

    def test_reset_project(self, temp_dir):
        manager = SettingsManager()
        manager.attach_project(temp_dir)
        manager.set(SettingsScope.PROJECT, "project.tab_size", 8)
        manager.reset(SettingsScope.PROJECT, "project.tab_size")
        assert manager.get(SettingsScope.PROJECT, "project.tab_size") == 4

    def test_add_listener(self):
        manager = SettingsManager()
        events = []

        def listener(event):
            events.append(event)

        manager.add_listener(listener)
        manager.set(SettingsScope.GLOBAL, "editor.tab_size", 8)
        assert len(events) >= 1

    def test_remove_listener(self):
        manager = SettingsManager()

        def listener(event):
            pass

        manager.add_listener(listener)
        manager.remove_listener(listener)
        manager.set(SettingsScope.GLOBAL, "editor.tab_size", 8)

    def test_save_all(self, temp_dir):
        global_path = os.path.join(temp_dir, "global.json")
        project_path = os.path.join(temp_dir, "project.json")
        global_settings = GlobalSettings(path=global_path, auto_load=False)
        project_settings = ProjectSettings(root=temp_dir, path=project_path, auto_load=False)
        manager = SettingsManager(global_settings=global_settings, project_settings=project_settings)
        manager.set(SettingsScope.GLOBAL, "editor.tab_size", 8)
        manager.set(SettingsScope.PROJECT, "project.tab_size", 8)
        manager.save_all()

        manager2 = SettingsManager(global_settings=GlobalSettings(path=global_path))
        assert manager2.get(SettingsScope.GLOBAL, "editor.tab_size") == 8

    def test_context_manager(self, temp_dir):
        path = os.path.join(temp_dir, "settings.json")
        global_settings = GlobalSettings(path=path, auto_load=False)
        with SettingsManager(global_settings=global_settings) as manager:
            manager.set(SettingsScope.GLOBAL, "editor.tab_size", 8)

        manager2 = SettingsManager(global_settings=GlobalSettings(path=path))
        assert manager2.get(SettingsScope.GLOBAL, "editor.tab_size") == 8

    def test_global_all(self):
        manager = SettingsManager()
        result = manager.global_all()
        assert isinstance(result, dict)
        assert "editor.tab_size" in result

    def test_project_all_no_project(self):
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
        assert "editor.tab_size" in result

    def test_repr(self):
        manager = SettingsManager()
        r = repr(manager)
        assert "SettingsManager" in r
