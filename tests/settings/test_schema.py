import os
import tempfile

import pytest

from modules.settings.base import (
    Settings,
    SettingsChangeEvent,
    SettingSpec,
    SettingsSchema,
    SettingsScope,
    SettingValueType,
)


class TestSettingsScope:
    def test_global(self):
        assert SettingsScope.GLOBAL.value == "global"

    def test_project(self):
        assert SettingsScope.PROJECT.value == "project"


class TestSettingValueType:
    def test_string(self):
        assert SettingValueType.STRING.value == "string"

    def test_integer(self):
        assert SettingValueType.INTEGER.value == "integer"

    def test_boolean(self):
        assert SettingValueType.BOOLEAN.value == "boolean"

    def test_choice(self):
        assert SettingValueType.CHOICE.value == "choice"

    def test_list(self):
        assert SettingValueType.LIST.value == "list"


class TestSettingSpec:
    def test_creation(self):
        spec = SettingSpec(key="test.key", type=SettingValueType.STRING, default="value")
        assert spec.key == "test.key"
        assert spec.type == SettingValueType.STRING
        assert spec.default == "value"

    def test_validate_string_valid(self):
        spec = SettingSpec(key="test", type=SettingValueType.STRING, default="")
        result = spec.validate("hello")
        assert result == "hello"

    def test_validate_string_invalid(self):
        spec = SettingSpec(key="test", type=SettingValueType.STRING, default="")
        with pytest.raises(ValueError):
            spec.validate(123)

    def test_validate_integer_valid(self):
        spec = SettingSpec(key="test", type=SettingValueType.INTEGER, default=0)
        result = spec.validate(42)
        assert result == 42

    def test_validate_integer_bool_rejected(self):
        spec = SettingSpec(key="test", type=SettingValueType.INTEGER, default=0)
        with pytest.raises(ValueError):
            spec.validate(True)

    def test_validate_integer_min(self):
        spec = SettingSpec(key="test", type=SettingValueType.INTEGER, default=0, min=10)
        with pytest.raises(ValueError):
            spec.validate(5)

    def test_validate_integer_max(self):
        spec = SettingSpec(key="test", type=SettingValueType.INTEGER, default=0, max=10)
        with pytest.raises(ValueError):
            spec.validate(15)

    def test_validate_float_valid(self):
        spec = SettingSpec(key="test", type=SettingValueType.FLOAT, default=0.0)
        result = spec.validate(3.14)
        assert result == 3.14

    def test_validate_boolean_valid(self):
        spec = SettingSpec(key="test", type=SettingValueType.BOOLEAN, default=False)
        result = spec.validate(True)
        assert result == True

    def test_validate_boolean_invalid(self):
        spec = SettingSpec(key="test", type=SettingValueType.BOOLEAN, default=False)
        with pytest.raises(ValueError):
            spec.validate("true")

    def test_validate_choice_valid(self):
        spec = SettingSpec(key="test", type=SettingValueType.CHOICE, default="a", choices=("a", "b", "c"))
        result = spec.validate("b")
        assert result == "b"

    def test_validate_choice_invalid(self):
        spec = SettingSpec(key="test", type=SettingValueType.CHOICE, default="a", choices=("a", "b", "c"))
        with pytest.raises(ValueError):
            spec.validate("d")

    def test_validate_list_valid(self):
        spec = SettingSpec(key="test", type=SettingValueType.LIST, default=[])
        result = spec.validate(["a", "b"])
        assert result == ["a", "b"]

    def test_validate_list_invalid(self):
        spec = SettingSpec(key="test", type=SettingValueType.LIST, default=[])
        with pytest.raises(ValueError):
            spec.validate("not a list")


class TestSettingsSchema:
    def test_creation(self):
        spec1 = SettingSpec(key="key1", type=SettingValueType.STRING, default="")
        spec2 = SettingSpec(key="key2", type=SettingValueType.INTEGER, default=0)
        schema = SettingsSchema((spec1, spec2))
        assert len(schema) == 2

    def test_keys(self):
        spec1 = SettingSpec(key="key1", type=SettingValueType.STRING, default="")
        spec2 = SettingSpec(key="key2", type=SettingValueType.INTEGER, default=0)
        schema = SettingsSchema((spec1, spec2))
        assert "key1" in schema.keys()
        assert "key2" in schema.keys()

    def test_get(self):
        spec1 = SettingSpec(key="key1", type=SettingValueType.STRING, default="")
        spec2 = SettingSpec(key="key2", type=SettingValueType.INTEGER, default=0)
        schema = SettingsSchema((spec1, spec2))
        result = schema.get("key1")
        assert result is spec1

    def test_get_nonexistent(self):
        schema = SettingsSchema(())
        result = schema.get("nonexistent")
        assert result is None

    def test_contains(self):
        spec = SettingSpec(key="key1", type=SettingValueType.STRING, default="")
        schema = SettingsSchema((spec,))
        assert "key1" in schema
        assert "key2" not in schema

    def test_defaults(self):
        spec1 = SettingSpec(key="key1", type=SettingValueType.STRING, default="default1")
        spec2 = SettingSpec(key="key2", type=SettingValueType.INTEGER, default=42)
        schema = SettingsSchema((spec1, spec2))
        defaults = schema.defaults()
        assert defaults["key1"] == "default1"
        assert defaults["key2"] == 42

    def test_duplicate_key_raises(self):
        spec1 = SettingSpec(key="key1", type=SettingValueType.STRING, default="")
        spec2 = SettingSpec(key="key1", type=SettingValueType.INTEGER, default=0)
        with pytest.raises(ValueError):
            SettingsSchema((spec1, spec2))


class TestSettingsChangeEvent:
    def test_creation(self):
        event = SettingsChangeEvent(
            scope=SettingsScope.GLOBAL,
            key="test.key",
            old="old_value",
            new="new_value"
        )
        assert event.scope == SettingsScope.GLOBAL
        assert event.key == "test.key"
        assert event.old == "old_value"
        assert event.new == "new_value"
