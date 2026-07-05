"""Admin site singleton — the entry point for registering models."""
from typing import Any, Dict, List, Optional

from .options import ModelAdmin


class AlreadyRegistered(Exception):
    pass


class NotRegistered(Exception):
    pass


class AdminSite:
    """A registry mapping model classes to their :class:`ModelAdmin`."""

    def __init__(self, name: str = 'admin') -> None:
        self.name = name
        self._registry: Dict[type, ModelAdmin] = {}
        self._actions: Dict[str, Any] = {}

    def register(self, model: type, admin_class: Optional[type] = None) -> None:
        admin_class = admin_class or ModelAdmin
        if model in self._registry:
            raise AlreadyRegistered(f'{model.__name__} is already registered')
        if not issubclass(model, __import__('Uui.web.orm', fromlist=['Model']).Model):
            raise TypeError(f'{model.__name__} is not a Model')
        instance = admin_class(model, self)
        self._registry[model] = instance

    def unregister(self, model: type) -> None:
        if model not in self._registry:
            raise NotRegistered(f'{model.__name__} is not registered')
        del self._registry[model]

    def is_registered(self, model: type) -> bool:
        return model in self._registry

    def get_admin_for(self, model: type) -> Optional[ModelAdmin]:
        return self._registry.get(model)

    @property
    def registered_models(self) -> List[type]:
        return list(self._registry.keys())

    def get_urls(self) -> List[Any]:
        from ..router import path
        from . import views
        urlpatterns: List[Any] = [
            path('', views.index, name='index'),
            path('logout/', views.logout_view, name='logout'),
        ]
        urlpatterns += [
            path('<app_label>/', views.app_index, name='app_index'),
            path('<app_label>/<model_name>/', views.change_list, name='change_list'),
            path('<app_label>/<model_name>/add/', views.add_form, name='add_form'),
            path('<app_label>/<model_name>/<int:pk>/change/', views.change_form, name='change_form'),
            path('<app_label>/<model_name>/<int:pk>/delete/', views.delete_view, name='delete_view'),
        ]
        return urlpatterns

    @property
    def urls(self):
        """Return a 2-tuple ``(urlpatterns, app_name)`` for include()."""
        from ..router import Include
        return Include(f'Uui.web.admin.urls_module', namespace=self.name)

    def has_permission(self, request) -> bool:
        user = getattr(request, 'user', None)
        return user is not None and (
            getattr(user, 'is_active', False) and (
                getattr(user, 'is_staff', False) or getattr(user, 'is_superuser', False)
            )
        )


# Default site singleton
site = AdminSite()
