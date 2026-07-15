# `modules/settings/widgets.py`

源文件路径：`modules/settings/widgets.py`

设置模块的可视化 UI 封装。依赖 `modules.Uui.widgets` 中的 UButton/UCheckButton/UComboBox/UEntry/UFrame/ULabel/USettingsNavBar/theme。

## 内部辅助

### `_group_key(spec: SettingSpec) -> str`
按 `key` 前缀自动归类：`editor.tab_size` → `editor`；无 `.` 时归为 `"_"`。

## 类

### `USettingPanel`
为某一作用域渲染一组 `SettingSpec` 的可视化面板。每个 spec 显示为"标签 + 控件 + 说明"的三段行；按 `key` 前缀自动分组。

用户编辑控件时只修改"工作副本" `_working`，需要 `apply()` 才写回底层 `Settings`，或 `revert()` 丢弃改动。

构造参数：
- `parent`
- `settings: Settings`
- `on_change: Optional[Callable[[str, Any], None]] = None` — 控件改动回调（仅工作副本变化，不写回）。
- `show_only_keys: Optional[List[str]] = None` — 只渲染这些 key。
- `filter_group_keys: Optional[List[str]] = None` — 只渲染这些分组。
- `**kwargs` 转发给 `UFrame.__init__`。

#### 内部字段
- `_settings`, `_on_change`, `_working: Dict[str, Any]`, `_widgets: Dict[str, Any]`, `_vars: Dict[str, tk.Variable]`
- `_listener`: 用于在销毁时移除监听。

#### 方法
- `_build()`：按分组渲染 UI（标题行 + 每行一个 spec）。
- `_build_row(row, spec)`：渲染单行（标签 + 控件 + 描述）。
- `_make_widget(spec)`：根据 spec.type 返回对应控件：
  - `BOOLEAN` → `UCheckButton` + `tk.BooleanVar`。
  - `CHOICE` → `UComboBox`。
  - `BUTTON` → `UButton`（点击时调用 `_on_button`）。
  - 其它 → `UEntry` + `tk.StringVar`。
- `_current_value(spec)`：优先 `_working`，否则 `settings.get()`。
- `_stringify(value)`：列表用 `, ` 连接；`None` 返回空串。
- `_on_button(key)`：调用 `on_change(key, None)`。
- `_user_changed(key, value)`：写入 `_working`（校验失败时记入 `_last_error`），并通知 `on_change`。
- `_coerce(key, value)`：把控件原始值转为 spec 要求的类型（BUTTON 直接返回；空字符串退回默认；LIST 用 `,` 拆分）。
- `apply() -> int`：把 `_working` 写回底层 `settings`，返回成功条数；BUTTON 跳过；失败项被忽略。
- `revert() -> None`：丢弃 `_working` 并刷新所有控件。
- `last_error() -> Optional[Exception]`：最近一次校验错误。
- `_refresh_widgets()` / `_refresh_single_widget(key)`：从 `_working`/`settings` 重置控件显示值。
- `_on_settings_event(event)`：监听 `SettingsChangeEvent` 同步 `working` 与控件；当外部事件改变本 scope 的某个 key 时更新该控件。
- `destroy()`：先解绑监听，再调用父类 `destroy`。

### `UProjectSettingsWindow`
同时呈现"全局 / 项目"两份设置的窗口。

构造参数：
- `manager: SettingsManager`
- `title: str = "Settings"`
- `parent: Optional[tk.Misc] = None`
- `geometry: str = "640x520"`
- `on_change: Optional[Callable[[str, Any], None]] = None`

行为：
- 左侧导航栏（`USettingsNavBar`） + 右侧 `USettingPanel`（用水平 `PanedWindow` 分隔，`<Map>` 后将分隔条放到 `220px`）。
- 顶部标题栏 + 底部按钮行：应用 / 保存 / 关闭 / 恢复默认。
- 切换导航节点 / scope 时自动重建右侧面板。

#### 方法
- `_build()`：构建 UI 框架、加载导航树。
- `_init_paned_position(event=None)`：首次显示后将分隔条放到 `220px`（必要时递归延迟一帧）。
- `_load_nav()`：根据 `manager.project_settings` 是否存在决定是否显示"项目"分支。
- `_switch(scope)`：导航到指定 scope 根节点；切换 PROJECT 时若未挂项目会引导用户选目录并 `attach_project`。
- `_on_nav_select(selection)`：根据 selection 类型（scope 根 / 分组 / 叶子）以 `show_only_keys` 或 `filter_group_keys` 重建面板。
- `_rebuild_panel(selection)`：销毁并重建右侧 `USettingPanel`。
- `_on_apply()`：调用 `panel.apply()` 并弹窗显示写入条数。
- `_on_save()`：先 `apply()` 再 `manager.save_all()`，并弹窗。
- `_on_close()`：销毁窗口。
- `_on_reset_defaults()`：二次确认后 `manager.reset(current_scope)`，重建面板。
- `show() -> None`：进入 `mainloop`。
- `root`（属性）：返回 `tk.Toplevel`/`tk.Tk` 根容器。

> 这些 UI 类只是便捷封装，业务代码仍通过 `SettingsManager` / `Settings` 读写。