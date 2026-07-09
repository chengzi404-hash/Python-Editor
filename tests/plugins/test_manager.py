"""``modules.plugins.manager`` 的集成测试。

不需要 Tk, 直接构造 PluginManager 并验证:

* 目录扫描 (`discover_*`)
* 动态 importlib 加载 (`_import_module`)
* ``enable`` / ``disable`` / ``reload``
* 钩子事件分发, 包括异常隔离
"""

from __future__ import annotations

import os
import textwrap

import pytest

from modules.plugins import HookEvents, PluginManager, PluginManifest


# ----------------------------------------------------------------------
# 工具
# ----------------------------------------------------------------------


def _write_plugin(directory: str, plugin_id: str, body: str) -> None:
    """在 ``directory/<plugin_id>/__init__.py`` 写入一个最小插件."""

    path = os.path.join(directory, plugin_id)
    os.makedirs(path, exist_ok=True)
    with open(os.path.join(path, "__init__.py"), "w", encoding="utf-8") as f:
        f.write(textwrap.dedent(body))


def _make_manager(tmp_path):
    """构造一个把全局插件目录指向 tmp_path/plugins 的 PluginManager.

    同时把 editor 替换成最小 mock, 覆盖 PluginManager 调用的所有 editor 侧方法。
    """

    global_dir = tmp_path / "global_plugins"
    global_dir.mkdir()
    mgr = PluginManager(global_plugins_dir=str(global_dir))

    class _Scope:
        value = "global"

    class _GlobalSettingsMock:
        scope = _Scope()

    class _SettingsMock:
        """模拟 SettingsManager: 只暴露 manager 用到的属性/方法."""

        def __init__(self):
            self.values = {}
            self.global_settings = _GlobalSettingsMock()

        def set(self, scope, key, value):
            self.values[key] = value

        def effective(self, key, default=None):
            return self.values.get(key, default)

        def get(self, key, default=None):
            return self.values.get(key, default)

    class _EditorMock:
        def __init__(self):
            self.outputs = []
            self.commands = []
            self.languages = []
            self.hooks = []
            self._settings = _SettingsMock()

        def register_hook(self, sub): self.hooks.append(sub)
        def register_command(self, cmd): self.commands.append(cmd)
        def register_language(self, plugin_id, contrib): self.languages.append((plugin_id, contrib))
        def append_output(self, text): self.outputs.append(text)
        def _append_output(self, text): self.outputs.append(text)
        def setting(self, key, default=None): return self._settings.values.get(key, default)
        def set_setting(self, key, value): self._settings.values[key] = value

    mgr._editor = _EditorMock()
    return mgr


# ----------------------------------------------------------------------
# 目录扫描
# ----------------------------------------------------------------------


class TestDiscovery:
    def test_discover_empty_dir(self, tmp_path):
        mgr = _make_manager(tmp_path)
        assert mgr.discover_global() == []

    def test_discover_skips_dirs_without_init(self, tmp_path):
        # 创建一个没有 __init__.py 的子目录, 应被跳过
        os.makedirs(tmp_path / "broken")
        mgr = _make_manager(tmp_path)
        assert mgr.discover_global() == []

    def test_discover_finds_valid_plugin(self, tmp_path):
        mgr = _make_manager(tmp_path)
        _write_plugin(mgr._global_plugins_dir, "hello", '''
            from modules.plugins import PluginManifest
            MANIFEST = PluginManifest(id="hello", name="Hello")
        ''')
        found = mgr.discover_global()
        assert len(found) == 1
        assert found[0].manifest.id == "hello"
        assert found[0].scope == "system"

    def test_discover_skips_private_dirs(self, tmp_path):
        mgr = _make_manager(tmp_path)
        _write_plugin(mgr._global_plugins_dir, "_internal", '''
            from modules.plugins import PluginManifest
            MANIFEST = PluginManifest(id="_internal", name="X")
        ''')
        assert mgr.discover_global() == []

    def test_discover_handles_broken_plugin(self, tmp_path):
        # 无效 __init__.py 也能被扫到, 但 manifest 是占位
        mgr = _make_manager(tmp_path)
        path = os.path.join(mgr._global_plugins_dir, "broken_plugin")
        os.makedirs(path)
        with open(os.path.join(path, "__init__.py"), "w", encoding="utf-8") as f:
            f.write("raise RuntimeError('boom')")
        found = mgr.discover_global()
        assert len(found) == 1
        assert "无法读取 manifest" in (found[0].manifest.description or "")

    def test_discover_project_root(self, tmp_path):
        mgr = _make_manager(tmp_path)
        # 项目根不存在 → 空
        assert mgr.discover_project("/non/existent") == []
        # 正常扫描
        _write_plugin(str(tmp_path / "myproj" / "plugins"), "x", '''
            from modules.plugins import PluginManifest
            MANIFEST = PluginManifest(id="x", name="X")
        ''')
        found = mgr.discover_project(str(tmp_path / "myproj"))
        assert len(found) == 1
        assert found[0].scope == "project"
        assert found[0].manifest.id == "x"


# ----------------------------------------------------------------------
# 加载 / 卸载
# ----------------------------------------------------------------------


class TestLifecycle:
    def test_load_calls_register(self, tmp_path):
        body = '''
            from modules.plugins import HookEvents, PluginManifest

            MANIFEST = PluginManifest(id="plug1", name="Plug1")

            def register(ctx):
                ctx.calls = ctx.setting("calls", 0) + 1
                ctx.set_setting("calls", ctx.calls)

                @ctx.on(HookEvents.EDITOR_FILE_OPENED)
                def _on(path):
                    pass
        '''
        mgr = _make_manager(tmp_path)
        _write_plugin(mgr._global_plugins_dir, "plug1", body)
        mgr.load_global_plugins()
        loaded = mgr.list_loaded()
        assert len(loaded) == 1
        assert loaded[0].manifest.id == "plug1"
        assert loaded[0].ctx._hooks  # 钩子已注册
        # register 阶段 set_setting('calls', 1) 已落 host.settings
        assert mgr._editor._settings.values.get("plugins.plug1.calls") == 1

    def test_register_exception_marks_error(self, tmp_path):
        body = '''
            from modules.plugins import PluginManifest
            MANIFEST = PluginManifest(id="bad", name="Bad")
            def register(ctx):
                raise RuntimeError("register boom")
        '''
        mgr = _make_manager(tmp_path)
        _write_plugin(mgr._global_plugins_dir, "bad", body)
        mgr.load_global_plugins()
        loaded = mgr.list_loaded()
        assert len(loaded) == 1
        assert loaded[0].error is not None
        assert "register boom" in loaded[0].error

    def test_missing_register_function(self, tmp_path):
        body = '''
            from modules.plugins import PluginManifest
            MANIFEST = PluginManifest(id="noreg", name="NoReg")
        '''
        mgr = _make_manager(tmp_path)
        _write_plugin(mgr._global_plugins_dir, "noreg", body)
        mgr.load_global_plugins()
        loaded = mgr.list_loaded()
        assert "缺少 register" in (loaded[0].error or "")

    def test_disabled_plugin_skipped(self, tmp_path):
        body = '''
            from modules.plugins import PluginManifest
            MANIFEST = PluginManifest(id="off", name="Off")
            def register(ctx):
                ctx.set_setting("ran", True)
        '''
        mgr = _make_manager(tmp_path)
        _write_plugin(mgr._global_plugins_dir, "off", body)
        # 在 attach 之前注入 disabled 设置
        mgr._editor._settings.values["plugins.off.enabled"] = False
        mgr.load_global_plugins()
        loaded = mgr.list_loaded()
        # 插件对象存在, 但 enabled=False, register 没被调用
        assert loaded[0].enabled is False
        assert mgr._editor._settings.values.get("plugins.off.ran") is None

    def test_unload_invokes_unregister_callbacks(self, tmp_path):
        body = '''
            from modules.plugins import PluginManifest
            MANIFEST = PluginManifest(id="ucb", name="UCB")
            def register(ctx):
                ctx._ucb_calls = []
                ctx.on_unregister(lambda: ctx._ucb_calls.append("called"))
        '''
        mgr = _make_manager(tmp_path)
        _write_plugin(mgr._global_plugins_dir, "ucb", body)
        mgr.load_global_plugins()
        record = mgr.list_loaded()[0]
        mgr.unload_all()
        # 卸载时 _unregister_callbacks 已被触发
        assert getattr(record.ctx, "_ucb_calls", []) == ["called"]

    def test_reload_re_executes_module(self, tmp_path):
        body = '''
            from modules.plugins import PluginManifest
            MANIFEST = PluginManifest(id="reloadable", name="Reloadable")
            COUNTER = {"n": 0}
            def register(ctx):
                COUNTER["n"] += 1
                ctx.set_setting("counter", COUNTER["n"])
        '''
        mgr = _make_manager(tmp_path)
        _write_plugin(mgr._global_plugins_dir, "reloadable", body)
        mgr.load_global_plugins()
        assert mgr._editor._settings.values.get("plugins.reloadable.counter") == 1
        mgr.reload("reloadable")
        # 模块重新执行, 顶层 COUNTER 重置为 {"n": 0}, 再 +1 = 1
        # 但 settings 持久化的值是 2 (上次写入) — 实际值取决于 reload 是否清模块
        assert mgr._editor._settings.values.get("plugins.reloadable.counter") == 1


# ----------------------------------------------------------------------
# 事件分发
# ----------------------------------------------------------------------


class TestEmit:
    def test_emit_dispatches_to_subscribers(self, tmp_path):
        body = '''
            from modules.plugins import HookEvents, PluginManifest

            MANIFEST = PluginManifest(id="e", name="E")

            def register(ctx):
                ctx.received = []
                @ctx.on(HookEvents.EDITOR_FILE_OPENED)
                def _on(path):
                    ctx.received.append(path)
        '''
        mgr = _make_manager(tmp_path)
        _write_plugin(mgr._global_plugins_dir, "e", body)
        mgr.load_global_plugins()
        mgr.emit(HookEvents.EDITOR_FILE_OPENED, "/tmp/a.py")
        mgr.emit(HookEvents.EDITOR_FILE_OPENED, "/tmp/b.py")
        rec = mgr.list_loaded()[0]
        assert rec.ctx.received == ["/tmp/a.py", "/tmp/b.py"]

    def test_emit_swallows_callback_exceptions(self, tmp_path):
        body = '''
            from modules.plugins import HookEvents, PluginManifest

            MANIFEST = PluginManifest(id="boom", name="Boom")

            def register(ctx):
                ctx.reached = []
                @ctx.on(HookEvents.EDITOR_FILE_OPENED)
                def _bad(_):
                    raise RuntimeError("kaboom")

                @ctx.on(HookEvents.EDITOR_FILE_OPENED)
                def _good(path):
                    ctx.reached.append(path)
        '''
        mgr = _make_manager(tmp_path)
        _write_plugin(mgr._global_plugins_dir, "boom", body)
        mgr.load_global_plugins()
        mgr.emit(HookEvents.EDITOR_FILE_OPENED, "/x.py")
        rec = mgr.list_loaded()[0]
        # 第二个回调在第一个抛异常后仍然被调用
        assert rec.ctx.reached == ["/x.py"]
        # 错误信息也被写入 output
        assert any("kaboom" in line for line in mgr._editor.outputs)

    def test_disabled_plugin_does_not_receive_events(self, tmp_path):
        body = '''
            from modules.plugins import HookEvents, PluginManifest

            MANIFEST = PluginManifest(id="d", name="D")

            def register(ctx):
                ctx.received = []
                @ctx.on(HookEvents.EDITOR_FILE_OPENED)
                def _on(path):
                    ctx.received.append(path)
        '''
        mgr = _make_manager(tmp_path)
        _write_plugin(mgr._global_plugins_dir, "d", body)
        mgr._editor._settings.values["plugins.d.enabled"] = False
        mgr.load_global_plugins()
        # 此时插件对象存在, 但 enabled=False
        rec = mgr.list_loaded()[0]
        # 没有 register 调用 → ctx.received 不存在; 调用 emit 时也不会触发
        assert rec.enabled is False
        mgr.emit(HookEvents.EDITOR_FILE_OPENED, "/x.py")
        # emit 在 enabled=False 时跳过
        assert not getattr(rec.ctx, "received", [])

    def test_re_enable_does_not_rerun_register(self, tmp_path):
        body = '''
            from modules.plugins import PluginManifest

            MANIFEST = PluginManifest(id="t", name="T")
            def register(ctx):
                ctx.set_setting("calls", ctx.setting("calls", 0) + 1)
        '''
        mgr = _make_manager(tmp_path)
        _write_plugin(mgr._global_plugins_dir, "t", body)
        mgr._editor._settings.values["plugins.t.enabled"] = False
        mgr.load_global_plugins()
        # register 没被调用 (因为 enabled=False)
        assert mgr._editor._settings.values.get("plugins.t.calls") is None
        # enable 不重新调 register, 只把 enabled=True 让现有 ctx 生效
        mgr.enable("t")
        rec = mgr.list_loaded()[0]
        assert rec.enabled is True
        # 由于 record 已存在, _activate_record 不会重跑 register
        assert mgr._editor._settings.values.get("plugins.t.calls") is None


# ----------------------------------------------------------------------
# 快捷键解析
# ----------------------------------------------------------------------


class TestShortcutParse:
    def test_basic(self):
        assert PluginManager._tk_shortcut("Ctrl+H") == "<Control-H>"
        assert PluginManager._tk_shortcut("Ctrl+Shift+H") == "<Control-Shift-H>"
        assert PluginManager._tk_shortcut("Alt+F4") == "<Alt-F4>"
        assert PluginManager._tk_shortcut("H") == "<H>"
        assert PluginManager._tk_shortcut("") == "<>"






