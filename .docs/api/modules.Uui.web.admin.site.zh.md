# `modules/Uui/web/admin/site.py`

源文件路径：`modules/Uui/web/admin/site.py`

`AdminSite` 单例 + 全局 `site`。

## 类

### `AlreadyRegistered(Exception)`
重复注册同一模型时抛。

### `NotRegistered(Exception)`
注销未注册模型时抛。

### `AdminSite`
模型类 → `ModelAdmin` 注册表。

构造 `__init__(name='admin')`：
- `name: str`
- `_registry: Dict[type, ModelAdmin]`
- `_actions: Dict[str, Any]`

方法：
- `register(model, admin_class=None) -> None`：默认 `admin_class = ModelAdmin`；重复注册抛 `AlreadyRegistered`；模型必须继承 `Uui.web.orm.Model`，否则抛 `TypeError`。
- `unregister(model) -> None`：未注册抛 `NotRegistered`。
- `is_registered(model) -> bool`
- `get_admin_for(model) -> Optional[ModelAdmin]`
- `registered_models`（属性）：已注册模型列表。
- `get_urls() -> List`：注册以下路由：
  - `''` → `views.index`
  - `logout/` → `views.logout_view`
  - `<app_label>/` → `views.app_index`
  - `<app_label>/<model_name>/` → `views.change_list`
  - `<app_label>/<model_name>/add/` → `views.add_form`
  - `<app_label>/<model_name>/<int:pk>/change/` → `views.change_form`
  - `<app_label>/<model_name>/<int:pk>/delete/` → `views.delete_view`
- `urls`（属性）：返回 `Include('Uui.web.admin.urls_module', namespace=self.name)`，供根 URLconf `include()` 挂载。
- `has_permission(request) -> bool`：要求 `request.user.is_active` 且 `is_staff`/`is_superuser`。

## 模块级单例

- `site = AdminSite()` — 进程级默认站点。