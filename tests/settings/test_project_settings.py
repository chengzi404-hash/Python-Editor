import os
import tempfile

import pytest

from modules.settings.project_settings import ProjectSettings, default_project_path


class TestProjectSettings:
    def test_init_with_root(self, temp_dir):
        settings = ProjectSettings(root=temp_dir, auto_load=False)
        assert settings.root == os.path.abspath(temp_dir)

    def test_init_empty_root_raises(self):
        with pytest.raises(ValueError):
            ProjectSettings(root="")

    def test_scope(self, temp_dir):
        settings = ProjectSettings(root=temp_dir, auto_load=False)
        from modules.settings.base import SettingsScope
        assert settings.scope == SettingsScope.PROJECT

    def test_default_project_path(self, temp_dir):
        path = default_project_path(temp_dir)
        expected = os.path.join(temp_dir, ".pyeditor", "settings.json")
        assert path == expected

    def test_get_default_value(self, temp_dir):
        settings = ProjectSettings(root=temp_dir, auto_load=False)
        result = settings.get("project.tab_size", default=4)
        assert result == 4

    def test_set_and_get(self, temp_dir):
        settings = ProjectSettings(root=temp_dir, auto_load=False)
        settings.set("project.tab_size", 8)
        assert settings.get("project.tab_size") == 8

    def test_has(self, temp_dir):
        settings = ProjectSettings(root=temp_dir, auto_load=False)
        settings.set("project.tab_size", 8)
        assert settings.has("project.tab_size")

    def test_save_and_load(self, temp_dir):
        path = os.path.join(temp_dir, ".pyeditor", "settings.json")
        settings = ProjectSettings(root=temp_dir, path=path)
        settings.set("project.tab_size", 8)
        settings.save()

        settings2 = ProjectSettings(root=temp_dir, path=path)
        assert settings2.get("project.tab_size") == 8

    def test_project_name_default(self, temp_dir):
        settings = ProjectSettings(root=temp_dir, auto_load=False)
        name = settings.project_name()
        assert name == os.path.basename(temp_dir)

    def test_project_name_custom(self, temp_dir):
        settings = ProjectSettings(root=temp_dir, auto_load=False)
        settings.set("project.name", "MyProject")
        name = settings.project_name()
        assert name == "MyProject"
