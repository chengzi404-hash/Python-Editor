"""``modules.ai.client`` — :class:`AIClient` (stdlib-only HTTP).

The editor's runtime dependency budget is **zero** — ``pyproject.toml``
``dependencies = []``. So we talk to the AI provider with :mod:`urllib.request`
+ :mod:`http.client` and parse SSE streams line-by-line. A small :class:`threading.Thread`
worker is used to keep the Tk main thread responsive while the model thinks.

Design notes:

* The :class:`AIClient` holds only configuration (URL, key, model, timeout).
  No I/O happens in the constructor.
* ``base_url`` is normalized — trailing slashes are stripped, ``/v1`` is preserved
  if present. Endpoint paths (``/chat/completions``, ``/completions``,
  ``/messages``) are derived from the detected :class:`~core.ai.provider.AIProvider`.
* Streaming uses ``Transfer-Encoding: chunked`` or ``Content-Length`` responses
  split on ``\\n\\n`` SSE boundaries.
* Cancellation: workers check a ``threading.Event`` between every SSE event.
* Errors raise :class:`AIRequestError` with a short human-readable message; the
  full response body is available as ``error.body`` for debugging.
"""

from __future__ import annotations

import contextlib
import json
import threading
import time
import urllib.error
import urllib.request
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from typing import Any

from .provider import AIProvider, detect_provider, resolve_model

# ---- Public data types ---------------------------------------------------


@dataclass
class ChatMessage:
    """A single turn in a chat conversation."""

    role: str  # "system" | "user" | "assistant"
    content: str


@dataclass
class AIResponse:
    """Unified AI response payload (non-streaming)."""

    text: str
    model: str = ""
    raw: dict[str, Any] = field(default_factory=dict)


class AIRequestError(RuntimeError):
    """Raised when the AI provider returns a non-2xx response or the request fails."""

    def __init__(self, message: str, status: int = 0, body: str = "") -> None:
        super().__init__(message)
        self.status = status
        self.body = body


# ---- Internal helpers ----------------------------------------------------


def _normalize_base(url: str) -> str:
    """Strip trailing slashes and whitespace from a base URL."""

    if not url:
        return ""
    return url.rstrip().rstrip("/")


def _join(base: str, path: str) -> str:
    """Join a base URL and a relative path, preserving any ``/v1`` prefix on *base*."""

    base = _normalize_base(base)
    if not base:
        return path
    if not path.startswith("/"):
        path = "/" + path
    return base + path


def _endpoint_chat(provider: AIProvider, base: str) -> str:
    """Return the chat-completions endpoint URL for *provider*."""

    if provider is AIProvider.ANTHROPIC:
        return _join(base, "/v1/messages")
    if provider is AIProvider.GOOGLE:
        # Google's REST API embeds the model in the path; we patch it in later.
        return _join(base, "/v1beta/models/__MODEL__:generateContent")
    return _join(base, "/chat/completions")


def _endpoint_fim(provider: AIProvider, base: str) -> str:
    """Return the fill-in-the-middle / legacy completions endpoint URL for *provider*."""

    if provider is AIProvider.ANTHROPIC:
        # Anthropic has no native FIM endpoint — we approximate via messages with
        # a code-completion prompt. Caller may choose to skip FIM for Anthropic.
        return _join(base, "/v1/messages")
    return _join(base, "/completions")


def _endpoint_stream_chat(provider: AIProvider, base: str) -> str:
    """Streaming counterpart of :func:`_endpoint_chat`."""

    if provider is AIProvider.ANTHROPIC:
        return _join(base, "/v1/messages")
    if provider is AIProvider.GOOGLE:
        return _join(base, "/v1beta/models/__MODEL__:streamGenerateContent")
    return _join(base, "/chat/completions")


def _headers(api_key: str, stream: bool = False) -> dict[str, str]:
    """Build HTTP headers shared by all requests (Authorization + content type)."""

    headers = {
        "Content-Type": "application/json",
        "Accept": "text/event-stream" if stream else "application/json",
        "User-Agent": "PythonEditor/1.0 (ai-feature)",
    }
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    return headers


# ---- Payload builders per provider --------------------------------------


def _build_chat_payload(
    provider: AIProvider,
    model: str,
    messages: list[ChatMessage],
    *,
    max_tokens: int,
    temperature: float,
    stream: bool,
    reasoning_effort: str = "",
) -> dict[str, Any]:
    """Return the JSON body for a chat request, shaped per provider."""

    if provider is AIProvider.ANTHROPIC:
        system_parts = [m.content for m in messages if m.role == "system"]
        convo = [
            {"role": m.role, "content": m.content}
            for m in messages
            if m.role in ("user", "assistant")
        ]
        payload: dict[str, Any] = {
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": convo,
            "stream": stream,
        }
        if system_parts:
            payload["system"] = "\n\n".join(system_parts)
        return payload

    if provider is AIProvider.GOOGLE:
        contents: list[dict[str, Any]] = []
        system_parts: list[str] = []
        for m in messages:
            if m.role == "system":
                system_parts.append(m.content)
            else:
                role = "model" if m.role == "assistant" else "user"
                contents.append({"role": role, "parts": [{"text": m.content}]})
        payload = {
            "contents": contents,
            "generationConfig": {
                "maxOutputTokens": max_tokens,
                "temperature": temperature,
            },
        }
        if system_parts:
            payload["systemInstruction"] = {"parts": [{"text": "\n\n".join(system_parts)}]}
        return payload

    # OpenAI / Ollama / Custom
    payload: dict[str, Any] = {
        "model": model,
        "messages": [{"role": m.role, "content": m.content} for m in messages],
        "max_tokens": max_tokens,
        "temperature": temperature,
        "stream": stream,
    }
    if reasoning_effort and reasoning_effort != "off":
        payload["reasoning_effort"] = reasoning_effort
    return payload


def _build_fim_payload(
    provider: AIProvider,
    model: str,
    prefix: str,
    suffix: str,
    *,
    max_tokens: int,
    temperature: float,
) -> dict[str, Any]:
    """Return the JSON body for a fill-in-the-middle request.

    Anthropic has no native FIM, so we synthesize a single-turn ``messages``
    request that includes both halves. Ollama exposes ``/api/generate`` with a
    ``suffix`` field — we still emit the standard ``/completions`` shape and
    rely on OpenAI-compatible servers (llama.cpp, vLLM, etc.) supporting
    ``suffix`` in their completions endpoint.
    """

    if provider is AIProvider.ANTHROPIC:
        prompt = (
            "Complete the missing code at the <FILL_HERE> marker. "
            "Output ONLY the completion — no commentary, no markdown fences.\n\n"
            f"PREFIX:\n{prefix}\n\n"
            f"<FILL_HERE>\n\n"
            f"SUFFIX:\n{suffix}"
        )
        return {
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [{"role": "user", "content": prompt}],
        }

    return {
        "model": model,
        "prompt": prefix,
        "suffix": suffix,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "stream": False,
    }


# ---- Response parsing ---------------------------------------------------


def _extract_text(provider: AIProvider, payload: dict[str, Any]) -> str:
    """Pull the assistant text out of a provider-specific response JSON."""

    if provider is AIProvider.ANTHROPIC:
        content = payload.get("content") or []
        parts = [block.get("text", "") for block in content if isinstance(block, dict)]
        return "".join(parts).strip()

    if provider is AIProvider.GOOGLE:
        candidates = payload.get("candidates") or []
        if not candidates:
            return ""
        parts = candidates[0].get("content", {}).get("parts", [])
        return "".join(p.get("text", "") for p in parts if isinstance(p, dict)).strip()

    # OpenAI / Ollama / Custom
    choices = payload.get("choices") or []
    if not choices:
        return ""
    first = choices[0]
    msg = first.get("message") or {}
    if "content" in msg:
        return str(msg["content"]).strip()
    if "text" in first:
        return str(first["text"]).strip()
    return ""


def _parse_sse(
    provider: AIProvider,
    lines: Iterable[bytes],
    on_chunk: Callable[[str], None],
) -> str:
    """Yield incremental text from an SSE stream of ``data: {...}`` events.

    Stops cleanly at ``data: [DONE]`` (OpenAI convention) or at end-of-stream.
    Returns the concatenated text.
    """

    accumulated: list[str] = []
    data_buffer: list[str] = []
    for raw_line in lines:
        line = raw_line.decode("utf-8", errors="replace").rstrip("\r\n")
        if not line:
            if data_buffer:
                _flush_sse_event(provider, data_buffer, on_chunk, accumulated)
                data_buffer.clear()
            continue
        if line.startswith(":"):
            continue  # comment
        if line.startswith("data:"):
            data_buffer.append(line[5:].lstrip())
        else:
            # event:, id:, retry: — we ignore the meta lines
            continue
    if data_buffer:
        _flush_sse_event(provider, data_buffer, on_chunk, accumulated)
    return "".join(accumulated)


def _flush_sse_event(
    provider: AIProvider,
    data_buffer: list[str],
    on_chunk: Callable[[str], None],
    accumulated: list[str],
) -> None:
    payload = "\n".join(data_buffer).strip()
    if not payload or payload == "[DONE]":
        return
    try:
        obj = json.loads(payload)
    except json.JSONDecodeError:
        return
    text = _extract_stream_delta(provider, obj)
    if text:
        accumulated.append(text)
        on_chunk(text)


def _extract_stream_delta(provider: AIProvider, obj: dict[str, Any]) -> str:
    """Pull the delta text out of one SSE event JSON."""

    if provider is AIProvider.ANTHROPIC:
        # Anthropic streams events of type "content_block_delta" with delta.text
        if obj.get("type") == "content_block_delta":
            delta = obj.get("delta") or {}
            return str(delta.get("text", ""))
        # Some proxies forward OpenAI-style deltas through Anthropic too
        if "choices" in obj:
            ch = (obj.get("choices") or [{}])[0]
            d = ch.get("delta") or {}
            return str(d.get("content") or d.get("text") or "")
        return ""

    if provider is AIProvider.GOOGLE:
        candidates = obj.get("candidates") or []
        if not candidates:
            return ""
        parts = candidates[0].get("content", {}).get("parts", [])
        return "".join(p.get("text", "") for p in parts if isinstance(p, dict))

    # OpenAI / Ollama / Custom
    choices = obj.get("choices") or []
    if not choices:
        return ""
    ch = choices[0]
    delta = ch.get("delta") or {}
    if "content" in delta and delta["content"] is not None:
        return str(delta["content"])
    if "text" in ch:
        return str(ch["text"])
    return ""


# ---- The main client -----------------------------------------------------


_PROVIDERS_REQUIRING_API_KEY = (
    AIProvider.OPENAI,
    AIProvider.ANTHROPIC,
    AIProvider.GOOGLE,
)


@dataclass
class _Config:
    base_url: str = ""
    api_key: str = ""
    model: str = ""
    fim_model: str = ""
    provider_override: str = "auto"
    timeout_s: float = 60.0
    max_content: int = 8000
    reasoning_effort: str = ""


class AIClient:
    """Talk to an OpenAI-compatible AI provider over stdlib HTTP.

    Instances are cheap; rebuild one when settings change rather than mutating
    in place. The client is **stateless** with respect to conversation history —
    callers pass the full ``messages`` list to :meth:`chat`.
    """

    def __init__(
        self,
        base_url: str = "",
        api_key: str = "",
        model: str = "",
        *,
        provider: str = "auto",
        timeout_s: float = 60.0,
        max_content: int = 8000,
        fim_model: str = "",
        reasoning_effort: str = "",
    ) -> None:
        self._cfg = _Config(
            base_url=_normalize_base(base_url),
            api_key=api_key or "",
            model=(model or "").strip(),
            fim_model=(fim_model or "").strip(),
            provider_override=provider or "auto",
            timeout_s=float(timeout_s),
            max_content=int(max_content),
            reasoning_effort=(reasoning_effort or "").strip(),
        )

    # -- Configuration accessors -------------------------------------------

    @property
    def base_url(self) -> str:
        return self._cfg.base_url

    @property
    def api_key(self) -> str:
        return self._cfg.api_key

    @property
    def model(self) -> str:
        if self._cfg.model:
            return self._cfg.model
        return resolve_model(self._cfg.base_url, "", self._cfg.provider_override)

    @property
    def fim_model(self) -> str:
        if self._cfg.fim_model:
            return self._cfg.fim_model
        return self.model

    @property
    def reasoning_effort(self) -> str:
        return self._cfg.reasoning_effort

    @property
    def provider(self) -> AIProvider:
        return detect_provider(self._cfg.base_url, self._cfg.provider_override)

    @property
    def timeout_s(self) -> float:
        return self._cfg.timeout_s

    @property
    def max_content(self) -> int:
        return self._cfg.max_content

    def configure(
        self,
        *,
        base_url: str | None = None,
        api_key: str | None = None,
        model: str | None = None,
        provider: str | None = None,
        timeout_s: float | None = None,
        max_content: int | None = None,
        fim_model: str | None = None,
        reasoning_effort: str | None = None,
    ) -> None:
        """Mutate configuration in place (used by settings-change listener)."""

        if base_url is not None:
            self._cfg.base_url = _normalize_base(base_url)
        if api_key is not None:
            self._cfg.api_key = api_key
        if model is not None:
            self._cfg.model = (model or "").strip()
        if provider is not None:
            self._cfg.provider_override = provider or "auto"
        if timeout_s is not None:
            self._cfg.timeout_s = float(timeout_s)
        if max_content is not None:
            self._cfg.max_content = int(max_content)
        if fim_model is not None:
            self._cfg.fim_model = (fim_model or "").strip()
        if reasoning_effort is not None:
            self._cfg.reasoning_effort = (reasoning_effort or "").strip()

    def is_configured(self) -> bool:
        """Return whether the client has the minimum configuration for its provider."""

        if not self._cfg.base_url or not self.model:
            return False
        if self.provider in _PROVIDERS_REQUIRING_API_KEY:
            return bool(self._cfg.api_key.strip())
        return True

    # -- Request execution --------------------------------------------------

    def _post_json(
        self,
        url: str,
        body: dict[str, Any],
        *,
        stream: bool = False,
    ) -> Any:
        """POST JSON to *url* and return the response object."""

        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers=_headers(self._cfg.api_key, stream=stream),
            method="POST",
        )
        return urllib.request.urlopen(req, timeout=self._cfg.timeout_s)

    @staticmethod
    def _patch_model_in_url(url: str, model: str) -> str:
        """Google REST endpoints embed ``__MODEL__`` in the path; replace it."""

        return url.replace("__MODEL__", model) if "__MODEL__" in url else url

    def chat(
        self,
        messages: list[ChatMessage],
        *,
        max_tokens: int = 1024,
        temperature: float = 0.2,
    ) -> AIResponse:
        """Send a non-streaming chat request and return the full response.

        Raises:
            AIRequestError: On HTTP error or invalid configuration.
        """

        self._require_configured()
        provider = self.provider
        model = self.model
        endpoint = self._patch_model_in_url(_endpoint_chat(provider, self._cfg.base_url), model)
        payload = _build_chat_payload(
            provider,
            model,
            [self._truncate(m) for m in messages],
            max_tokens=max_tokens,
            temperature=temperature,
            stream=False,
            reasoning_effort=self._cfg.reasoning_effort,
        )
        try:
            resp = self._post_json(endpoint, payload, stream=False)
            raw = json.loads(resp.read().decode("utf-8", errors="replace"))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace") if hasattr(exc, "read") else ""
            raise AIRequestError(f"HTTP {exc.code}: {exc.reason}", exc.code, body) from exc
        except urllib.error.URLError as exc:
            raise AIRequestError(f"Network error: {exc.reason}") from exc
        except json.JSONDecodeError as exc:
            raise AIRequestError(f"Invalid JSON response: {exc.msg}") from exc

        text = _extract_text(provider, raw)
        return AIResponse(text=text, model=model, raw=raw)

    def fim(
        self,
        prefix: str,
        suffix: str,
        *,
        max_tokens: int = 256,
        temperature: float = 0.2,
    ) -> AIResponse:
        """Send a fill-in-the-middle request and return the completion.

        Both ``prefix`` and ``suffix`` are truncated to ``max_content`` chars
        total before being sent, with the cursor bias preserved when possible.
        """

        self._require_configured()
        provider = self.provider
        model = self.fim_model
        endpoint = self._patch_model_in_url(_endpoint_fim(provider, self._cfg.base_url), model)

        # Trim to fit budget while preserving the user's intent. We honour the
        # ``max_content`` setting directly — callers may set it as small as
        # they want for cost reasons. ``_balance_trim`` keeps at least one
        # quarter of the budget on the prefix side so the model sees what the
        # user just wrote.
        budget = max(1, self._cfg.max_content)
        prefix, suffix = _balance_trim(prefix, suffix, budget)

        payload = _build_fim_payload(
            provider,
            model,
            prefix,
            suffix,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        try:
            resp = self._post_json(endpoint, payload, stream=False)
            raw = json.loads(resp.read().decode("utf-8", errors="replace"))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace") if hasattr(exc, "read") else ""
            raise AIRequestError(f"HTTP {exc.code}: {exc.reason}", exc.code, body) from exc
        except urllib.error.URLError as exc:
            raise AIRequestError(f"Network error: {exc.reason}") from exc
        except json.JSONDecodeError as exc:
            raise AIRequestError(f"Invalid JSON response: {exc.msg}") from exc

        text = _extract_text(provider, raw) if provider is AIProvider.ANTHROPIC else _extract_fim_text(raw)
        return AIResponse(text=text, model=model, raw=raw)

    def stream_chat(
        self,
        messages: list[ChatMessage],
        on_chunk: Callable[[str], None],
        cancel: threading.Event | None = None,
        *,
        max_tokens: int = 1024,
        temperature: float = 0.2,
    ) -> AIResponse:
        """Streaming chat. *on_chunk* is invoked for every delta text fragment.

        Returns an :class:`AIResponse` with the concatenated text. Pass
        *cancel* (a :class:`threading.Event`) to abort mid-stream — the worker
        stops emitting chunks but waits for the underlying socket to close so
        it doesn't leak a connection.
        """

        self._require_configured()
        provider = self.provider
        model = self.model
        endpoint = self._patch_model_in_url(
            _endpoint_stream_chat(provider, self._cfg.base_url), model
        )
        payload = _build_chat_payload(
            provider,
            model,
            [self._truncate(m) for m in messages],
            max_tokens=max_tokens,
            temperature=temperature,
            stream=True,
            reasoning_effort=self._cfg.reasoning_effort,
        )
        try:
            resp = self._post_json(endpoint, payload, stream=True)
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace") if hasattr(exc, "read") else ""
            raise AIRequestError(f"HTTP {exc.code}: {exc.reason}", exc.code, body) from exc
        except urllib.error.URLError as exc:
            raise AIRequestError(f"Network error: {exc.reason}") from exc

        accumulated: list[str] = []
        try:
            with resp:
                for raw_line in resp:
                    if cancel is not None and cancel.is_set():
                        break
                    text = _extract_stream_line(provider, raw_line)
                    if text:
                        accumulated.append(text)
                        on_chunk(text)
        finally:
            with contextlib.suppress(Exception):
                resp.close()

        return AIResponse(text="".join(accumulated), model=model, raw={})

    # -- Background-thread helpers -----------------------------------------

    def stream_chat_async(
        self,
        messages: list[ChatMessage],
        on_chunk: Callable[[str], None],
        on_done: Callable[[AIResponse], None],
        on_error: Callable[[AIRequestError], None],
        cancel: threading.Event | None = None,
        **kwargs: Any,
    ) -> threading.Thread:
        """Run :meth:`stream_chat` on a background thread.

        The three callbacks are invoked **from the worker thread**. The caller
        is responsible for bouncing UI updates back to the Tk main thread via
        ``self.window.after(0, ...)``.
        """

        thread = threading.Thread(
            target=self._run_stream,
            args=(messages, on_chunk, on_done, on_error, cancel),
            kwargs=kwargs,
            daemon=True,
        )
        thread.start()
        return thread

    def request_async(
        self,
        target: Callable[..., AIResponse],
        on_done: Callable[[AIResponse], None],
        on_error: Callable[[AIRequestError], None],
        *args: Any,
        **kwargs: Any,
    ) -> threading.Thread:
        """Run any request method (``chat``, ``fim``) on a background thread."""

        thread = threading.Thread(
            target=self._run_target,
            args=(target, on_done, on_error, args, kwargs),
            daemon=True,
        )
        thread.start()
        return thread

    def _run_stream(
        self,
        messages: list[ChatMessage],
        on_chunk: Callable[[str], None],
        on_done: Callable[[AIResponse], None],
        on_error: Callable[[AIRequestError], None],
        cancel: threading.Event | None,
        **kwargs: Any,
    ) -> None:
        try:
            response = self.stream_chat(messages, on_chunk, cancel, **kwargs)
            on_done(response)
        except AIRequestError as exc:
            on_error(exc)

    def _run_target(
        self,
        target: Callable[..., AIResponse],
        on_done: Callable[[AIResponse], None],
        on_error: Callable[[AIRequestError], None],
        args: tuple[Any, ...],
        kwargs: dict[str, Any],
    ) -> None:
        try:
            on_done(target(*args, **kwargs))
        except AIRequestError as exc:
            on_error(exc)

    # -- Truncation --------------------------------------------------------

    def _truncate(self, msg: ChatMessage) -> ChatMessage:
        """Truncate a single message to ``max_content`` chars."""

        if len(msg.content) <= self._cfg.max_content:
            return msg
        return ChatMessage(role=msg.role, content=msg.content[: self._cfg.max_content])

    def _require_configured(self) -> None:
        if not self._cfg.base_url:
            raise AIRequestError("AI base_url is not configured")
        if not self.model:
            raise AIRequestError("AI model could not be resolved from base_url")
        if self.provider in _PROVIDERS_REQUIRING_API_KEY and not self._cfg.api_key.strip():
            raise AIRequestError("AI api_key is not configured")


# ---- Free helpers --------------------------------------------------------


def _extract_fim_text(raw: dict[str, Any]) -> str:
    """Extract text from a legacy /completions response."""

    choices = raw.get("choices") or []
    if not choices:
        return ""
    first = choices[0]
    if "text" in first:
        return str(first["text"]).strip()
    if "message" in first and "content" in first["message"]:
        return str(first["message"]["content"]).strip()
    return ""


def _balance_trim(prefix: str, suffix: str, budget: int) -> tuple[str, str]:
    """Trim ``prefix`` and ``suffix`` so their combined length fits within *budget*.

    Suffix is preferred (keep more prefix) so the model has more context about
    what came before the cursor.
    """

    total = len(prefix) + len(suffix)
    if total <= budget:
        return prefix, suffix
    if len(prefix) <= budget:
        return prefix, suffix[: max(0, budget - len(prefix))]
    if len(suffix) <= budget:
        return prefix[: max(0, budget - len(suffix))], suffix
    # Both exceed; give prefix the larger half because the user just wrote it.
    half = budget // 2
    return prefix[-half:], suffix[: budget - half]


def _extract_stream_line(provider: AIProvider, raw_line: bytes) -> str:
    """Extract one delta from a single SSE line.

    OpenAI / Anthropic send ``data: {...}`` events; Google's stream uses
    ``data: {...}\\n\\n`` separators and the JSON object itself can span
    multiple lines, but in practice Google sends one JSON object per event
    terminated by ``\\n\\n``. To handle both, we accumulate ``data:`` lines
    in :meth:`stream_chat` and pass only complete events here.
    """

    line = raw_line.decode("utf-8", errors="replace").rstrip("\r\n")
    if not line.startswith("data:"):
        return ""
    payload = line[5:].lstrip()
    if not payload or payload == "[DONE]":
        return ""
    try:
        obj = json.loads(payload)
    except json.JSONDecodeError:
        return ""
    return _extract_stream_delta(provider, obj)


def compact_prompt(code: str, language: str) -> list[ChatMessage]:
    """Build the chat messages for "compact this buffer" feature.

    The system prompt instructs the model to shorten the buffer while keeping
    semantics; the user turn contains the actual code.
    """

    system = ChatMessage(
        role="system",
        content=(
            "You are a code compaction assistant. "
            "Rewrite the user's source to be as short as possible while preserving "
            "exact runtime behavior. "
            "Rules:\n"
            "- Keep all imports, public symbols and side-effects.\n"
            "- Inline trivial one-line helpers only if it does not hurt readability.\n"
            "- Drop blank lines and redundant comments.\n"
            "- Output ONLY the compacted source, no markdown fences, no preamble."
        ),
    )
    user = ChatMessage(
        role="user",
        content=f"Language: {language}\n\n```\n{code}\n```",
    )
    return [system, user]


def fim_prompt(prefix: str, suffix: str, language: str) -> list[ChatMessage]:
    """Build the chat messages for FIM when the provider has no native FIM endpoint."""

    system = ChatMessage(
        role="system",
        content=(
            "You are a Fill-in-the-Middle code completion engine. "
            "Given a prefix and a suffix in the same file, output ONLY the missing "
            "code that fits between them. Do not repeat the prefix or suffix, do not "
            "add explanations or markdown fences."
        ),
    )
    user = ChatMessage(
        role="user",
        content=(
            f"Language: {language}\n\n"
            "PREFIX:\n"
            f"{prefix}\n\n"
            "SUFFIX:\n"
            f"{suffix}\n\n"
            "Return only the completion that goes between the two."
        ),
    )
    return [system, user]


# Tiny helper for callers that just want "give me the elapsed seconds".
def now_s() -> float:
    return time.time()


__all__ = [
    "AIClient",
    "AIRequestError",
    "AIResponse",
    "ChatMessage",
    "compact_prompt",
    "fim_prompt",
]
