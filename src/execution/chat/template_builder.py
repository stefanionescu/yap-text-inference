"""Chat prompt construction using tokenizer templates."""

from __future__ import annotations

import logging
from collections.abc import Sequence
from src.state.session import ChatMessage
from src.tokens.tokenizer import FastTokenizer
from src.config.chat import CHAT_TEMPLATE_ENABLE_THINKING

logger = logging.getLogger(__name__)

# Chat templates like Qwen3 emit `<think>` sections by default. The toggle lives
# in config so deployments can reason about it centrally (default: disabled).
_CHAT_TEMPLATE_DEFAULT_KWARGS = {"enable_thinking": CHAT_TEMPLATE_ENABLE_THINKING}


def _build_messages(
    system_prompt: str,
    history_messages: Sequence[ChatMessage],
    chat_user_utt: str | None,
) -> list[dict[str, str]]:
    """Build message dicts for the tokenizer chat template."""
    messages: list[dict[str, str]] = []

    def _append_message(role: str, content: str) -> None:
        content = content.strip()
        if not content:
            return
        if messages and messages[-1]["role"] == role:
            messages[-1]["content"] += "\n\n" + content
            return
        messages.append({"role": role, "content": content})

    if system_prompt.strip():
        messages.append({"role": "system", "content": system_prompt.strip()})

    for message in history_messages:
        _append_message(message.role, message.content)

    if chat_user_utt is not None:
        _append_message("user", chat_user_utt)

    return messages


def _build_chatml_prompt_from_messages(
    messages: list[dict[str, str]],
    add_generation_prompt: bool,
) -> str:
    """Fallback builder when the tokenizer has no chat template."""
    lines: list[str] = []
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        lines.extend([f"<|im_start|>{role}", content, "<|im_end|>"])
    if add_generation_prompt:
        lines.append("<|im_start|>assistant")
    return "\n".join(lines)


def _apply_chat_template(
    chat_tokenizer: FastTokenizer,
    messages: list[dict[str, str]],
    *,
    add_generation_prompt: bool = True,
) -> str:
    """Apply the tokenizer chat template with a ChatML fallback."""
    try:
        return chat_tokenizer.apply_chat_template(
            messages,
            add_generation_prompt,
            **_CHAT_TEMPLATE_DEFAULT_KWARGS,
        )
    except (RuntimeError, ValueError) as exc:
        logger.warning("Chat template not available, falling back to ChatML: %s", exc)
        return _build_chatml_prompt_from_messages(messages, add_generation_prompt)


def _compose_system_prompt(static_prefix: str, runtime_text: str) -> str:
    parts = [segment.strip() for segment in (static_prefix, runtime_text) if segment and segment.strip()]
    return "\n\n".join(parts)


def build_chat_prompt_with_prefix(
    static_prefix: str,
    runtime_text: str,
    history_messages: list[ChatMessage],
    chat_user_utt: str,
    chat_tokenizer: FastTokenizer,
) -> str:
    """Build a chat prompt including the current user turn."""
    system_prompt = _compose_system_prompt(static_prefix, runtime_text)
    messages = _build_messages(system_prompt, history_messages, chat_user_utt)
    return _apply_chat_template(chat_tokenizer, messages, add_generation_prompt=True)


def build_chat_warm_prompt(
    static_prefix: str,
    runtime_text: str,
    history_messages: list[ChatMessage],
    chat_tokenizer: FastTokenizer,
) -> str:
    """Build a prompt that warms persona and history without a new user turn."""
    system_prompt = _compose_system_prompt(static_prefix, runtime_text)
    messages = _build_messages(system_prompt, history_messages, chat_user_utt=None)
    return _apply_chat_template(chat_tokenizer, messages, add_generation_prompt=True)


__all__ = ["build_chat_prompt_with_prefix", "build_chat_warm_prompt"]
