"""Tests for :class:`core.ai.client.AIClient`.

Uses an in-process HTTP server (single-threaded ``http.server``-derived) so we
can exercise the real ``urllib`` path that production uses — no monkey-patching
of ``urllib.request``. Tests run with ``BaseTestServer.run_in_thread``.
"""

from __future__ import annotations

import json
import socket
import threading
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import ClassVar

import pytest

from core.ai import AIClient, AIProvider, AIRequestError, ChatMessage

# ---- Tiny test HTTP server -----------------------------------------------


class _Handler(BaseHTTPRequestHandler):
    """HTTP handler whose response is configured by the caller via class attrs."""

    response_status: ClassVar[int] = 200
    response_body: ClassVar[bytes] = b"{}"
    response_headers: ClassVar[dict[str, str]] = {}
    captured: ClassVar[list[dict]] = []

    def do_POST(self):
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length) if length else b""
        try:
            payload = json.loads(body.decode("utf-8"))
        except Exception:
            payload = None
        _Handler.captured.append(
            {
                "path": self.path,
                "headers": dict(self.headers),
                "body": payload,
            }
        )
        for key, value in _Handler.response_headers.items():
            self.send_header(key, value)
        self.send_response(_Handler.response_status)
        self.send_header("Content-Length", str(len(_Handler.response_body)))
        self.end_headers()
        self.wfile.write(_Handler.response_body)

    def log_message(self, *_args, **_kwargs):
        return


def _free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


@contextmanager
def _server(handler_cls: type):
    port = _free_port()
    server = HTTPServer(("127.0.0.1", port), handler_cls)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


@pytest.fixture(autouse=True)
def reset_handler():
    _Handler.response_status = 200
    _Handler.response_body = b"{}"
    _Handler.response_headers = {}
    _Handler.captured = []
    yield


# ---- Tests ---------------------------------------------------------------


class TestAIClientBasics:
    def test_default_provider_for_openai_url(self):
        client = AIClient(base_url="https://api.openai.com/v1")
        assert client.provider is AIProvider.OPENAI

    def test_default_model_for_openai_url(self):
        client = AIClient(base_url="https://api.openai.com/v1")
        assert client.model == "gpt-4o-mini"

    def test_explicit_model_wins(self):
        client = AIClient(base_url="https://api.openai.com/v1", model="gpt-4o")
        assert client.model == "gpt-4o"

    def test_configure_updates_runtime(self):
        client = AIClient(base_url="https://api.openai.com/v1")
        assert client.timeout_s == 60.0
        client.configure(timeout_s=10)
        assert client.timeout_s == 10.0

    def test_configure_updates_model(self):
        client = AIClient(base_url="https://api.openai.com/v1")
        client.configure(model="custom")
        assert client.model == "custom"

    def test_is_configured_requires_base_url_and_model(self):
        assert AIClient(base_url="", model="x").is_configured() is False
        assert AIClient(base_url="http://x", model="").is_configured() is False
        assert AIClient(base_url="http://x", model="y").is_configured() is True

    @pytest.mark.parametrize(
        "base_url",
        [
            "https://api.openai.com/v1",
            "https://api.anthropic.com",
            "https://generativelanguage.googleapis.com/v1beta",
        ],
    )
    def test_hosted_provider_requires_api_key(self, base_url):
        assert AIClient(base_url=base_url, model="x").is_configured() is False
        assert AIClient(base_url=base_url, api_key="key", model="x").is_configured() is True

    def test_ollama_does_not_require_api_key(self):
        client = AIClient(base_url="http://localhost:11434", model="qwen2.5-coder")
        assert client.is_configured() is True

    def test_trailing_slash_is_normalized(self):
        client = AIClient(base_url="https://api.openai.com/v1/")
        assert client.base_url == "https://api.openai.com/v1"


class TestAIClientChat:
    def test_openai_chat_against_test_server(self):
        with _server(_Handler) as base_url:
            _Handler.response_body = json.dumps(
                {"choices": [{"message": {"role": "assistant", "content": "Hi there."}}]}
            ).encode()
            client = AIClient(base_url=base_url, api_key="sk-test", model="gpt-x")
            response = client.chat(
                [ChatMessage(role="user", content="hello")],
                max_tokens=10,
                temperature=0.0,
            )
            assert response.text == "Hi there."
            assert _Handler.captured, "server should have received the request"
            req = _Handler.captured[0]
            assert req["path"] == "/chat/completions"
            assert req["headers"].get("Authorization") == "Bearer sk-test"
            assert req["body"]["model"] == "gpt-x"
            assert req["body"]["messages"][0]["content"] == "hello"

    def test_http_error_raises_ai_request_error(self):
        with _server(_Handler) as base_url:
            _Handler.response_status = 401
            _Handler.response_body = b'{"error":"bad key"}'
            client = AIClient(base_url=base_url, api_key="bad", model="x")
            with pytest.raises(AIRequestError) as excinfo:
                client.chat([ChatMessage(role="user", content="x")])
            assert excinfo.value.status == 401

    def test_unconfigured_raises(self):
        client = AIClient(base_url="", model="")
        with pytest.raises(AIRequestError):
            client.chat([ChatMessage(role="user", content="x")])

    def test_hosted_provider_without_api_key_raises_before_request(self):
        client = AIClient(base_url="https://api.openai.com/v1", model="gpt-4o-mini")
        with pytest.raises(AIRequestError, match="api_key"):
            client.chat([ChatMessage(role="user", content="x")])


class TestAIClientFim:
    def test_fim_against_test_server(self):
        with _server(_Handler) as base_url:
            _Handler.response_body = json.dumps(
                {"choices": [{"text": "def foo():\n    return 1"}]}
            ).encode()
            client = AIClient(base_url=base_url, api_key="k", model="code-model")
            resp = client.fim("# header\n", "rest", max_tokens=32)
            assert resp.text.startswith("def foo")
            req = _Handler.captured[0]
            assert req["path"] == "/completions"
            assert req["body"]["model"] == "code-model"
            assert req["body"]["prompt"] == "# header\n"
            assert req["body"]["suffix"] == "rest"

    def test_fim_truncates_to_max_content(self):
        with _server(_Handler) as base_url:
            _Handler.response_body = json.dumps({"choices": [{"text": "x"}]}).encode()
            client = AIClient(
                base_url=base_url,
                api_key="k",
                model="m",
                max_content=10,
            )
            client.fim("a" * 50, "b" * 50)
            req = _Handler.captured[0]
            # Total sent length is bounded by max_content.
            assert len(req["body"]["prompt"]) + len(req["body"]["suffix"]) <= 10
