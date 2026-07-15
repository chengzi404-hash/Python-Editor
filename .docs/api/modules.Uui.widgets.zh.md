# `modules/Uui/widgets/__init__.py`

源文件路径：`modules/Uui/widgets/__init__.py`

`modules.Uui.widgets` 包的公开入口。汇总所有 UI 控件、主题与控件级市场。

## 公开 API

### 主题
- `theme` — 主题模块（颜色、字体、`set_theme`/`apply_theme_recursive`/`follow_system`/`on_change` 等）。
- `ui_theme_marketplace` — UI 主题市场抽象（`MarketplaceItem`/`UIThemePackage`/`MarketplaceSearchResult`/`MarketplaceProvider`/`UIMarketplace`/`get_marketplace`）。

### 基础控件
- `UFrame` / `ULabel` / `UButton` / `UEntry` / `UText`
- `UCheckButton` / `URadioButton` / `UComboBox`
- `UProgressBar` / `USlider` / `UScrollBar`
- `UMenuBar` / `UMenu`

### 编辑器扩展
- `UEditorSuggestion` / `CompletionItem` — 浮动补全框。
- `UFileTree` — VS 风格文件树。
- `LineNumberCanvas` — 基于 Canvas 的行号栏。
- `TabBar` / `Tab` — 多文件标签栏。
- `UTabView` — 简单 Tab 容器。

### 设置 / 通用
- `USettingsNavBar` / `NavSelection` — 设置导航树。
- `TreeCanvas` — Canvas 渲染层通用树控件。
- `UDialog` — 主题感知对话框。
- `UListView` — 多列列表视图。
- `message_box` — `showinfo/showwarning/showerror/askyesno` 便捷封装。

### 侧边栏 / 卡片
- `ActivityBar` / `ActivityBarItem` / `SideBar` — VSCode 风格侧边栏。
- `ExplorerCard` — 文件浏览器卡片。
- `DebugCard` — 调试卡片（变量、调用栈、断点、调试控制）。
- `GitCard` — Git 源代码管理卡片。

## `__all__`

见源码顶部。