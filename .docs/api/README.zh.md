# API 参考目录

本目录为 `modules/` 下所有 Python 源文件的 API 参考，按 **模块路径** 平铺命名：

- 顶层文件 `modules/data.py` → `modules.data.md`
- 子包 `modules/settings/manager.py` → `modules.settings.manager.md`
- 子包的 `__init__.py` → `modules.<subpkg>.__init__.md`

> 文件名中含 `.` 的源文件（如 `modules/Uui/call/_command.py`）以 `.` 替换为下划线；前缀 `_` 与 `__` 直接保留。

## 顶层模块

- `modules.data` — 数据目录路径解析。
- `modules.charts.__init__` — 占位包。

## checker

检查器抽象与 Python 实现。

- `modules.checker.__init__` / `modules.checker.base` / `modules.checker.python`

## env_manager

Python 解释器环境管理（扫描、切换、包管理）。

- `modules.env_manager.__init__` / `modules.env_manager.manager`

## highlighter

语法高亮（专家 + 主题 + 库 DOM 缓存 + 市场）。

- `modules.highlighter.__init__`
- `modules.highlighter.base` / `ccpp` / `dom_cache`
- `modules.highlighter.json_expert` / `log_expert`
- `modules.highlighter.marketplace` / `python` / `themes`
- `modules.highlighter.xml_expert` / `yaml_expert`

## i18n / logging / runner

- `modules.i18n.__init__` / `translator` / `marketplace`
- `modules.logging.__init__` / `logger`
- `modules.runner.__init__` / `runner`

## plugins

- `modules.plugins.__init__` / `api` / `hooks`
- `modules.plugins.manager` / `marketplace` / `widgets`

## settings

- `modules.settings.__init__` / `base` / `storage`
- `modules.settings.global_settings` / `project_settings`
- `modules.settings.manager` / `schema` / `widgets`

## suggestion

- `modules.suggestion.__init__` / `base`
- `modules.suggestion.c` / `cpp` / `python`

## Uui（独立窗口小部件工具集）

- 根：`modules.Uui.__init__` / `cli` / `demo`
- call：`modules.Uui.call.__init__` / `_command` / `exceptions` / `git` / `npm` / `pip`
- tool：`modules.Uui.tool.__init__` / `designer`
- web 核心：`modules.Uui.web.__init__` / `app` / `cli` / `exceptions`
  - `modules.Uui.web.middleware` / `request` / `response` / `router`
  - `modules.Uui.web.server` / `server_http2` / `templates`
  - `modules.Uui.web.tls` / `tls_pyfallback` / `_smoke_http2`
- web admin：`modules.Uui.web.admin.__init__` / `options` / `site` / `urls` / `views`
- web auth：`modules.Uui.web.auth.__init__` / `decorators` / `password` / `session` / `users`
- web conf：`modules.Uui.web.conf.default_settings`
- web orm：`modules.Uui.web.orm.__init__` / `connection` / `fields` / `migration` / `models` / `query`
  - `modules.Uui.web.orm.backend.__init__` / `base` / `sqlite` / `mysql` / `postgresql` / `oracle`
- web testing：`modules.Uui.web.testing.__init__` / `client`
- widgets：`modules.Uui.widgets.__init__` / `window` / `theme` / `ui_theme_marketplace`
  - `modules.Uui.widgets.frame` / `label` / `button` / `entry` / `text`
  - `modules.Uui.widgets.checkbutton` / `radiobutton` / `combobox`
  - `modules.Uui.widgets.progressbar` / `slider` / `scrollbar`
  - `modules.Uui.widgets.menu` / `editor_suggestion` / `file_tree`
  - `modules.Uui.widgets.settings_nav` / `tree_canvas` / `line_number`
  - `modules.Uui.widgets.tab_bar` / `tab_view`
  - `modules.Uui.widgets.dialog` / `list_view` / `message_box`
  - `modules.Uui.widgets.sidebar` / `explorer_card` / `debug_card` / `git_card`
  - `modules.Uui.widgets.icons`
