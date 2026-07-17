import os

import pytest

from core.settings import ProjectSettings, SettingsScope, default_project_path


class TestProjectSettings:
    def test_init_with_root(self, temp_dir):
        settings = ProjectSettings(root=temp_dir, auto_load=False)
        assert settings.root == os.path.abspath(temp_dir)

    def test_init_empty_root_raises(self):
        with pytest.raises(ValueError):
            ProjectSettings(root="")

    def test_scope(self):
        settings = ProjectSettings(root="/fake/path", auto_load=False)
        assert settings.scope == SettingsScope.PROJECT

    def test_path(self, temp_dir):
        settings = ProjectSettings(root=temp_dir, auto_load=False)
        expected = default_project_path(temp_dir)
        assert settings.path == expected

    def test_get_default_value(self, temp_dir):
        settings = ProjectSettings(root=temp_dir, auto_load=False)
        result = settings.get("project.python_interpreter", default="python")
        assert result == "python"

    def test_get_with_schema_default(self, temp_dir):
        settings = ProjectSettings(root=temp_dir, auto_load=False)
        result = settings.get("project.tab_size")
        assert result == 4

    def test_set_and_get(self, temp_dir):
        settings = ProjectSettings(root=temp_dir, auto_load=False)
        settings.set("project.python_interpreter", "/usr/bin/python3")
        assert settings.get("project.python_interpreter") == "/usr/bin/python3"

    def test_has(self, temp_dir):
        settings = ProjectSettings(root=temp_dir, auto_load=False)
        settings.set("project.python_interpreter", "/usr/bin/python3")
        assert settings.has("project.python_interpreter")

    def test_has_not_set(self, temp_dir):
        settings = ProjectSettings(root=temp_dir, auto_load=False)
        assert not settings.has("project.python_interpreter")

    def test_reset_single(self, temp_dir):
        settings = ProjectSettings(root=temp_dir, auto_load=False)
        settings.set("project.tab_size", 8)
        settings.reset("project.tab_size")
        assert settings.get("project.tab_size") == 4

    def test_reset_all(self, temp_dir):
        settings = ProjectSettings(root=temp_dir, auto_load=False)
        settings.set("project.tab_size", 8)
        settings.reset()
        assert settings.get("project.tab_size") == 4

    def test_save_and_load(self, temp_dir):
        path = os.path.join(temp_dir, "settings.json")
        settings = ProjectSettings(root=temp_dir, path=path)
        settings.set("project.python_interpreter", "/usr/bin/python3")
        settings.save()

        settings2 = ProjectSettings(root=temp_dir, path=path)
        assert settings2.get("project.python_interpreter") == "/usr/bin/python3"

    def test_all(self, temp_dir):
        settings = ProjectSettings(root=temp_dir, auto_load=False)
        all_values = settings.all()
        assert isinstance(all_values, dict)
        assert "project.tab_size" in all_values

    def test_project_name_with_setting(self, temp_dir):
        settings = ProjectSettings(root=temp_dir, auto_load=False)
        settings.set("project.name", "MyProject")
        assert settings.project_name() == "MyProject"

    def test_project_name_without_setting(self, temp_dir):
        settings = ProjectSettings(root=temp_dir, auto_load=False)
        expected_name = os.path.basename(os.path.abspath(temp_dir))
        assert settings.project_name() == expected_name


class TestDefaultProjectPath:
    def test_returns_path(self, temp_dir):
        path = default_project_path(temp_dir)
        assert isinstance(path, str)
        expected = os.path.join(temp_dir, ".pyeditor", "settings.json")
        assert path == expected
