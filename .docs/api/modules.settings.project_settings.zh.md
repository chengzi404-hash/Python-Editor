# `modules/settings/project_settings.py`

源文件路径：`modules/settings/project_settings.py`

与项目目录绑定的设置。存储位置：`<project_root>/.pyeditor/settings.json`。构造时必须通过 `root=` 指定项目根目录。

## 模块常量

- `_HIDDEN_DIR = ".pyeditor"`
- `_FILE_NAME = "settings.json"`

## 函数

### `default_project_path(project_root: str) -> str`
返回项目设置文件应位于的路径：`<root>/.pyeditor/settings.json`。

## 类

### `ProjectSettings(JsonFileSettings)`
单个项目设置实例。构造参数：
- `root: str` — 项目根目录（必填，非空校验）。
- `path: Optional[str] = None` — 显式覆盖。
- `auto_load: bool = True`

构造时若未提供 `path` 且 `auto_load=True`，会立刻解析默认路径以加载已存在的 `settings.json`。

属性：
- `root: str` — `os.path.abspath(root)`。

方法：
- `_resolve_path() -> str`：返回 `default_project_path(self._root)`。
- `project_name() -> str` — 返回 `project.name`（非空时）或目录名/根目录。

## `__all__`

```python
["ProjectSettings", "default_project_path", "PROJECT_SPECS", "PROJECT_SCHEMA"]
```