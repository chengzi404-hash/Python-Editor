# `modules/Uui/web/auth/users.py`

源文件路径：`modules/Uui/web/auth/users.py`

默认 `User` 模型与认证工具。

## 类

### `AnonymousUser`
匿名用户占位。
- `id = None` / `is_authenticated = False` / `is_anonymous = True` / `is_active = False` / `is_staff = False` / `is_superuser = False` / `username = ''` / `pk = None`。

模块级单例 `_ANONYMOUS = AnonymousUser()`。

### `get_anonymous_user() -> AnonymousUser`
返回 `_ANONYMOUS` 单例。

### `User(Model)`
默认用户模型（可通过 `settings.AUTH_USER_MODEL` 替换）。
- `username = CharField(max_length=150, unique=True)`
- `email = CharField(max_length=254, null=True)`
- `password_hash = CharField(max_length=255, db_column='password')`
- `is_active = BooleanField(default=True)`
- `is_staff = BooleanField(default=False)`
- `is_superuser = BooleanField(default=False)`
- `last_login = DateTimeField(null=True)`
- `Meta.app = 'auth'` / `Meta.table = 'auth_user'`

属性 / 方法：
- `pk`（属性）— `self.id`
- `is_authenticated`（属性）— `True`
- `is_anonymous`（属性）— `False`
- `set_password(raw)` / `check_password(raw) -> bool`：用 `password.make_password` / `check_password`。
- `get_username() -> str`
- `has_perm(perm) -> bool` / `has_perms(perms) -> bool`：仅 `is_superuser` 决定。

## 函数

### `authenticate(username, password) -> Optional[User]`
- 缺失入参 → `None`。
- `User.objects.get(username=username)`；用户不存在/未激活/密码不匹配 → `None`。
- 成功返回 `User` 实例。

### `get_user_by_id(pk) -> Optional[User]`
按主键查 `User`；失败返回 `None`。