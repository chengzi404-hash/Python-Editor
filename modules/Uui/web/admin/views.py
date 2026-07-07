"""Admin views: index, app_index, change_list, add_form, change_form, delete."""
from typing import Any, Dict, List, Optional

from .. import response
from ..exceptions import Http403, Http404
from ..auth.decorators import staff_member_required
from .site import site as default_site


def _site(request) -> Any:
    return getattr(request, '_admin_site', None) or default_site


def _require_staff(request) -> None:
    s = _site(request)
    if not s.has_permission(request):
        raise Http403('Admin access requires an active staff account.')


def _split_path(path: str) -> List[str]:
    parts = [p for p in path.split('/') if p]
    return parts


def _find_admin(request, parts: List[str]):
    s = _site(request)
    if not parts:
        return None, None, None
    app_label = parts[0]
    model_name = parts[1] if len(parts) > 1 else None
    for model, admin in s._registry.items():
        if admin.app_label == app_label:
            if model_name is None or admin.model_name == model_name:
                return s, app_label, admin
    return s, app_label, None



@staff_member_required
def index(request):
    s = _site(request)
    apps: Dict[str, List[Dict[str, Any]]] = {}
    for model, admin in s._registry.items():
        apps.setdefault(admin.app_label, []).append({
            'name': admin.verbose_name_plural,
            'url': f'/admin/{admin.app_label}/{admin.model_name}/',
            'model_name': admin.model_name,
        })
    context = {
        'title': 'Site administration',
        'site': s,
        'apps': apps,
        'user': request.user,
    }
    return response.render(request, 'admin/index.html', context)


@staff_member_required
def app_index(request, app_label: str):
    s = _site(request)
    models = [a for a in s._registry.values() if a.app_label == app_label]
    if not models:
        raise Http404(f'No app labelled {app_label!r}')
    context = {
        'title': f'{app_label} administration',
        'app_label': app_label,
        'models': models,
        'user': request.user,
    }
    return response.render(request, 'admin/app_index.html', context)


@staff_member_required
def logout_view(request):
    sess = request.session
    if sess is not None:
        sess.flush()
    return response.redirect('/')


@staff_member_required
def change_list(request, app_label: str, model_name: str):
    admin = _find_admin(request, [app_label, model_name])[2]
    if admin is None:
        raise Http404(f'No model {app_label}.{model_name}')
    if not admin.has_change_permission(request):
        raise Http403('No change permission')

    qs = admin.get_queryset(request)
    search = request.GET.get('q', '').strip()
    if search and admin.get_search_fields(request):
        for term in search.split():
            q_filter = {f + '__icontains': term for f in admin.get_search_fields(request)}
            qs = qs.filter(**q_filter)
    page = int(request.GET.get('p', '1') or '1')
    per_page = admin.get_list_per_page(request)
    total = qs.count()
    items = qs.order_by(*admin.get_ordering(request)).all()
    start = (page - 1) * per_page
    page_items = items[start:start + per_page]
    total_pages = max(1, (total + per_page - 1) // per_page)

    context = {
        'title': f'Select {admin.verbose_name} to change',
        'admin': admin,
        'items': page_items,
        'page': page,
        'total_pages': total_pages,
        'total': total,
        'search': search,
        'app_label': app_label,
        'model_name': model_name,
        'list_display': admin.get_list_display(request),
        'user': request.user,
    }
    return response.render(request, 'admin/change_list.html', context)


@staff_member_required
def add_form(request, app_label: str, model_name: str):
    admin = _find_admin(request, [app_label, model_name])[2]
    if admin is None:
        raise Http404(f'No model {app_label}.{model_name}')
    if not admin.has_add_permission(request):
        raise Http403('No add permission')

    if request.method == 'POST':
        return _save_form(request, admin, None)

    fields = admin.get_fields(request)
    context = {
        'title': f'Add {admin.verbose_name}',
        'admin': admin,
        'obj': None,
        'fields': fields,
        'form_data': {},
        'errors': [],
        'app_label': app_label,
        'model_name': model_name,
        'user': request.user,
    }
    return response.render(request, 'admin/change_form.html', context)


@staff_member_required
def change_form(request, app_label: str, model_name: str, pk: int):
    admin = _find_admin(request, [app_label, model_name])[2]
    if admin is None:
        raise Http404(f'No model {app_label}.{model_name}')
    obj = admin.get_object(request, pk)
    if obj is None:
        raise Http404(f'{admin.model_name} pk={pk} not found')
    if not admin.has_change_permission(request, obj):
        raise Http403('No change permission')

    if request.method == 'POST':
        action = request.POST.get('_action', 'save')
        if action == 'delete':
            return response.redirect(f'/admin/{app_label}/{model_name}/{pk}/delete/')
        return _save_form(request, admin, obj)

    fields = admin.get_fields(request, obj)
    context = {
        'title': f'Change {admin.verbose_name}',
        'admin': admin,
        'obj': obj,
        'fields': fields,
        'form_data': {f: getattr(obj, f, '') for f in fields},
        'errors': [],
        'app_label': app_label,
        'model_name': model_name,
        'user': request.user,
    }
    return response.render(request, 'admin/change_form.html', context)


@staff_member_required
def delete_view(request, app_label: str, model_name: str, pk: int):
    admin = _find_admin(request, [app_label, model_name])[2]
    if admin is None:
        raise Http404(f'No model {app_label}.{model_name}')
    obj = admin.get_object(request, pk)
    if obj is None:
        raise Http404(f'{admin.model_name} pk={pk} not found')
    if not admin.has_delete_permission(request, obj):
        raise Http403('No delete permission')

    if request.method == 'POST':
        admin.delete_model(request, obj)
        return response.redirect(f'/admin/{app_label}/{model_name}/')

    context = {
        'title': f'Delete {admin.verbose_name}',
        'admin': admin,
        'obj': obj,
        'app_label': app_label,
        'model_name': model_name,
        'user': request.user,
    }
    return response.render(request, 'admin/delete_confirmation.html', context)


def _save_form(request, admin, obj):
    fields = admin.get_fields(request, obj)
    errors: List[str] = []
    form_data: Dict[str, Any] = {}
    for fname in fields:
        raw = request.POST.get(fname, '')
        if isinstance(raw, list):
            value = raw[0] if raw else ''
        else:
            value = raw
        form_data[fname] = value
        fld = admin.opts['fields'].get(fname)
        if fld is not None and not fld.nullable and not str(value).strip():
            errors.append(f'{fname!r} is required')
    if errors:
        import sys
        print(f'[admin] save errors: {errors}, form_data={form_data}, fields={fields}, POST={dict(request.POST)}', file=sys.stderr)
        context = {
            'title': f'Change {admin.verbose_name}' if obj else f'Add {admin.verbose_name}',
            'admin': admin,
            'obj': obj,
            'fields': fields,
            'form_data': form_data,
            'errors': errors,
            'app_label': admin.app_label,
            'model_name': admin.model_name,
            'user': request.user,
        }
        return response.render(request, 'admin/change_form.html', context, status=400)

    if obj is None:
        obj = admin.model()
    for fname in fields:
        fld = admin.opts['fields'].get(fname)
        raw = form_data.get(fname, '')
        if fld is not None and hasattr(fld, 'to_python'):
            try:
                raw = fld.to_python(raw)
            except Exception:
                pass
        setattr(obj, fname, raw)
    admin.save_model(request, obj, form_data, change=obj is not None and obj.id is not None)
    return response.redirect(f'/admin/{admin.app_label}/{admin.model_name}/{obj.id}/change/')
