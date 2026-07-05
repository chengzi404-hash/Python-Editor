"""Uui.web auth: User model, session, password hashing, decorators.

Quickstart::

    from Uui.web.auth import User, authenticate, login_required
    from Uui.web.auth.session import SessionMiddleware  # in MIDDLEWARE
"""
from .password import make_password, check_password, needs_rehash
from .users import User, AnonymousUser, get_anonymous_user, authenticate, get_user_by_id
from .decorators import login_required, permission_required, staff_member_required
from .session import Session, SessionStore, SessionMiddleware


__all__ = [
    'make_password', 'check_password', 'needs_rehash',
    'User', 'AnonymousUser', 'get_anonymous_user', 'authenticate', 'get_user_by_id',
    'login_required', 'permission_required', 'staff_member_required',
    'Session', 'SessionStore', 'SessionMiddleware',
]
