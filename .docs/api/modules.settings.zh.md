# `modules/settings/__init__.py`

源文件路径：`modules/settings/__init__.py`

`modules.settings` 包的公开入口。提供全局与项目设置、Schema 元信息与统一 `SettingsManager` 入口。

## 快速上手

```python
from modules.settings import SettingsManager, SettingsScope

manager = SettingsManager()                  # 默认加载全局设置
manager.attach_project("/path/to/proj")      # 附加项目

# 全局
manager.set(SettingsScope.GLOBAL, "ui.theme", "Light")
# 项目
manager.set(SettingsScope.PROJECT, "project.python_interpreter", "/usr/bin/python3")

# 生效值（项目优先，回退全局）
theme = manager.effective("ui.theme")
interpreter = manager.effective("project.python_interpreter")

# 持久化（也可使用 ``with SettingsManager() as m:`` 自动保存）
manager.save_all()
```

## 公开 API

- `SettingsManager` — 统一入口。
- `GlobalSettings` / `ProjectSettings` — 全局与项目设置实现。
- `Settings`（抽象基类）/ `JsonFileSettings` — JSON 文件存储基类。
- `SettingsSchema` / `SettingSpec` / `SettingValueType` / `SettingsScope` — Schema 与枚举。
- `SettingsChangeEvent` / `SettingsListener` — 事件载荷与回调类型。
- `GLOBAL_SCHEMA` / `PROJECT_SCHEMA` / `SCHEMA_BY_SCOPE` / `get_schema(scope)` — 默认 Schema。
- `GLOBAL_SPECS` / `PROJECT_SPECS` — 原始 spec 元组。
- `default_global_path()` / `default_project_path(root)` — 默认文件路径工具。
- `CURRENT_VERSION` — 存储格式版本号。

## `__all__`

```python
[
    "SettingsManager", "GlobalSettings", "ProjectSettings",
    "Settings", "JsonFileSettings",
    "SettingsSchema", "SettingSpec", "SettingValueType", "SettingsScope",
    "SettingsChangeEvent", "SettingsListener",
    "GLOBAL_SCHEMA", "PROJECT_SCHEMA",
    "GLOBAL_SPECS", "PROJECT_SPECS",
    "SCHEMA_BY_SCOPE", "get_schema",
    "default_global_path", "default_project_path",
    "CURRENT_VERSION",
]
```