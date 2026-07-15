# `modules/env_manager/__init__.py`

源文件路径：`modules/env_manager/__init__.py`

`modules.env_manager` 包的公开入口，重新导出环境管理核心类与全局工厂。

## 导出

- `PythonEnvironment` — 表示一个 Python 解释器环境的数据类。
- `EnvironmentManager` — 负责扫描/管理多个 Python 环境的核心类。
- `get_env_manager` — 全局单例工厂函数。

## `__all__`

```python
[
    "PythonEnvironment",
    "EnvironmentManager",
    "get_env_manager",
]
```