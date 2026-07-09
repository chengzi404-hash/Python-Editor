# Widgets API 参考文档

本文档介绍 `widgets` 包内提供的 UI 组件与主题系统。所有控件都继承自 `tkinter`，并支持运行时切换主题。

## 目录

- [主题系统 (theme)](#主题系统-theme)
  - [内置主题](#内置主题)
  - [颜色与字体常量](#颜色与字体常量)
  - [主题切换](#主题切换)
  - [跟随系统外观](#跟随系统外观)
- [通用约定](#通用约定)
- [控件列表](#控件列表)
  - [UFrame —— 容器](#uframe--容器)
  - [ULabel —— 文本标签](#ulabel--文本标签)
  - [UButton —— 按钮](#ubutton--按钮)
  - [UEntry —— 单行输入框](#uentry--单行输入框)
  - [UText —— 多行文本框](#utext--多行文本框)
  - [UCheckButton —— 复选框](#ucheckbutton--复选框)
  - [URadioButton —— 单选框](#uradiobutton--单选框)
  - [UComboBox —— 下拉选择](#ucombobox--下拉选择)
  - [UProgressBar —— 进度条](#uprogressbar--进度条)
  - [USlider —— 滑动条](#uslider--滑动条)
  - [UMenu / UMenuBar —— 菜单栏与菜单](#umenu--umenubar--菜单栏与菜单)
  - [UEditorSuggestion / CompletionItem —— 代码补全弹出框](#ueditorsuggestion--completionitem--代码补全弹出框)

---

## 主题系统 (theme)

`theme` 模块负责管理颜色、字体以及主题切换。控件内部统一通过 `from . import theme` 获取当前主题色，避免硬编码颜色。

### 内置主题

| 类名                  | `name` 属性     | 说明             |
| --------------------- | --------------- | ---------------- |
| `theme.DarkTheme`     | `"Dark"`        | 默认深色主题     |
| `theme.LightTheme`    | `"Light"`       | 浅色主题         |
| `theme.SolarizedDarkTheme` | `"Solarized Dark"` | Solarized 深色变体 |

### 颜色与字体常量

通过 `theme.<常量名>` 可访问当前主题的颜色和字体。常用常量如下：

- 背景色：`BG_TITLE`、`BG_BASE`、`BG_PANEL`、`BG_RAISED`、`BG_HOVER`、`BG_ACTIVE`、`BG_INPUT`、`BG_DROPDOWN`
- 前景色：`FG_PRIMARY`、`FG_SECONDARY`、`FG_TERTIARY`、`FG_DISABLED`
- 边框：`BORDER`、`BORDER_STRONG`、`BORDER_FOCUS`
- 强调色：`RED`、`YELLOW`、`GREEN`、`BLUE`、`PURPLE`（`RED`/`YELLOW`/`GREEN`/`BLUE` 还提供对应的 `_HOVER`、`_DARK` 变体）
- 字体：`TITLE_FONT`、`MENU_FONT`、`LABEL_FONT`、`LABEL_FONT_BOLD`、`LABEL_FONT_SMALL`、`BUTTON_FONT`、`ICON_FONT`、`MONO_FONT`

> 由于 `theme` 模块使用了 `__getattr__`，直接访问的常量始终是当前主题的值；切换主题后访问会得到新的颜色。

### 主题切换

```python
from widgets import theme

# 获取当前主题对象
cur = theme.current()

# 列出所有可用主题
for t in theme.available():
    print(t.name)

# 按名字获取主题
dark = theme.by_name('Dark')

# 切换主题（需要传入根控件以刷新现有控件）
theme.set_theme(dark, refresh_root=root)
```

- `theme.available() -> list[Theme]`：返回所有内置主题实例。
- `theme.by_name(name: str) -> Theme | None`：根据 `name` 属性查找主题。
- `theme.current() -> Theme`：返回当前正在使用的主题。
- `theme.set_theme(theme_obj, *, refresh_root=None)`：切换主题。若提供 `refresh_root`，会递归调用每个控件的 `_apply_theme()` 以应用新外观；同时触发通过 `on_change()` 注册的回调。

### 监听主题变化

```python
def on_theme_changed(new_theme):
    print('主题已切换为', new_theme.name)

theme.on_change(on_theme_changed)
theme.off_change(on_theme_changed)   # 取消监听
```

### 跟随系统外观

```python
theme.follow_system(root=None, mapping=None, poll_interval_ms=1500)
theme.stop_following()
```

- `follow_system(root=None, *, mapping=None, poll_interval_ms=1500)`：开始跟随操作系统外观。`root` 为 Tk 根控件，用于周期轮询；`mapping` 可自定义 `dark`/`light`/`default` 三种 OS 主题对应的内置主题名。返回是否在调用时立即应用了主题。
- `stop_following()`：停止轮询。

默认映射（`mapping` 会与该默认映射合并，可只覆盖部分键）：

```python
FOLLOW_SYSTEM_THEME = {
    'dark':    'Dark',
    'light':   'Light',
    'default': 'Dark',
}
```

`theme.apply_theme_recursive(widget)`：手动遍历控件树并调用每个子控件的 `_apply_theme()`。自定义控件如需支持主题刷新，只需实现无参的 `_apply_theme()` 方法即可被自动发现。

---

## 通用约定

- 所有控件都接受 `parent` 作为第一个位置参数（父容器）。
- 大多数控件支持 `bg` 关键字参数覆盖背景色；若未指定，则使用 `theme` 中的颜色并在主题切换时自动刷新。
- 数值类控件（如 `UProgressBar`、`USlider`）提供 `get()` / `set()` 方法。
- 状态字符串 `'normal'` / `'disabled'` 在多个控件中通用。
- `config(**kwargs)` / `configure(**kwargs)` 可在控件创建后调整参数。

---

## 控件列表

### UFrame —— 容器

继承自 `tkinter.Frame`，用于按主题渲染的不同背景块。

**导入**：`from widgets import UFrame`

**构造**：

```python
UFrame(parent, variant='panel', bg_key=None, **kwargs)
```

| 参数      | 类型            | 默认值     | 说明                                                                 |
| --------- | --------------- | ---------- | -------------------------------------------------------------------- |
| `variant` | `str`           | `'panel'`  | 主题背景预设：`title` / `base` / `panel` / `raised` / `input`        |
| `bg_key`  | `str | None`    | `None`     | 若指定，则从 `theme.<bg_key>` 读取颜色（如 `'BG_BASE'`、`'BG_PANEL'`）|
| `**kwargs` | —              | —          | 透传给 `tk.Frame`，常包括 `bg`、`width`、`height`、`padx`、`pady` 等 |

**行为**：

- 若同时指定 `bg_key` 与 `bg`，优先使用 `bg_key`。
- `variant` 指定的预设会被主题切换自动刷新。

**示例**：

```python
panel = UFrame(root, variant='panel')
side  = UFrame(panel, variant='title', height=32)
```

---

### ULabel —— 文本标签

继承自 `tkinter.Label`，提供主题色文字。

**导入**：`from widgets import ULabel`

**构造**：

```python
ULabel(parent, text='', variant='primary', font=None, bg=None, **kwargs)
```

| 参数      | 类型      | 默认值       | 说明                                                                                                |
| --------- | --------- | ------------ | --------------------------------------------------------------------------------------------------- |
| `text`    | `str`     | `''`         | 显示文本                                                                                            |
| `variant` | `str`     | `'primary'`  | 前景色预设：`primary` / `secondary` / `tertiary` / `disabled` / `blue` / `red` / `green` / `yellow` |
| `font`    | `tuple|None` | `None`    | 字体；缺省时使用 `theme.LABEL_FONT`                                                                 |
| `bg`      | `str|None` | `None`     | 背景色；未指定时尝试继承父容器背景                                                                  |
| `**kwargs` | —        | —            | 透传给 `tk.Label`                                                                                   |

**示例**：

```python
ULabel(root, text='用户名')
ULabel(root, text='错误信息', variant='red')
```

---

### UButton —— 按钮

支持圆角、多色彩变体以及悬停/按下交互。继承自 `tkinter.Frame`，内部由 `tk.Canvas` 绘制。

**导入**：`from widgets import UButton`

**构造**：

```python
UButton(parent, text='', command=None, variant='default',
        width=96, height=28, radius=6,
        font=None, state='normal', **kwargs)
```

| 参数      | 类型            | 默认值        | 说明                                                                                                              |
| --------- | --------------- | ------------- | ----------------------------------------------------------------------------------------------------------------- |
| `text`    | `str`           | `''`          | 按钮文字                                                                                                          |
| `command` | `Callable|None` | `None`        | 点击回调，无参                                                                                                    |
| `variant` | `str`           | `'default'`   | 颜色变体：`default` / `primary` / `success` / `danger` / `warning` / `ghost`                                      |
| `width`   | `int`           | `96`          | 控件宽度（像素）                                                                                                  |
| `height`  | `int`           | `28`          | 控件高度（像素）                                                                                                  |
| `radius`  | `int`           | `6`           | 圆角半径                                                                                                          |
| `font`    | `tuple|None`    | `None`        | 字体；缺省使用 `theme.BUTTON_FONT`                                                                                |
| `state`   | `str`           | `'normal'`    | `'normal'` 或 `'disabled'`                                                                                        |
| `**kwargs` | —              | —             | 透传给父 `tk.Frame`（如 `bg`）                                                                                    |

**方法**：

- `config(text=..., command=..., state=..., bg=..., **kwargs)` / `configure(...)`：动态修改属性。
- `_apply_theme()`：主题切换时被自动调用。

**示例**：

```python
UButton(root, text='保存', variant='primary', command=on_save)
UButton(root, text='取消', variant='ghost')
UButton(root, text='禁用', state='disabled')
```

---

### UEntry —— 单行输入框

带占位符与焦点高亮的单行文本输入控件。继承自 `tkinter.Frame`，内部使用 `tk.Entry`。

**导入**：`from widgets import UEntry`

**构造**：

```python
UEntry(parent, textvariable=None, placeholder='', width=20, show='', **kwargs)
```

| 参数            | 类型                | 默认值   | 说明                                                       |
| --------------- | ------------------- | -------- | ---------------------------------------------------------- |
| `textvariable`  | `tk.StringVar|None` | `None`   | 双向绑定的 `StringVar`                                     |
| `placeholder`   | `str`               | `''`     | 占位文本（仅在值为空时显示）                               |
| `width`         | `int`               | `20`     | 输入框字符宽度                                             |
| `show`          | `str`               | `''`     | 密码模式（如 `'*'`）；运行时可通过 `config(show=...)` 修改 |
| `**kwargs`      | —                   | —        | 透传给父 `tk.Frame`                                        |

**方法**：

- `get() -> str`：返回当前输入文本；若当前显示的是占位符则返回空串。
- `set(value: str)`：写入文本（会自动清除占位符状态）。
- `config(state=..., bg=..., show=..., **kwargs)` / `configure(...)`

**示例**：

```python
var = tk.StringVar()
e = UEntry(root, textvariable=var, placeholder='请输入用户名')
pwd = UEntry(root, show='*', placeholder='密码')
print(var.get())
```

---

### UText —— 多行文本框

带垂直滚动条的多行编辑器，支持撤销。继承自 `tkinter.Frame`，内部为 `tk.Text + tk.Scrollbar`。

**导入**：`from widgets import UText`

**构造**：

```python
UText(parent, width=40, height=10, wrap='word', font=None,
      show_line_numbers=False, **kwargs)
```

| 参数                | 类型          | 默认值    | 说明                                                                  |
| ------------------- | ------------- | --------- | --------------------------------------------------------------------- |
| `width`             | `int`         | `40`      | 文本区宽度（字符数）                                                  |
| `height`            | `int`         | `10`      | 文本区高度（行数）                                                    |
| `wrap`              | `str`         | `'word'`  | 换行模式：`'char'` / `'word'` / `'none'`                              |
| `font`              | `tuple|None`  | `None`    | 字体；缺省使用 `theme.MONO_FONT`                                      |
| `show_line_numbers` | `bool`        | `False`   | 是否在文本区左侧显示行号（基于 `LineNumberCanvas` / Canvas 实现）；当前行号会用 `theme.FG_PRIMARY`，其他行用 `theme.FG_TERTIARY`，宽度按最大行号位数自动留白 |
| `**kwargs`          | —             | —         | 透传给父 `tk.Frame`                                                   |

**方法**：

- `get(*args)`：与 `tk.Text.get` 一致。
- `insert(*args)`：与 `tk.Text.insert` 一致。
- `delete(*args)`：与 `tk.Text.delete` 一致。
- `clear()`：清空全部内容。
- `see(index)`：滚动到指定位置。
- `config(state=..., **kwargs)`：可设置 `'normal'` / `'disabled'`。

**示例**：

```python
t = UText(root, height=8)
t.insert('1.0', 'Hello, UUI\n')
print(t.get('1.0', tk.END))
t.clear()

# 带行号的编辑器
t2 = UText(root, height=8, show_line_numbers=True)
```

---

### LineNumberCanvas —— 基于 Canvas 的代码行号栏

`UText` 在 `show_line_numbers=True` 时内部使用的行号控件，通常无需直接调用；在需要自己挂到其他 `tk.Text` 上时可单独使用。继承自 `tkinter.Frame`，内部为 `tk.Canvas`。

**导入**：`from widgets import LineNumberCanvas`

**构造**：

```python
LineNumberCanvas(text, pad_x=6, min_width=28, **kwargs)
```

| 参数        | 类型        | 默认值 | 说明                                                                                          |
| ----------- | ----------- | ------ | --------------------------------------------------------------------------------------------- |
| `text`      | `tk.Text`   | —      | 被观察的 `tk.Text`；构造时会接管其 `yscrollcommand` 并保留原回调转发                              |
| `pad_x`     | `int`       | `6`    | 行号文字与分隔线之间的水平内边距（像素）                                                       |
| `min_width` | `int`       | `28`   | gutter 最小宽度（像素）；防止文件为空时缩成 0                                                  |
| `**kwargs`  | —           | —      | 透传给父 `tk.Frame`                                                                            |

**行为**：

- 行号宽度按当前最大行号位数自动留白（多 1 位按 2 位预留，避免加 1 行后 gutter 突然变宽推动光标）。
- 文本变更（`<<Modified>>`）、光标移动（`KeyRelease` / `ButtonRelease`）、滚动（`yscrollcommand`）以及 text 几何变化（`Configure`）都会触发重画，重画经过 `after_idle` 防抖。
- 当前行号用 `theme.FG_PRIMARY` 高亮，其他行用 `theme.FG_TERTIARY`。
- 鼠标滚轮在 gutter 上时转发给 text，与在 text 上滚动一致。
- 主题切换通过 `_apply_theme()` 重画，背景跟随 `theme.BG_INPUT`。

---

### UCheckButton —— 复选框

自定义绘制方框与勾选的复选控件。继承自 `tkinter.Frame`。

**导入**：`from widgets import UCheckButton`

**构造**：

```python
UCheckButton(parent, text='', variable=None, command=None,
             external_toggle=None, **kwargs)
```

| 参数             | 类型                | 默认值    | 说明                                                              |
| ---------------- | ------------------- | --------- | ----------------------------------------------------------------- |
| `text`           | `str`               | `''`      | 文本标签                                                          |
| `variable`       | `tk.BooleanVar|None` | `None`   | 状态变量；缺省时内部创建一个                                       |
| `command`        | `Callable|None`     | `None`    | 切换后回调，无参                                                  |
| `external_toggle` | `Callable|None`   | `None`    | 若提供，点击时只调用此函数而不再内部切换（用于自定义状态机）       |
| `**kwargs`       | —                   | —         | 透传给父 `tk.Frame`                                               |

**方法**：

- `get() -> bool`：返回当前勾选状态。
- `set(value: bool)`：设置状态。

**示例**：

```python
agree = tk.BooleanVar()
cb = UCheckButton(root, text='同意条款', variable=agree)
print(agree.get())
```

---

### URadioButton —— 单选框

自定义绘制圆形与圆点的单选控件，必须与同组的 `variable` 配合使用。

**导入**：`from widgets import URadioButton`

**构造**：

```python
URadioButton(parent, text='', value=None, variable=None,
             command=None, external_toggle=None, **kwargs)
```

| 参数             | 类型                | 默认值    | 说明                                                              |
| ---------------- | ------------------- | --------- | ----------------------------------------------------------------- |
| `text`           | `str`               | `''`      | 文本标签                                                          |
| `value`          | `Any`               | `None`    | 该选项对应的值；写入 `variable` 时被转换为 `str`                  |
| `variable`       | `tk.StringVar|None` | `None`    | 组内共享的状态变量                                                |
| `command`        | `Callable|None`     | `None`    | 选中时回调，无参                                                  |
| `external_toggle` | `Callable|None`   | `None`    | 若提供，点击时只调用此函数而不修改 `variable`                     |
| `**kwargs`       | —                   | —         | 透传给父 `tk.Frame`                                               |

**方法**：

- `get()`：返回当前 `variable` 的值。

**示例**：

```python
choice = tk.StringVar(value='a')
URadioButton(root, text='选项 A', value='a', variable=choice)
URadioButton(root, text='选项 B', value='b', variable=choice)
print(choice.get())
```

---

### UComboBox —— 下拉选择

弹出式下拉选择控件，自动检测屏幕边界。继承自 `tkinter.Frame`。

**导入**：`from widgets import UComboBox`

**构造**：

```python
UComboBox(parent, values=(), textvariable=None, command=None,
          select_first=True, **kwargs)
```

| 参数            | 类型                | 默认值    | 说明                                                                                |
| --------------- | ------------------- | --------- | ----------------------------------------------------------------------------------- |
| `values`        | `Iterable`          | `()`      | 可选项集合                                                                          |
| `textvariable`  | `tk.StringVar|None` | `None`    | 双向绑定的字符串变量                                                                |
| `command`       | `Callable|None`     | `None`    | 选择某项后的回调，参数为所选值                                                      |
| `select_first`  | `bool`              | `True`    | 若为 `True` 且变量为空，自动选中第一项                                              |
| `**kwargs`      | —                   | —         | 透传给父 `tk.Frame`                                                                 |

**方法**：

- `get() -> str`：返回当前选中值。
- `set(value)`：设置选中值。
- `set_values(values)`：替换候选项；如新值不包含当前选择且 `select_first=True`，则回退到首项。

**示例**：

```python
def on_change(v):
    print('选择了', v)

cb = UComboBox(root, values=['A', 'B', 'C'], command=on_change)
cb.set_values(['X', 'Y', 'Z'])
```

---

### UProgressBar —— 进度条

纯 Canvas 实现的线性进度条。继承自 `tkinter.Canvas`。

**导入**：`from widgets import UProgressBar`

**构造**：

```python
UProgressBar(parent, maximum=100, value=0, height=6, color=None, **kwargs)
```

| 参数      | 类型          | 默认值     | 说明                                                       |
| --------- | ------------- | ---------- | ---------------------------------------------------------- |
| `maximum` | `int`         | `100`      | 最大值（进度 = `value / maximum`）                         |
| `value`   | `float`       | `0`        | 当前进度                                                   |
| `height`  | `int`         | `6`        | 进度条高度（像素）                                         |
| `color`   | `str|None`    | `None`     | 进度填充色；缺省使用 `theme.BLUE`                          |
| `**kwargs` | —           | —          | 透传给 `tk.Canvas`（如 `bg`、`width`）                     |

**方法**：

- `set(value: float)`：更新进度。
- `get() -> float`：返回当前进度值。
- `config(value=..., maximum=..., color=..., bg=..., **kwargs)` / `configure(...)`

**示例**：

```python
bar = UProgressBar(root, height=8)
for i in range(101):
    bar.set(i)
    root.update()
```

---

### USlider —— 滑动条

支持水平/垂直方向的自绘滑动条。继承自 `tkinter.Canvas`。

**导入**：`from widgets import USlider`

**构造**：

```python
USlider(parent, from_=0, to=100, value=None, orient='horizontal',
        command=None, show_value=False, **kwargs)
```

| 参数         | 类型             | 默认值         | 说明                                                       |
| ------------ | ---------------- | -------------- | ---------------------------------------------------------- |
| `from_`      | `float`          | `0`            | 最小值（关键字参数名固定为 `from_`）                       |
| `to`         | `float`          | `100`          | 最大值                                                     |
| `value`      | `float|None`     | `None`         | 初始值；缺省时取 `from_`                                   |
| `orient`     | `str`            | `'horizontal'` | `'horizontal'` 或 `'vertical'`                             |
| `command`    | `Callable|None`  | `None`         | 值变化时的回调，参数为当前值                               |
| `show_value` | `bool`           | `False`        | 是否在滑块上方绘制当前值（仅水平方向可见）                 |
| `**kwargs`   | —                | —              | 透传给 `tk.Canvas`（如 `bg`、`width`、`height`）           |

**方法**：

- `get() -> float`：返回当前值。
- `set(value: float)`：设置值，会自动夹紧到 `[from_, to]`，并在变化时调用 `command`。

**示例**：

```python
def on_slide(v):
    print(v)

s = USlider(root, from_=0, to=10, value=3, command=on_slide, show_value=True)
```

---

### UMenu / UMenuBar —— 菜单栏与菜单

`UMenuBar` 是一个顶部菜单栏容器；每个顶层项通过 `add_cascade(label)` 创建，并返回一个 `UMenu` 对象用于添加条目。

**导入**：`from widgets import UMenuBar, UMenu`

#### UMenuBar

**构造**：

```python
UMenuBar(parent, **kwargs)
```

| 参数       | 类型   | 默认值 | 说明                                                         |
| ---------- | ------ | ------ | ------------------------------------------------------------ |
| `bg`       | `str`  | `theme.BG_TITLE` | 菜单栏背景色                                       |
| `**kwargs` | —      | —      | 透传给 `tk.Frame`                                            |

**方法**：

- `add_cascade(label: str) -> UMenu`：添加一个顶层菜单项，返回对应的 `UMenu`。

#### UMenu

用于描述下拉菜单内容，本身不是 widget。

**方法**：

- `add_command(label: str, command: Callable | None = None, shortcut: str = '')`：添加普通菜单项。`shortcut` 显示在右侧（如 `'Ctrl+S'`）。
- `add_separator()`：添加分隔线。
- `add_checkbutton(label: str, variable: tk.BooleanVar | None = None, command: Callable | None = None, shortcut: str = '')`：添加复选项（带勾选标记）。
- `add_radiobutton(label: str, value, variable: tk.StringVar | None = None, command: Callable | None = None, shortcut: str = '')`：添加单选项。

**示例**：

```python
bar = UMenuBar(root)

file_menu = bar.add_cascade('文件')
file_menu.add_command('新建', command=on_new, shortcut='Ctrl+N')
file_menu.add_command('打开', command=on_open, shortcut='Ctrl+O')
file_menu.add_separator()
file_menu.add_command('退出', command=root.destroy)

view_menu = bar.add_cascade('视图')
debug = tk.BooleanVar()
view_menu.add_checkbutton('调试模式', variable=debug, command=on_toggle_debug)

mode = tk.StringVar(value='light')
view_menu.add_radiobutton('浅色', value='light', variable=mode)
view_menu.add_radiobutton('深色', value='dark',  variable=mode)
```

**交互行为**：

- 单击顶层菜单项或悬停其上即可展开下拉。
- 在下拉菜单外点击会自动关闭。
- 点击下拉项会自动关闭下拉，再触发回调。
- 主题切换后菜单栏与已展开的下拉会自动刷新颜色。

---

### UEditorSuggestion / CompletionItem —— 代码补全弹出框

`UEditorSuggestion` 是一个无边框的 `Toplevel` 弹出控件，用于展示代码补全、命令提示等可选项。`CompletionItem` 描述单个候选项。

**导入**：`from widgets import UEditorSuggestion, CompletionItem`

#### CompletionItem

```python
CompletionItem(label, detail='', description='', insert='', kind='')
```

| 参数          | 类型   | 默认值 | 说明                                                         |
| ------------- | ------ | ------ | ------------------------------------------------------------ |
| `label`       | `str`  | —      | 显示文本                                                     |
| `detail`      | `str`  | `''`   | 右侧补充信息（如类型、签名）                                 |
| `description` | `str`  | `''`   | 底部详情说明；非空时会展开详情区域                           |
| `insert`      | `str`  | `''`   | 确认后应插入的文本；为空时默认等于 `label`                   |
| `kind`        | `str`  | `''`   | 类别标记，当前仅作保留字段                                   |

#### UEditorSuggestion

**构造**：

```python
UEditorSuggestion(parent, items=(), on_select=None, *,
                  max_visible=8, show_detail=True,
                  show_description=True, grab_focus=False)
```

| 参数                | 类型                       | 默认值  | 说明                                                         |
| ------------------- | -------------------------- | ------- | ------------------------------------------------------------ |
| `parent`            | `tk.Widget`                | —       | 父控件；用于确定顶层窗口与坐标锚定                           |
| `items`             | `Iterable[Any]`            | `()`    | 初始候选项；可以是 `CompletionItem`、字符串或字典             |
| `on_select`         | `Callable[[CompletionItem], None] \| None` | `None`  | 确认选择后的回调                                             |
| `max_visible`       | `int`                      | `8`     | 列表区域最多同时显示的行数，超出时需要滚动                    |
| `show_detail`       | `bool`                     | `True`  | 是否显示 `detail` 列                                         |
| `show_description`  | `bool`                     | `True`  | 是否在底部显示 `description` 详情                            |
| `grab_focus`        | `bool`                     | `False` | 为 `True` 时弹出后抢占焦点，失焦自动隐藏                      |

**方法**：

- `show(items=None, *, x=None, y=None, attach_to=None, index='insert')`：弹出窗口。`attach_to` 可指定一个文本类控件，此时 `x`/`y` 会根据 `index` 的 `bbox` 自动计算。
- `hide()`：隐藏当前弹窗。
- `set_items(items)`：替换候选项，支持 `CompletionItem` / `str` / `dict` 的混合列表。
- `select_next()` / `select_prev()`：向下/向上移动选中项。
- `selected() -> CompletionItem | None`：返回当前选中的候选项。
- `move(x, y)`：重新定位并自动限制在屏幕范围内。
- `destroy()`：销毁窗口并取消主题监听。

**示例**：

```python
from widgets import UEditorSuggestion, CompletionItem

def on_select(item):
    text.insert('insert', item.insert)

items = [
    CompletionItem('print', detail='builtin', description='输出对象到控制台'),
    CompletionItem('range', detail='builtin', description='生成整数序列'),
    'sorted',  # 字符串会被包装为 CompletionItem
    {'label': 'len', 'detail': 'builtin'},
]

popup = UEditorSuggestion(root, items=items, on_select=on_select)
popup.show(attach_to=text_widget, index='insert')
```

**交互行为**：

- 同一时刻最多只有一个 `UEditorSuggestion` 实例处于可见状态；新的 `show()` 会自动隐藏上一个。
- 支持键盘导航：`Down` / `Up` 移动选中，`Return` / `Tab` 确认，`Escape` 隐藏。
- 在弹窗外点击会自动关闭。
- 主题切换后弹窗颜色会自动刷新。

---

## 自定义主题支持

实现一个新的主题只需继承 `theme.Theme` 并覆盖所需的颜色/字体常量，然后通过 `theme.set_theme(...)` 切换：

```python
from widgets import theme

class OceanTheme(theme.Theme):
    name = 'Ocean'
    BG_BASE = '#001f3f'
    BG_PANEL = '#003366'
    FG_PRIMARY = '#e0f7ff'
    BLUE = '#39cccc'
    # ... 覆盖其他常量

theme.set_theme(OceanTheme(), refresh_root=root)
```

若要让现有控件在主题切换后自动刷新，只需让自定义控件实现无参方法 `_apply_theme()`，并在该方法内重新读取 `theme.*` 常量并调用 `config(...)` 即可。`theme.apply_theme_recursive(root)` 会自动遍历整棵控件树并调用该方法。