"""``modules.ai.provider`` — AI provider auto-detection.

Given a ``base_url`` (and an explicit provider override from settings), pick the
matching provider kind and a sensible default model id. Keeps the rest of the
codebase free of provider-specific hardcoded URLs.

The detection is deliberately string-based: we only look at the **hostname** of
the URL. The library is stdlib-only, so we use :mod:`urllib.parse`.

Provider shapes (all emit OpenAI-style ``chat.completions`` JSON unless noted):

* :attr:`AIProvider.OPENAI` — ``https://api.openai.com/v1`` style. Model default: ``gpt-4o-mini``.
* :attr:`AIProvider.ANTHROPIC` — ``https://api.anthropic.com`` style. Uses ``messages`` endpoint.
  Model default: ``claude-3-5-sonnet-latest``.
* :attr:`AIProvider.GOOGLE` — ``https://generativelanguage.googleapis.com`` style. Model default: ``gemini-1.5-flash``.
* :attr:`AIProvider.OLLAMA` — ``http://localhost:11434`` style. Model default: ``qwen2.5-coder``.
* :attr:`AIProvider.CUSTOM` — anything else; OpenAI-compatible POST.
"""

from __future__ import annotations

from enum import Enum
from urllib.parse import urlparse


class AIProvider(str, Enum):
    """Identifies which API dialect a ``base_url`` points to."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    OLLAMA = "ollama"
    CUSTOM = "custom"


# Substrings of hostnames → provider kind.
_HOST_HINTS: tuple[tuple[str, AIProvider], ...] = (
    ("api.openai.com", AIProvider.OPENAI),
    ("openai.azure.com", AIProvider.OPENAI),  # Azure OpenAI uses same protocol
    ("anthropic.com", AIProvider.ANTHROPIC),
    ("generativelanguage.googleapis.com", AIProvider.GOOGLE),
    ("googleapis.com", AIProvider.GOOGLE),
    ("localhost", AIProvider.OLLAMA),
    ("127.0.0.1", AIProvider.OLLAMA),
    ("0.0.0.0", AIProvider.OLLAMA),
    ("ollama", AIProvider.OLLAMA),
)

_DEFAULT_MODELS: dict[AIProvider, str] = {
    AIProvider.OPENAI: "gpt-4o-mini",
    AIProvider.ANTHROPIC: "claude-3-5-sonnet-latest",
    AIProvider.GOOGLE: "gemini-1.5-flash",
    AIProvider.OLLAMA: "qwen2.5-coder",
    AIProvider.CUSTOM: "",
}


def _host_of(url: str) -> str:
    """Return the lowercase hostname of *url*, or ``""`` if it cannot be parsed."""

    if not url:
        return ""
    try:
        parsed = urlparse(url if "://" in url else f"https://{url}")
        return (parsed.hostname or "").lower()
    except (ValueError, TypeError):
        return ""


def detect_provider(base_url: str, override: str | None = None) -> AIProvider:
    """Return the provider kind for *base_url*.

    Args:
        base_url: Endpoint URL configured by the user (may be empty).
        override: Optional explicit provider id from settings (``"openai"``,
            ``"anthropic"`` …). When the value is ``"auto"``, ``None`` or empty,
            the function falls back to URL sniffing.

    Returns:
        The detected :class:`AIProvider`. Returns :attr:`AIProvider.CUSTOM`
        when no rule matches (the safest fallback for OpenAI-compatible servers).
    """

    if override and override != "auto":
        try:
            return AIProvider(override)
        except ValueError:
            pass
    host = _host_of(base_url)
    if not host:
        return AIProvider.CUSTOM
    for needle, provider in _HOST_HINTS:
        if needle in host:
            return provider
    return AIProvider.CUSTOM


def default_model(provider: AIProvider) -> str:
    """Return a sensible default model id for *provider* (empty for :attr:`AIProvider.CUSTOM`)."""

    return _DEFAULT_MODELS.get(provider, "")


def resolve_model(base_url: str, configured: str, override: str | None = None) -> str:
    """Return the effective model id.

    Order of precedence:

    1. *configured* — non-empty user setting → use it as-is.
    2. Otherwise, auto-pick from the provider inferred via :func:`detect_provider`.
    """

    if configured and configured.strip():
        return configured.strip()
    provider = detect_provider(base_url, override)
    return default_model(provider)


def provider_label(provider: AIProvider) -> str:
    """Return a human-readable label for *provider* (English-only; i18n is UI-side)."""

    return {
        AIProvider.OPENAI: "OpenAI",
        AIProvider.ANTHROPIC: "Anthropic",
        AIProvider.GOOGLE: "Google",
        AIProvider.OLLAMA: "Ollama / local",
        AIProvider.CUSTOM: "OpenAI-compatible",
    }.get(provider, "Unknown")


__all__ = [
    "AIProvider",
    "default_model",
    "detect_provider",
    "provider_label",
    "resolve_model",
]
