# `modules/Uui/web/admin/options.py`

源文件路径：`modules/Uui/web/admin/options.py`

`ModelAdmin` — 模型在 admin UI 中的展示配置。

## 类

### `ModelAdmin`
描述某个 `Model` 在 admin 中的展示方式。可通过子类化设置类属性，或重写方法。

类属性：
- `list_display: List[str] = ['__str__']`
- `list_filter: List[str] = []`
- `search_fields: List[str] = []`
- `list_per_page: int = 25`
- `ordering: List[str] = []`
- `fields: Optional[List[str]] = None` — `None` 表示显示所有非自动字段。
- `exclude: List[str] = []`
- `readonly_fields: List[str] = []`
- `date_hierarchy: Optional[str] = None`
- `list_select_related: bool = False`
- `save_on_top: bool = False`

构造 `__init__(model, admin_site)`：
- 保存 `model`、`admin_site`、`opts = model._meta`、`app_label`、`model_name`、`verbose_name`、`verbose_name_plural`。

方法：
- `get_list_display(request) -> List[str]`
- `get_fields(request, obj=None) -> List[str]`：优先使用 `fields` 减去 `exclude`；否则遍历 `opts['fields']` 跳过 auto / 主键。
- `get_search_fields(request) -> List[str]`
- `get_ordering(request) -> List[str]`：默认使用主键。
- `get_list_per_page(request) -> int`
- `has_add_permission(request) / has_change_permission(request, obj=None) / has_delete_permission(request, obj=None) -> bool` — 默认 `True`。
- `get_queryset(request) -> QuerySet`
- `get_object(request, pk)` — `model.objects.get(id=pk)`；失败返回 `None`。
- `save_model(request, obj, form, change)` / `delete_model(request, obj)` — 默认调用 `obj.save()` / `obj.delete()`。
- `__repr__`：`<ModelAdmin <ModelName>>`