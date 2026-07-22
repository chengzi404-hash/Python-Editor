"""``modules.ai`` — AI features for the editor.

Submodules:

* :mod:`.provider` — provider auto-detection from ``base_url``
* :mod:`.client` — :class:`AIClient` (urllib + threading, stdlib-only)
* :mod:`.skills` — :class:`AISkill` + :class:`AISkillRegistry`
* :mod:`.marketplace` — :class:`AISkillMarketplaceProvider`
"""

from __future__ import annotations

from .client import AIClient, AIRequestError, AIResponse, ChatMessage
from .marketplace import (
    AISkillMarketplaceProvider,
    bundled_skills,
    install_skill_from_marketplace,
)
from .provider import AIProvider, default_model, detect_provider, provider_label, resolve_model
from .skills import AISkill, AISkillRegistry, MCPServer

__all__ = [
    "AIClient",
    "AIProvider",
    "AIRequestError",
    "AIResponse",
    "AISkill",
    "AISkillMarketplaceProvider",
    "AISkillRegistry",
    "ChatMessage",
    "MCPServer",
    "bundled_skills",
    "default_model",
    "detect_provider",
    "install_skill_from_marketplace",
    "provider_label",
    "resolve_model",
]
