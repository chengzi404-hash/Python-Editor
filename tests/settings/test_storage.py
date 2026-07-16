import json
import os
import tempfile

import pytest

from modules.settings.base import SettingSpec, SettingsSchema, SettingsScope, SettingValueType
from modules.settings.storage import CURRENT_VERSION, JsonFileSettings


class TestJsonFileSettings:
    def test_init_with_path(self, temp_dir):
        path = os.path.join(temp_dir, "settings.json")
        schema = SettingsSchema((
            SettingSpec(key="test.key", type=SettingValueType.STRING, default=""),
        ))
        settings = JsonFileSettings(schema=schema, scope=SettingsScope.GLOBAL, path=path, auto_load=False)
        assert settings.path == path

    def test_is_plugin_key(self):
        schema = SettingsSchema(())
        settings = JsonFileSettings(schema=schema, scope=SettingsScope.GLOBAL, auto_load=False)
        assert settings._is_plugin_key("plugins.myplugin.enabled")
        assert not settings._is_plugin_key("plugins.myplugin")
        assert not settings._is_plugin_key("normal.key")

    def test_get_with_default(self):
        schema = SettingsSchema((
            SettingSpec(key="test.key", type=SettingValueType.STRING, default="default"),
        ))
        settings = JsonFileSettings(schema=schema, scope=SettingsScope.GLOBAL, auto_load=False)
        result = settings.get("test.key")
        assert result == "default"

    def test_set_and_get(self):
        schema = SettingsSchema((
            SettingSpec(key="test.key", type=SettingValueType.STRING, default=""),
        ))
        settings = JsonFileSettings(schema=schema, scope=SettingsScope.GLOBAL, auto_load=False)
        settings.set("test.key", "value")
        assert settings.get("test.key") == "value"

    def test_plugin_key_bypass_validation(self):
        schema = SettingsSchema((
            SettingSpec(key="normal.key", type=SettingValueType.STRING, default=""),
        ))
        settings = JsonFileSettings(schema=schema, scope=SettingsScope.GLOBAL, auto_load=False)
        settings.set("plugins.myplugin.anykey", "anyvalue")
        assert settings.get("plugins.myplugin.anykey") == "anyvalue"

    def test_has(self):
        schema = SettingsSchema((
            SettingSpec(key="test.key", type=SettingValueType.STRING, default=""),
        ))
        settings = JsonFileSettings(schema=schema, scope=SettingsScope.GLOBAL, auto_load=False)
        assert not settings.has("test.key")
        settings.set("test.key", "value")
        assert settings.has("test.key")

    def test_all(self):
        schema = SettingsSchema((
            SettingSpec(key="key1", type=SettingValueType.STRING, default="default1"),
            SettingSpec(key="key2", type=SettingValueType.INTEGER, default=42),
        ))
        settings = JsonFileSettings(schema=schema, scope=SettingsScope.GLOBAL, auto_load=False)
        all_values = settings.all()
        assert all_values["key1"] == "default1"
        assert all_values["key2"] == 42

    def test_defined(self):
        schema = SettingsSchema((
            SettingSpec(key="key1", type=SettingValueType.STRING, default=""),
        ))
        settings = JsonFileSettings(schema=schema, scope=SettingsScope.GLOBAL, auto_load=False)
        settings.set("key1", "value")
        defined = settings.defined()
        assert "key1" in defined
        assert defined["key1"] == "value"

    def test_save_and_load(self, temp_dir):
        path = os.path.join(temp_dir, "settings.json")
        schema = SettingsSchema((
            SettingSpec(key="test.key", type=SettingValueType.STRING, default=""),
        ))
        settings = JsonFileSettings(schema=schema, scope=SettingsScope.GLOBAL, path=path)
        settings.set("test.key", "saved_value")
        settings.save()

        settings2 = JsonFileSettings(schema=schema, scope=SettingsScope.GLOBAL, path=path)
        assert settings2.get("test.key") == "saved_value"

    def test_load_nonexistent_file(self, temp_dir):
        path = os.path.join(temp_dir, "nonexistent.json")
        schema = SettingsSchema((
            SettingSpec(key="test.key", type=SettingValueType.STRING, default="default"),
        ))
        settings = JsonFileSettings(schema=schema, scope=SettingsScope.GLOBAL, path=path)
        assert settings.get("test.key") == "default"

    def test_reset_single_key(self):
        schema = SettingsSchema((
            SettingSpec(key="test.key", type=SettingValueType.STRING, default="default"),
        ))
        settings = JsonFileSettings(schema=schema, scope=SettingsScope.GLOBAL, auto_load=False)
        settings.set("test.key", "custom")
        settings.reset("test.key")
        assert settings.get("test.key") == "default"

    def test_reset_all(self):
        schema = SettingsSchema((
            SettingSpec(key="key1", type=SettingValueType.STRING, default="default1"),
            SettingSpec(key="key2", type=SettingValueType.INTEGER, default=42),
        ))
        settings = JsonFileSettings(schema=schema, scope=SettingsScope.GLOBAL, auto_load=False)
        settings.set("key1", "custom1")
        settings.set("key2", 100)
        settings.reset()
        assert settings.get("key1") == "default1"
        assert settings.get("key2") == 42
