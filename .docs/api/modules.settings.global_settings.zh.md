# `modules/settings/global_settings.py`

源文件路径：`modules/settings/global_settings.py`

跨项目共享的全局设置。默认存储位置：
- Windows — `%APPDATA%/PythonEditor/settings.json`（若 `APPDATA` 未设置则回退到 `~/PythonEditor/settings.json`）。
- macOS — `~/Library/Application Support/PythonEditor/settings.json`。
- Linux — `$XDG_CONFIG_HOME/PythonEditor/settings.json`（回退到 `~/.config/PythonEditor/settings.json`）。

可通过 `path=` 显式覆盖（测试场景）。

## 模块常量

- `_APP_NAME = "PythonEditor"`
- `_FILE_NAME = "settings.json"`

## 函数

### `default_global_path() -> str`
返回默认的全局设置文件路径（按平台策略）。

## 类

### `GlobalSettings(JsonFileSettings)`
跨项目共享的全局设置实例。构造参数：
- `path: Optional[str] = None` — 显式覆盖路径。
- `auto_load: bool = True` — 构造时是否自动 `load()`。

方法：
- `_resolve_path() -> str`：返回 `default_global_path()`。

## `__all__`

```python
["GlobalSettings", "default_global_path", "GLOBAL_SPECS", "GLOBAL_SCHEMA"]
```