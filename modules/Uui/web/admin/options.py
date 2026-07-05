"""ModelAdmin — describes how a model is presented in the admin UI."""
from typing import Any, Dict, List, Optional


class ModelAdmin:
    """Declarative admin config attached to a model.

    Subclass and override ``list_display``, ``list_filter``, ``search_fields``,
    ``list_per_page`` etc. to customise the change list page.
    """

    list_display: List[str] = ['__str__']
    list_filter: List[str] = []
    search_fields: List[str] = []
    list_per_page: int = 25
    ordering: List[str] = []
    fields: Optional[List[str]] = None  # None = all fields
    exclude: List[str] = []
    readonly_fields: List[str] = []
    date_hierarchy: Optional[str] = None
    list_select_related: bool = False
    save_on_top: bool = False

    def __init__(self, model: type, admin_site: Any) -> None:
        self.model = model
        self.admin_site = admin_site
        self.opts = model._meta
        self.app_label = self.opts.get('app') or model.__name__.lower()
        self.model_name = model.__name__.lower()
        self.verbose_name = getattr(model, 'verbose_name', model.__name__)
        self.verbose_name_plural = getattr(model, 'verbose_name_plural', self.verbose_name + 's')

    def get_list_display(self, request) -> List[str]:
        return list(self.list_display)

    def get_fields(self, request, obj=None) -> List[str]:
        if self.fields is not None:
            return [f for f in self.fields if f not in self.exclude]
        out = []
        for fname, fld in self.opts['fields'].items():
            if fname in self.exclude:
                continue
            if getattr(fld, 'auto', False):
                continue
            if fld.primary_key and getattr(fld, 'auto', False):
                continue
            out.append(fname)
        return out

    def get_search_fields(self, request) -> List[str]:
        return list(self.search_fields)

    def get_ordering(self, request) -> List[str]:
        return list(self.ordering) or [self.opts.get('pk', 'id')]

    def get_list_per_page(self, request) -> int:
        return self.list_per_page

    def has_add_permission(self, request) -> bool:
        return True

    def has_change_permission(self, request, obj=None) -> bool:
        return True

    def has_delete_permission(self, request, obj=None) -> bool:
        return True

    def get_queryset(self, request):
        return self.model.objects

    def get_object(self, request, pk):
        try:
            return self.model.objects.get(id=int(pk))
        except Exception:
            return None

    def save_model(self, request, obj, form, change: bool) -> None:
        obj.save()

    def delete_model(self, request, obj) -> None:
        obj.delete()

    def __repr__(self) -> str:
        return f'<ModelAdmin {self.model.__name__}>'
