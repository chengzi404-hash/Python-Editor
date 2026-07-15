# `modules/Uui/demo.py`

源文件路径：`modules/Uui/demo.py`

Uui 内置组件画廊（`python -m Uui.cli demo`）。

## 模块常量

- `BOLD = ('Arial', 12, 'bold')`
- `H1 = ('Arial', 14, 'bold')`

## 函数

### `build_demo(window: Window) -> None`
填充画廊窗口：
- 构建菜单栏（File / Edit / View / Help）。
- 顶部 header（含主题切换 `UComboBox` + "Follow system" `UCheckButton`）。
- 中部可滚动主体（Canvas + 自定义 `_ThemeCanvas` + `_ThemeScrollbar`）。
- 演示区段：Buttons（6 种 variant + Disabled）、Text Input（UEntry / UText）、Selection（UCheckButton / URadioButton / UComboBox）、Progress + Slider、Live Editor（UText）。
- 启用 `theme.follow_system(window, poll_interval_ms=2000)`。

### `_build_menu(window)` — 构建 UMenuBar。
### `_build_header(window)` — 构建顶部标题与主题选择器。
### `_build_theme_picker(parent, window) -> UFrame`
  - `UComboBox` 切换主题（选中后 `theme.set_theme(target, refresh_root=window)`）。
  - `UCheckButton` 控制 `theme.follow_system` / `theme.stop_following`。
  - 通过 `theme.on_change` 同步 UI。
### `_build_scrollable_body(window) -> (body, canvas)`
  返回内部 `UFrame` 与外部 `tk.Canvas`（`_ThemeCanvas`，构造后立刻 `config(bg=theme.BG_BASE)`）。
### `_section(parent, title, body)` — 标题 + 分割线。
### `_build_button_row(canvas, body)` / `_build_inputs(canvas, body)` / `_build_selection(canvas, body)` / `_build_progress_and_slider(canvas, body)` / `_build_text_demo(canvas, body)` — 各演示区段实现。

### `main() -> None`
创建 `Window(title='Uui  Component  Gallery')`，尺寸 `860x760+80+60`，调用 `build_demo` 并进入 `mainloop`。

## 内部类

### `_ThemeCanvas(tk.Canvas)`
- `_apply_theme()`：将画布背景设为 `theme.BG_BASE`。

### `_ThemeScrollbar(UScrollBar)`
滚动条槽背景与 `BG_BASE` 一致。
- 类属性 `_theme_key_trough = 'BG_BASE'`。
- `__init__(parent, **kwargs)`：默认 `troughcolor=theme.BG_BASE`，然后调用父类构造函数。