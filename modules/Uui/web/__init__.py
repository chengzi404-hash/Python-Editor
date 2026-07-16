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
from .exceptions import (
    Http400Error,
    Http403Error,
    Http404Error,
    Http405Error,
    Http500Error,
    ImproperlyConfiguredError,
    UWebError,
)
from .request import URequest
from .response import (
    UResponse,
    empty,
    error,
    file,
    html,
    json,
    redirect,
    text,
)
from .router import URLRouter, clear_url_caches, include, path

__all__ = [
    "Http400Error",
    "Http403Error",
    "Http404Error",
    "Http405Error",
    "Http500Error",
    "ImproperlyConfiguredError",
    "URLRouter",
    "URequest",
    "UResponse",
    "UWSGIApp",
    "UWebError",
    "clear_url_caches",
    "empty",
    "error",
    "file",
    "get_application",
    "get_settings",
    "html",
    "include",
    "json",
    "path",
    "redirect",
    "text",
]
