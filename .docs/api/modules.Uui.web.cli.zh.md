# `modules/Uui/web/cli.py`

源文件路径：`modules/Uui/web/cli.py`

Uui.web 的命令行管理工具，仿 Django `manage.py`。

## 模块常量

- `SCAFFOLD_TEMPLATES = 'D:/Code/Uui/web/_scaffold'` — 项目脚手架模板来源。
- `PROJECT_LAYOUT: dict[str, str]` — 每个新项目要写入的文件 → 内容模板（`manage.py` / `config.py` / `urls.py` / `wsgi.py` / `asgi.py` / `requirements.txt` / `.gitignore` / `README.md` / `apps/home/{apps,models,views,urls}.py` / 模板与测试等）。

## 命令

- `cmd_new(args)` — 校验 name 为合法 Python 标识符，按 `PROJECT_LAYOUT` 创建项目文件。
- `cmd_runserver(args)` — 解析 `addr`，可选启动 HTTP/2（h2c 或 TLS+ALPN）；无 SSL 时若 `--http2` 会自动通过 `Uui.web.tls.ensure_dev_cert` 生成自签名证书。
- `cmd_serve(args)` — waitress 生产服务器；同样支持 HTTP/2。
- `cmd_shell(args)` — 启动带 `app` / `settings` 上下文的 Python REPL。
- `cmd_test(args)` — 调用 `python -m pytest -x -q [path]`。
- `cmd_collectstatic(args)` — 把 `settings.STATICFILES_DIRS` 中的文件复制到 `settings.STATIC_ROOT`。
- `cmd_bench(args)` — 用 100 个精确路径 + 1 个 `<name>` 模式对路由做 N 次请求基准；可选与 Flask 对比。
- `cmd_routes(args)` — 列出注册路由（exact 与 regex）。
- `cmd_migrate(args)` — 自动生成初始 migration（若没有）并通过 `MigrationEngine` 应用；可通过 `--apps-dir` 指定应用根目录。
- `cmd_showmigrations(args)` — 显示迁移状态。
- `cmd_makemigrations(args)` — 调用 `generate_migration(target_app, name)` 并写入 `<app>/migrations/<id>.json`。
- `cmd_createsuperuser(args)` — 交互式或通过 `--username/--password/--email` 创建/更新 superuser（自动 `is_staff`/`is_superuser`/`is_active`）。

## argparse

### `build_parser(prog='uui-web') -> argparse.ArgumentParser`
构建含子命令的 parser：`new` / `runserver` / `serve` / `shell` / `bench` / `routes` / `createsuperuser` / `makemigrations` / `migrate` / `showmigrations` / `test` / `collectstatic`。

## 入口

### `main(argv=None) -> int`
解析 argv 并调用对应 `cmd_*`；`KeyboardInterrupt` 返回 `130`。

### 内部辅助
- `_resolve_addr(addr) -> (host, port)`
- `_load_apps(settings)` — 遍历 `settings.INSTALLED_APPS` 并 import，确保模型注册到元类。
- `_web_prompt(question, default='', required=False)` / `_web_error` / `_web_warn`