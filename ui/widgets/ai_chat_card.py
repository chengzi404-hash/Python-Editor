"""``modules.Uui.widgets.ai_chat_card`` — AI chat sidebar card.

Owns the chat history and a streaming conversation with the :class:`AIClient`.

UI structure:

    +---------------------------------+
    | AI              [Clear] [Stop]  |   <- header
    +---------------------------------+
    |                                 |
    |  [10:31] You                    |
    |  Explain this regex             |
    |                                 |
    |  [10:31] Assistant              |
    |  The regex matches ...          |
    |                                 |   <- scrollable log (UText, disabled)
    |                                 |
    +---------------------------------+
    | > Ask the AI...          [Send] |   <- input row
    +---------------------------------+

The card is intentionally chat-only — it does not execute the AI itself. The
host (CodeEditor) is responsible for:

* calling :meth:`add_user_message` then :meth:`request_assistant_reply`
  with an AIClient (typically via :meth:`AIClient.stream_chat_async`).
* updating the client via :meth:`set_client` whenever settings change.

Callbacks the host can listen to:

* :attr:`on_send` — invoked when the user presses Enter/Send. Receives the
  typed text. Host should reply by calling :meth:`add_user_message` (which
  already happens) and then :meth:`request_assistant_reply`.
"""

from __future__ import annotations

import contextlib
import datetime
import threading
import tkinter as tk
from collections.abc import Callable
from typing import TYPE_CHECKING

from core.ai import AIClient, AIRequestError, AIResponse, ChatMessage
from core.settings.i18n import t

from . import theme
from .button import UButton
from .entry import UEntry
from .frame import UFrame
from .label import ULabel
from .text import UText

if TYPE_CHECKING:
    pass


SendCallback = Callable[[str], None]


class AIChatCard(UFrame):
    """AI chat history + input sidebar card."""

    _PAD = 8

    def __init__(
        self,
        parent,
        *,
        title: str | None = None,
        on_send: SendCallback | None = None,
        **kwargs,
    ) -> None:
        kwargs.setdefault("variant", "panel")
        super().__init__(parent, **kwargs)

        self._title_text = title if title is not None else t("sidebar.ai")
        self._on_send = on_send

        self._client: AIClient | None = None
        self._messages: list[ChatMessage] = []
        self._busy = False
        self._cancel_event: threading.Event | None = None
        self._pending_assistant_text: list[str] = []

        self._build()

    # ---- Construction ----------------------------------------------------

    def _build(self) -> None:
        header = UFrame(self, variant="title", height=26)
        header.pack(fill=tk.X)
        header.pack_propagate(False)

        accent = tk.Frame(header, bg=theme.TITLE_ACCENT, width=theme.TITLE_ACCENT_WIDTH)
        accent.pack(side=tk.LEFT, fill=tk.Y)

        title_label = ULabel(
            header, text=f"  {self._title_text}", variant="secondary", bg=theme.BG_TITLE
        )
        title_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self._clear_btn = UButton(
            header,
            text=t("ai.chat.clear"),
            width=56,
            height=20,
            variant="ghost",
            command=self.clear_history,
        )
        self._clear_btn.pack(side=tk.RIGHT, padx=4, pady=3)

        self._stop_btn = UButton(
            header,
            text=t("ai.chat.stop"),
            width=48,
            height=20,
            variant="warning",
            command=self.cancel_streaming,
        )
        self._stop_btn.pack(side=tk.RIGHT, padx=(0, 2), pady=3)
        self._stop_btn.config(state="disabled")

        body = UFrame(self, variant="base")
        body.pack(fill=tk.BOTH, expand=True, padx=self._PAD, pady=(self._PAD, 4))

        self._log = UText(body, width=40, height=10, wrap="word", show_line_numbers=False)
        self._log.pack(fill=tk.BOTH, expand=True)
        self._log.config(state="disabled")
        self._configure_log_tags()

        input_row = UFrame(self, variant="base")
        input_row.pack(fill=tk.X, padx=self._PAD, pady=(0, self._PAD))

        self._input_var = tk.StringVar()
        self._entry = UEntry(
            input_row, textvariable=self._input_var, placeholder=t("ai.chat.placeholder")
        )
        self._entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 4))
        self._entry._entry.bind("<Return>", self._on_return)

        self._send_btn = UButton(
            input_row,
            text=t("ai.chat.send"),
            width=64,
            height=24,
            variant="primary",
            command=self._on_send_clicked,
        )
        self._send_btn.pack(side=tk.RIGHT)

        self._set_busy(False)

    def _configure_log_tags(self) -> None:
        text = self._log._text
        text.tag_configure("role_user", foreground=theme.BLUE, font=theme.LABEL_FONT_BOLD)
        text.tag_configure("role_assistant", foreground=theme.GREEN, font=theme.LABEL_FONT_BOLD)
        text.tag_configure("role_system", foreground=theme.YELLOW, font=theme.LABEL_FONT_BOLD)
        text.tag_configure("role_error", foreground=theme.RED, font=theme.LABEL_FONT_BOLD)
        text.tag_configure("timestamp", foreground=theme.FG_DIM, font=theme.LABEL_FONT_SMALL)
        text.tag_configure("body", foreground=theme.FG_PRIMARY)
        text.tag_configure("placeholder", foreground=theme.FG_DIM)

    # ---- Public API -------------------------------------------------------

    def set_client(self, client: AIClient | None) -> None:
        """Attach (or replace) the AI client used for streaming replies."""

        self._client = client

    def set_on_send(self, callback: SendCallback | None) -> None:
        """Replace the callback invoked when the user submits a message."""

        self._on_send = callback

    def add_user_message(self, text: str) -> None:
        """Append a user turn to the log and to the conversation history."""

        self._append_turn("user", t("ai.chat.you"), text)
        self._messages.append(ChatMessage(role="user", content=text))
        # Cancel any in-flight assistant reply if the user interrupts.
        self.cancel_streaming()

    def add_assistant_message(self, text: str) -> None:
        """Append a complete (non-streaming) assistant reply to history."""

        self._append_turn("assistant", t("ai.chat.assistant"), text)
        if text:
            self._messages.append(ChatMessage(role="assistant", content=text))

    def add_system_message(self, text: str, *, level: str = "system") -> None:
        """Append a system/info/error line to the log (not added to history)."""

        role_label = {
            "system": t("ai.chat.system"),
            "error": t("ai.chat.error", message=""),
        }.get(level, t("ai.chat.system"))
        self._append_turn(level, role_label, text)

    def set_system_prompt(self, text: str) -> None:
        """Replace the persistent system prompt (kept as the first history entry)."""

        if self._messages and self._messages[0].role == "system":
            self._messages[0] = ChatMessage(role="system", content=text)
        else:
            self._messages.insert(0, ChatMessage(role="system", content=text))

    def clear_history(self) -> None:
        """Drop the conversation log and history."""

        self.cancel_streaming()
        self._messages.clear()
        self._log.config(state="normal")
        self._log.clear()
        self._log.config(state="disabled")

    def get_history(self) -> list[ChatMessage]:
        """Return a copy of the in-memory conversation history."""

        return list(self._messages)

    def cancel_streaming(self) -> None:
        """Ask the in-flight stream to stop, if any."""

        if self._cancel_event is not None:
            self._cancel_event.set()

    # ---- Streaming --------------------------------------------------------

    def request_assistant_reply(
        self,
        *,
        on_complete: Callable[[AIResponse | None, Exception | None], None] | None = None,
    ) -> bool:
        """Kick off a streaming assistant reply. Returns False if not possible.

        Updates the conversation log incrementally. *on_complete* is called
        once on the Tk main thread with either the final :class:`AIResponse`
        or an :class:`AIRequestError`.
        """

        if self._busy:
            return False
        client = self._client
        if client is None or not client.is_configured():
            self.add_system_message(t("ai.chat.no_provider"), level="error")
            if on_complete is not None:
                on_complete(None, AIRequestError("AI is not configured"))
            return False

        self._pending_assistant_text = []
        self._append_turn_header("assistant", t("ai.chat.assistant"))
        # Reserve an empty line for the streaming body — we'll fill it incrementally.
        self._log.config(state="normal")
        text_widget = self._log._text
        text_widget.insert(tk.END, t("ai.chat.thinking") + "\n", ("body", "placeholder"))
        text_widget.see(tk.END)
        self._log.config(state="disabled")
        self._pending_assistant_text.append("")

        self._cancel_event = threading.Event()
        self._set_busy(True)

        def _on_chunk(chunk: str) -> None:
            self._schedule_stream_chunk(chunk)

        def _on_done(response: AIResponse) -> None:
            self._schedule_stream_done(response, on_complete)

        def _on_error(err: AIRequestError) -> None:
            self._schedule_stream_error(err, on_complete)

        client.stream_chat_async(
            list(self._messages),
            _on_chunk,
            _on_done,
            _on_error,
            self._cancel_event,
        )
        return True

    # ---- Internal: log rendering -----------------------------------------

    def _append_turn(self, role: str, label: str, body: str) -> None:
        self._append_turn_header(role, label)
        self._log.config(state="normal")
        text_widget = self._log._text
        text_widget.insert(tk.END, body.rstrip("\n") + "\n\n", ("body",))
        text_widget.see(tk.END)
        self._log.config(state="disabled")

    def _append_turn_header(self, role: str, label: str) -> None:
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        self._log.config(state="normal")
        text_widget = self._log._text
        text_widget.insert(tk.END, f"[{ts}] ", ("timestamp",))
        text_widget.insert(tk.END, f"{label}\n", (f"role_{role}",))
        self._log.config(state="disabled")

    # ---- Internal: streaming scheduling ----------------------------------

    def _schedule_stream_chunk(self, chunk: str) -> None:
        """Bounce a streamed chunk from the worker thread back to the Tk loop."""

        with contextlib.suppress(tk.TclError):
            self.after(0, self._render_stream_chunk, chunk)

    def _render_stream_chunk(self, chunk: str) -> None:
        if not self._pending_assistant_text:
            return
        text_widget = self._log._text
        self._log.config(state="normal")
        # Replace the placeholder ("Thinking...") with the first real chunk,
        # then append subsequent chunks to the last line.
        if not self._pending_assistant_text[0]:
            # Drop the placeholder line.
            end_index = text_widget.index(f"{tk.END} - 1 lines")
            line_start = f"{end_index}"
            text_widget.delete(line_start, tk.END)
            self._pending_assistant_text[0] = chunk
            text_widget.insert(tk.END, chunk, ("body",))
        else:
            self._pending_assistant_text.append(chunk)
            text_widget.insert(tk.END, chunk, ("body",))
        text_widget.see(tk.END)
        self._log.config(state="disabled")

    def _schedule_stream_done(
        self,
        response: AIResponse,
        on_complete: Callable[[AIResponse | None, Exception | None], None] | None,
    ) -> None:
        with contextlib.suppress(tk.TclError):
            self.after(0, self._render_stream_done, response, on_complete)

    def _render_stream_done(
        self,
        response: AIResponse,
        on_complete: Callable[[AIResponse | None, Exception | None], None] | None,
    ) -> None:
        # Finalise log: trim trailing whitespace, add a blank line.
        text_widget = self._log._text
        self._log.config(state="normal")
        text_widget.insert(tk.END, "\n\n", ("body",))
        text_widget.see(tk.END)
        self._log.config(state="disabled")
        full_text = response.text or "".join(self._pending_assistant_text)
        self._pending_assistant_text = []
        if full_text:
            self._messages.append(ChatMessage(role="assistant", content=full_text))
        self._cancel_event = None
        self._set_busy(False)
        if on_complete is not None:
            on_complete(response, None)

    def _schedule_stream_error(
        self,
        err: AIRequestError,
        on_complete: Callable[[AIResponse | None, Exception | None], None] | None,
    ) -> None:
        with contextlib.suppress(tk.TclError):
            self.after(0, self._render_stream_error, err, on_complete)

    def _render_stream_error(
        self,
        err: AIRequestError,
        on_complete: Callable[[AIResponse | None, Exception | None], None] | None,
    ) -> None:
        text_widget = self._log._text
        self._log.config(state="normal")
        # Replace the placeholder ("Thinking...") with the error message.
        end_index = text_widget.index(f"{tk.END} - 1 lines")
        line_start = f"{end_index}"
        text_widget.delete(line_start, tk.END)
        text_widget.insert(
            tk.END,
            t("ai.chat.error", message=str(err)) + "\n\n",
            ("role_error",),
        )
        text_widget.see(tk.END)
        self._log.config(state="disabled")
        self._pending_assistant_text = []
        self._cancel_event = None
        self._set_busy(False)
        if on_complete is not None:
            on_complete(None, err)

    # ---- Internal: state --------------------------------------------------

    def _set_busy(self, busy: bool) -> None:
        self._busy = busy
        if busy:
            self._stop_btn.config(state="normal")
            self._send_btn.config(state="disabled")
            with contextlib.suppress(tk.TclError):
                self._entry._entry.config(state="disabled")
        else:
            self._stop_btn.config(state="disabled")
            self._send_btn.config(state="normal")
            with contextlib.suppress(tk.TclError):
                self._entry._entry.config(state="normal")

    def _on_return(self, _event=None) -> str:
        self._on_send_clicked()
        return "break"

    def _on_send_clicked(self) -> None:
        if self._busy:
            return
        text = self._entry.get().strip()
        if not text:
            return
        self._entry.set("")
        self.add_user_message(text)
        if self._on_send is not None:
            try:
                self._on_send(text)
            except Exception as exc:
                self.add_system_message(str(exc), level="error")
            return
        # Default: immediately try to stream a reply.
        self.request_assistant_reply()

    def _apply_theme(self) -> None:
        with contextlib.suppress(tk.TclError):
            super()._apply_theme()
        self._configure_log_tags()


__all__ = ["AIChatCard"]
