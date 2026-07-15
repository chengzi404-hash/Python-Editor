# `modules/Uui/widgets/window.py`

源文件路径：`modules/Uui/widgets/window.py`

主窗口 `Window`，自带 macOS 风格标题栏（红黄绿圆点 + 拖动 + 最小化/最大化/关闭）。

## 模块常量

- `GWL_EXSTYLE = -20`、`WS_EX_APPWINDOW = 0x00040000`、`SW_SHOWNORMAL/SW_SHOWMAXIMIZED/SW_MINIMIZE` — Windows API 常量。
- `class WindowPlacement(ctypes.Structure)` — Windows `WINDOWPLACEMENT` 结构布局。

## 类

### `Window(tk.Tk)`
主题感知的主窗口。

构造 `__init__(screenName=None, baseName=None, className='Tk', useTk=True, sync=False, use=None, title='Uui Sample Window', title_font=None, debug=False, custom_titlebar=True)`：
- 调用 `tk.Tk.__init__` 并 `title(title)`。
- `custom_titlebar=False` 时直接返回（用系统默认标题栏）。
- 否则：调用 `_remove_title_bar()` 与 `_ensure_taskbar_button()`（Windows），构造 `_title_frame`、红黄绿圆点 `_dot_canvas`、`drag_offset_x/y` 等。
- `debug=True` 时绑定 `<Escape>` 到 `destroy`。

主要方法（基于源码前 199 行）：
- `_remove_title_bar()` — 调用 Windows API 隐藏标题栏。
- `_ensure_taskbar_button()` — 添加 `WS_EX_APPWINDOW` 扩展样式，确保任务栏图标可见。
- `start_move(event) / set_position(event)` — 自定义标题栏拖动。
- `_create_dot(x, color, hover_char, command)` — 创建一个红/黄/绿圆点及其悬浮字符（`-` / `+` / `x`）。
- `minimize() / maximize() / close()` — 自定义窗口按钮行为。