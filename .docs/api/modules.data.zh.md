# `modules/data.py`

源文件路径：`modules/data.py`

统一的运行时数据/缓存目录路径解析器。所有访问 `data/` 与 `cache/` 子目录的代码都应通过本模块暴露的函数取路径。

## 模块常量（内部）

- `_ROOT`：项目根 `data/` 目录的绝对路径。
- `_CACHE_ROOT`：项目根 `cache/` 目录的绝对路径。

## 函数

### `i18n_path(*parts: str) -> str`
拼接并返回 `data/i18n/<parts>` 的绝对路径。`*parts` 按顺序拼接为子路径段。

### `data_path(*parts: str) -> str`
拼接并返回 `data/<parts>` 的绝对路径。

### `data_dir() -> str`
返回 `data/` 根目录绝对路径。

### `suggestions_path(*parts: str) -> str`
拼接并返回 `data/suggestions/<parts>` 的绝对路径（用于代码补全/模板等数据文件）。

### `cache_dir() -> str`
返回 `cache/` 根目录绝对路径；若不存在会自动创建。

### `cache_path(*parts: str) -> str`
返回 `cache/<parts>` 的绝对路径。若 `parts` 非空，会确保父目录存在。

## `__all__`

```
["i18n_path", "data_path", "data_dir", "suggestions_path", "cache_dir", "cache_path"]
```