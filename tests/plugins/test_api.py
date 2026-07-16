import pytest

from modules.plugins.api import (
    HookEvents,
    LanguageContribution,
    PluginCommand,
    PluginContext,
    PluginLoadError,
    PluginManifest,
    _HookSubscription,
)


class MockHost:
    def __init__(self):
        self.hooks = []
        self.commands = []
        self.languages = []
        self.outputs = []
        self.settings = {}

    def register_hook(self, sub):
        self.hooks.append(sub)

    def register_command(self, cmd):
        self.commands.append(cmd)

    def register_language(self, plugin_id, contrib):
        self.languages.append((plugin_id, contrib))

    def append_output(self, text):
        self.outputs.append(text)

    def setting(self, key, default=None):
        return self.settings.get(key, default)

    def set_setting(self, key, value):
        self.settings[key] = value


class TestPluginManifest:
    def test_valid_manifest(self):
        manifest = PluginManifest(id="test-plugin", name="Test Plugin")
        assert manifest.id == "test-plugin"
        assert manifest.name == "Test Plugin"
        assert manifest.version == "0.0.0"
        assert manifest.scope == "global"

    def test_manifest_validate_valid(self):
        manifest = PluginManifest(id="test-plugin", name="Test Plugin", scope="global")
        manifest.validate()

    def test_manifest_validate_invalid_id_empty(self):
        manifest = PluginManifest(id="", name="Test Plugin")
        with pytest.raises(ValueError):
            manifest.validate()

    def test_manifest_validate_invalid_id_chars(self):
        manifest = PluginManifest(id="test plugin!", name="Test Plugin")
        with pytest.raises(ValueError):
            manifest.validate()

    def test_manifest_validate_invalid_scope(self):
        manifest = PluginManifest(id="test-plugin", name="Test Plugin", scope="invalid")
        with pytest.raises(ValueError):
            manifest.validate()

    def test_manifest_validate_empty_name(self):
        manifest = PluginManifest(id="test-plugin", name="")
        with pytest.raises(ValueError):
            manifest.validate()


class TestPluginCommand:
    def test_creation(self):
        cmd = PluginCommand(plugin_id="test", label="Test", callback=lambda: None)
        assert cmd.plugin_id == "test"
        assert cmd.label == "Test"


class TestHookSubscription:
    def test_creation(self):
        sub = _HookSubscription(hook="test-hook", callback=lambda: None, plugin_id="test")
        assert sub.hook == "test-hook"
        assert sub.plugin_id == "test"


class TestPluginContext:
    def test_creation(self):
        host = MockHost()
        ctx = PluginContext(plugin_id="test", plugin_name="Test", host=host)
        assert ctx.plugin_id == "test"
        assert ctx.plugin_name == "Test"

    def test_on_decorator_style(self):
        host = MockHost()
        ctx = PluginContext(plugin_id="test", plugin_name="Test", host=host)

        @ctx.on("test-hook")
        def callback():
            pass

        assert len(host.hooks) == 1

    def test_on_direct_call(self):
        host = MockHost()
        ctx = PluginContext(plugin_id="test", plugin_name="Test", host=host)
        ctx.on("test-hook", callback=lambda: None)
        assert len(host.hooks) == 1

    def test_on_invalid_hook(self):
        host = MockHost()
        ctx = PluginContext(plugin_id="test", plugin_name="Test", host=host)
        with pytest.raises(ValueError):
            ctx.on("")

    def test_add_command(self):
        host = MockHost()
        ctx = PluginContext(plugin_id="test", plugin_name="Test", host=host)
        ctx.add_command(label="Test Command", callback=lambda: None)
        assert len(host.commands) == 1

    def test_append_output(self):
        host = MockHost()
        ctx = PluginContext(plugin_id="test", plugin_name="Test", host=host)
        ctx.append_output("test output")
        assert "test output" in host.outputs

    def test_setting(self):
        host = MockHost()
        host.settings["plugins.test.key"] = "value"
        ctx = PluginContext(plugin_id="test", plugin_name="Test", host=host)
        assert ctx.setting("key") == "value"

    def test_set_setting(self):
        host = MockHost()
        ctx = PluginContext(plugin_id="test", plugin_name="Test", host=host)
        ctx.set_setting("key", "value")
        assert host.settings["plugins.test.key"] == "value"

    def test_is_enabled(self):
        host = MockHost()
        ctx = PluginContext(plugin_id="test", plugin_name="Test", host=host)
        assert ctx.is_enabled()

    def test_log(self):
        host = MockHost()
        ctx = PluginContext(plugin_id="test", plugin_name="Test", host=host)
        ctx.log("info", "test message")
        assert len(host.outputs) == 1
