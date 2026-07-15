# `modules/Uui/web/templates.py`

源文件路径：`modules/Uui/web/templates.py`

Uui.web 的模板引擎后端（Jinja2 是默认）。

## 模块常量

- `_BACKEND_CACHE: Dict[str, TemplateBackend]` — backend 单例缓存（`BACKEND_PATH -> instance`）。
- `DEFAULT_TEMPLATES`：默认 `TEMPLATES` 配置。

## 类

### `TemplateBackend`
抽象基类。
- `__init__(config, settings)`
- `render(template_name, context) -> str`（抽象）

### `Jinja2Backend(TemplateBackend)`
Jinja2 后端：每个项目共享一个 `jinja2.Environment`。

构造 `__init__(config, settings)`：
- 缺失 `jinja2` 包时抛 `ImproperlyConfigured('jinja2 is required for the default template backend; install via `pip install jinja2`')`。
- 调用 `_build_env(jinja2)`。

方法：
- `_build_env(jinja2) -> jinja2.Environment`
  - 默认 `autoescape=True` / `auto_reload=settings.DEBUG` / `cache_size=-1`。
  - 把 `STATIC_URL` 注入 `env.globals`。
  - 注册 `safe` filter（`jinja2.Markup` 旧 API 兼容）。

- `_build_loader(jinja2) -> jinja2.FileSystemLoader`
  - 合并 `config['DIRS']`（相对 `settings.PROJECT_ROOT`，默认 `os.getcwd()`）。
  - 遍历 `settings.INSTALLED_APPS`，把每个 app 的 `<APP_DIRS>` 子目录（默认 `templates`）加入搜索路径。
  - 加入 `Uui/web/templates/`。
  - 若全空，回退 `<root>/templates`。

- `render(template_name, context) -> str`
  - 找不到模板抛 `ImproperlyConfigured('Template not found: <name>')`。