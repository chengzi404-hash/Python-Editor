"""Uui.web admin: automatic CRUD UI for registered models.

Quickstart::

    from Uui.web.admin import admin
    from Uui.web.admin.options import ModelAdmin
    from apps.blog.models import Post

    @admin.register(Post)
    class PostAdmin(ModelAdmin):
        list_display = ('id', 'title', 'published')
        list_filter = ('published',)
        search_fields = ('title',)
"""

from . import views
from .options import ModelAdmin
from .site import AdminSite, AlreadyRegisteredError, NotRegisteredError, site

__all__ = [
    "AdminSite",
    "AlreadyRegisteredError",
    "ModelAdmin",
    "NotRegisteredError",
    "site",
    "views",
]
