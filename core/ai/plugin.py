"""AI Assistant Plugin — FIM, chat, compact, skills marketplace."""

from __future__ import annotations

import contextlib
import logging
import tkinter as tk
from typing import Any

from core.plugins.api import PluginContext, PluginManifest
from core.plugins.hooks import HookEvents

MANIFEST = PluginManifest(
    id="ai_assistant",
    name="AI Assistant",
    version="1.0.0",
    description="AI-powered FIM, chat, compact, and skills marketplace",
    author="Python Editor Team",
    scope="system",
)

_log = logging.getLogger("ai.plugin")


def register(ctx: PluginContext) -> None:
    editor = ctx.editor
    if editor is None:
        _log.error("No editor attached, skipping AI plugin")
        return

    gs = editor._settings.global_settings
    text_widget = editor._editor._text

    # ------------------------------------------------------------------
    # 1. AI client, skill registry, marketplace provider
    # ------------------------------------------------------------------
    from core.ai import AIClient, AISkillMarketplaceProvider, AISkillRegistry

    def _build_client() -> Any:
        return AIClient(
            base_url=str(gs.get("ai.base_url", "https://api.openai.com/v1") or ""),
            api_key=str(gs.get("ai.api_key", "") or ""),
            model=str(gs.get("ai.model", "") or ""),
            provider=str(gs.get("ai.provider", "auto") or "auto"),
            timeout_s=float(gs.get("ai.timeout_s", 60) or 60),
            max_content=int(gs.get("ai.max_content", 8000) or 8000),
            fim_model=str(gs.get("ai.fim_model", "") or ""),
            reasoning_effort=str(gs.get("ai.reasoning_effort", "") or ""),
        )

    client = _build_client()

    def _settings_root_dir() -> str:
        import os

        from core.settings.settings.global_settings import default_global_path

        return os.path.dirname(default_global_path())

    registry = AISkillRegistry(_settings_root_dir())
    marketplace = AISkillMarketplaceProvider(
        index_url=str(gs.get("ai.skills_marketplace_url", "") or "")
    )
    from core.plugins import plugin_marketplace

    plugin_marketplace.get_plugin_marketplace().register_provider(marketplace)

    fim_epoch: int = 0

    # ------------------------------------------------------------------
    # 2. Settings snapshot + listener
    # ------------------------------------------------------------------
    def _ai_settings() -> dict:
        return {
            "provider": str(gs.get("ai.provider", "auto") or "auto"),
            "base_url": str(gs.get("ai.base_url", "") or ""),
            "model": str(gs.get("ai.model", "") or ""),
            "api_key": str(gs.get("ai.api_key", "") or ""),
            "timeout_s": float(gs.get("ai.timeout_s", 60) or 60),
            "max_content": int(gs.get("ai.max_content", 8000) or 8000),
            "fim_model": str(gs.get("ai.fim_model", "") or ""),
            "reasoning_effort": str(gs.get("ai.reasoning_effort", "") or ""),
            "fim_enabled": bool(gs.get("ai.fim_enabled", True)),
            "skills_marketplace_url": str(gs.get("ai.skills_marketplace_url", "") or ""),
        }

    def _apply_ai_settings() -> None:
        snap = _ai_settings()
        if client is not None:
            client.configure(**snap)
        if hasattr(editor, "_ai_chat_card") and editor._ai_chat_card is not None:
            editor._ai_chat_card.set_client(client)
        if marketplace is not None:
            marketplace.set_index_url(snap["skills_marketplace_url"])

    def _on_ai_settings_changed(event) -> None:
        if event.key is None:
            return
        if event.key.startswith("ai."):
            _apply_ai_settings()

    gs.add_listener(_on_ai_settings_changed)

    # ------------------------------------------------------------------
    # 3. AI Chat card (sidebar)
    # ------------------------------------------------------------------
    from ui.widgets.ai_chat_card import AIChatCard

    def _chat_on_send(text: str) -> None:
        card = getattr(editor, "_ai_chat_card", None)
        if card is None:
            return
        if registry is not None and not card.get_history():
            active = registry.active
            if active is not None and active.system_prompt:
                card.set_system_prompt(active.system_prompt)
        card.request_assistant_reply()

    chat_card = AIChatCard(editor._sidebar, on_send=_chat_on_send)
    chat_card.set_client(client)
    if registry.active is not None and registry.active.system_prompt:
        chat_card.set_system_prompt(registry.active.system_prompt)
    editor._sidebar.add_card("ai", chat_card)
    editor._ai_chat_card = chat_card

    # ------------------------------------------------------------------
    # 4. Helper: open AI chat
    # ------------------------------------------------------------------
    def _open_ai_chat() -> None:
        if hasattr(editor, "_sidebar") and editor._sidebar is not None:
            with contextlib.suppress(Exception):
                editor._sidebar.set_active("ai")
        if chat_card is not None:
            with contextlib.suppress(Exception):
                chat_card._entry._entry.focus_set()

    editor._open_ai_chat = _open_ai_chat

    # ------------------------------------------------------------------
    # 5. AI FIM (Fill-in-the-Middle) — renders ghost text via editor
    # ------------------------------------------------------------------
    def _render_fim_ghost_text(text: str, fim_epoch_ref: int) -> None:
        nonlocal fim_epoch
        if fim_epoch_ref != fim_epoch:
            return
        if not text:
            return
        first_line = text.split("\n", 1)[0]
        if not first_line.strip():
            return
        editor._show_ghost_text(first_line)
        if "\n" in text:
            remainder = text.split("\n", 1)[1]
            from core.settings.i18n import t

            editor._append_output(
                f"{t('ai.tab_complete.inserted', chars=len(text))}\n{remainder}\n",
                "system",
            )

    def _ai_tab_complete() -> None:
        nonlocal fim_epoch
        snap = _ai_settings()
        if not snap.get("fim_enabled", True):
            return
        from core.ai import AIRequestError

        if client is None or not client.is_configured():
            tk.messagebox.showwarning(
                "AI",
                "No AI provider configured. Please set AI settings first.",
                parent=editor.window,
            )
            return
        try:
            code = editor._editor.get("1.0", "end-1c")
        except tk.TclError:
            return
        try:
            cursor = text_widget.index(tk.INSERT)
            line, col = (int(p) for p in cursor.split("."))
        except (tk.TclError, ValueError, IndexError):
            return
        offset = sum(len(line_text) + 1 for line_text in code.split("\n")[: line - 1]) + col
        prefix = code[:offset]
        suffix = code[offset:]
        if not prefix.strip():
            editor._append_output("Streaming FIM response...\n", "system")
        fim_epoch += 1
        cur_epoch = fim_epoch

        def _on_done(response) -> None:
            text = (response.text or "").strip()
            editor.window.after(0, _render_fim_ghost_text, text, cur_epoch)

        def _on_error(err: AIRequestError) -> None:
            editor.window.after(
                0,
                lambda: editor._append_output(f"FIM error: {err}\n", "system"),
            )

        client.request_async(client.fim, _on_done, _on_error, prefix, suffix)

    # ------------------------------------------------------------------
    # 6. AI Compact Buffer
    # ------------------------------------------------------------------
    def _apply_compact_result(new_code: str) -> None:
        if not new_code.strip():
            editor._append_output("Compact error: empty response\n", "system")
            return
        try:
            editor._editor._text.delete("1.0", tk.END)
            editor._editor._text.insert("1.0", new_code)
            editor._editor._text.mark_set(tk.INSERT, "1.0")
            editor._editor._text.see("1.0")
            editor._mark_dirty()
            editor._apply_highlight()
            editor._append_output(f"Compact done ({len(new_code)} chars)\n", "system")
        except tk.TclError:
            pass

    def _ai_compact_buffer() -> None:
        from core.ai import AIRequestError
        from core.ai.client import compact_prompt

        if client is None or not client.is_configured():
            tk.messagebox.showwarning(
                "AI",
                "No AI provider configured.",
                parent=editor.window,
            )
            return
        try:
            code = editor._editor.get("1.0", "end-1c")
        except tk.TclError:
            return
        language = getattr(editor, "_lang", "Python")
        messages = compact_prompt(code, language)

        def _on_done(response) -> None:
            editor.window.after(0, _apply_compact_result, response.text or "")

        def _on_error(err: AIRequestError) -> None:
            editor.window.after(
                0,
                lambda: editor._append_output(f"Compact error: {err}\n", "system"),
            )

        client.request_async(
            client.chat,
            _on_done,
            _on_error,
            messages,
            max_tokens=2048,
            temperature=0.1,
        )

    # ------------------------------------------------------------------
    # 7. AI Skills Marketplace
    # ------------------------------------------------------------------
    def _open_ai_skill_marketplace() -> None:
        if registry is None or marketplace is None:
            return
        from ui.widgets.ai_skills_window import AISkillsWindow

        def _on_skill_activated(skill) -> None:
            if client is None or skill is None:
                return
            if skill.system_prompt and chat_card is not None:
                chat_card.set_system_prompt(skill.system_prompt)
            if skill.model_override:
                editor._write_setting(
                    editor._settings.global_settings.scope,
                    "ai.model",
                    skill.model_override,
                )

        AISkillsWindow(
            editor,
            registry=registry,
            provider=marketplace,
            on_skill_activated=_on_skill_activated,
        )

    # ------------------------------------------------------------------
    # 8. AI commands (registered into Plugins → AI sub-menu)
    # ------------------------------------------------------------------
    from core.plugins.manager import PluginManager
    from core.settings.i18n import t

    ctx.add_command(
        label=t("menu.ai.tab_complete"),
        menu="AI",
        callback=_ai_tab_complete,
        shortcut="Alt+\\",
    )
    ctx.add_command(
        label=t("menu.ai.chat"),
        menu="AI",
        callback=_open_ai_chat,
        shortcut="Ctrl+Shift+L",
    )
    ctx.add_command(
        label=t("menu.ai.compact"),
        menu="AI",
        callback=_ai_compact_buffer,
        shortcut="Ctrl+Shift+K",
    )
    ctx.add_command(
        label=t("menu.ai.skills_marketplace"),
        menu="AI",
        callback=_open_ai_skill_marketplace,
    )

    tk_shortcut = PluginManager._tk_shortcut
    editor.window.bind(tk_shortcut("Alt+\\"), lambda e: _ai_tab_complete(), add="+")
    editor.window.bind(tk_shortcut("Ctrl+Shift+L"), lambda e: _open_ai_chat(), add="+")
    editor.window.bind(tk_shortcut("Ctrl+Shift+K"), lambda e: _ai_compact_buffer(), add="+")

    # ------------------------------------------------------------------
    # 9. Hook subscriptions
    # ------------------------------------------------------------------
    @ctx.on(HookEvents.EDITOR_THEME_CHANGED)
    def _on_theme_changed(name: str) -> None:
        if hasattr(editor, "_ghost_text") and editor._ghost_text is not None:
            editor._ghost_text.hide()

    @ctx.on(HookEvents.EDITOR_CLOSING)
    def _on_closing() -> None:
        _cleanup()

    # ------------------------------------------------------------------
    # 10. Cleanup
    # ------------------------------------------------------------------
    def _cleanup() -> None:
        nonlocal chat_card, marketplace
        if chat_card is not None:
            with contextlib.suppress(Exception):
                chat_card.destroy()
            chat_card = None
        if marketplace is not None:
            with contextlib.suppress(Exception):
                plugin_marketplace.get_plugin_marketplace().unregister_provider(marketplace.name())
            marketplace = None
        for attr in ("_ai_chat_card", "_open_ai_chat"):
            if hasattr(editor, attr):
                with contextlib.suppress(Exception):
                    delattr(editor, attr)

    ctx.on_unregister(_cleanup)
