# `modules/Uui/web/admin/__init__.py`

源文件路径：`modules/Uui/web/admin/__init__.py`

`Uui.web.admin` 子包公开入口：自动 CRUD 管理 UI。

## 快速上手

```python
from Uui.web.admin import admin, site
from Uui.web.admin.options import ModelAdmin
from apps.blog.models import Post

@admin.register(Post)
class PostAdmin(ModelAdmin):
    list_display = ('id', 'title', 'published')
    list_filter = ('published',)
    search_fields = ('title',)
```

## 重新导出

- `AdminSite` — 管理站点类。
- `site` — 默认全局 `AdminSite` 实例。
- `ModelAdmin` — 模型管理配置类。
- `AlreadyRegistered` / `NotRegistered` — 注册异常。
- `views` — 内置视图（index / app_index / change_list / add_form / change_form / delete_view）。

## `__all__`

```python
['AdminSite', 'site', 'ModelAdmin', 'AlreadyRegistered', 'NotRegistered', 'views']
```