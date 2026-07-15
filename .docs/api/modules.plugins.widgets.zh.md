# `modules/plugins/widgets.py`

源文件路径：`modules/plugins/widgets.py`

插件管理窗口（基于 Tk）。依赖 `modules.Uui.widgets` 中的 UButton/UCheckButton/UFrame/ULabel/UText/theme。

## 类

### `UPluginManagerWindow`
可视化插件管理界面。

构造：`__init__(editor: Any, manager: Any) -> None`
- `editor` — `CodeEditor` 实例，提供 `_refresh_plugin_menu`、`_refresh_plugin_languages`、`_show_plugin_info`、`_append_output` 等方法。
- `manager` — `PluginManager` 实例。
- 构造时立即创建 `tk.Toplevel(editor.window)`，尺寸 `720x520+300+150`，`transient(editor.window)`。

#### 内部方法（按职责）
- `_build()`：构建 UI。
  - 顶部信息条：全局插件目录路径。
  - 左栏（已加载插件）：`UText` 显示 `已加载` 列表。
  - 右栏（已发现但未启用）：`UText` 显示 `发现` 列表。
  - 底部按钮：启用 / 禁用 / 重新加载 / 详情 / 关闭。
  - 钩子事件参考：列出 `HOOK_SPECS` 中每个 hook 的名称、参数与说明。
  - 末尾调用 `_refresh()`。

- `_refresh()`：重渲染左右两栏。
  - 左栏：每项两行（标题+错误/路径）。
  - 右栏：每项三行（标题/描述/路径）。

- `_selected_loaded_index() -> Optional[int]`：从左栏选区推断索引（按 `(line-1)//2` 还原）。
- `_selected_discovered_index() -> Optional[int]`：从右栏选区推断索引（按 `(line-1)//3` 还原）。

- `_on_enable()` / `_on_disable()` / `_on_reload()`：操作右栏/左栏选中项，调用 `manager.enable/disable/reload`，完成后调用 `editor._refresh_plugin_menu()` 与 `_refresh_plugin_languages()` 并 `_refresh()`；失败时通过 `messagebox.showerror` 提示。
- `_on_info()`：左栏选中则调用 `editor._show_plugin_info(record)`；右栏选中则弹出含名称/ID/版本/作者/作用域/来源/状态/描述的对话框；都未选中时给出提示。

## `__all__`

```python
["UPluginManagerWindow"]
```