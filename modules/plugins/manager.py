"""``modules.plugins.manager`` — 插件加载/卸载/事件分发。

主要职责
========

* :class:`PluginManager` 持有所有已加载插件 + 钩子订阅 + 命令 + 语言贡献。
* ``discover_*`` 系列方法扫描磁盘上的插件目录, 生成候选列表。
* ``load_all`` / ``unload_all`` / ``load_project`` 控制激活生命周期。
* :meth:`emit` 把钩子事件分发给所有订阅者, 单个回调异常被吞掉并 log。

作用域
======

* ``scope == "system"`` 的插件从全局插件目录加载, 编辑器启动即生效,
  关闭前一直保留; 用户在插件管理窗口里**禁用**也只是不再触发事件,
  命令/语言可选择是否一并清理。
* ``scope == "global"`` 的插件默认也是从全局插件目录加载, 但
  ``load_project(root)`` 会把项目级 ``<root>/plugins/`` 目录里的
  ``"global"`` 插件按需加载, 切项目时由 ``unload_project`` 清掉。

启用 / 禁用
===========

每个插件在 settings.json 中有 ``plugins.<id>.enabled`` 键, 默认 True。
``emit`` 时只调用 enabled 的订阅者; 命令注册时已经按 enabled 过滤。
禁用时仅注销命令 / 语言, 插件对象保留以便重新启用时不用重新 import。
"""

from __future__ import annotations

import importlib
import importlib.util
import logging
import os
import sys
import threading
import traceback
from dataclasses import dataclass, field
from typing import (
    Any,
    Callable,
    Dict,
    Iterable,
    List,
    Optional,
    Sequence,
    Tuple,
)

from .api import (
    _HookSubscription,
    LanguageContribution,
    PluginContext,
    PluginHostAPI,
    PluginLoadError,
    PluginManifest,
)
from .hooks import HookEvents


_log = logging.getLogger("modules.plugins")


@dataclass
class _PluginRecord:
    """一个已加载插件的运行时状态。"""

    manifest: PluginManifest
    module: Any
    ctx: PluginContext
    location: str  # 来自的目录, 用于在 UI 里展示
    scope: str  # "system" / "project"
    enabled: bool = True
    error: Optional[str] = None  # 加载/注册失败时记录, UI 显示


@dataclass
class DiscoveredPlugin:
    """磁盘上发现但尚未加载的插件描述, 用于 UI 展示与按需 enable。"""

    manifest: PluginManifest
    location: str
    scope: str  # "system" / "project"


class PluginManager(PluginHostAPI):
    """插件管理器, 单例使用。

    构造时不需要 Tk, 但 :meth:`attach_editor` 之后命令才会真的渲染到菜单里。
    大多数方法都是线程安全的 (内部用 ``self._lock`` 串行化关键操作);
    钩子回调本身假设由 Tk 主线程调用 (与编辑器其它回调一致)。
    """

    def __init__(
        self,
        *,
        global_plugins_dir: Optional[str] = None,
    ) -> None:
        self._lock = threading.RLock()
        self._plugins: Dict[str, _PluginRecord] = {}
        self._discovered: Dict[str, DiscoveredPlugin] = {}
        self._hooks: List[_HookSubscription] = []
        self._commands: List[Any] = []  # PluginCommand list
        self._languages: List[Tuple[str, LanguageContribution]] = []  # (plugin_id, contrib)
        self._shortcuts: Dict[str, Any] = {}  # shortcut -> command record
        self._editor = None  # editor.CodeEditor, see attach_editor
        self._project_root: Optional[str] = None
        self._global_plugins_dir = global_plugins_dir or self._default_global_dir()

    # ------------------------------------------------------------------
    # 默认路径
    # ------------------------------------------------------------------

    @staticmethod
    def _default_global_dir() -> str:
        """默认全局插件目录: ``<config_root>/plugins/``。

        复用 settings 的路径策略, 保证与 settings.json 同根, 方便用户找。
        """

        from modules.settings.global_settings import default_global_path
        settings_path = default_global_path()
        base = os.path.dirname(settings_path)
        return os.path.join(base, "plugins")

    # ------------------------------------------------------------------
    # 编辑器绑定 (延迟, 因为 PluginManager 在 CodeEditor.__init__ 中先构造)
    # ------------------------------------------------------------------

    def attach_editor(self, editor: Any) -> None:
        """把 :class:`CodeEditor` 实例挂到 manager 上, 之后才能注册命令到菜单。

        之所以延迟: :class:`CodeEditor` 在创建 :class:`PluginManager` 时
        菜单栏还没建好, 等 ``_build_menubar()`` 之后再调一次更安全。
        """

        with self._lock:
            self._editor = editor

    def detach_editor(self) -> None:
        with self._lock:
            self._editor = None

    # ------------------------------------------------------------------
    # 目录扫描
    # ------------------------------------------------------------------

    def discover_global(self) -> List[DiscoveredPlugin]:
        """扫描全局插件目录, 返回发现列表 (不执行 import)。"""

        return self._discover_dir(self._global_plugins_dir, scope="system")

    def discover_project(self, root: str) -> List[DiscoveredPlugin]:
        """扫描项目级 ``<root>/plugins/`` 目录。"""

        if not root:
            return []
        return self._discover_dir(os.path.join(root, "plugins"), scope="project")

    def _discover_dir(self, directory: str, *, scope: str) -> List[DiscoveredPlugin]:
        """通用目录扫描: 每个直接子目录视作一个插件 (有 ``__init__.py`` 才算)。"""

        if not directory or not os.path.isdir(directory):
            return []
        out: List[DiscoveredPlugin] = []
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
            if not os.path.isfile(init_py):
                # 也兼容 manifest.py + plugin.py 风格, 见 _load_module
                if not os.path.isfile(os.path.join(sub, "plugin.py")):
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
        """只读 manifest, 不执行 register。失败则返回一个占位 manifest。

        占位 manifest 用目录名当 id, 保证 UI 仍能展示一个不可加载的插件,
        让用户知道"这里有个插件但它坏了"。
        """

        # _load_module 用了独立 spec, 这里也用临时 spec 避免污染 sys.modules
        spec = importlib.util.spec_from_file_location(
            "_plugin_peek", os.path.join(directory, "__init__.py"),
        )
        if spec is None or spec.loader is None:
            return PluginManifest(
                id=os.path.basename(directory),
                name=os.path.basename(directory),
                description="(无法读取 manifest)",
            )
        module = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(module)
        except Exception:
            return PluginManifest(
                id=os.path.basename(directory),
                name=os.path.basename(directory),
                description="(无法读取 manifest)",
            )
        manifest = getattr(module, "MANIFEST", None)
        if not isinstance(manifest, PluginManifest):
            return PluginManifest(
                id=os.path.basename(directory),
                name=os.path.basename(directory),
                description="(MANIFEST 未定义或类型错误)",
            )
        return manifest

    # ------------------------------------------------------------------
    # 加载 / 卸载
    # ------------------------------------------------------------------

    def load_global_plugins(self) -> None:
        """扫描并加载全局插件目录中所有 enabled 的插件。"""

        self._discovered = {
            d.manifest.id: d for d in self.discover_global()
        }
        for plugin_id, d in list(self._discovered.items()):
            if d.scope != "system":
                continue
            if plugin_id in self._plugins:
                continue
            self._load_one(d)

    def load_project_plugins(self, root: str) -> None:
        """附加项目时调用: 扫描 ``<root>/plugins/`` 并加载 enabled 的项目级插件。"""

        with self._lock:
            self._project_root = root
        for d in self.discover_project(root):
            if d.manifest.id in self._plugins:
                continue
            self._load_one(d)

    def unload_project_plugins(self) -> None:
        """卸载当前项目的所有项目级插件, 不动系统级插件。"""

        with self._lock:
            project_ids = [
                pid for pid, rec in self._plugins.items() if rec.scope == "project"
            ]
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
        """启用一个**已发现但未启用**的插件。"""

        with self._lock:
            discovered = self._discovered.get(plugin_id)
            record = self._plugins.get(plugin_id)
        if discovered is None and record is None:
            return
        self._set_enabled(plugin_id, True)
        if record is None and discovered is not None:
            self._load_one(discovered)
        elif record is not None:
            # 已加载过, 同步 record.enabled 标志 + 重新注册命令和语言
            record.enabled = True
            self._activate_record(record)

    def disable(self, plugin_id: str) -> None:
        self._set_enabled(plugin_id, False)
        record = self._plugins.get(plugin_id)
        if record is not None:
            self._deactivate_record(record)

    def reload(self, plugin_id: str) -> None:
        """重新加载插件 (重新 import + 重新调用 register)。

        用于开发调试: 修改插件源码后无需重启编辑器。
        """

        with self._lock:
            record = self._plugins.get(plugin_id)
        if record is None:
            return
        location = record.location
        scope = record.scope
        self._unload_one(plugin_id)
        # 清掉 sys.modules 里旧 module, 避免 importlib 命中缓存
        for mod_name in list(sys.modules.keys()):
            if mod_name == plugin_id or mod_name.endswith(f".{plugin_id}"):
                sys.modules.pop(mod_name, None)
        discovered = DiscoveredPlugin(
            manifest=record.manifest, location=location, scope=scope,
        )
        self._discovered[plugin_id] = discovered
        self._load_one(discovered)

    def _set_enabled(self, plugin_id: str, enabled: bool) -> None:
        editor = self._editor
        if editor is None:
            return
        try:
            editor._settings.set(
                editor._settings.global_settings.scope,  # type: ignore[attr-defined]
                f"plugins.{plugin_id}.enabled",
                enabled,
            )
        except Exception:
            pass

    # ------------------------------------------------------------------
    # 单个插件的加载 / 卸载
    # ------------------------------------------------------------------

    def _load_one(self, discovered: DiscoveredPlugin) -> None:
        """执行 ``importlib`` + 调 ``register``, 失败时记录到 ``_plugins`` 的 error 字段."""

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
                enabled = bool(editor._settings.effective(  # type: ignore[attr-defined]
                    f"plugins.{manifest.id}.enabled", True,
                ))
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
                raise PluginLoadError(
                    f"plugin {manifest.id!r} 缺少 register(ctx) 函数"
                )
            register(ctx)
        except Exception as exc:
            tb = traceback.format_exc(limit=3)
            _log.warning("plugin register failed: %s\n%s", exc, tb)
            record.error = f"register 失败: {type(exc).__name__}: {exc}"
            record.enabled = False
            return

        # 命令 / 语言挂到 UI
        self._activate_record(record)

    def _activate_record(self, record: _PluginRecord) -> None:
        """把 record 里的命令 / 语言贡献同步到 UI。"""

        editor = self._editor
        if editor is None:
            return
        # 命令: 加到菜单
        with self._lock:
            commands = list(record.ctx._commands)
        for cmd in commands:
            self._install_command(record, cmd)
        # 语言: 加到 LANG_CONFIG + 下拉框
        with self._lock:
            languages = list(record.ctx._languages)
        for lang in languages:
            self._install_language(record, lang)

    def _deactivate_record(self, record: _PluginRecord) -> None:
        """移除命令 / 语言; 保留 ctx 与模块引用以便重新激活。"""

        editor = self._editor
        if editor is None:
            return
        with self._lock:
            # 找出属于该 plugin_id 的命令/语言, 反向移除
            self._commands = [c for c in self._commands if c.plugin_id != record.manifest.id]
            self._languages = [
                (pid, lc) for (pid, lc) in self._languages if pid != record.manifest.id
            ]
            self._hooks = [h for h in self._hooks if h.plugin_id != record.manifest.id]
            for sc in list(self._shortcuts.keys()):
                cmd = self._shortcuts[sc]
                if getattr(cmd, "plugin_id", None) == record.manifest.id:
                    self._shortcuts.pop(sc, None)
        # 命令: 让 editor 重建菜单
        try:
            editor._refresh_plugin_menu()  # type: ignore[attr-defined]
        except Exception:
            pass
        try:
            editor._refresh_plugin_languages()  # type: ignore[attr-defined]
        except Exception:
            pass

    def _unload_one(self, plugin_id: str) -> None:
        with self._lock:
            record = self._plugins.pop(plugin_id, None)
        if record is None:
            return
        # 先调 plugin 自己的 unregister 钩子 (如果有)
        for cb in record.ctx._unregister_callbacks:
            try:
                cb()
            except Exception:
                pass
        # 再清 UI
        self._deactivate_record(record)
        # 清掉 sys.modules
        for mod_name in list(sys.modules.keys()):
            if mod_name == plugin_id or mod_name.endswith(f".{plugin_id}"):
                sys.modules.pop(mod_name, None)

    @staticmethod
    def _import_module(directory: str, plugin_id: str) -> Any:
        """从 ``directory`` 用 importlib 动态 import。

        优先 ``__init__.py``, 否则 ``plugin.py``。模块名 = ``plugin_id``,
        存进 ``sys.modules[plugin_id]`` 方便 ``from <plugin_id> import ...``。
        """

        init_py = os.path.join(directory, "__init__.py")
        plugin_py = os.path.join(directory, "plugin.py")
        if os.path.isfile(init_py):
            path = init_py
        elif os.path.isfile(plugin_py):
            path = plugin_py
        else:
            raise PluginLoadError(
                f"插件目录 {directory!r} 既没有 __init__.py 也没有 plugin.py"
            )
        spec = importlib.util.spec_from_file_location(plugin_id, path)
        if spec is None or spec.loader is None:
            raise PluginLoadError(f"无法为 {path!r} 构造 importlib spec")
        module = importlib.util.module_from_spec(spec)
        sys.modules[plugin_id] = module
        # 把插件目录加进 sys.path, 方便插件内 import 兄弟模块
        parent = os.path.dirname(directory)
        added = False
        if parent not in sys.path:
            sys.path.insert(0, parent)
            added = True
        try:
            spec.loader.exec_module(module)
        finally:
            if added:
                try:
                    sys.path.remove(parent)
                except ValueError:
                    pass
        return module

    @staticmethod
    def _resolve_manifest(module: Any, fallback: DiscoveredPlugin) -> PluginManifest:
        manifest = getattr(module, "MANIFEST", None)
        if isinstance(manifest, PluginManifest):
            return manifest
        # 没有 MANIFEST 时退化: 用目录名作 id + name
        return PluginManifest(
            id=fallback.manifest.id or os.path.basename(fallback.location),
            name=fallback.manifest.name or os.path.basename(fallback.location),
            description="(插件未声明 MANIFEST)",
        )

    # ------------------------------------------------------------------
    # PluginHostAPI — 供 PluginContext 调用
    # ------------------------------------------------------------------

    def register_hook(self, sub: _HookSubscription) -> None:
        with self._lock:
            self._hooks.append(sub)

    def register_command(self, cmd: Any) -> None:
        """ctx.add_command 时调用: 校验冲突 + 写入 _commands + 安装到 editor。

        ``_install_command`` 由编辑器菜单系统按 ``menu`` 分组渲染。
        """

        with self._lock:
            # 同 plugin 内重复 label 视为重复注册, 忽略
            if any(
                c.plugin_id == cmd.plugin_id and c.label == cmd.label
                for c in self._commands
            ):
                _log.warning(
                    "plugin %r 重复注册命令 %r, 已忽略",
                    cmd.plugin_id, cmd.label,
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
                        "plugin %r 的快捷键 %r 已被占用, 已忽略",
                        cmd.plugin_id, cmd.shortcut,
                    )
                else:
                    self._shortcuts[cmd.shortcut] = cmd
                    try:
                        editor.window.bind(  # type: ignore[attr-defined]
                            self._tk_shortcut(cmd.shortcut),
                            lambda e, c=cmd: self._safe_invoke(c),
                            add="+",
                        )
                    except Exception:
                        pass
        try:
            editor._add_plugin_command(record, cmd)  # type: ignore[attr-defined]
        except Exception:
            pass

    def register_language(self, plugin_id: str, contrib: LanguageContribution) -> None:
        with self._lock:
            # 同 plugin 重复注册同名语言 → 忽略
            if any(pid == plugin_id and c.name == contrib.name for pid, c in self._languages):
                _log.warning(
                    "plugin %r 重复注册语言 %r, 已忽略",
                    plugin_id, contrib.name,
                )
                return
            self._languages.append((plugin_id, contrib))
        editor = self._editor
        if editor is None:
            return
        try:
            editor._add_plugin_language(plugin_id, contrib)  # type: ignore[attr-defined]
        except Exception:
            pass

    def _install_language(self, record: _PluginRecord, contrib: LanguageContribution) -> None:
        editor = self._editor
        if editor is None:
            return
        try:
            editor._add_plugin_language(record.manifest.id, contrib)  # type: ignore[attr-defined]
        except Exception:
            pass

    def append_output(self, text: str) -> None:
        editor = self._editor
        if editor is None:
            return
        try:
            editor._append_output(text)  # type: ignore[attr-defined]
        except Exception:
            pass

    def setting(self, key: str, default: Any = None) -> Any:
        editor = self._editor
        if editor is None:
            return default
        try:
            return editor._settings.effective(key, default)  # type: ignore[attr-defined]
        except Exception:
            return default

    def set_setting(self, key: str, value: Any) -> None:
        editor = self._editor
        if editor is None:
            return
        try:
            editor._settings.set(  # type: ignore[attr-defined]
                editor._settings.global_settings.scope,  # type: ignore[attr-defined]
                key, value,
            )
        except Exception:
            pass

    # ------------------------------------------------------------------
    # 事件分发
    # ------------------------------------------------------------------

    def emit(self, hook: str, *args: Any, **kwargs: Any) -> None:
        """触发 ``hook``, 串行调用所有 enabled 插件的订阅者。

        抛异常的回调被吞掉, 但会 log error 到 output + logging,
        避免单个坏插件拖垮整个事件链。
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
                f"[ERROR] [{cmd.plugin_id}] 命令 {cmd.label!r} 执行失败: {exc}\n"
            )

    def _safe_invoke_handler(
        self, sub: _HookSubscription, args: tuple, kwargs: dict,
    ) -> None:
        try:
            sub.callback(*args, **kwargs)
        except Exception as exc:
            tb = traceback.format_exc(limit=3)
            _log.warning("plugin hook %s failed: %s\n%s", sub.hook, exc, tb)
            self.append_output(
                f"[ERROR] [{sub.plugin_id}] 钩子 {sub.hook!r} 回调失败: {exc}\n"
            )

    # ------------------------------------------------------------------
    # 查询 API (供 UI 用)
    # ------------------------------------------------------------------

    def list_loaded(self) -> List[_PluginRecord]:
        with self._lock:
            return list(self._plugins.values())

    def list_discovered(self) -> List[DiscoveredPlugin]:
        with self._lock:
            return list(self._discovered.values())

    def get_commands(self) -> List[Any]:
        with self._lock:
            return list(self._commands)

    def get_languages(self) -> List[Tuple[str, LanguageContribution]]:
        with self._lock:
            return list(self._languages)

    @staticmethod
    def _tk_shortcut(spec: str) -> str:
        """``Ctrl+Shift+H`` → ``<Control-Shift-H>`` (Tk 风格)。"""

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
    "PluginManager",
    "DiscoveredPlugin",
]