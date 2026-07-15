# `modules/plugins/manager.py`

源文件路径：`modules/plugins/manager.py`

插件加载/卸载/事件分发核心实现。同时实现 `PluginHostAPI` 协议，把插件上下文对编辑器的操作转译为对 `CodeEditor` 的调用。

## 内部数据类

### `_PluginRecord`
单个已加载插件的运行时状态。
- `manifest: PluginManifest`
- `module: Any`
- `ctx: PluginContext`
- `location: str`
- `scope: str` — `'system'` / `'project'`
- `enabled: bool = True`
- `error: Optional[str] = None`

## 数据类

### `DiscoveredPlugin`
磁盘上发现但尚未加载的插件描述。
- `manifest: PluginManifest`
- `location: str`
- `scope: str` — `'system'` / `'project'`

## 类

### `PluginManager(PluginHostAPI)`
单例使用的插件管理器。构造时不需要 Tk，但命令注册需要 `attach_editor` 之后才会真的渲染到菜单。

构造参数（关键字）：
- `global_plugins_dir: Optional[str] = None` — 默认走 `_default_global_dir()` → `<settings_root>/plugins`。

#### 编辑器绑定
- `attach_editor(editor) -> None` / `detach_editor() -> None`：注入/解绑 `CodeEditor` 实例。命令和语言注册依赖此引用。

#### 目录扫描
- `discover_global() -> List[DiscoveredPlugin]`：扫描全局插件目录。
- `discover_project(root: str) -> List[DiscoveredPlugin]`：扫描 `<root>/plugins/`。
- `_discover_dir(directory, *, scope)`：通用扫描；每个直接子目录视作一个插件，需要存在 `__init__.py` 或 `plugin.py`。

- `_peek_manifest(directory) -> PluginManifest`（静态）：不执行 `register`，仅临时加载模块读取 `MANIFEST`；失败时返回占位 manifest（用目录名做 id/name）。

#### 加载 / 卸载
- `load_global_plugins() -> None`：扫描并加载全局插件中所有 `enabled` 的项。
- `load_project_plugins(root: str) -> None`：附加项目时调用。
- `unload_project_plugins() -> None`：仅卸载当前项目级插件（不动系统级）。
- `unload_all() -> None`：卸载所有。
- `enable(plugin_id) -> None`：启用一个已发现或已加载的插件；`disabled` 状态会重新 import + register。
- `disable(plugin_id) -> None`：禁用并从菜单/语言列表中移除，保留模块对象以便快速重新启用。
- `reload(plugin_id) -> None`：清掉 `sys.modules` 缓存后重新 import + register。

#### 内部辅助
- `_set_enabled(plugin_id, enabled)`：把 `plugins.<id>.enabled` 写回全局 settings。
- `_load_one(discovered)`：`importlib` 加载模块 → 解析并 `validate()` manifest → 检查 `plugins.<id>.enabled` → 构建 `PluginContext` → 调用 `register(ctx)` → `_activate_record`。
- `_activate_record(record)`：把 record 中的命令和语言贡献同步到 UI。
- `_deactivate_record(record)`：从 `_commands` / `_languages` / `_hooks` / `_shortcuts` 移除该插件的项目，并调用 editor 的 `_refresh_plugin_menu` 和 `_refresh_plugin_languages`。
- `_unload_one(plugin_id)`：弹出记录 → 调用 `_unregister_callbacks` → `_deactivate_record` → 从 `sys.modules` 移除。
- `_import_module(directory, plugin_id)`（静态）：用 `importlib.util.spec_from_file_location` 加载；优先 `__init__.py` 否则 `plugin.py`；模块名 = `plugin_id`；临时把插件目录加入 `sys.path` 便于兄弟模块导入。
- `_resolve_manifest(module, fallback)`（静态）：返回模块中定义的 `MANIFEST`，否则退化（用目录名）。

#### PluginHostAPI 实现
- `register_hook(sub)`：把订阅追加到 `_hooks`。
- `register_command(cmd)`：去重（同一 plugin 内同 label 忽略）后写入 `_commands` 并调用 `_install_command`。
- `_install_command(record, cmd)`：若指定 `shortcut`，将 `Ctrl+Shift+H` 等字符串转为 Tk 风格 `<Control-Shift-H>` 并绑定到 `editor.window`；冲突时忽略。然后调用 `editor._add_plugin_command`。
- `register_language(plugin_id, contrib)`：去重后写入 `_languages`，调用 `editor._add_plugin_language`。
- `_install_language(record, contrib)`：调用 `editor._add_plugin_language`。
- `append_output(text)` → `editor._append_output`。
- `setting(key, default=None)` → `editor._settings.effective(...)`；未绑定 editor 时返回 `default`。
- `set_setting(key, value)` → `editor._settings.set(...)`。

#### 事件分发
- `emit(hook, *args, **kwargs) -> None`：复制当前 `hook` 的订阅者列表（脱锁），按订阅者依次调用 `_safe_invoke_handler`，跳过未启用的插件。
- `_safe_invoke(cmd)` / `_safe_invoke_handler(sub, args, kwargs)`：调用回调；异常被记录到 `logging` 与 output panel。

#### 查询 API
- `list_loaded() -> List[_PluginRecord]`
- `list_discovered() -> List[DiscoveredPlugin]`
- `get_commands() -> List[PluginCommand]`
- `get_languages() -> List[Tuple[str, LanguageContribution]]`

#### 工具
- `_tk_shortcut(spec: str) -> str`（静态）：`Ctrl+Shift+H` → `<Control-Shift-H>`，可识别 `Ctrl`/`Control`/`Shift`/`Alt`/`Meta`（大小写不敏感）。

## `__all__`

```python
["PluginManager", "DiscoveredPlugin"]
```