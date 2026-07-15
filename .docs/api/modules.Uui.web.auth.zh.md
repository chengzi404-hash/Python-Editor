# `modules/Uui/web/auth/__init__.py`

源文件路径：`modules/Uui/web/auth/__init__.py`

`Uui.web.auth` 子包公开入口：用户模型、会话、密码哈希、装饰器。

## 重新导出

- `password.make_password / check_password / needs_rehash`
- `users.User` / `AnonymousUser` / `get_anonymous_user` / `authenticate` / `get_user_by_id`
- `decorators.login_required` / `permission_required` / `staff_member_required`
- `session.Session` / `SessionStore` / `SessionMiddleware`

## `__all__`

```python
['make_password', 'check_password', 'needs_rehash',
 'User', 'AnonymousUser', 'get_anonymous_user', 'authenticate', 'get_user_by_id',
 'login_required', 'permission_required', 'staff_member_required',
 'Session', 'SessionStore', 'SessionMiddleware']
```