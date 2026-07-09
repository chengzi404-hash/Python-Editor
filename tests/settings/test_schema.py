"""
针对 modules.settings.schema 的测试。

覆盖:

* GLOBAL_SCHEMA / PROJECT_SCHEMA 都是 SettingsSchema 实例。
* 默认 schema 至少包含若干已知的设置项,以及对 type/scope 的校验。
* CHOICE 类型必须携带非空 choices;INTEGER/FLOAT 的 min/max 合法。
* SCHEMA_BY_SCOPE 与 get_schema 的取值正确。
"""

from __future__ import annotations

import pytest

from modules.settings.base import (
    SettingsSchema,
    SettingsScope,
    SettingValueType,
)
from modules.settings.schema import (
    GLOBAL_SCHEMA,
    GLOBAL_SPECS,
    PROJECT_SCHEMA,
    PROJECT_SPECS,
    SCHEMA_BY_SCOPE,
    get_schema,
)


class TestSchemaTypes:
    """GLOBAL_SCHEMA 与 PROJECT_SCHEMA 都应是 SettingsSchema 实例。"""

    def test_global_schema_is_settings_schema(self) -> None:
        assert isinstance(GLOBAL_SCHEMA, SettingsSchema)

    def test_project_schema_is_settings_schema(self) -> None:
        assert isinstance(PROJECT_SCHEMA, SettingsSchema)

    def test_global_schema_is_not_empty(self) -> None:
        assert len(GLOBAL_SCHEMA) > 0

    def test_project_schema_is_not_empty(self) -> None:
        assert len(PROJECT_SCHEMA) > 0


class TestGlobalKeysPresent:
    """默认 GLOBAL_SCHEMA 必须包含若干核心全局设置项。"""

    @pytest.mark.parametrize(
        """key""",
        [
            """ui.theme""",
            """editor.tab_size""",
            """completion.enabled""",
            """checker.timeout_ms""",
        ],
    )
    def test_known_global_key_exists(self, key: str) -> None:
        assert key in GLOBAL_SCHEMA
        spec = GLOBAL_SCHEMA.get(key)
        assert spec is not None
        assert spec.key == key


class TestProjectKeysPresent:
    """默认 PROJECT_SCHEMA 必须包含若干核心项目设置项。"""

    @pytest.mark.parametrize(
        """key""",
        [
            """project.python_interpreter""",
            """project.entry_point""",
            """checker.enabled""",
            """project.exclude_paths""",
        ],
    )
    def test_known_project_key_exists(self, key: str) -> None:
        assert key in PROJECT_SCHEMA
        spec = PROJECT_SCHEMA.get(key)
        assert spec is not None
        assert spec.key == key


class TestSpecTypes:
    """若干已知 key 的 type 字段必须符合预期。"""

    def test_ui_theme_is_choice(self) -> None:
        spec = GLOBAL_SCHEMA.get("""ui.theme""")
        assert spec is not None
        assert spec.type is SettingValueType.CHOICE

    def test_editor_tab_size_is_integer(self) -> None:
        spec = GLOBAL_SCHEMA.get("""editor.tab_size""")
        assert spec is not None
        assert spec.type is SettingValueType.INTEGER

    def test_completion_enabled_is_boolean(self) -> None:
        spec = GLOBAL_SCHEMA.get("""completion.enabled""")
        assert spec is not None
        assert spec.type is SettingValueType.BOOLEAN

    def test_checker_timeout_is_integer(self) -> None:
        spec = GLOBAL_SCHEMA.get("""checker.timeout_ms""")
        assert spec is not None
        assert spec.type is SettingValueType.INTEGER

    def test_checker_enabled_is_list(self) -> None:
        spec = PROJECT_SCHEMA.get("""checker.enabled""")
        assert spec is not None
        assert spec.type is SettingValueType.LIST

    def test_project_exclude_paths_is_list(self) -> None:
        spec = PROJECT_SCHEMA.get("""project.exclude_paths""")
        assert spec is not None
        assert spec.type is SettingValueType.LIST

    def test_project_python_interpreter_is_path(self) -> None:
        spec = PROJECT_SCHEMA.get("""project.python_interpreter""")
        assert spec is not None
        assert spec.type is SettingValueType.PATH

    def test_project_entry_point_is_path(self) -> None:
        spec = PROJECT_SCHEMA.get("""project.entry_point""")
        assert spec is not None
        assert spec.type is SettingValueType.PATH


class TestChoiceSpecsHaveChoices:
    """所有 CHOICE 类型 spec 都应声明非空 choices。"""

    @pytest.mark.parametrize(
        """schema,scope""",
        [(GLOBAL_SCHEMA, SettingsScope.GLOBAL), (PROJECT_SCHEMA, SettingsScope.PROJECT)],
    )
    def test_every_choice_has_non_empty_choices(
        self, schema: SettingsSchema, scope: SettingsScope,
    ) -> None:
        for spec in schema:
            if spec.type is SettingValueType.CHOICE:
                assert spec.choices, (
                    """CHOICE 规格 %r 必须声明至少一个候选项""" % spec.key,
                )
                assert spec.default in spec.choices, (
                    """CHOICE 规格 %r 的 default=%r 不在 choices=%r 中""" % (
                        spec.key, spec.default, list(spec.choices),
                    )
                )


class TestNumericBounds:
    """数值 spec 的 min/max 边界及 default 区间校验。"""

    @pytest.mark.parametrize(
        """schema""",
        [GLOBAL_SCHEMA, PROJECT_SCHEMA],
    )
    def test_numeric_specs_have_valid_bounds(self, schema: SettingsSchema) -> None:
        """数值 spec 须满足 min <= max,且 default 在区间内。"""
        for spec in schema:
            if spec.type not in (
                SettingValueType.INTEGER,
                SettingValueType.FLOAT,
            ):
                continue
            if spec.min is None or spec.max is None:
                continue
            assert spec.min <= spec.max, (
                """数值规格 %r 的 min=%s =%s""" % (spec.key, spec.min, spec.max),
            )
            assert spec.min <= spec.default <= spec.max, (
                """数值规格 %r 的 default=%s 不在 [%s, %s] 区间内""" % (spec.key, spec.default, spec.min, spec.max),
            )


class TestGlobalSpecsScope:
    """GLOBAL_SPECS 中每个 spec 的 scope 必须是 SettingsScope.GLOBAL。"""

    def test_all_global_specs_have_global_scope(self) -> None:
        assert GLOBAL_SPECS, """GLOBAL_SPECS 不应为空"""
        for spec in GLOBAL_SPECS:
            assert spec.scope is SettingsScope.GLOBAL, (
                """GLOBAL_SPECS 中的 %r scope=%r""" % (spec.key, spec.scope)
            )


class TestProjectSpecsScope:
    """PROJECT_SPECS 中每个 spec 的 scope 必须是 SettingsScope.PROJECT。"""

    def test_all_project_specs_have_project_scope(self) -> None:
        assert PROJECT_SPECS, """PROJECT_SPECS 不应为空"""
        for spec in PROJECT_SPECS:
            assert spec.scope is SettingsScope.PROJECT, (
                """PROJECT_SPECS 中的 %r scope=%r""" % (spec.key, spec.scope)
            )


class TestSchemaByScope:
    """SCHEMA_BY_SCOPE 同时包含 GLOBAL 与 PROJECT 两个键。"""

    def test_contains_global(self) -> None:
        assert SettingsScope.GLOBAL in SCHEMA_BY_SCOPE
        assert SCHEMA_BY_SCOPE[SettingsScope.GLOBAL] is GLOBAL_SCHEMA

    def test_contains_project(self) -> None:
        assert SettingsScope.PROJECT in SCHEMA_BY_SCOPE
        assert SCHEMA_BY_SCOPE[SettingsScope.PROJECT] is PROJECT_SCHEMA

    def test_only_contains_known_scopes(self) -> None:
        from modules.settings.base import SettingsScope as _SS
        assert set(SCHEMA_BY_SCOPE.keys()) == {_SS.GLOBAL, _SS.PROJECT}


class TestGetSchema:
    """get_schema 应按作用域返回对应的内置 SettingsSchema。"""

    def test_get_global_returns_global_schema(self) -> None:
        assert get_schema(SettingsScope.GLOBAL) is GLOBAL_SCHEMA

    def test_get_project_returns_project_schema(self) -> None:
        assert get_schema(SettingsScope.PROJECT) is PROJECT_SCHEMA


class TestHighlightDelaySpec:
    """``editor.highlight_delay_ms`` —— 高亮防抖延迟设置项。

    类型、默认值、范围、scope 都必须严格符合 :mod:`main.py` 中的消费方约定:
    0 表示"无延迟"(走 ``after(0, ...)`` 立即路径),5000 是上限。
    """

    def test_key_exists(self) -> None:
        assert "editor.highlight_delay_ms" in GLOBAL_SCHEMA

    def test_type_is_integer(self) -> None:
        spec = GLOBAL_SCHEMA.get("editor.highlight_delay_ms")
        assert spec is not None
        assert spec.type is SettingValueType.INTEGER

    def test_default_is_300(self) -> None:
        spec = GLOBAL_SCHEMA.get("editor.highlight_delay_ms")
        assert spec is not None
        assert spec.default == 300

    def test_default_allows_zero(self) -> None:
        """默认值为 0 意味着可以关闭防抖(立即高亮)。"""
        spec = GLOBAL_SCHEMA.get("editor.highlight_delay_ms")
        assert spec is not None
        validated = spec.validate(0)
        assert validated == 0

    def test_min_is_zero(self) -> None:
        spec = GLOBAL_SCHEMA.get("editor.highlight_delay_ms")
        assert spec is not None
        assert spec.min == 0

    def test_max_is_5000(self) -> None:
        spec = GLOBAL_SCHEMA.get("editor.highlight_delay_ms")
        assert spec is not None
        assert spec.max == 5000

    def test_negative_value_rejected(self) -> None:
        spec = GLOBAL_SCHEMA.get("editor.highlight_delay_ms")
        assert spec is not None
        with pytest.raises(ValueError):
            spec.validate(-1)

    def test_value_above_max_rejected(self) -> None:
        spec = GLOBAL_SCHEMA.get("editor.highlight_delay_ms")
        assert spec is not None
        with pytest.raises(ValueError):
            spec.validate(5001)

    def test_scope_is_global(self) -> None:
        spec = GLOBAL_SCHEMA.get("editor.highlight_delay_ms")
        assert spec is not None
        assert spec.scope is SettingsScope.GLOBAL

    def test_round_trip_via_global_settings(self, tmp_path) -> None:
        """通过 GlobalSettings 真实读写:延迟值应当能正确持久化。"""
        from modules.settings import GlobalSettings

        gs = GlobalSettings(path=str(tmp_path / "g.json"))
        gs.set("editor.highlight_delay_ms", 150)
        assert gs.get("editor.highlight_delay_ms") == 150
        gs.save()

        gs2 = GlobalSettings(path=str(tmp_path / "g.json"))
        assert gs2.get("editor.highlight_delay_ms") == 150

    def test_global_settings_default_when_unset(self, tmp_path) -> None:
        """未显式 set 时,读取应得到 schema 的默认值。"""
        from modules.settings import GlobalSettings

        gs = GlobalSettings(path=str(tmp_path / "g.json"))
        assert gs.get("editor.highlight_delay_ms") == 300
        assert gs.has("editor.highlight_delay_ms") is False
