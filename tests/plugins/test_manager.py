import pytest
import os
import tempfile
from unittest.mock import MagicMock, patch
from modules.plugins.manager import PluginManager, DiscoveredPlugin
from modules.plugins.api import PluginManifest, _HookSubscription


class TestPluginManager:
    def test_init(self):
        manager = PluginManager()
        assert manager is not None

    def test_init_with_custom_dir(self):
        manager = PluginManager(global_plugins_dir="/custom/path")
        assert manager is not None

    def test_attach_editor(self):
        manager = PluginManager()
        mock_editor = MagicMock()
        manager.attach_editor(mock_editor)
        with manager._lock:
            assert manager._editor is mock_editor

    def test_detach_editor(self):
        manager = PluginManager()
        mock_editor = MagicMock()
        manager.attach_editor(mock_editor)
        manager.detach_editor()
        with manager._lock:
            assert manager._editor is None

    def test_discover_global_empty_dir(self):
        manager = PluginManager(global_plugins_dir="/nonexistent/path")
        result = manager.discover_global()
        assert result == []

    def test_discover_project_empty_root(self):
        manager = PluginManager()
        result = manager.discover_project("")
        assert result == []

    def test_discover_project_nonexistent(self):
        manager = PluginManager()
        result = manager.discover_project("/nonexistent/path")
        assert result == []

    def test_list_loaded_empty(self):
        manager = PluginManager()
        result = manager.list_loaded()
        assert result == []

    def test_list_discovered_empty(self):
        manager = PluginManager()
        result = manager.list_discovered()
        assert result == []

    def test_get_commands_empty(self):
        manager = PluginManager()
        result = manager.get_commands()
        assert result == []

    def test_get_languages_empty(self):
        manager = PluginManager()
        result = manager.get_languages()
        assert result == []


class TestDiscoveredPlugin:
    def test_creation(self):
        manifest = PluginManifest(id="test", name="Test")
        plugin = DiscoveredPlugin(manifest=manifest, location="/path", scope="global")
        assert plugin.manifest == manifest
        assert plugin.location == "/path"
        assert plugin.scope == "global"


class TestTkShortcut:
    def test_ctrl_shortcut(self):
        manager = PluginManager()
        result = manager._tk_shortcut("Ctrl+H")
        assert result == "<Control-H>"

    def test_ctrl_shift_shortcut(self):
        manager = PluginManager()
        result = manager._tk_shortcut("Ctrl+Shift+H")
        assert result == "<Control-Shift-H>"

    def test_alt_shortcut(self):
        manager = PluginManager()
        result = manager._tk_shortcut("Alt+F4")
        assert result == "<Alt-F4>"

    def test_simple_key(self):
        manager = PluginManager()
        result = manager._tk_shortcut("F5")
        assert result == "<F5>"

    def test_empty_shortcut(self):
        manager = PluginManager()
        result = manager._tk_shortcut("")
        assert result == "<>"
