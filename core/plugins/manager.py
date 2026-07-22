"""``modules.plugins.manager`` — Plugin loading/unloading/event dispatch.

Main responsibilities
====================

* :class:`PluginManager` holds all loaded plugins + hook subscriptions + commands + language contributions.
* ``discover_*`` methods scan plugin directories on disk, generating candidate lists.
* ``load_all`` / ``unload_all`` / ``load_project`` control the activation lifecycle.
* :meth:`emit` dispatches hook events to all subscribers; single callback exceptions are swallowed and logged.

Scope
=====

* Plugins with ``scope == "system"`` are loaded from the global plugin directory, take effect on editor startup,
  and persist until shutdown; users **disabling** in the plugin manager window only stops event triggering,
  commands/languages can optionally be cleaned up.
* Plugins with ``scope == "global"`` are also loaded from the global plugin directory by default, but
  ``load_project(root)`` loads ``"global"`` plugins from project-level ``<root>/plugins/`` on demand,
  switched projects are cleared by ``unload_project``.

Enable / Disable
================

Each plugin has ``plugins.<id>.enabled`` key in settings.json, default True.
``emit`` only calls enabled subscribers; command registration is already filtered by enabled.
Disabling only unregisters commands/languages; plugin object is retained so re-enabling doesn't require re-import.
"""

from __future__ import annotations

import contextlib
import importlib
import importlib.util
import logging
import os
import sys
import threading
import traceback
from dataclasses import dataclass
from typing import (
    Any,
)

from core.settings.i18n import t

from .api import (
    LanguageContribution,
    PluginContext,
    PluginHostAPI,
    PluginLoadError,
    PluginManifest,
    _HookSubscription,
)

_log = logging.getLogger("modules.plugins")


@dataclass
class _PluginRecord:
    """Runtime state of a loaded plugin."""

    manifest: PluginManifest
    module: Any
    ctx: PluginContext
    location: str  # directory of origin, for UI display
    scope: str  # "system" / "project"
    enabled: bool = True
    error: str | None = None  # recorded on load/register failure, for UI display


@dataclass
class DiscoveredPlugin:
    """Description of a plugin discovered on disk but not yet loaded, for UI display and on-demand enable."""

    manifest: PluginManifest
    location: str
    scope: str  # "system" / "project"


class PluginManager(PluginHostAPI):
    """Plugin manager, used as singleton.

    Tk is not required at construction, but commands only actually render in the menu after :meth:`attach_editor`.
    Most methods are thread-safe (internally use ``self._lock`` to serialize critical operations);
    hook callbacks themselves are assumed to be called from the Tk main thread (same as other editor callbacks).
    """

    def __init__(
        self,
        *,
        global_plugins_dir: str | None = None,
    ) -> None:
        self._lock = threading.RLock()
        self._plugins: dict[str, _PluginRecord] = {}
        self._discovered: dict[str, DiscoveredPlugin] = {}
        self._hooks: list[_HookSubscription] = []
        self._commands: list[Any] = []  # PluginCommand list
        self._languages: list[tuple[str, LanguageContribution]] = []  # (plugin_id, contrib)
        self._shortcuts: dict[str, Any] = {}  # shortcut -> command record
        self._editor = None  # editor.CodeEditor, see attach_editor
        self._project_root: str | None = None
        self._global_plugins_dir = global_plugins_dir or self._default_global_dir()

    # ------------------------------------------------------------------
    # Default paths
    # ------------------------------------------------------------------

    @staticmethod
    def _default_global_dir() -> str:
        """Default global plugin directory: ``<config_root>/plugins/``.

        Reuses settings path strategy, ensures same root as settings.json for easy user location.
        """

        from core.settings.settings.global_settings import default_global_path

        settings_path = default_global_path()
        base = os.path.dirname(settings_path)
        return os.path.join(base, "plugins")

    # ------------------------------------------------------------------
    # Editor binding (delayed, because PluginManager is constructed before CodeEditor.__init__)
    # ------------------------------------------------------------------

    def attach_editor(self, editor: Any) -> None:
        """Attach :class:`CodeEditor` instance to manager, only then can commands be registered to menu.

        Reason for delay: :class:`CodeEditor` menu bar isn't built yet when :class:`PluginManager`
        is created; safer to call again after ``_build_menubar()``.
        """

        with self._lock:
            self._editor = editor

    def detach_editor(self) -> None:
        with self._lock:
            self._editor = None

    # ------------------------------------------------------------------
    # Directory scanning
    # ------------------------------------------------------------------

    def discover_global(self) -> list[DiscoveredPlugin]:
        """Scan global plugin directory, return discovery list (no import executed)."""

        return self._discover_dir(self._global_plugins_dir, scope="system")

    def discover_project(self, root: str) -> list[DiscoveredPlugin]:
        """Scan project-level ``<root>/plugins/`` directory."""

        if not root:
            return []
        return self._discover_dir(os.path.join(root, "plugins"), scope="project")

    def _discover_dir(self, directory: str, *, scope: str) -> list[DiscoveredPlugin]:
        """Generic directory scan: each immediate subdirectory is treated as a plugin (only if it has ``__init__.py``)."""

        if not directory or not os.path.isdir(directory):
            return []
        out: list[DiscoveredPlugin] = []
        try:
            entries = sorted(os.listdir(directory))
        except OSError:
            return []
        for name in entries:
            if name.startswith(("_", ".")):
                continue
            sub = os.path.join(directory, name)
            if not os.path.isdir(sub):
                continue
            init_py = os.path.join(sub, "__init__.py")
            if not os.path.isfile(init_py) and not os.path.isfile(os.path.join(sub, "plugin.py")):
                continue
            out.append(
                DiscoveredPlugin(
                    manifest=self._peek_manifest(sub),
                    location=sub,
                    scope=scope,
                )
            )
        return out

    @staticmethod
    def _peek_manifest(directory: str) -> PluginManifest:
        """Read-only manifest, no register executed. Returns a placeholder manifest on failure.

        Placeholder manifest uses directory name as id, ensures UI can still display a non-loadable plugin,
        letting user know "there's a plugin here but it's broken".
        """

        # _load_module uses independent spec, here also use temp spec to avoid polluting sys.modules
        spec = importlib.util.spec_from_file_location(
            "_plugin_peek",
            os.path.join(directory, "__init__.py"),
        )
        if spec is None or spec.loader is None:
            return PluginManifest(
                id=os.path.basename(directory),
                name=os.path.basename(directory),
                description=t("plugin.error.manifest_unreadable"),
            )
        module = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(module)
        except Exception:
            return PluginManifest(
                id=os.path.basename(directory),
                name=os.path.basename(directory),
                description=t("plugin.error.manifest_unreadable"),
            )
        manifest = getattr(module, "MANIFEST", None)
        if not isinstance(manifest, PluginManifest):
            return PluginManifest(
                id=os.path.basename(directory),
                name=os.path.basename(directory),
                description=t("plugin.error.no_manifest"),
            )
        return manifest

    # ------------------------------------------------------------------
    # Load / Unload
    # ------------------------------------------------------------------

    def load_global_plugins(self) -> None:
        """Scan and load all enabled plugins in the global plugin directory."""

        self._discovered = {d.manifest.id: d for d in self.discover_global()}
        for plugin_id, d in list(self._discovered.items()):
            if d.scope != "system":
                continue
            if plugin_id in self._plugins:
                continue
            self._load_one(d)

    def load_project_plugins(self, root: str) -> None:
        """Called when attaching project: scan ``<root>/plugins/`` and load enabled project-level plugins."""

        with self._lock:
            self._project_root = root
        for d in self.discover_project(root):
            if d.manifest.id in self._plugins:
                continue
            self._load_one(d)

    def unload_project_plugins(self) -> None:
        """Unload all project-level plugins for current project, leave system-level plugins alone."""

        with self._lock:
            project_ids = [pid for pid, rec in self._plugins.items() if rec.scope == "project"]
        for pid in project_ids:
            self._unload_one(pid)
        with self._lock:
            self._project_root = None

    def unload_all(self) -> None:
        with self._lock:
            ids = list(self._plugins.keys())
        for pid in ids:
            self._unload_one(pid)

    def enable(self, plugin_id: str) -> None:
        """Enable a **discovered but not enabled** plugin."""

        with self._lock:
            discovered = self._discovered.get(plugin_id)
            record = self._plugins.get(plugin_id)
        if discovered is None and record is None:
            return
        self._set_enabled(plugin_id, True)
        if record is None and discovered is not None:
            self._load_one(discovered)
        elif record is not None:
            # Already loaded, sync record.enabled flag + re-register commands and languages
            record.enabled = True
            self._activate_record(record)

    def disable(self, plugin_id: str) -> None:
        self._set_enabled(plugin_id, False)
        record = self._plugins.get(plugin_id)
        if record is not None:
            self._deactivate_record(record)

    def reload(self, plugin_id: str) -> None:
        """Reload plugin (re-import + re-call register).

        For development debugging: no need to restart editor after modifying plugin source.
        """

        with self._lock:
            record = self._plugins.get(plugin_id)
        if record is None:
            return
        location = record.location
        scope = record.scope
        self._unload_one(plugin_id)
        # Clear old module from sys.modules, avoid importlib hitting cache
        for mod_name in list(sys.modules.keys()):
            if mod_name == plugin_id or mod_name.endswith(f".{plugin_id}"):
                sys.modules.pop(mod_name, None)
        discovered = DiscoveredPlugin(
            manifest=record.manifest,
            location=location,
            scope=scope,
        )
        self._discovered[plugin_id] = discovered
        self._load_one(discovered)

    def _set_enabled(self, plugin_id: str, enabled: bool) -> None:
        editor = self._editor
        if editor is None:
            return
        with contextlib.suppress(Exception):
            editor._settings.set(
                editor._settings.global_settings.scope,
                f"plugins.{plugin_id}.enabled",
                enabled,
            )

    # ------------------------------------------------------------------
    # Load / Unload individual plugin
    # ------------------------------------------------------------------

    def _load_one(self, discovered: DiscoveredPlugin) -> None:
        """Execute ``importlib`` + call ``register``, on failure record to ``_plugins`` error field."""

        with self._lock:
            if discovered.manifest.id in self._plugins:
                return
        try:
            module = self._import_module(discovered.location, discovered.manifest.id)
            manifest = self._resolve_manifest(module, discovered)
            manifest.validate()
        except Exception as exc:
            tb = traceback.format_exc(limit=3)
            _log.warning("plugin load failed: %s\n%s", exc, tb)
            record = _PluginRecord(
                manifest=discovered.manifest,
                module=None,
                ctx=None,  # type: ignore[arg-type]
                location=discovered.location,
                scope=discovered.scope,
                enabled=False,
                error=f"{type(exc).__name__}: {exc}",
            )
            with self._lock:
                self._plugins[discovered.manifest.id] = record
            return

        editor = self._editor
        enabled = True
        if editor is not None:
            try:
                enabled = bool(
                    editor._settings.effective(
                        f"plugins.{manifest.id}.enabled",
                        True,
                    )
                )
            except Exception:
                enabled = True

        ctx = PluginContext(
            plugin_id=manifest.id,
            plugin_name=manifest.name,
            host=self,
        )
        record = _PluginRecord(
            manifest=manifest,
            module=module,
            ctx=ctx,
            location=discovered.location,
            scope=discovered.scope,
            enabled=enabled,
        )
        with self._lock:
            self._plugins[manifest.id] = record
            self._discovered[manifest.id] = discovered

        if not enabled:
            return

        try:
            register = getattr(module, "register", None)
            if not callable(register):
                raise PluginLoadError(f"plugin {manifest.id!r} missing register(ctx) function")
            register(ctx)
        except Exception as exc:
            tb = traceback.format_exc(limit=3)
            _log.warning("plugin register failed: %s\n%s", exc, tb)
            record.error = f"register failed: {type(exc).__name__}: {exc}"
            record.enabled = False
            return

        # Commands / languages attached to UI
        self._activate_record(record)

    def _activate_record(self, record: _PluginRecord) -> None:
        """Sync commands / language contributions from record to UI."""

        editor = self._editor
        if editor is None:
            return
        # Commands: add to menu
        with self._lock:
            commands = list(record.ctx._commands)
        for cmd in commands:
            self._install_command(record, cmd)
        # Languages: add to LANG_CONFIG + dropdown
        with self._lock:
            languages = list(record.ctx._languages)
        for lang in languages:
            self._install_language(record, lang)

    def _deactivate_record(self, record: _PluginRecord) -> None:
        """Remove commands / languages; retain ctx and module references for reactivation."""

        editor = self._editor
        if editor is None:
            return
        with self._lock:
            # Find commands/languages belonging to this plugin_id, remove in reverse
            self._commands = [c for c in self._commands if c.plugin_id != record.manifest.id]
            self._languages = [
                (pid, lc) for (pid, lc) in self._languages if pid != record.manifest.id
            ]
            self._hooks = [h for h in self._hooks if h.plugin_id != record.manifest.id]
            for sc in list(self._shortcuts.keys()):
                cmd = self._shortcuts[sc]
                if getattr(cmd, "plugin_id", None) == record.manifest.id:
                    self._shortcuts.pop(sc, None)
        # Commands: let editor rebuild menu
        with contextlib.suppress(Exception):
            editor._refresh_plugin_menu()
        with contextlib.suppress(Exception):
            editor._refresh_plugin_languages()

    def _unload_one(self, plugin_id: str) -> None:
        with self._lock:
            record = self._plugins.pop(plugin_id, None)
        if record is None:
            return
        # First call plugin's own unregister hook (if any)
        for cb in record.ctx._unregister_callbacks:
            with contextlib.suppress(Exception):
                cb()
        # Then clear UI
        self._deactivate_record(record)
        # Clear sys.modules
        for mod_name in list(sys.modules.keys()):
            if mod_name == plugin_id or mod_name.endswith(f".{plugin_id}"):
                sys.modules.pop(mod_name, None)

    @staticmethod
    def _import_module(directory: str, plugin_id: str) -> Any:
        """Dynamically import from ``directory`` using importlib.

        Prefer ``__init__.py``, otherwise ``plugin.py``. Module name = ``plugin_id``,
        stored in ``sys.modules[plugin_id]`` for convenience of ``from <plugin_id> import ...``.
        """

        init_py = os.path.join(directory, "__init__.py")
        plugin_py = os.path.join(directory, "plugin.py")
        if os.path.isfile(init_py):
            path = init_py
        elif os.path.isfile(plugin_py):
            path = plugin_py
        else:
            raise PluginLoadError(
                f"plugin directory {directory!r} has neither __init__.py nor plugin.py"
            )
        spec = importlib.util.spec_from_file_location(plugin_id, path)
        if spec is None or spec.loader is None:
            raise PluginLoadError(f"cannot construct importlib spec for {path!r}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[plugin_id] = module
        # Add plugin directory to sys.path, convenient for plugin internal import of sibling modules
        parent = os.path.dirname(directory)
        added = False
        if parent not in sys.path:
            sys.path.insert(0, parent)
            added = True
        try:
            spec.loader.exec_module(module)
        finally:
            if added:
                with contextlib.suppress(ValueError):
                    sys.path.remove(parent)
        return module

    @staticmethod
    def _resolve_manifest(module: Any, fallback: DiscoveredPlugin) -> PluginManifest:
        manifest = getattr(module, "MANIFEST", None)
        if isinstance(manifest, PluginManifest):
            return manifest
        # Fallback when no MANIFEST: use directory name as id + name
        return PluginManifest(
            id=fallback.manifest.id or os.path.basename(fallback.location),
            name=fallback.manifest.name or os.path.basename(fallback.location),
            description=t("plugin.error.no_manifest"),
        )

    # ------------------------------------------------------------------
    # PluginHostAPI — for PluginContext to call
    # ------------------------------------------------------------------

    def register_hook(self, sub: _HookSubscription) -> None:
        with self._lock:
            self._hooks.append(sub)

    def register_command(self, cmd: Any) -> None:
        """Called on ctx.add_command: check conflicts + write to _commands + install to editor.

        ``_install_command`` is rendered by editor menu system grouped by ``menu``.
        """

        with self._lock:
            # Duplicate label within same plugin is treated as duplicate registration, ignore
            if any(c.plugin_id == cmd.plugin_id and c.label == cmd.label for c in self._commands):
                _log.warning(
                    "plugin %r duplicate command registration %r, ignored",
                    cmd.plugin_id,
                    cmd.label,
                )
                return
            self._commands.append(cmd)
        record = self._plugins.get(cmd.plugin_id)
        if record is None:
            return
        self._install_command(record, cmd)

    def _install_command(self, record: _PluginRecord, cmd: Any) -> None:
        editor = self._editor
        if editor is None:
            return
        if cmd.shortcut:
            with self._lock:
                if cmd.shortcut in self._shortcuts:
                    _log.warning(
                        "plugin %r shortcut %r already taken, ignored",
                        cmd.plugin_id,
                        cmd.shortcut,
                    )
                else:
                    self._shortcuts[cmd.shortcut] = cmd
                    with contextlib.suppress(Exception):
                        editor.window.bind(
                            self._tk_shortcut(cmd.shortcut),
                            lambda e, c=cmd: self._safe_invoke(c),
                            add="+",
                        )
        with contextlib.suppress(Exception):
            editor._add_plugin_command(record, cmd)

    def register_language(self, plugin_id: str, contrib: LanguageContribution) -> None:
        with self._lock:
            # Same plugin re-registering same language name → ignore
            if any(pid == plugin_id and c.name == contrib.name for pid, c in self._languages):
                _log.warning(
                    "plugin %r duplicate language registration %r, ignored",
                    plugin_id,
                    contrib.name,
                )
                return
            self._languages.append((plugin_id, contrib))
        editor = self._editor
        if editor is None:
            return
        with contextlib.suppress(Exception):
            editor._add_plugin_language(plugin_id, contrib)

    def _install_language(self, record: _PluginRecord, contrib: LanguageContribution) -> None:
        editor = self._editor
        if editor is None:
            return
        with contextlib.suppress(Exception):
            editor._add_plugin_language(record.manifest.id, contrib)

    def append_output(self, text: str) -> None:
        editor = self._editor
        if editor is None:
            return
        with contextlib.suppress(Exception):
            editor._append_output(text)

    def setting(self, key: str, default: Any = None) -> Any:
        editor = self._editor
        if editor is None:
            return default
        try:
            return editor._settings.effective(key, default)
        except Exception:
            return default

    def set_setting(self, key: str, value: Any) -> None:
        editor = self._editor
        if editor is None:
            return
        with contextlib.suppress(Exception):
            editor._settings.set(
                editor._settings.global_settings.scope,
                key,
                value,
            )

    # ------------------------------------------------------------------
    # Event dispatch
    # ------------------------------------------------------------------

    def emit(self, hook: str, *args: Any, **kwargs: Any) -> None:
        """Trigger ``hook``, call all enabled plugin subscribers serially.

        Callbacks that raise exceptions are swallowed, but errors are logged to output + logging,
        preventing a single bad plugin from breaking the entire event chain.
        """

        with self._lock:
            subs = [h for h in self._hooks if h.hook == hook]
        for sub in subs:
            record = self._plugins.get(sub.plugin_id)
            if record is None or not record.enabled:
                continue
            self._safe_invoke_handler(sub, args, kwargs)

    def _safe_invoke(self, cmd: Any) -> None:
        try:
            cmd.callback()
        except Exception as exc:
            tb = traceback.format_exc(limit=3)
            _log.warning("plugin command failed: %s\n%s", exc, tb)
            self.append_output(
                t(
                    "plugin.error.cmd_failed",
                    id=cmd.plugin_id,
                    label=cmd.label,
                    err=exc,
                )
                + "\n"
            )

    def _safe_invoke_handler(
        self,
        sub: _HookSubscription,
        args: tuple,
        kwargs: dict,
    ) -> None:
        try:
            sub.callback(*args, **kwargs)
        except Exception as exc:
            tb = traceback.format_exc(limit=3)
            _log.warning("plugin hook %s failed: %s\n%s", sub.hook, exc, tb)
            self.append_output(
                t(
                    "plugin.error.hook_failed",
                    id=sub.plugin_id,
                    hook=sub.hook,
                    err=exc,
                )
                + "\n"
            )

    # ------------------------------------------------------------------
    # Query API (for UI use)
    # ------------------------------------------------------------------

    def list_loaded(self) -> list[_PluginRecord]:
        with self._lock:
            return list(self._plugins.values())

    def list_discovered(self) -> list[DiscoveredPlugin]:
        with self._lock:
            return list(self._discovered.values())

    def get_commands(self) -> list[Any]:
        with self._lock:
            return list(self._commands)

    def get_languages(self) -> list[tuple[str, LanguageContribution]]:
        with self._lock:
            return list(self._languages)

    @staticmethod
    def _tk_shortcut(spec: str) -> str:
        """``Ctrl+Shift+H`` → ``<Control-Shift-H>`` (Tk style)."""

        parts = [p.strip() for p in spec.split("+") if p.strip()]
        if not parts:
            return "<>"
        key = parts[-1]
        mods = parts[:-1]
        mapping = {
            "ctrl": "Control",
            "control": "Control",
            "shift": "Shift",
            "alt": "Alt",
            "meta": "Meta",
        }
        mod_str = "-".join(mapping.get(m.lower(), m.capitalize()) for m in mods)
        if mod_str:
            return f"<{mod_str}-{key}>"
        return f"<{key}>"


__all__ = [
    "DiscoveredPlugin",
    "PluginManager",
]
