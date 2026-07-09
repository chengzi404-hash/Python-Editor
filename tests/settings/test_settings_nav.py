# -*- coding: utf-8 -*-
"""``modules.Uui.widgets.settings_nav`` 的纯数据层测试。

这些测试只覆盖无 Tk 依赖的部分 (:func:`group_key` / :func:`node_id`
/ :func:`parse_node_id` / :func:`group_keys_for_schema`), 因此可以
在没有显示环境(headless CI、跨平台等)的条件下运行。组件本身的
Treeview 渲染 / 主题刷新等行为由手测与现有 ``tests/settings/`` 的
集成测试间接覆盖(它们走的是 ``USettingPanel``, 而 panel 由
``UProjectSettingsWindow`` 装载, 后者现在持有 ``USettingsNavBar``)。
"""

from __future__ import annotations

import pytest

from modules.settings.schema import (
    GLOBAL_SCHEMA,
    PROJECT_SCHEMA,
)
from modules.Uui.widgets.settings_nav import (
    group_key,
    group_keys_for_schema,
    node_id,
    parse_node_id,
)


# ----------------------------------------------------------------------
# group_key
# ----------------------------------------------------------------------


class TestGroupKey:
    """``group_key`` 提取 key 的首段作为分组名。"""

    def test_with_dot_returns_prefix(self):
        assert group_key("editor.tab_size") == "editor"

    def test_with_multiple_dots_uses_first_segment(self):
        # 防御: 未来 key 出现更深层级时仍取首段 (如 a.b.c -> a)。
        assert group_key("ui.theme.dark_variant") == "ui"

    def test_without_dot_returns_underscore(self):
        # 与 modules.settings.widgets._group_key 的行为保持一致:
        # 无前缀的 key 归到 "_" 桶, 避免根级 spec 散落在树顶层。
        assert group_key("foo") == "_"

    def test_empty_string_returns_underscore(self):
        # 极端边界: 空 key 也不会抛异常。
        assert group_key("") == "_"


# ----------------------------------------------------------------------
# node_id / parse_node_id (round-trip)
# ----------------------------------------------------------------------


class TestNodeIdRoundtrip:
    """``parse_node_id(node_id(...))`` 必须能拿回原始三元组。"""

    @pytest.mark.parametrize(
        "scope_value, group, key",
        [
            ("global", None, None),
            ("project", None, None),
            ("global", "ui", None),
            ("global", "editor", None),
            ("global", "ui", "ui.theme"),
            ("project", "project", "project.python_interpreter"),
            ("project", "checker", "checker.enabled"),
        ],
    )
    def test_roundtrip(self, scope_value, group, key):
        iid = node_id(scope_value, group, key)
        assert parse_node_id(iid) == (scope_value, group, key)

    def test_scope_root_iid(self):
        assert node_id("global") == "global"
        assert node_id("project") == "project"

    def test_group_iid_uses_single_colon(self):
        # 设计契约: 必须是 "<scope>:<group>" 这种单冒号,
        # 否则 parse_node_id 的 partition 会切错。
        assert node_id("global", "ui") == "global:ui"

    def test_leaf_iid_uses_two_colons(self):
        assert node_id("global", "ui", "ui.theme") == "global:ui:ui.theme"

    def test_parse_node_id_scope_root(self):
        # 没有冒号: scope 根, group/key 都是 None。
        assert parse_node_id("global") == ("global", None, None)

    def test_parse_node_id_group(self):
        # 单冒号: 叶子 group; key 是 None。
        assert parse_node_id("global:ui") == ("global", "ui", None)

    def test_parse_node_id_leaf(self):
        # 双冒号: 完整三元组。
        assert parse_node_id(
            "global:ui:ui.theme",
        ) == ("global", "ui", "ui.theme")


# ----------------------------------------------------------------------
# group_keys_for_schema
# ----------------------------------------------------------------------


class TestGroupKeysForSchema:
    """``group_keys_for_schema`` 保留 schema 声明顺序, 不依赖 dict 重新 hash。"""

    def test_returns_ordered_dict(self):
        from collections import OrderedDict
        result = group_keys_for_schema(GLOBAL_SCHEMA)
        assert isinstance(result, OrderedDict)

    def test_global_schema_groups(self):
        # 契约: 这是用户能看到的导航树顶层分组。
        # 一旦 schema 重构, 这个集合也得跟着改; 把它显式钉在测试里
        # 可以避免无声地破坏"ui 改名为 view"这类重构。
        result = group_keys_for_schema(GLOBAL_SCHEMA)
        assert set(result.keys()) == {
            "ui", "editor", "completion", "checker", "runner", "startup",
        }

    def test_project_schema_groups(self):
        result = group_keys_for_schema(PROJECT_SCHEMA)
        assert set(result.keys()) == {"project", "checker"}

    def test_global_ui_group_keys_in_order(self):
        # UI 分组是用户在导航树里点开 "ui" 后看到的第一组叶子,
        # 顺序与 schema 中声明一致(主题 → 字体 → 字号 → 行号)。
        result = group_keys_for_schema(GLOBAL_SCHEMA)
        keys_in_group = [k for k, _ in result["ui"]]
        assert keys_in_group == [
            "ui.theme",
            "ui.font_family",
            "ui.font_size",
            "ui.show_line_numbers",
        ]

    def test_global_ui_group_labels_use_spec_label(self):
        # label 来自 spec.label, 在叶子节点渲染时会被显示出来。
        result = group_keys_for_schema(GLOBAL_SCHEMA)
        labels = [label for _, label in result["ui"]]
        assert labels == ["界面主题", "编辑器字体", "编辑器字号", "显示行号"]

    def test_global_editor_group_keys_in_order(self):
        result = group_keys_for_schema(GLOBAL_SCHEMA)
        keys_in_group = [k for k, _ in result["editor"]]
        assert keys_in_group == [
            "editor.tab_size",
            "editor.use_spaces",
            "editor.auto_save",
            "editor.auto_save_delay_ms",
            "editor.word_wrap",
            "editor.highlight_delay_ms",
            "editor.suggestion_delay_ms",
            "editor.large_file_threshold_bytes",
        ]


    def test_project_group_keys_in_order(self):
        result = group_keys_for_schema(PROJECT_SCHEMA)
        keys_in_group = [k for k, _ in result["project"]]
        # 全部 project.* 都在这里
        assert all(k.startswith("project.") for k in keys_in_group)
        assert "project.python_interpreter" in keys_in_group
        assert "project.entry_point" in keys_in_group
        assert "project.c_compiler" in keys_in_group
        assert "project.cpp_compiler" in keys_in_group
        assert "project.tab_size" in keys_in_group
        assert "project.name" in keys_in_group

    def test_checker_group_appears_in_both_scopes(self):
        # checker.* 在 GLOBAL 和 PROJECT 里都有; 两个 schema 应该
        # 都包含一个 "checker" 桶, 互不干扰。
        g_groups = set(group_keys_for_schema(GLOBAL_SCHEMA).keys())
        p_groups = set(group_keys_for_schema(PROJECT_SCHEMA).keys())
        assert "checker" in g_groups
        assert "checker" in p_groups

    def test_label_falls_back_to_key_when_empty(self):
        # spec.label 为空时, 应回退到 key (而不是空字符串),
        # 这样导航树不会出现空文本节点。
        from modules.settings.base import (
            SettingSpec,
            SettingValueType,
            SettingsScope,
            SettingsSchema,
        )
        schema = SettingsSchema((
            SettingSpec(
                key="misc.empty_label",
                type=SettingValueType.STRING,
                default="",
                label="",
                scope=SettingsScope.GLOBAL,
            ),
        ))
        result = group_keys_for_schema(schema)
        assert ("misc.empty_label", "misc.empty_label") in result["misc"]


# ----------------------------------------------------------------------
# 集成: schema -> iid 字典 (模拟 set_roots 内部的填充行为)
# ----------------------------------------------------------------------


class TestSchemaToIidMapping:
    """验证从真实 schema 出发能生成与 ``node_id`` 契约一致的 iid 集合。"""

    def test_global_schema_yields_expected_iids(self):
        # 这套数据是 ``USettingsNavBar.set_roots`` 应当构建出的最小
        # iid 集合; 测试不实例化 Treeview, 只验证我们手工按 node_id
        # 规则生成的结果是否符合预期, 从而把"算法正确"和"UI 渲染"
        # 两个关注点解耦。
        expected = {"global"}
        for g, items in group_keys_for_schema(GLOBAL_SCHEMA).items():
            expected.add(node_id("global", g))
            for k, _ in items:
                expected.add(node_id("global", g, k))
        assert "global" in expected
        assert "global:ui" in expected
        assert "global:ui:ui.theme" in expected
        assert "global:editor:editor.tab_size" in expected
        assert "global:completion:completion.enabled" in expected
        # 全局 schema 不应出现 project 前缀
        assert not any(":project." in iid for iid in expected)

    def test_project_schema_yields_expected_iids(self):
        expected = {"project"}
        for g, items in group_keys_for_schema(PROJECT_SCHEMA).items():
            expected.add(node_id("project", g))
            for k, _ in items:
                expected.add(node_id("project", g, k))
        assert "project" in expected
        assert "project:project" in expected
        assert "project:project:project.python_interpreter" in expected
        assert "project:checker" in expected
        assert "project:checker:checker.enabled" in expected

    def test_no_duplicate_iids_across_scopes(self):
        # GLOBAL 和 PROJECT 的 iid 集合应当互不相交(因为 scope 段不同)。
        g_iids = {"global"}
        for g, items in group_keys_for_schema(GLOBAL_SCHEMA).items():
            g_iids.add(node_id("global", g))
            for k, _ in items:
                g_iids.add(node_id("global", g, k))
        p_iids = {"project"}
        for g, items in group_keys_for_schema(PROJECT_SCHEMA).items():
            p_iids.add(node_id("project", g))
            for k, _ in items:
                p_iids.add(node_id("project", g, k))
        assert g_iids.isdisjoint(p_iids)
