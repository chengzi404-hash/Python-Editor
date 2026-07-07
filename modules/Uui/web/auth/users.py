"""User model and helpers for the auth system."""
from typing import Any, Dict, Optional

from ..orm import Model, fields
from . import password as _pw


class AnonymousUser:
    """Stand-in returned for unauthenticated requests."""

    id = None
    is_authenticated = False
    is_anonymous = True
    is_active = False
    is_staff = False
    is_superuser = False
    username = ''
    pk = None

    def __repr__(self) -> str:
        return '<AnonymousUser>'


_ANONYMOUS = AnonymousUser()


def get_anonymous_user() -> AnonymousUser:
    return _ANONYMOUS


class User(Model):  # type: ignore[misc]
    """Default user model. Override with ``settings.AUTH_USER_MODEL``."""

    username = fields.CharField(max_length=150, unique=True)
    email = fields.CharField(max_length=254, null=True)
    password_hash = fields.CharField(max_length=255, db_column='password')
    is_active = fields.BooleanField(default=True)
    is_staff = fields.BooleanField(default=False)
    is_superuser = fields.BooleanField(default=False)
    last_login = fields.DateTimeField(null=True)

    class Meta:
        app = 'auth'
        table = 'auth_user'


    @property
    def pk(self):  # type: ignore[override]
        return self.id

    @property
    def is_authenticated(self) -> bool:
        return True

    @property
    def is_anonymous(self) -> bool:
        return False

    def set_password(self, raw: str) -> None:
        self.password_hash = _pw.make_password(raw)

    def check_password(self, raw: str) -> bool:
        return _pw.check_password(raw, self.password_hash or '')

    def get_username(self) -> str:
        return self.username or ''

    def has_perm(self, perm: str) -> bool:
        return self.is_superuser

    def has_perms(self, perms) -> bool:
        return self.is_superuser

    def __repr__(self) -> str:
        return f'<User {self.username!r}>'


def authenticate(username: Optional[str], password: Optional[str]) -> Optional[User]:
    """Return a matching :class:`User` or ``None``."""
    if not username or not password:
        return None
    try:
        user = User.objects.get(username=username)
    except Exception:
        return None
    if not user.is_active:
        return None
    if not user.check_password(password):
        return None
    return user


def get_user_by_id(pk: int) -> Optional[User]:
    try:
        return User.objects.get(id=pk)
    except Exception:
        return None
