# `modules/settings/schema.py`

源文件路径：`modules/settings/schema.py`

内置全局/项目 Schema 的集中定义。

## 模块常量

### `GLOBAL_SPECS: tuple`
全局设置项集合。包含以下键（key / 类型 / 默认 / 标签）：

- `ui.theme` — CHOICE，默认 `"Dark"`，候选 `("Dark", "Light", "Solarized Dark")`。
- `ui.highlight_theme` — CHOICE，默认 `"Default Dark"`。
- `ui.highlight_theme_marketplace` — BUTTON（打开主题市场）。
- `ui.font_family` — STRING，默认 `"Consolas"`。
- `ui.font_size` — INTEGER，默认 `10`，范围 `[6, 72]`。
- `ui.show_line_numbers` — BOOLEAN，默认 `True`。
- `editor.tab_size` — INTEGER，默认 `4`，范围 `[1, 16]`。
- `editor.use_spaces` — BOOLEAN，默认 `True`。
- `editor.auto_save` / `editor.auto_save_delay_ms` / `editor.auto_save_format` — 自动保存相关。
- `editor.word_wrap` — BOOLEAN，默认 `False`。
- `editor.highlight_delay_ms` / `editor.suggestion_delay_ms` — INTEGER，范围 `[0, 5000]`，默认 `300` / `200`。
- `editor.large_file_threshold_bytes` — INTEGER，默认 `5 MB`，上限 `1 GB`，`0` 关闭特性。
- `completion.enabled` / `completion.max_suggestions` / `completion.max_visible` / `completion.auto_trigger` / `completion.min_chars_before_trigger` — 补全相关。
- `checker.run_on_open` / `checker.run_on_save` / `checker.timeout_ms` — 检查相关（`timeout_ms` 默认 `30000`，范围 `[500, 600000]`）。
- `runner.timeout_ms` / `runner.clear_output_before_run` / `runner.stream_output` — 运行相关。
- `startup.restore_files` — BOOLEAN。
- `i18n.language` — CHOICE，候选来自 `AVAILABLE_LANGUAGES`（`("zh_CN", "en_US")`）。
- `i18n.language_marketplace` — BUTTON（打开语言市场）。
- `logging.enabled` / `logging.level` / `logging.file_enabled` / `logging.console_enabled` / `logging.max_bytes` / `logging.backup_count` — 日志相关。
- `plugins.marketplace` — BUTTON（打开插件市场）。

### `GLOBAL_SCHEMA = SettingsSchema(GLOBAL_SPECS)`

### `PROJECT_SPECS: tuple`
项目级设置项集合：

- `project.python_interpreter` — PATH，默认 `""`。
- `project.entry_point` — PATH，F5 入口文件。
- `project.c_compiler` / `project.cpp_compiler` — PATH，默认 `"gcc"` / `"g++"`。
- `checker.enabled` — LIST，默认 `["flake8", "pyright"]`。
- `checker.ignore` — LIST，默认 `[]`。
- `project.exclude_paths` — LIST，默认 `["__pycache__", ".git", ".venv", "venv", "build", "dist"]`。
- `project.tab_size` — INTEGER，范围 `[0, 16]`，`0` 表示回退到全局。
- `project.use_spaces` — BOOLEAN。
- `project.name` / `project.description` — STRING。

### `PROJECT_SCHEMA = SettingsSchema(PROJECT_SPECS)`

### `SCHEMA_BY_SCOPE: dict[SettingsScope, SettingsSchema]`
`{GLOBAL: GLOBAL_SCHEMA, PROJECT: PROJECT_SCHEMA}`。

## 函数

### `get_schema(scope: SettingsScope) -> SettingsSchema`
按作用域返回内置 Schema。

## `__all__`

```python
["GLOBAL_SPECS", "GLOBAL_SCHEMA", "PROJECT_SPECS", "PROJECT_SCHEMA",
 "SCHEMA_BY_SCOPE", "get_schema"]
```