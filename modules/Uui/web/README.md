# Uui.web API 参考

> 基于标准库构建的极简 Django 风格 WSGI 框架。

- **WSGI 为主**,附带极简的 **ASGI** 适配器
- **无 Web 框架依赖** —— 仅依赖 `regex`(更快的 `re`)和 `jinja2`(模板),生产环境可选 `waitress`
- **性能目标**:相对 Flask 0.6× 延迟(见 `web bench`)
- 内置 **ORM**(SQLite,Django 风格声明式模型 + QuerySet)
- **JSON 格式迁移** + 自动生成
- 内置 **Auth**(pbkdf2 密码哈希、会话、装饰器)
- 内置 **Admin** UI(已注册模型的自动 CRD)
- 进程内 **测试客户端**(Django 风格 `UTestClient`)

---

## 目录

1. [快速开始](#快速开始)
2. [公开 API 索引](#公开-api-索引)
3. [核心模块](#核心模块)
   - [`Uui.web` —— 顶层导出](#Uuiweb--顶层导出)
   - [`Uui.web.app` —— 应用对象](#Uuiwebapp--应用对象)
   - [`Uui.web.request` —— 请求对象](#Uuiwebrequest--请求对象)
   - [`Uui.web.response` —— 响应对象与工厂函数](#Uuiwebresponse--响应对象与工厂函数)
   - [`Uui.web.router` —— URL 路由](#Uuiwebrouter--url-路由)
   - [`Uui.web.middleware` —— 中间件](#Uuiwebmiddleware--中间件)
   - [`Uui.web.exceptions` —— 异常](#Uuiwebexceptions--异常)
4. [ORM](#orm)
5. [迁移](#迁移)
6. [认证与授权](#认证与授权)
7. [Admin 后台](#admin-后台)
8. [模板](#模板)
9. [静态文件](#静态文件)
10. [测试](#测试)
11. [CLI 命令](#cli-命令)
12. [配置项](#配置项)
13. [性能基准](#性能基准)
14. [架构](#架构)
15. [许可证](#许可证)

---

## 快速开始

```bash
python -m Uui.cli web new myapp
cd myapp
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

打开 <http://127.0.0.1:8000/> 与 <http://127.0.0.1:8000/admin/>。

---

## 公开 API 索引

```python
from Uui.web import (
    # 应用
    UWSGIApp, get_application, get_settings,
    # 请求 / 响应
    URequest, UResponse,
    # 响应工厂
    text, html, json, empty, redirect, file, error,
    # 路由
    URLRouter, path, include, clear_url_caches,
    # 异常
    UWebError, Http400, Http403, Http404, Http405, Http500, ImproperlyConfigured,
)
```

`__all__` 见 `web/__init__.py:26`。

---

## 核心模块

### `Uui.web` —— 顶层导出

模块入口在 `web/__init__.py:1`,统一对外暴露下列符号:

| 名称 | 类别 | 来源 |
|---|---|---|
| `UWSGIApp` | 类 | `web/app.py` |
| `get_application` | 函数 | `web/app.py` |
| `get_settings` | 函数 | `web/app.py` |
| `URequest` | 类 | `web/request.py` |
| `UResponse` | 类 | `web/response.py` |
| `text` `html` `json` `empty` `redirect` `file` `error` | 工厂函数 | `web/response.py` |
| `URLRouter` | 类 | `web/router.py` |
| `path` `include` `clear_url_caches` | 函数 | `web/router.py` |
| `UWebError` `Http400/403/404/405/500` `ImproperlyConfigured` | 异常类 | `web/exceptions.py` |

---

### `Uui.web.app` —— 应用对象

| 名称 | 签名 | 说明 |
|---|---|---|
| `UWSGIApp` | `class UWSGIApp(settings: str \| ModuleType)` | WSGI 可调用对象。`settings` 为配置模块名或模块对象。 |
| `get_application` | `(settings=None) -> UWSGIApp` | 进程内单例应用工厂。重复调用返回同一实例。 |
| `get_settings` | `(settings=None) -> ModuleType` | 加载并返回已合并默认值的配置模块。 |

**使用示例**

```python
from Uui.web import UWSGIApp
application = UWSGIApp('config')   # config.py 必须与 manage.py 同目录
```

---

### `Uui.web.request` —— 请求对象

`URequest` 包装一次 HTTP 请求,惰性解析 body / headers / form / json。

| 属性 / 方法 | 类型 | 说明 |
|---|---|---|
| `method` | `str` | HTTP 方法,大写。 |
| `path` | `str` | 请求路径(不含 query string)。 |
| `path_info` | `str` | 同 `path`。 |
| `query_string` | `str` | 原始查询字符串。 |
| `GET` | `dict[str, str]` | 解析后的查询参数(单值)。 |
| `POST` | `dict[str, str]` | `application/x-www-form-urlencoded` 表单。 |
| `headers` | `dict[str, str]` | 大小写不敏感的请求头。 |
| `body` | `bytes` | 原始请求体(惰性读取)。 |
| `json` | `Any` | 解析后的 JSON 体;若不是 JSON 抛出 `ValueError`。 |
| `cookies` | `dict[str, str]` | 已解析 cookie。 |
| `files` | `dict[str, Upload]` | `multipart/form-data` 上传文件。 |
| `META` | `dict` | 原始 WSGI environ。 |
| `resolver_match` | `ResolverMatch \| None` | 路由匹配结果,含 `route` / `args` / `kwargs` / `url_name`。 |
| `user` | `User \| AnonymousUser` | 由 `AuthenticationMiddleware` 注入。 |
| `session` | `Session` | 由 `SessionMiddleware` 注入。 |

**视图函数签名约定**

```python
def view(request: URequest, *args, **kwargs) -> UResponse: ...
```

URL 路由捕获到的参数(位置或命名)会作为额外位置/关键字参数传入。

---

### `Uui.web.response` —— 响应对象与工厂函数

#### `UResponse`

| 字段 | 类型 | 说明 |
|---|---|---|
| `status_code` | `int` | HTTP 状态码,默认 `200`。 |
| `headers` | `dict[str, str]` | 响应头。 |
| `body` | `bytes \| str` | 响应体(`text` 类响应内部编码为 UTF-8)。 |
| `content_type` | `str` | `Content-Type`,可单独设置。 |

#### 工厂函数

所有工厂返回 `UResponse`,可直接 `return` 自视图。

| 函数 | 签名 | 行为 |
|---|---|---|
| `text(body, status=200, headers=None)` | `(str, int, dict) -> UResponse` | `text/plain; charset=utf-8`。 |
| `html(body, status=200, headers=None)` | `(str, int, dict) -> UResponse` | `text/html; charset=utf-8`。 |
| `json(data, status=200, headers=None)` | `(Any, int, dict) -> UResponse` | `application/json`,默认 `ensure_ascii=False`,`allow_nan=False`。 |
| `empty(status=204, headers=None)` | `(int, dict) -> UResponse` | 空 body。 |
| `redirect(location, status=302, permanent=False)` | `(str, int, bool) -> UResponse` | `permanent=True` 时 `status=301`。 |
| `file(path, status=200, headers=None)` | `(str \| Path, int, dict) -> UResponse` | 流式读取文件,自动设置 `Content-Type` 与 `Content-Length`;支持 `Range`。 |
| `error(status, body=None)` | `(int, str \| None) -> UResponse` | 构造错误响应,正文可选。 |
| `render(request, template_name, context=None, status=200)` | `(URequest, str, dict, int) -> UResponse` | 渲染 Jinja2 模板(详见[模板](#模板))。 |

---

### `Uui.web.router` —— URL 路由

#### `path(route, view, name=None, kwargs=None)`

| 参数 | 类型 | 说明 |
|---|---|---|
| `route` | `str` | URL 模式。支持 `<int:id>`、`<str:name>`、`<slug:slug>`、`<uuid:uuid>` 转换器;默认 `<...>` 匹配除 `/` 外的任意段。 |
| `view` | `Callable` | 视图函数或 `include(...)` 返回的列表。 |
| `name` | `str \| None` | 用于反向解析 `reverse(name, **kwargs)`。 |
| `kwargs` | `dict \| None` | 注入到视图的额外关键字参数。 |

返回:`Route` 节点,可放入 `urlpatterns`。

#### `include(module_or_patterns, namespace=None)`

| 参数 | 类型 | 说明 |
|---|---|---|
| `module_or_patterns` | `str \| list[Route]` | `str` 时按模块名懒加载其 `urlpatterns`。 |
| `namespace` | `str \| None` | 命名空间前缀,反向解析时使用。 |

#### `URLRouter`

低层路由器,通常不需要直接使用 —— `path` / `include` 已经够用。可用于手动构建:

```python
from Uui.web import URLRouter, path
router = URLRouter([path('health', lambda r: text('ok'))])
```

#### `clear_url_caches()`

清理 `include('<module>')` 解析时缓存的 `urlpatterns`,在测试或动态重载场景下调用。

#### `reverse(name, **kwargs) -> str`

模块内提供的反向解析函数(在 `web/router.py` 中),根据注册的 `name` 与参数构造 URL。

---

### `Uui.web.middleware` —— 中间件

中间件是接受 `get_response` 并返回新可调用对象的纯函数。

| 中间件 | 说明 |
|---|---|
| `CommonMiddleware` | 通用处理(URL 规范化、`Content-Length` 补全等)。 |
| `StaticMiddleware` | `STATIC_URL` 下的文件直读;开发期无需 `collectstatic`。 |
| `SessionMiddleware` | 启用基于 DB 表的 session,向请求注入 `request.session`。 |
| `AuthenticationMiddleware` | 解析 session 后向请求注入 `request.user`。 |

**配置示例**

```python
MIDDLEWARE = [
    'Uui.web.middleware.CommonMiddleware',
    'Uui.web.auth.session.SessionMiddleware',
    'Uui.web.middleware.AuthenticationMiddleware',
    'Uui.web.middleware.StaticMiddleware',
]
```

注意顺序:`CommonMiddleware` → `SessionMiddleware` → `AuthenticationMiddleware` → `StaticMiddleware`,依赖关系不可调换。

---

### `Uui.web.exceptions` —— 异常

| 异常 | 状态码 | 说明 |
|---|---|---|
| `UWebError` | — | 基类。 |
| `Http400` | 400 | `BadRequest`。 |
| `Http403` | 403 | `PermissionDenied`。 |
| `Http404` | 404 | `NotFound`。 |
| `Http405` | 405 | `MethodNotAllowed`。 |
| `Http500` | 500 | `ServerError`。 |
| `ImproperlyConfigured` | — | 配置错误(启动期抛出)。 |

视图抛出上述任意异常,框架自动转为对应 HTTP 响应。

---

## ORM

模块:`Uui.web.orm`(`web/orm/__init__.py`)。

```python
from Uui.web.orm import Model, fields
```

### 字段

| 字段类 | 主要参数 |
|---|---|
| `CharField` | `max_length` |
| `TextField` | — |
| `IntegerField` | `null`, `default`, `primary_key` |
| `BigIntegerField` | 同上 |
| `FloatField` | 同上 |
| `BooleanField` | `default` |
| `DateTimeField` | `auto_now_add`, `auto_now` |
| `DateField` | 同 `DateTimeField` |
| `EmailField` | 同 `CharField` |
| `URLField` | 同 `CharField` |
| `UUIDField` | `default=uuid4` |
| `JSONField` | `default` |
| `ForeignKey` | `to`, `on_delete`, `related_name` |
| `OneToOneField` | 同上 |
| `ManyToManyField` | `to`, `related_name` |

### 模型

```python
class Post(Model):
    title = fields.CharField(max_length=200)
    body = fields.TextField()
    published = fields.BooleanField(default=False)
    created_at = fields.DateTimeField(auto_now_add=True)

    class Meta:
        app = 'blog'
```

- `Meta.app`:app 标识,迁移系统据此分组。
- 内部表名默认 `<app>_<ModelName 小写>`。

### `Model` 提供的接口

| 成员 | 说明 |
|---|---|
| `Model.objects` | `Manager` 实例。 |
| `Model._meta` | 字段元信息集合。 |
| `instance.save()` | 插入或更新(`pk` 是否为空决定)。 |
| `instance.delete()` | 按主键删除。 |
| `instance.refresh_from_db()` | 从 DB 重新加载字段。 |
| `instance.full_clean()` | 触发字段校验(`clean_field`)。 |

### `Manager` 与 `QuerySet`

| 方法 | 说明 |
|---|---|
| `create(**kwargs)` | 创建并保存。 |
| `get(**filters)` | 命中 1 行;0 行抛 `Model.DoesNotExist`,>1 行抛 `MultipleObjectsReturned`。 |
| `filter(**filters)` | 链式 QuerySet,惰性求值。 |
| `exclude(**filters)` | 反向 `filter`。 |
| `all()` | 全部记录。 |
| `order_by(*fields)` | 排序,字段前缀 `-` 表示降序。 |
| `count()` | 计数。 |
| `exists()` | 是否非空。 |
| `first()` / `last()` | 取首/末。 |
| `values(*fields)` | 以 `dict` 列表返回。 |
| `delete()` | 批量删除。 |

支持切片:

```python
Post.objects.filter(published=True).order_by('-created_at').all()[:20]
```

---

## 迁移

迁移以纯 JSON 文件存放在 `apps/<app>/migrations/000N_<name>.json`,便于 diff 与 review。

```bash
python manage.py makemigrations <app>   # 生成 apps/<app>/migrations/0001_initial.json
python manage.py migrate <app>          # 应用 pending 迁移
python manage.py showmigrations         # 列出迁移状态
```

**JSON 格式**

```json
{
  "id": "0001_initial",
  "app": "home",
  "dependencies": [],
  "operations": [
    {"op": "create_table", "name": "home_post", "columns": [
      {"name": "id", "type": "INTEGER", "primary_key": true, "auto": true},
      {"name": "title", "type": "VARCHAR(200)", "null": false}
    ]}
  ]
}
```

**支持的操作(op)**

| op | 字段 |
|---|---|
| `create_table` | `name`, `columns[]` |
| `drop_table` | `name` |
| `add_column` | `table`, `column` |
| `drop_column` | `table`, `name` |
| `rename_table` | `from`, `to` |

`column` 对象字段:`name`、`type`、`null`、`default`、`primary_key`、`auto`。

---

## 认证与授权

模块:`Uui.web.auth`。

### `User`

源:`web/auth/users.py`。

```python
from Uui.web.auth import User

u = User(username='alice', email='a@x.com')
u.set_password('s3cr3t')
u.save()
u.check_password('s3cr3t')   # True
```

| 方法 | 说明 |
|---|---|
| `set_password(raw)` | 使用 `pbkdf2_sha256`(320k 次迭代,仅 stdlib)计算哈希并写入 `password_hash`。 |
| `check_password(raw)` | 验证明文。 |
| `save()` | 插入或更新。 |
| `is_authenticated` / `is_anonymous` | 布尔属性。 |
| `is_staff` / `is_superuser` | 角色标记。 |

### 装饰器

源:`web/auth/decorators.py`。

| 装饰器 | 行为 |
|---|---|
| `@login_required` | 未登录:GET 重定向至 `/login/?next=...`;其他方法返回 403。 |
| `@permission_required('app.codename')` | 缺少指定权限返回 403。 |
| `@staff_member_required` | 非 `is_staff` 用户返回 403。 |

### Session

源:`web/auth/session.py`。

- `SessionMiddleware` 将 session 持久化到默认的 `auth_session` 表。
- `request.session` 提供 `dict` 风格 API(`session['key'] = value`,`session.get(k)` 等)。

### CLI

```bash
python manage.py createsuperuser [--username --password]
```

---

## Admin 后台

模块:`Uui.web.admin`。

### 注册

```python
# apps/blog/apps.py
from Uui.web.admin import site
from Uui.web.admin.options import ModelAdmin
from .models import Post

class PostAdmin(ModelAdmin):
    list_display = ('id', 'title', 'published', 'created_at')
    list_filter = ('published',)
    search_fields = ('title',)
    list_per_page = 25

site.register(Post, PostAdmin)
```

### `ModelAdmin` 选项

| 属性 | 默认 | 说明 |
|---|---|---|
| `list_display` | `('__str__',)` | 列表页列。 |
| `list_filter` | `()` | 右侧过滤器字段。 |
| `search_fields` | `()` | 模糊搜索字段。 |
| `list_per_page` | `25` | 每页条数。 |
| `list_display_links` | `list_display[0]` | 可点击进入详情页的列。 |
| `ordering` | `()` | 默认排序。 |
| `fields` | 全部字段 | 编辑表单字段集。 |

### URL 路由(由 `site` 自动注册)

| 路径 | 方法 | 用途 |
|---|---|---|
| `/admin/` | GET | 首页。 |
| `/admin/<app>/<model>/` | GET | 列表。 |
| `/admin/<app>/<model>/add/` | GET, POST | 新建。 |
| `/admin/<app>/<model>/<pk>/change/` | GET, POST | 修改。 |
| `/admin/<app>/<model>/<pk>/delete/` | GET, POST | 删除。 |

通过 `path('admin/', include('Uui.web.admin.urls'))` 挂载。

---

## 模板

```python
from Uui.web import response

def index(request):
    posts = Post.objects.filter(published=True).all()
    return response.render(request, 'blog/index.html', {'posts': posts})
```

`render()` 的查找顺序:

1. `settings.TEMPLATES[*].DIRS` 中配置的项目级目录。
2. 每个 `INSTALLED_APP` 下的 `<app>/templates/`。
3. 内置 `Uui/web/templates/`(Admin / 错误页)。

底层使用 `jinja2`,`render()` 内部由 `Jinja2Backend` 提供,源:`web/templates.py`。

---

## 静态文件

```python
MIDDLEWARE = [..., 'Uui.web.middleware.StaticMiddleware']
STATIC_URL = '/static/'
STATIC_ROOT = 'staticfiles'
STATICFILES_DIRS = ['static']
```

- 开发期:`StaticMiddleware` 直接在 `STATIC_URL` 下响应静态文件。
- 生产期:运行 `python manage.py collectstatic` 收集到 `STATIC_ROOT`,由外部服务器(或 `waitress` 配合)托管。

---

## 测试

源:`web/testing/client.py`。

```python
from Uui.web.testing import UTestClient

def test_home():
    c = UTestClient(settings='config')
    r = c.get('/')
    assert r.status_code == 200
    assert 'Hello' in r.text

def test_login():
    c = UTestClient(settings='config')
    r = c.login(username='alice', password='s3cr3t')
    assert r.status_code == 302
    r = c.get('/dashboard/')
    assert r.status_code == 200
```

`UTestClient` 主要方法:

| 方法 | 说明 |
|---|---|
| `get(path, **extra)` | 发起 GET,返回 `UResponse`。 |
| `post(path, data=None, **extra)` | 发起 POST;`data` 为 `dict` 时按 form 编码。 |
| `put(path, data=None, **extra)` | 发起 PUT。 |
| `delete(path, **extra)` | 发起 DELETE。 |
| `login(username, password)` | 登录并保留 cookie。 |
| `logout()` | 登出。 |

`UResponse` 字段:`status_code`、`headers`、`text`、`json()`、`cookies`。

```bash
python manage.py test tests/
```

---

## CLI 命令

通过 `python -m Uui.cli web <subcommand>` 调用。

| 子命令 | 参数 | 说明 |
|---|---|---|
| `new` | `<project>` | 脚手架生成项目。 |
| `runserver` | `[host:port]` | `wsgiref` 线程化开发服务器。 |
| `serve` | `[host:port]` | `waitress` 生产服务器。 |
| `shell` | — | 进入已加载应用上下文的 Python REPL。 |
| `makemigrations` | `[app]` | 生成迁移 JSON。 |
| `migrate` | `[app]` | 应用 pending 迁移。 |
| `showmigrations` | — | 列出迁移状态。 |
| `createsuperuser` | `[--username --password]` | 创建管理员。 |
| `collectstatic` | — | 收集静态文件。 |
| `test` | `[path]` | 运行 pytest。 |
| `bench` | `[--target flask]` | 性能基准。 |
| `routes` | — | 列出已注册的 URL patterns。 |

---

## 配置项

`config.py` 中常用项(默认值见 `web/conf/default_settings.py`):

| 项 | 默认 | 说明 |
|---|---|---|
| `DEBUG` | `False` | 调试模式。 |
| `SECRET_KEY` | — | 用于签名等;生产必须设置。 |
| `INSTALLED_APPS` | `[]` | 启用的 app 模块列表。 |
| `ROOT_URLCONF` | `'urls'` | 根路由模块名。 |
| `MIDDLEWARE` | `[]` | 中间件路径列表(顺序敏感)。 |
| `DATABASES.default` | — | DB 配置:`ENGINE='Uui.web.orm.backend.sqlite'`、`NAME='db.sqlite3'`。 |
| `TEMPLATES[0].DIRS` | `[]` | 项目级模板目录。 |
| `STATIC_URL` | `'/static/'` | 静态 URL 前缀。 |
| `STATIC_ROOT` | `'staticfiles'` | 收集目标目录。 |
| `STATICFILES_DIRS` | `[]` | 待收集的源目录。 |
| `ALLOWED_HOSTS` | `[]` | 允许的 Host 列表。 |

---

## 性能基准

```bash
python -m Uui.cli web bench
```

`web bench` 默认向 Uui.web 与 Flask 发起 2000 次 hello-world 请求并输出比率。

参考输出:

```
Uui.web:  N=2000  mean=0.605ms  p50=0.592ms  p99=0.800ms  rps=1653
Flask:    N=2000  mean=0.695ms  p50=0.680ms  p99=0.964ms  rps=1438

Uui.web / Flask ratio = 0.870  (INFO; target is < 0.6)
```

默认 `0.6×` 为延伸目标,`0.87×` 是基于 `wsgiref` 的基线;切换到 `waitress` 或 `web runserver` 后差距会进一步扩大。

---

## 架构

```
web/
├── __init__.py            # 公开 API
├── app.py                 # UWSGIApp, get_application, get_settings
├── asgi.py                # ASGI 适配器(仅 HTTP)
├── request.py             # URequest(惰性 body / headers / form / json)
├── response.py            # UResponse + text/html/json/redirect/file/error/render
├── router.py              # URLRouter + path / include / reverse
├── server.py              # wsgiref + waitress 服务器
├── middleware.py          # Common / Static / Session / Authentication
├── templates.py           # Jinja2Backend
├── exceptions.py          # Http400/403/404/405/500, ImproperlyConfigured
├── cli.py                 # 12 个子命令
├── conf/default_settings.py
├── testing/client.py      # UTestClient + UResponse
├── orm/                   # Model / Fields / QuerySet / SQLite backend
├── auth/                  # User / Session / password / decorators
└── admin/                 # site / ModelAdmin / views / templates
```

---

## 许可证

MIT(与 Uui 项目其余部分一致)。