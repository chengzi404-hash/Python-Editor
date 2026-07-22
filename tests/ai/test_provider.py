"""Tests for ``core.ai.provider``."""

from __future__ import annotations

from core.ai import (
    AIProvider,
    default_model,
    detect_provider,
    provider_label,
    resolve_model,
)


class TestDetectProvider:
    def test_openai_default(self):
        assert detect_provider("https://api.openai.com/v1") is AIProvider.OPENAI

    def test_openai_azure(self):
        assert detect_provider("https://foo.openai.azure.com/v1") is AIProvider.OPENAI

    def test_anthropic(self):
        assert detect_provider("https://api.anthropic.com") is AIProvider.ANTHROPIC

    def test_google_genai(self):
        assert detect_provider("https://generativelanguage.googleapis.com/v1beta") is AIProvider.GOOGLE

    def test_google_other(self):
        assert detect_provider("https://translation.googleapis.com") is AIProvider.GOOGLE

    def test_ollama_localhost(self):
        assert detect_provider("http://localhost:11434") is AIProvider.OLLAMA

    def test_ollama_127(self):
        assert detect_provider("http://127.0.0.1:11434/v1") is AIProvider.OLLAMA

    def test_ollama_by_name(self):
        # 'ollama' substring in hostname flags Ollama.
        assert detect_provider("http://my-ollama-server.lan:11434") is AIProvider.OLLAMA
        assert detect_provider("http://foo.ollama.cloud") is AIProvider.OLLAMA
        # No 'ollama' substring → CUSTOM.
        assert detect_provider("http://my-server.lan:11434") is AIProvider.CUSTOM

    def test_custom_unknown_host(self):
        assert detect_provider("https://api.together.xyz/v1") is AIProvider.CUSTOM

    def test_empty_url(self):
        assert detect_provider("") is AIProvider.CUSTOM

    def test_explicit_override(self):
        assert detect_provider("https://example.com", "anthropic") is AIProvider.ANTHROPIC

    def test_explicit_override_unknown_value_falls_back_to_url(self):
        # An unknown override string is silently ignored, URL detection wins.
        assert detect_provider("https://api.openai.com/v1", "weird") is AIProvider.OPENAI

    def test_no_scheme_url(self):
        assert detect_provider("api.openai.com/v1") is AIProvider.OPENAI


class TestDefaultModel:
    def test_openai_default(self):
        assert default_model(AIProvider.OPENAI) == "gpt-4o-mini"

    def test_anthropic_default(self):
        assert default_model(AIProvider.ANTHROPIC) == "claude-3-5-sonnet-latest"

    def test_google_default(self):
        assert default_model(AIProvider.GOOGLE) == "gemini-1.5-flash"

    def test_ollama_default(self):
        assert default_model(AIProvider.OLLAMA) == "qwen2.5-coder"

    def test_custom_default_is_empty(self):
        assert default_model(AIProvider.CUSTOM) == ""


class TestResolveModel:
    def test_explicit_value_wins(self):
        assert resolve_model("https://api.openai.com/v1", "my-custom-model") == "my-custom-model"

    def test_empty_value_picks_default_for_openai(self):
        assert resolve_model("https://api.openai.com/v1", "") == "gpt-4o-mini"

    def test_empty_value_picks_default_for_anthropic(self):
        assert resolve_model("https://api.anthropic.com", "") == "claude-3-5-sonnet-latest"

    def test_whitespace_value_is_treated_as_empty(self):
        assert resolve_model("https://api.openai.com/v1", "   ") == "gpt-4o-mini"

    def test_custom_provider_has_no_default(self):
        # Custom (unknown) URL: no default model — user must supply one.
        assert resolve_model("https://api.together.xyz/v1", "") == ""


class TestProviderLabel:
    def test_known_labels(self):
        assert provider_label(AIProvider.OPENAI) == "OpenAI"
        assert provider_label(AIProvider.ANTHROPIC) == "Anthropic"
        assert provider_label(AIProvider.GOOGLE) == "Google"
        assert provider_label(AIProvider.OLLAMA) == "Ollama / local"
        assert provider_label(AIProvider.CUSTOM) == "OpenAI-compatible"
