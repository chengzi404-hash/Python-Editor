"""Decorators for protecting views with login / permission checks."""
from functools import wraps
from typing import Callable

from ..exceptions import ImproperlyConfigured
from ..response import redirect
from .users import get_anonymous_user


def login_required(view_func: Callable) -> Callable:
    """Reject anonymous requests. Unauthenticated GET redirects to
    ``/login/?next=<path>``; other methods return 403."""

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        user = getattr(request, 'user', None)
        if user is None:
            user = request.state.get('user') if hasattr(request, 'state') else None
        if user is None or getattr(user, 'is_authenticated', False) is False:
            if request.method == 'GET':
                next_url = request.full_path
                return redirect(f'/login/?next={_q(next_url)}', status=302)
            from ..exceptions import Http403
            raise Http403('Authentication required')
        return view_func(request, *args, **kwargs)

    return wrapper


def permission_required(perm: str) -> Callable:
    """Require ``user.has_perm(perm)``. Superusers always pass."""
    def decorator(view_func: Callable) -> Callable:
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            user = getattr(request, 'user', None)
            if user is None or not getattr(user, 'is_authenticated', False):
                from ..exceptions import Http403
                raise Http403('Authentication required')
            if not user.has_perm(perm):
                from ..exceptions import Http403
                raise Http403(f'Permission denied: {perm!r}')
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def staff_member_required(view_func: Callable) -> Callable:
    """Require ``user.is_staff`` (or superuser)."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        user = getattr(request, 'user', None)
        if user is None or not getattr(user, 'is_authenticated', False):
            from ..exceptions import Http403
            raise Http403('Authentication required')
        if not (getattr(user, 'is_staff', False) or getattr(user, 'is_superuser', False)):
            from ..exceptions import Http403
            raise Http403('Staff access required')
        return view_func(request, *args, **kwargs)
    return wrapper


def _q(s: str) -> str:
    from urllib.parse import quote
    return quote(s, safe='')
