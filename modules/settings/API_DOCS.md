# `modules.settings` — 统一设置接口 API 文档

> 适用于 **Python Editor** 项目。本模块提供"**全局设置** + **项目设置**"两层
> 作用域的统一读写接口，并附带可视化的设置对话框封装。

---

## 1. 模块概览

```
modules/settings/
├── __init__.py            # 公开 API
├── base.py                # 抽象基类: Settings / SettingSpec / SettingsScope ...
├── schema.py              # 默认 GLOBAL_SCHEMA / PROJECT_SCHEMA
├── storage.py             # JsonFileSettings (JSON 文件持久化基类)
├── global_settings.py     # GlobalSettings
├── project_settings.py    # ProjectSettings
├── manager.py             # SettingsManager (统一对外入口)
├── widgets.py             # 可视化 UI: USettingPanel / UProjectSettingsWindow
└── API_DOCS.md            # 本文档
```

### 关键设计原则

* **作用域分离**: `SettingsScope.GLOBAL` / `SettingsScope.PROJECT`，互不污染。
* **优先级合并**: `effective()` 实现"项目覆盖全局 → 默认值"的解析链。
* **类型安全**: 任何写入都通过 `SettingSpec.validate()` 做类型与边界校验。
* **线程安全**: 内部使用 `RLock`，允许多线程并发读写。
* **持久化原子性**: 先写临时文件再 `os.replace`，避免半写状态。
* **UI 无关**: 核心 API 不依赖 tkinter，可被测试 / CLI / 后台任务安全使用。

---

## 2. 快速上手

```python
from modules.settings import SettingsManager, SettingsScope

# 1) 创建管理器(自动加载全局默认路径)
manager = SettingsManager()

# 2) 修改全局设置
manager.set(SettingsScope.GLOBAL, "ui.theme", "Light")
manager.set(SettingsScope.GLOBAL, "editor.tab_size", 2)

# 3) 附加项目
project = manager.attach_project("/path/to/my_project")
project.set("project.python_interpreter", "/usr/bin/python3")

# 4) 读取"生效值"(项目优先, 否则全局)
theme       = manager.effective("ui.theme")                   # -> 'Light'
interpreter = manager.effective("project.python_interpreter") # -> '/usr/bin/python3'
tab_size    = manager.effective("editor.tab_size")            # -> 2

# 5) 持久化
manager.save_all()

# 6) 卸载项目
manager.detach_project()
```

也可配合 `with` 语句使用：

```python
with SettingsManager() as m:
    m.set(SettingsScope.GLOBAL, "ui.font_size", 12)
# 退出时自动 save_all()
```

---

## 3. 类型与 Schema

### 3.1 `SettingsScope`

| 成员 | 含义 |
| --- | --- |
| `GLOBAL` | 跨项目共享，存放在用户主目录下 |
| `PROJECT` | 与具体项目目录绑定，只对当前项目生效 |

### 3.2 `SettingValueType`

支持 7 种底层类型：

| 类型 | Python 类型 | UI 控件 |
| --- | --- | --- |
| `STRING` | `str` | 文本框 |
| `INTEGER` | `int` | 数值框（带边界校验） |
| `FLOAT` | `float` | 数值框 |
| `BOOLEAN` | `bool` | 复选框 |
| `CHOICE` | `str`（枚举） | 下拉框 |
| `LIST` | `list[str]` | 逗号分隔文本框 |
| `PATH` | `str`（路径） | 文本框 |

### 3.3 `SettingSpec`

每个设置项的元信息：

```python
SettingSpec(
    key="editor.tab_size",
    type=SettingValueType.INTEGER,
    default=4,
    label="Tab 宽度",
    description="按一次 Tab 键插入的空格数。",
    min=1, max=16,
    scope=SettingsScope.GLOBAL,  # 默认 GLOBAL
)
```

字段：

| 字段 | 必填 | 含义 |
| --- | --- | --- |
| `key` | ✅ | 作用域内唯一标识符，建议 `category.name` 形式 |
| `type` | ✅ | 底层值类型 |
| `default` | ✅ | 默认值 |
| `label` |  | UI 显示用标题 |
| `description` |  | UI 显示用说明 |
| `choices` |  | `CHOICE` 类型的候选项 |
| `min` / `max` |  | 数值类型的边界 |
| `scope` |  | 限定该 spec 只允许出现在哪种作用域 |

### 3.4 `SettingsSchema`

```python
from modules.settings import (
    GLOBAL_SCHEMA, PROJECT_SCHEMA, SCHEMA_BY_SCOPE, get_schema
)

schema = GLOBAL_SCHEMA
spec = schema.get("editor.tab_size")
for spec in schema:
    print(spec.key, spec.type, spec.default)
```

---

## 4. `Settings` 抽象类

所有设置实例（`GlobalSettings` / `ProjectSettings`）都实现以下 API：

| 方法 | 行为 |
| --- | --- |
| `get(key, default=None)` | 读取（未定义返回 schema 默认值或 `default`） |
| `set(key, value)` | 写入（触发类型校验 + 事件回调） |
| `has(key)` | 是否被显式赋值 |
| `all()` | 全部键（缺失键用 schema 默认填充） |
| `defined()` | 仅返回显式赋值过的键值 |
| `reset(key=None)` | 重置单个键或全部 |
| `save()` | 落盘到 JSON 文件 |
| `load()` | 从磁盘重新载入 |
| `add_listener(cb)` / `remove_listener(cb)` | 订阅变更事件 |
| `spec(key)` | 返回键对应的 `SettingSpec` |

事件签名：

```python
def on_change(event: SettingsChangeEvent) -> None: ...

# event.scope: SettingsScope
# event.key  : str | None     # None 表示批量重置
# event.old  : Any            # 旧值(批量时为整个 old snapshot dict)
# event.new  : Any            # 新值(批量时为整个 new snapshot dict)
```

---

## 5. `SettingsManager` 统一接口

| 方法 | 行为 |
| --- | --- |
| `global_settings` | 返回 `GlobalSettings` 实例 |
| `project_settings` | 返回当前 `ProjectSettings` 或 `None` |
| `project_root` | 返回当前项目根目录或 `None` |
| `attach_project(root)` | 挂载项目根目录 |
| `detach_project()` | 卸载并保存当前项目 |
| `get(scope, key, default=None)` | 在指定作用域上读取 |
| `set(scope, key, value)` | 在指定作用域上写入 |
| `reset(scope, key=None)` | 重置 |
| `effective(key, default=None)` | 项目优先回退全局的合并值 |
| `global_all()` / `project_all()` / `effective_all()` | 字典视图 |
| `add_listener(cb)` / `remove_listener(cb)` | 监听两侧变更 |
| `save_all()` / `reload_all()` | 整体持久化 |
| `__enter__` / `__exit__` | 上下文（退出时自动 save_all） |

### 5.1 优先级合并示例

```python
manager.set(SettingsScope.GLOBAL, "ui.font_size", 11)
manager.attach_project("/p")
manager.set(SettingsScope.PROJECT, "ui.font_size", 14)

assert manager.effective("ui.font_size") == 14   # 项目覆盖
assert manager.global_settings.get("ui.font_size") == 11
```

---

## 6. 默认 Schema

### 6.1 全局设置 (`GLOBAL_SCHEMA`)

涵盖 UI 主题 / 字体 / Tab 宽度 / 自动保存 / 补全 / 检查器 / 运行 / 启动 等
约 20 项设置。

### 6.2 项目设置 (`PROJECT_SCHEMA`)

涵盖 Python / C / C++ 解释器与编译器、入口文件、检查器列表、忽略项、
排除路径、项目级 Tab 覆盖、项目元信息等约 11 项设置。

如需新增设置项，可直接编辑 `modules/settings/schema.py`：

```python
GLOBAL_SPECS = GLOBAL_SPECS + (
    SettingSpec(
        key="my.new.setting",
        type=SettingValueType.STRING,
        default="",
        label="我的新设置",
        scope=SettingsScope.GLOBAL,
    ),
)
```

或在外部组装新的 `SettingsSchema` 并传入自定义 `Settings` 实例。

---

## 7. 持久化路径

### 7.1 全局设置

| 平台 | 默认路径 |
| --- | --- |
| Windows | `%APPDATA%\PythonEditor\settings.json` |
| macOS | `~/Library/Application Support/PythonEditor/settings.json` |
| Linux | `$XDG_CONFIG_HOME/PythonEditor/settings.json`（默认 `~/.config/PythonEditor/settings.json`） |

可通过 `GlobalSettings(path=...)` 显式覆盖（测试场景）。

### 7.2 项目设置

固定存放在 `<project_root>/.pyeditor/settings.json`。

`ProjectSettings(root, path=...)` 中的 `path` 参数同样允许覆盖。

---

## 8. 可视化 UI（widgets）

> 需要在有 Tk 的环境下使用。`widgets` 模块在 tkinter 不可用时会被设为
> `_UUI_AVAILABLE = False`，但 **不会** 影响核心 API 的导入。

### 8.1 `USettingPanel`

渲染某个作用域下的所有 `SettingSpec`：

```python
from modules.settings import SettingsManager, SettingsScope
from modules.settings.widgets import USettingPanel

manager = SettingsManager()
manager.attach_project("/path/to/proj")

panel = USettingPanel(parent_frame, settings=manager.global_settings)
panel.pack(fill="both", expand=True)

# ...用户操作...
panel.apply()    # 把 working 副本写回 settings
panel.revert()   # 丢弃改动并刷新控件
```

### 8.2 `UProjectSettingsWindow`

带顶部 **全局 / 项目 Tab** 与底部 `应用 / 保存 / 关闭 / 恢复默认` 按钮的完整窗口：

```python
from modules.settings import SettingsManager
from modules.settings.widgets import UProjectSettingsWindow

manager = SettingsManager()
manager.attach_project("/path/to/proj")

win = UProjectSettingsWindow(manager)
win.show()
```

行为约定：

* 切换 Tab 时丢弃当前未保存的修改并重新载入。
* `保存` 按钮：先把 working 写回 `Settings`，再调用 `manager.save_all()` 落盘。
* `恢复默认`：清空当前作用域的全部自定义值。

---

## 9. 与 main.py 集成示例

```python
from modules.settings import SettingsManager, SettingsScope

class CodeEditor:
    def __init__(self):
        # ...原有初始化...
        self._settings = SettingsManager()

    def _open_settings(self):
        from modules.settings.widgets import UProjectSettingsWindow
        UProjectSettingsWindow(self._settings, parent=self.window)

    def _run_code(self):
        timeout = self._settings.effective("runner.timeout_ms", 30000)
        interpreter = self._settings.effective("project.python_interpreter")
        cmd = [interpreter or sys.executable, temp_path]
        # ...
```

绑定快捷键：

```python
self.window.bind('<Control-,>', lambda e: self._open_settings())
```

---

## 10. 错误处理与约束

* `set()` 写入时类型不合法 → 抛 `ValueError`，**不修改**原值。
* `set()` 写入不存在的 key → 抛 `KeyError`。
* `JsonFileSettings` 在加载失败（损坏 / 不存在 / 权限）时会**静默回退**到默认空字典；
  写入失败会向上抛异常。
* 监听器回调若抛异常会被捕获，避免影响其他订阅者与主流程。

---

## 11. 测试覆盖

测试位于 `tests/settings/`，覆盖：

* `test_base.py` — `SettingSpec` 校验、`SettingsSchema`、`Settings` 抽象。
* `test_schema.py` — 默认 schema 的完整性。
* `test_storage.py` — JSON 文件读写 / 原子替换 / 错误容忍。
* `test_global_settings.py` — 跨平台路径解析与持久化。
* `test_project_settings.py` — 项目设置与 `root` 绑定。
* `test_manager.py` — 优先级合并 / 切换项目 / 监听器转发 / 上下文协议。
* `test_widgets.py` — `USettingPanel` / `UProjectSettingsWindow`
  （依赖真实 Tk 环境，会自动 skip）。