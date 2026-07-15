"""Uui.web auth: User model, session, password hashing, decorators.

Quickstart::

    from Uui.web.auth import User, authenticate, login_required
    from Uui.web.auth.session import SessionMiddleware  # in MIDDLEWARE
"""
from .decorators import login_required, permission_required, staff_member_required
from .password import check_password, make_password, needs_rehash
from .session import Session, SessionMiddleware, SessionStore
from .users import AnonymousUser, User, authenticate, get_anonymous_user, get_user_by_id

__all__ = [
    'AnonymousUser',
    'Session',
    'SessionMiddleware',
    'SessionStore',
    'User',
    'authenticate',
    'check_password',
    'get_anonymous_user',
    'get_user_by_id',
    'login_required',
    'make_password',
    'needs_rehash',
    'permission_required',
    'staff_member_required',
]
