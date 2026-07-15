# `modules/Uui/tool/designer.py`

源文件路径：`modules/Uui/tool/designer.py`

Uui 可视化控件设计器（Qt Creator 风格），单文件 1800+ 行，按 Qt Designer 习惯组织三大区域：

- 左侧：`Widget Palette` / `Object Explorer`（`_SidebarTabBar` 切换）。
- 中部：`Canvas` 表面 + 选中/拖拽/调整大小/对齐参考线。
- 右侧：属性编辑器 + 操作面板（`Actions`）。

## 模块常量

- `DESIGNER_VERSION = '2.0'`
- `WIDGET_TYPES` — 支持的 10 种 Uui 控件。
- `WIDGET_CLASSES` — 名字 → 类对象的映射。
- `DEFAULT_PROPS` / `DEFAULT_SIZE` — 每个控件的默认属性与默认尺寸。
- `VARIANT_OPTIONS` — 各控件的 `variant` 选项列表。
- `NUMERIC_PROPS = {'x', 'y', 'width', 'height', 'maximum', 'value', 'from_', 'to'}`
- `BOOL_PROPS = {'show_value'}`
- `WIDGET_GROUPS` — 控件分组（Layouts / Spacers / Buttons / Item / Input / Display / Containers）。
- `WIDGET_ICON` — 控件 → 显示图标（Unicode 符号）。
- `COMMON_GEOMETRY = ['x', 'y', 'width', 'height']` / `COMMON_OBJECT = ['name']`
- `TYPE_PROPS` — 各类型属性分组（如 `('Text', ['text', 'variant'])`）。

## 内部小部件

### `_FlatButton(tk.Frame)`
扁平按钮（hover/press 效果），用于设计器工具栏 / 标题。
- `__init__(parent, text, command=None, width=30, height=24)`
- `_on_enter/_on_leave/_on_press/_on_release`

### `_PanelSection(tk.Frame)`
可折叠分组标题栏。
- `__init__(parent, title, expanded=True)`
- `_on_enter/_on_leave/_toggle`
- `body -> tk.Frame`（折叠时返回占位）

### `_SidebarTabBar(tk.Frame)`
左右两侧的 tab 切换栏。
- `__init__(parent, tabs, command=None)`
- `_select(idx, fire=True)`

## 主类

### `DesignerApp(Window)`
设计器主窗口。

#### 构造
- `__init__(project_file=None)`：初始化窗口、菜单、工具栏、主体、状态栏；可选加载 `project_file`。

#### UI 构建
- `_create_menu()` — File（New / Open / Save / Save As / Export Python / Reset / Exit）+ Edit（Undo / Redo / Cut/Copy/Paste / Delete / Select All）+ View（Toggle Preview）+ Help（About）。
- `_create_toolbar()` — 顶部工具栏（主题下拉 + 模式切换 Edit/Preview + 缩放控制）。
- `_set_mode(mode)` / `_set_preview(on)` — 切换设计/预览模式。
- `_create_body()` — 构建左/中/右三栏（`tk.PanedWindow`）。
- `_build_left_sidebar()` — 调色板 + 对象树（用 `_SidebarTabBar`）。
- `_build_widget_palette()` / `_refresh_palette()` / `_build_palette_group(title, items)` / `_make_palette_cell(parent, wtype, friendly)` — 调色板；每个 cell 支持拖拽（`_on_drag`）。
- `_build_object_explorer()` / `_refresh_explorer()` / `_make_explorer_row(parent, kind, name, icon, item_id)` — 对象树，支持点击选中 / hover。
- `_on_left_tab_change(idx)` — 切换 palette / explorer；`_show_palette_page()` / `_show_explorer_page()`。
- `_build_center()` — 中部画布；`_redraw_checker()` 画参考线；`_on_canvas_motion` / `_configure_surface`。
- `_build_right_sidebar()` / `_on_right_tab_change(idx)` / `_build_properties_page()` / `_build_actions_page()` — 右侧属性 + 操作。
- `_create_status_bar()` / `_update_status_bar(message)` / `_toast(message)` — 状态栏与轻提示。

#### 属性编辑
- `_add_property_section(section_title, names)` / `_populate_prop_values()` / `_show_prop_rows(names)` / `_apply_props()` — 属性表编辑。
- `_set_title(value)` / `_set_geometry(value)` / `_parse_geometry()` — 顶层属性。
- `_on_theme_change(value)` / `_refresh_toolbar_theme()` — 主题切换。

#### 项目
- `_new_project()` / `_clear_widgets()` / `_unique_name(wtype)` / `_rename_widget(item_id)` / `_on_commit(event)` / `_on_cancel(event)` / `_focus()` / `_destroy_rename_overlay()` — 新建 / 重命名。
- `_add_widget(wtype)` / `_render_widget(item)` / `_build_kwargs(item)` — 添加并渲染控件。
- `_bind_design_events(widget, item_id)` / `_press/_double_click/_drag` — 设计期事件绑定。
- `_collect_descendants(widget)` / `_item_by_id(item_id)` / `_update_geometry(item)` / `_select(item_id)` / `_show_explorer_page_or_update()` / `_select_all()` / `_refresh_selection()` / `_clear_selection()` — 选中 / 层级。
- `_on_resize_press(event)` / `_on_resize_drag(event)` — 调整大小。
- `_refresh_list()` / `_delete_selected()` / `_destroy_widget_instance(item_id)` — 删除。
- `_to_int(value, default=0)` / `_to_float(value, default=0.0)` / `_to_bool(value)` — 类型转换。

#### 持久化
- `_load_xml(path)` — 从 XML 加载项目；`_widget_from_element(elem, idx)` 递归构建控件。
- `_save_xml(path)` / `_widget_to_element(item, parent)` — 保存。
- `_save_project()` / `_save_as_project()` / `_open_project()` — 文件对话框包装。
- `_export_python()` / `_generate_python()` / `_export_kwargs(item)` — 导出 Python 代码。
- `_safe_name(name)` — 安全化标识符。

#### 其他
- `_reset_layout()` — 清空控件列表。
- `_show_about()` — About 对话框。
- `_on_close()` — 关闭窗口钩子。

## 入口

### `main(project_file=None)`
启动 `DesignerApp(project_file)` 并进入 `mainloop`。