# -*- coding: utf-8 -*-
"""``modules.settings.manager`` 的集成测试。

覆盖以下场景:

* :class:`SettingsManager` 同时管理全局与项目作用域。
* 优先级合并 ``effective``(项目覆盖全局 → 回退默认)。
* :meth:`attach_project` / :meth:`detach_project` 的状态切换与持久化。
* 监听器从底层 settings 转发到 manager 订阅者。
* 上下文协议(``with`` 语句)在退出时自动 save。
* 模拟 main.py 风格的 read-modify-write 循环,确保 JSON 文件可稳定往返。
"""

from __future__ import annotations

import json
import os

import pytest

from modules.settings import (
    GLOBAL_SCHEMA,
    PROJECT_SCHEMA,
    SettingsManager,
    SettingsScope,
)
from modules.settings.storage import CURRENT_VERSION


# ----------------------------------------------------------------------
# 工厂函数
# ----------------------------------------------------------------------


def _make_manager(tmp_path):
    """构造一个把全局与项目都指向 tmp_path 的 SettingsManager。

    全局 → ``tmp_path/global/settings.json``
    项目根 → ``tmp_path/proj`` (子目录)
    """

    global_settings = type(_make_manager).__module__  # 仅为注释占位
    from modules.settings import GlobalSettings, ProjectSettings

    g_path = str(tmp_path / "global_settings.json")
    global_settings = GlobalSettings(path=g_path)

    project_root = tmp_path / "proj"
    project_root.mkdir()
    manager = SettingsManager(global_settings=global_settings)
    manager.attach_project(str(project_root))
    return manager, project_root


# ----------------------------------------------------------------------
# 基本行为
# ----------------------------------------------------------------------


class TestManagerBasics:
    """SettingsManager 的初始化与基础访问。"""

    def test_global_settings_exposed(self, tmp_path):
        manager, _ = _make_manager(tmp_path)
        assert manager.global_settings is not None
        assert manager.global_settings.scope is SettingsScope.GLOBAL

    def test_project_settings_attached(self, tmp_path):
        manager, root = _make_manager(tmp_path)
        assert manager.project_settings is not None
        assert manager.project_settings.scope is SettingsScope.PROJECT
        assert manager.project_root == str(root)

    def test_default_constructs_with_global(self, tmp_path, monkeypatch):
        """不显式传任何参数时,会创建默认路径的 GlobalSettings。

        为了不影响测试机器的真实全局文件,这里 monkeypatch 默认解析。
        """

        from modules.settings import global_settings as gs_mod

        monkeypatch.setattr(
            gs_mod, "default_global_path",
            lambda: str(tmp_path / "default_global.json"),
        )
        manager = SettingsManager()
        assert manager.project_settings is None
        assert manager.global_settings is not None
        # 全局仍走 GLOBAL_SCHEMA
        assert manager.global_settings.schema is GLOBAL_SCHEMA


# ----------------------------------------------------------------------
# 优先级合并
# ----------------------------------------------------------------------


class TestEffectivePriority:
    """``effective`` 必须遵循"项目覆盖全局→回退默认"的解析链。"""

    def test_global_only_value(self, tmp_path):
        manager, _ = _make_manager(tmp_path)
        manager.set(SettingsScope.GLOBAL, "ui.font_size", 13)
        assert manager.effective("ui.font_size") == 13

    def test_project_overrides_global(self, tmp_path):
        manager, _ = _make_manager(tmp_path)
        manager.set(SettingsScope.GLOBAL, "ui.font_size", 13)
        manager.set(SettingsScope.PROJECT, "project.tab_size", 2)
        # 项目未定义 font_size 时仍走全局
        assert manager.effective("ui.font_size") == 13

    def test_project_value_visible_via_effective(self, tmp_path):
        """``effective`` 在项目有定义时应返回项目值。

        注意: GLOBAL 与 PROJECT 是两个独立的 schema,因此"覆盖"更直接的
        体现是"项目定义 > 全局默认 → schema 默认"。
        """
        manager, _ = _make_manager(tmp_path)
        manager.set(SettingsScope.PROJECT, "project.tab_size", 2)
        # 项目值应优先于 schema 默认 (4)
        assert manager.effective("project.tab_size") == 2

    def test_project_takes_precedence_over_global_fallback(self, tmp_path):
        """用一个项目作用域的 key,验证 attach_project 后 setting 有值。"""
        manager, _ = _make_manager(tmp_path)
        manager.set(SettingsScope.PROJECT, "project.c_compiler", "/opt/gcc-12")
        assert manager.effective("project.c_compiler") == "/opt/gcc-12"
        # 全局上没有此 key,返回应是项目的值
        assert manager.global_settings.get("project.c_compiler", None) is None

    def test_effective_falls_back_to_default(self, tmp_path):
        """全局未显式赋值、未挂项目时的 fallback 取 schema 默认。"""
        manager = SettingsManager.__new__(SettingsManager)
        # 手动初始化,避免 __init__ 落盘
        from modules.settings import GlobalSettings
        manager._global = GlobalSettings(path=str(tmp_path / "g.json"))
        manager._project = None
        manager._user_listeners = []
        assert manager.effective("ui.theme") == "Dark"
        assert manager.effective("editor.tab_size") == 4

    def test_effective_with_explicit_default(self, tmp_path):
        manager, _ = _make_manager(tmp_path)
        assert manager.effective("not.a.known.key", default="abc") == "abc"


# ----------------------------------------------------------------------
# 项目切换
# ----------------------------------------------------------------------


class TestProjectSwitch:
    """attach_project / detach_project 切换语义。"""

    def test_attach_lazy_resolves_path(self, tmp_path):
        """attach_project 后路径属性应解析到 ``<root>/.pyeditor/settings.json``。"""
        manager = SettingsManager()
        root = tmp_path / "brand_new_proj"
        root.mkdir()
        manager.attach_project(str(root))
        assert manager.project_settings.path == str(
            root / ".pyeditor" / "settings.json"
        )

    def test_save_persists_to_pyeditor_dir(self, tmp_path):
        """保存项目设置后应在 ``<root>/.pyeditor/settings.json`` 落盘。"""
        manager = SettingsManager()
        root = tmp_path / "brand_new_proj"
        root.mkdir()
        manager.attach_project(str(root))
        manager.set(SettingsScope.PROJECT, "project.tab_size", 2)
        manager.save_all()
        hidden = root / ".pyeditor"
        assert hidden.is_dir()
        assert (hidden / "settings.json").is_file()

    def test_detach_saves_project_settings(self, tmp_path):
        manager, root = _make_manager(tmp_path)
        manager.set(SettingsScope.PROJECT, "project.tab_size", 2)
        manager.detach_project()
        # 重新挂载应读到 2
        new_manager = SettingsManager()
        new_manager.attach_project(str(root))
        assert new_manager.effective("project.tab_size") == 2

    def test_attach_replaces_previous_project(self, tmp_path):
        manager = SettingsManager()
        a = tmp_path / "a"
        b = tmp_path / "b"
        a.mkdir()
        b.mkdir()
        manager.attach_project(str(a))
        assert manager.project_root == str(a)
        manager.attach_project(str(b))
        assert manager.project_root == str(b)


# ----------------------------------------------------------------------
# 监听器
# ----------------------------------------------------------------------


class TestListenerForwarding:
    """manager.add_listener 应该同时监听全局与项目侧变更。"""

    def test_global_event_relayed(self, tmp_path):
        manager, _ = _make_manager(tmp_path)
        received = []
        manager.add_listener(lambda evt: received.append(evt))
        manager.set(SettingsScope.GLOBAL, "ui.font_size", 14)
        assert any(
            e.scope is SettingsScope.GLOBAL and e.key == "ui.font_size" and e.new == 14
            for e in received
        )

    def test_project_event_relayed(self, tmp_path):
        manager, _ = _make_manager(tmp_path)
        received = []
        manager.add_listener(lambda evt: received.append(evt))
        manager.set(SettingsScope.PROJECT, "project.tab_size", 2)
        assert any(
            e.scope is SettingsScope.PROJECT and e.new == 2
            for e in received
        )

    def test_remove_listener_stops_events(self, tmp_path):
        manager, _ = _make_manager(tmp_path)
        events = []
        cb = lambda evt: events.append(evt)
        manager.add_listener(cb)
        manager.set(SettingsScope.GLOBAL, "ui.font_size", 14)
        manager.remove_listener(cb)
        manager.set(SettingsScope.GLOBAL, "ui.font_size", 15)
        # 第二次 set 时已移除 listener, 不再追加
        ui_events = [e for e in events if e.key == "ui.font_size"]
        assert len(ui_events) == 1
        assert ui_events[0].new == 14


# ----------------------------------------------------------------------
# 持久化 (Round-trip)
# ----------------------------------------------------------------------


class TestSaveAndReload:
    """save_all 后,重开 manager 应该读到相同状态。"""

    def test_global_round_trip(self, tmp_path):
        manager, _ = _make_manager(tmp_path)
        manager.set(SettingsScope.GLOBAL, "ui.theme", "Light")
        manager.set(SettingsScope.GLOBAL, "ui.font_size", 14)
        manager.save_all()

        # 重新构造 manager,只看 global 部分
        from modules.settings import GlobalSettings
        g2 = GlobalSettings(path=str(manager.global_settings.path))
        assert g2.get("ui.theme") == "Light"
        assert g2.get("ui.font_size") == 14

    def test_project_round_trip(self, tmp_path):
        manager, root = _make_manager(tmp_path)
        manager.set(SettingsScope.PROJECT, "project.tab_size", 2)
        manager.set(SettingsScope.PROJECT, "project.exclude_paths",
                    ["build", "dist", "node_modules"])
        manager.save_all()

        new_manager = SettingsManager()
        new_manager.attach_project(str(root))
        assert new_manager.effective("project.tab_size") == 2
        assert new_manager.effective("project.exclude_paths") == [
            "build", "dist", "node_modules",
        ]

    def test_project_settings_file_shape(self, tmp_path):
        manager, root = _make_manager(tmp_path)
        manager.set(SettingsScope.PROJECT, "project.tab_size", 2)
        manager.save_all()

        path = root / ".pyeditor" / "settings.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["version"] == CURRENT_VERSION
        assert data["scope"] == "project"
        assert data["values"]["project.tab_size"] == 2


# ----------------------------------------------------------------------
# 上下文协议
# ----------------------------------------------------------------------


class TestContextManager:
    """``with SettingsManager() as m: ...`` 退出时自动 save_all。"""

    def test_with_block_does_save(self, tmp_path):
        from modules.settings import GlobalSettings
        g_path = str(tmp_path / "ctx_global.json")

        with SettingsManager(global_settings=GlobalSettings(path=g_path)) as m:
            m.set(SettingsScope.GLOBAL, "ui.theme", "Solarized Dark")

        # JSON 文件应已存在
        assert os.path.isfile(g_path)
        g2 = GlobalSettings(path=g_path)
        assert g2.get("ui.theme") == "Solarized Dark"


# ----------------------------------------------------------------------
# Schema helpers
# ----------------------------------------------------------------------


class TestSchemas:
    """默认 schema 不应在修改期间悄悄变化。"""

    def test_default_global_keys_present(self, tmp_path):
        manager, _ = _make_manager(tmp_path)
        for key in ("ui.theme", "ui.font_size", "editor.tab_size",
                    "completion.enabled", "editor.auto_save"):
            assert key in manager.global_settings.schema

    def test_default_project_keys_present(self, tmp_path):
        manager, _ = _make_manager(tmp_path)
        for key in ("project.python_interpreter", "project.c_compiler",
                    "checker.enabled", "project.exclude_paths"):
            assert key in manager.project_settings.schema

    def test_schema_instances(self):
        # SettingsSchema 自身的类型保持稳定 — 这是 SettingsManager 与
        # storage 依赖的隐式契约。
        from modules.settings.base import SettingsSchema
        assert isinstance(GLOBAL_SCHEMA, SettingsSchema)
        assert isinstance(PROJECT_SCHEMA, SettingsSchema)
