import pytest

from core.settings import (
    SettingSpec,
    SettingsSchema,
    SettingsScope,
    SettingValueType,
)


class TestSettingsScope:
    def test_global_value(self):
        assert SettingsScope.GLOBAL.value == "global"

    def test_project_value(self):
        assert SettingsScope.PROJECT.value == "project"


class TestSettingValueType:
    def test_string_value(self):
        assert SettingValueType.STRING.value == "string"

    def test_integer_value(self):
        assert SettingValueType.INTEGER.value == "integer"

    def test_float_value(self):
        assert SettingValueType.FLOAT.value == "float"

    def test_boolean_value(self):
        assert SettingValueType.BOOLEAN.value == "boolean"

    def test_choice_value(self):
        assert SettingValueType.CHOICE.value == "choice"

    def test_list_value(self):
        assert SettingValueType.LIST.value == "list"

    def test_path_value(self):
        assert SettingValueType.PATH.value == "path"

    def test_button_value(self):
        assert SettingValueType.BUTTON.value == "button"


class TestSettingSpecValidation:
    def test_validate_string_accepts_str(self):
        spec = SettingSpec(key="test", type=SettingValueType.STRING, default="")
        result = spec.validate("hello")
        assert result == "hello"

    def test_validate_string_rejects_non_str(self):
        spec = SettingSpec(key="test", type=SettingValueType.STRING, default="")
        with pytest.raises(ValueError):
            spec.validate(123)

    def test_validate_integer_accepts_int(self):
        spec = SettingSpec(key="test", type=SettingValueType.INTEGER, default=0)
        result = spec.validate(42)
        assert result == 42

    def test_validate_integer_rejects_bool(self):
        spec = SettingSpec(key="test", type=SettingValueType.INTEGER, default=0)
        with pytest.raises(ValueError):
            spec.validate(True)

    def test_validate_integer_respects_min(self):
        spec = SettingSpec(key="test", type=SettingValueType.INTEGER, default=0, min=10)
        with pytest.raises(ValueError):
            spec.validate(5)

    def test_validate_integer_respects_max(self):
        spec = SettingSpec(key="test", type=SettingValueType.INTEGER, default=0, max=100)
        with pytest.raises(ValueError):
            spec.validate(150)

    def test_validate_float_accepts_number(self):
        spec = SettingSpec(key="test", type=SettingValueType.FLOAT, default=0.0)
        result = spec.validate(3.14)
        assert result == 3.14

    def test_validate_float_converts_int(self):
        spec = SettingSpec(key="test", type=SettingValueType.FLOAT, default=0.0)
        result = spec.validate(5)
        assert result == 5.0

    def test_validate_boolean_accepts_bool(self):
        spec = SettingSpec(key="test", type=SettingValueType.BOOLEAN, default=False)
        result = spec.validate(True)
        assert result is True

    def test_validate_boolean_rejects_non_bool(self):
        spec = SettingSpec(key="test", type=SettingValueType.BOOLEAN, default=False)
        with pytest.raises(ValueError):
            spec.validate("true")

    def test_validate_choice_valid(self):
        spec = SettingSpec(
            key="test", type=SettingValueType.CHOICE, default="a", choices=("a", "b", "c")
        )
        result = spec.validate("b")
        assert result == "b"

    def test_validate_choice_invalid(self):
        spec = SettingSpec(
            key="test", type=SettingValueType.CHOICE, default="a", choices=("a", "b", "c")
        )
        with pytest.raises(ValueError):
            spec.validate("d")

    def test_validate_choice_empty_choices(self):
        spec = SettingSpec(key="test", type=SettingValueType.CHOICE, default="", choices=())
        with pytest.raises(ValueError):
            spec.validate("anything")

    def test_validate_list_valid(self):
        spec = SettingSpec(key="test", type=SettingValueType.LIST, default=[])
        result = spec.validate(["a", "b", "c"])
        assert result == ["a", "b", "c"]

    def test_validate_list_rejects_non_list(self):
        spec = SettingSpec(key="test", type=SettingValueType.LIST, default=[])
        with pytest.raises(ValueError):
            spec.validate("not a list")

    def test_validate_list_rejects_non_string_items(self):
        spec = SettingSpec(key="test", type=SettingValueType.LIST, default=[])
        with pytest.raises(ValueError):
            spec.validate([1, 2, 3])

    def test_validate_button(self):
        spec = SettingSpec(key="test", type=SettingValueType.BUTTON, default=None)
        result = spec.validate(None)
        assert result is None

    def test_validate_path_accepts_str(self):
        spec = SettingSpec(key="test", type=SettingValueType.PATH, default="")
        result = spec.validate("/some/path")
        assert result == "/some/path"

    def test_validate_path_rejects_non_str(self):
        spec = SettingSpec(key="test", type=SettingValueType.PATH, default="")
        with pytest.raises(ValueError):
            spec.validate(123)


class TestSettingsSchemaCollection:
    def test_multiple_specs(self):
        specs = (
            SettingSpec(
                key="ui.theme",
                type=SettingValueType.CHOICE,
                default="Dark",
                choices=("Dark", "Light"),
            ),
            SettingSpec(
                key="ui.font_size", type=SettingValueType.INTEGER, default=10, min=6, max=72
            ),
            SettingSpec(
                key="editor.tab_size", type=SettingValueType.INTEGER, default=4, min=1, max=16
            ),
        )
        schema = SettingsSchema(specs)
        assert len(schema) == 3
        assert schema.get("ui.theme") is not None
        assert schema.get("ui.font_size") is not None
        assert schema.get("editor.tab_size") is not None
