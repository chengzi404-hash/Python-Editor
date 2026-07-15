# `modules/Uui/web/admin/views.py`

源文件路径：`modules/Uui/web/admin/views.py`

admin 视图：全部用 `@staff_member_required` 装饰。

## 内部辅助

- `_site(request)`：从 `request._admin_site` 取站点，缺省回退到 `default_site`。
- `_require_staff(request)`：未通过 `site.has_permission(request)` 时抛 `Http403`。
- `_split_path(path) -> List[str]`：按 `/` 切分并去除空段。
- `_find_admin(request, parts)`：在 `parts` 解析 `app_label` / `model_name`，查找匹配的 `ModelAdmin`。

## 视图

- `index(request)` — 站点首页，按 `app_label` 分组列出已注册模型；渲染 `admin/index.html`。
- `app_index(request, app_label)` — 单个 app 的首页；空 app 抛 `Http404`。模板 `admin/app_index.html`。
- `logout_view(request)` — 清空 `request.session` 并 `redirect('/')`。
- `change_list(request, app_label, model_name)` — 列表页；支持 `q` 关键字搜索（按 `search_fields` 多个字段 `icontains`）与 `p` 分页参数；模板 `admin/change_list.html`。
- `add_form(request, app_label, model_name)` — 新增表单；`POST` 时调用 `_save_form`；模板 `admin/change_form.html`。
- `change_form(request, app_label, model_name, pk)` — 编辑表单；`POST` 时按 `_action` 字段决定 `save` 或重定向到删除页；模板同上。
- `delete_view(request, app_label, model_name, pk)` — 删除确认页；`POST` 时调用 `admin.delete_model` 并重定向到列表；模板 `admin/delete_confirmation.html`。

## 内部辅助

- `_save_form(request, admin, obj)`：从 `request.POST` 收集字段，校验必填；调用 `fld.to_python(raw)` 转换；最后 `admin.save_model(...)` 并重定向到 change 页。