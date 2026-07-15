# `modules/Uui/web/auth/decorators.py`

源文件路径：`modules/Uui/web/auth/decorators.py`

视图保护装饰器。

## 函数

### `login_required(view_func)`
装饰器：未登录的 `GET` 请求重定向到 `/login/?next=<path>`；其它方法抛 `Http403('Authentication required')`。

### `permission_required(perm: str)`
装饰器工厂：要求 `request.user.is_authenticated` 且 `user.has_perm(perm)`；superuser 总通过。失败抛 `Http403('Permission denied: <perm>')`。

### `staff_member_required(view_func)`
装饰器：要求 `user.is_authenticated` 且 `user.is_staff or is_superuser`；失败抛 `Http403('Staff access required')`。

## 内部辅助

- `_q(s)`：URL quote，`safe=''`。