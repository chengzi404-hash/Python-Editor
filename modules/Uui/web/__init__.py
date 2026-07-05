"""Uui.web — minimalist WSGI framework.

Public API:

* :class:`UWSGIApp` — the application callable
* :class:`URequest` — request wrapper
* :class:`UResponse` and helpers (text, html, json, redirect, file, error)
* :func:`path` / :func:`include` — URL routing
* :class:`URLRouter` — low-level router

The CLI lives in :mod:`Uui.web.cli`.
"""
from .app import UWSGIApp, get_application, get_settings
from .request import URequest
from .response import (
    UResponse,
    text, html, json, empty, redirect, file, error,
)
from .router import URLRouter, path, include, clear_url_caches
from .exceptions import (
    UWebError, Http404, Http405, Http400, Http403, Http500,
    ImproperlyConfigured,
)


__all__ = [
    'UWSGIApp', 'get_application', 'get_settings',
    'URequest',
    'UResponse', 'text', 'html', 'json', 'empty', 'redirect', 'file', 'error',
    'URLRouter', 'path', 'include', 'clear_url_caches',
    'UWebError', 'Http404', 'Http405', 'Http400', 'Http403', 'Http500',
    'ImproperlyConfigured',
]
