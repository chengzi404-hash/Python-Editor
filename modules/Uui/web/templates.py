"""Template engine backends for Uui.web. Jinja2 is the default."""

import os
from pathlib import Path
from typing import Any

from .exceptions import ImproperlyConfiguredError

_BACKEND_CACHE: dict[str, "TemplateBackend"] = {}


DEFAULT_TEMPLATES: list[dict[str, Any]] = [
    {
        "BACKEND": "Uui.web.templates.Jinja2Backend",
        "DIRS": ["templates"],
        "APP_DIRS": "templates",
        "OPTIONS": {},
    },
]


class TemplateBackend:
    """Base class for template backends."""

    def __init__(self, config: dict[str, Any], settings: Any) -> None:
        self.config = config
        self.settings = settings

    def render(self, template_name: str, context: dict[str, Any]) -> str:
        raise NotImplementedError


class Jinja2Backend(TemplateBackend):
    """Renders Jinja2 templates with a single Environment per project.

    The Environment is process-wide (cached) so compiled templates are reused
    across requests. The ``auto_reload`` flag is taken from ``settings.DEBUG``.
    """

    def __init__(self, config: dict[str, Any], settings: Any) -> None:
        super().__init__(config, settings)
        try:
            import jinja2
        except ImportError as exc:
            raise ImproperlyConfiguredError(
                "jinja2 is required for the default template backend; install via `pip install jinja2`"
            ) from exc
        self.jinja2 = jinja2
        self.env = self._build_env(jinja2)

    def _build_env(self, jinja2):
        debug = bool(getattr(self.settings, "DEBUG", False))
        options = dict(self.config.get("OPTIONS") or {})
        options.setdefault("autoescape", True)
        options.setdefault("auto_reload", debug)
        options.setdefault("cache_size", -1)
        loader = self._build_loader(jinja2)
        env = jinja2.Environment(loader=loader, **options)
        env.globals["STATIC_URL"] = getattr(self.settings, "STATIC_URL", "/static/")
        env.filters["safe"] = lambda s: jinja2.Markup(s) if hasattr(jinja2, "Markup") else s
        return env

    def _build_loader(self, jinja2):
        search_paths: list[str] = []
        root = Path(getattr(self.settings, "PROJECT_ROOT", os.getcwd()))
        for d in self.config.get("DIRS") or []:
            p = Path(d)
            if not p.is_absolute():
                p = root / d
            if p.is_dir():
                search_paths.append(str(p))
        for app_name in getattr(self.settings, "INSTALLED_APPS", []) or []:
            rel = self.config.get("APP_DIRS") or "templates"
            try:
                mod = __import__(app_name)
            except Exception:
                continue
            mod = __import__(app_name, fromlist=["__file__"])
            app_file = getattr(mod, "__file__", None)
            if not app_file:
                continue
            p = Path(app_file).parent / rel
            if p.is_dir():
                search_paths.append(str(p))
        own_templates = Path(__file__).parent / "templates"
        if own_templates.is_dir():
            search_paths.append(str(own_templates))
        if not search_paths:
            search_paths.append(str(root / "templates"))
        return jinja2.FileSystemLoader(search_paths)

    def render(self, template_name: str, context: dict[str, Any]) -> str:
        try:
            tmpl = self.env.get_template(template_name)
        except self.jinja2.TemplateNotFound:
            raise ImproperlyConfiguredError(f"Template not found: {template_name}")
        return tmpl.render(**context)
