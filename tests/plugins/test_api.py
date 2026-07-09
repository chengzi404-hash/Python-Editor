"""``modules.plugins`` 公共契约测试。

不依赖 PluginManager, 只验证 PluginManifest / PluginContext / HookEvents
这些给插件作者看的稳定类型。
"""

from __future__ import annotations

import pytest

from modules.plugins import (
    HookEvents,
    LanguageContribution,
    PluginCommand,
    PluginContext,
    PluginLoadError,
    PluginManifest,
)


# ----------------------------------------------------------------------
# PluginManifest
# ----------------------------------------------------------------------


class TestPluginManifest:
    def test_minimal_valid(self):
        m = PluginManifest(id="hello", name="Hello")
        assert m.id == "hello"
        assert m.version == "0.0.0"
        assert m.scope == "global"
        m.validate()

    def test_id_required(self):
        with pytest.raises(ValueError):
            PluginManifest(id="", name="x").validate()

    def test_id_charset(self):
        with pytest.raises(ValueError):
            PluginManifest(id="hello world", name="x").validate()
        with pytest.raises(ValueError):
            PluginManifest(id="hello/world", name="x").validate()
        # 合法字符
        for ok in ("abc", "a-b-c", "abc_123", "Hello-World"):
            PluginManifest(id=ok, name="x").validate()

    def test_name_required(self):
        with pytest.raises(ValueError):
            PluginManifest(id="ok", name="").validate()

    def test_scope_enum(self):
        with pytest.raises(ValueError):
            PluginManifest(id="ok", name="x", scope="weird").validate()
        # 合法值
        PluginManifest(id="ok", name="x", scope="global").validate()
        PluginManifest(id="ok", name="x", scope="system").validate()


# ----------------------------------------------------------------------
# HookEvents 常量
# ----------------------------------------------------------------------


class TestHookEvents:
    def test_event_names_stable(self):
        # 这些字符串是插件作者硬编码依赖的, 不能轻易改。
        assert HookEvents.EDITOR_FILE_OPENED == "editor:file_opened"
        assert HookEvents.EDITOR_FILE_SAVED == "editor:file_saved"
        assert HookEvents.EDITOR_FILE_CREATED == "editor:file_created"
        assert HookEvents.EDITOR_CONTENT_CHANGED == "editor:content_changed"
        assert HookEvents.EDITOR_LANGUAGE_CHANGED == "editor:language_changed"
        assert HookEvents.EDITOR_CURSOR_MOVED == "editor:cursor_moved"
        assert HookEvents.EDITOR_RUN_STARTED == "editor:run_started"
        assert HookEvents.EDITOR_RUN_FINISHED == "editor:run_finished"
        assert HookEvents.EDITOR_CHECK_FINISHED == "editor:check_finished"
        assert HookEvents.EDITOR_CLOSING == "editor:closing"


# ----------------------------------------------------------------------
# PluginContext (需要一个 mock host)
# ----------------------------------------------------------------------


class _FakeHost:
    """模拟 :class:`PluginHostAPI`, 记录所有回调."""

    def __init__(self):
        self.hooks = []
        self.commands = []
        self.languages = []
        self.outputs = []
        self.settings = {}
        self.set_calls = []

    def register_hook(self, sub): self.hooks.append(sub)
    def register_command(self, cmd): self.commands.append(cmd)
    def register_language(self, plugin_id, contrib): self.languages.append((plugin_id, contrib))
    def append_output(self, text): self.outputs.append(text)
    def setting(self, key, default=None): return self.settings.get(key, default)
    def set_setting(self, key, value): self.set_calls.append((key, value)); self.settings[key] = value


class TestPluginContextAPI:
    def setup_method(self):
        self.host = _FakeHost()
        self.ctx = PluginContext(
            plugin_id="hello", plugin_name="Hello", host=self.host,
        )

    def test_ids_exposed(self):
        assert self.ctx.plugin_id == "hello"
        assert self.ctx.plugin_name == "Hello"

    def test_on_registers_hook(self):
        sub = self.ctx.on("editor:file_opened", lambda path: None)
        assert len(self.host.hooks) == 1
        assert self.host.hooks[0] is sub
        assert sub.plugin_id == "hello"
        assert sub.hook == "editor:file_opened"

    def test_on_validates_args(self):
        with pytest.raises(ValueError):
            self.ctx.on("", lambda: None)
        with pytest.raises(TypeError):
            self.ctx.on("editor:file_opened", "not callable")

    def test_add_command_default_menu(self):
        cmd = self.ctx.add_command(label="Hi", callback=lambda: None)
        assert isinstance(cmd, PluginCommand)
        assert cmd.menu == "插件"
        assert cmd.shortcut is None
        assert cmd in self.host.commands

    def test_add_command_with_shortcut(self):
        cmd = self.ctx.add_command(
            label="Hi", menu="工具", shortcut="Ctrl+H", callback=lambda: None,
        )
        assert cmd.menu == "工具"
        assert cmd.shortcut == "Ctrl+H"

    def test_register_language(self):
        contrib = LanguageContribution(
            name="MyLang", ext=".ml",
            highlighter_factory=lambda: object(),
            suggestion_factory=lambda: object(),
        )
        self.ctx.register_language(contrib)
        assert ("hello", contrib) in self.host.languages

    def test_append_output_ignored_empty(self):
        self.ctx.append_output("")
        assert self.host.outputs == []

    def test_log_format(self):
        self.ctx.log("info", "loaded")
        self.ctx.log("warning", "watch out")
        self.ctx.log("error", "boom")
        self.ctx.log("custom", "msg")
        assert self.host.outputs == [
            "[INFO] [hello] loaded\n",
            "[WARN] [hello] watch out\n",
            "[ERROR] [hello] boom\n",
            "[LOG] [hello] msg\n",
        ]

    def test_setting_namespace(self):
        self.host.settings["plugins.hello.greeting"] = "hi"
        assert self.ctx.setting("greeting") == "hi"
        assert self.ctx.setting("missing", "fallback") == "fallback"

    def test_set_setting_namespace(self):
        self.ctx.set_setting("greeting", "hello")
        assert self.host.set_calls == [("plugins.hello.greeting", "hello")]
        assert self.host.settings["plugins.hello.greeting"] == "hello"

    def test_setting_key_required(self):
        with pytest.raises(ValueError):
            self.ctx.setting("")
        with pytest.raises(ValueError):
            self.ctx.set_setting("", "x")

    def test_is_enabled_default_true(self):
        assert self.ctx.is_enabled() is True
        self.host.settings["plugins.hello.enabled"] = False
        assert self.ctx.is_enabled() is False

    def test_on_unregister_stored(self):
        cb = lambda: None
        self.ctx.on_unregister(cb)
        assert self.ctx._unregister_callbacks == [cb]

    def test_on_unregister_validates_callable(self):
        with pytest.raises(TypeError):
            self.ctx.on_unregister("not callable")


__all__ = []