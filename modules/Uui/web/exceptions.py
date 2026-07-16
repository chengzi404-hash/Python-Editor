"""Exception hierarchy for Uui.web."""


class UWebError(Exception):
    """Base exception for all Uui.web errors."""

    status_code = 500
    default_message = "Internal server error"


class Http404(UWebError):
    status_code = 404
    default_message = "Not found"


class Http405(UWebError):
    status_code = 405
    default_message = "Method not allowed"


class Http400(UWebError):
    status_code = 400
    default_message = "Bad request"


class Http403(UWebError):
    status_code = 403
    default_message = "Forbidden"


class Http500(UWebError):
    status_code = 500
    default_message = "Server error"


class ImproperlyConfigured(UWebError):
    """Raised when the application is misconfigured."""

    default_message = "Improperly configured"


class AppRegistryNotReady(UWebError):
    """Raised when apps are accessed before the registry is ready."""

    default_message = "Apps are not loaded yet"
