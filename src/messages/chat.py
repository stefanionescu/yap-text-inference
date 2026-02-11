"""Prompt building helpers for chat prompts using dynamic inputs.

This module provides functions to build chat prompts using the tokenizer's
native chat template. It handles system prompts, conversation history,
and proper role alternation required by various model templates.

Key Functions:
    build_chat_prompt_with_prefix: Build a complete chat prompt with user query
    build_chat_warm_prompt: Build a prompt for warming persona/history without query
"""

from __future__ import annotations

import logging
from collections.abc import Sequence

from src.tokens.tokenizer import FastTokenizer

from ..config.chat import CHAT_TEMPLATE_ENABLE_THINKING
from ..handlers.session.history import parse_history_as_tuples

logger = logging.getLogger(__name__)

# Chat templates like Qwen3 emit `<think>` sections by default. The toggle lives
# in config so deployments can reason about it centrally (default: disabled).
_CHAT_TEMPLATE_DEFAULT_KWARGS = {"enable_thinking": CHAT_TEMPLATE_ENABLE_THINKING}


# ============================================================================
# Public API
# ============================================================================


def build_chat_prompt_with_prefix(
    static_prefix: str,
    runtime_text: str,
    history_text: str,
    user_utt: str,
    chat_tokenizer: FastTokenizer,
) -> str:
    """Build the chat prompt using the tokenizer's native chat template."""
    history_turns = parse_history_as_tuples(history_text)
    system_prompt = _compose_system_prompt(static_prefix, runtime_text)
    messages = _build_messages(system_prompt, history_turns, user_utt)
    return _apply_chat_template(chat_tokenizer, messages, add_generation_prompt=True)


def build_chat_warm_prompt(
    static_prefix: str,
    runtime_text: str,
    history_text: str,
    chat_tokenizer: FastTokenizer,
) -> str:
    """Build a prompt that primes persona + history without a fresh user query."""
    history_turns = parse_history_as_tuples(history_text)
    system_prompt = _compose_system_prompt(static_prefix, runtime_text)
    messages = _build_messages(system_prompt, history_turns, user_utt=None)
    return _apply_chat_template(chat_tokenizer, messages, add_generation_prompt=True)


# ============================================================================
# Internal Helpers
# ============================================================================


def _build_messages(
    system_prompt: str,
    history_turns: Sequence[tuple[str, str]],
    user_utt: str | None,
) -> list[dict[str, str]]:
    """Build a list of message dicts for the chat template.

    Ensures proper role alternation (user/assistant/user/assistant) as required
    by some tokenizer templates (e.g., Gemma 3). Consecutive messages of the
    same role are merged together.
    """
    messages: list[dict[str, str]] = []

    def _append_message(role: str, content: str) -> None:
        """Append a message, merging with previous if same role."""
        content = content.strip()
        if not content:
            return
        if messages and messages[-1]["role"] == role:
            # Merge with previous message of same role
            messages[-1]["content"] += "\n\n" + content
        else:
            messages.append({"role": role, "content": content})

    # System message (if present)
    if system_prompt.strip():
        messages.append({"role": "system", "content": system_prompt.strip()})

    # History turns
    for user_text, assistant_text in history_turns:
        if user_text:
            _append_message("user", user_text)
        if assistant_text:
            _append_message("assistant", assistant_text)

    # Current user message
    if user_utt is not None:
        _append_message("user", user_utt)

    return messages


def _apply_chat_template(
    chat_tokenizer: FastTokenizer,
    messages: list[dict[str, str]],
    add_generation_prompt: bool = True,
) -> str:
    """Apply the tokenizer's chat template to format messages."""
    try:
        return chat_tokenizer.apply_chat_template(
            messages,
            add_generation_prompt,
            **_CHAT_TEMPLATE_DEFAULT_KWARGS,
        )
    except (RuntimeError, ValueError) as e:
        # Fallback to basic ChatML if no chat template available
        logger.warning("Chat template not available, falling back to ChatML: %s", e)
        return _build_chatml_prompt_from_messages(messages, add_generation_prompt)


def _build_chatml_prompt_from_messages(
    messages: list[dict[str, str]],
    add_generation_prompt: bool,
) -> str:
    """Fallback: Build ChatML format prompt from messages."""
    lines: list[str] = []
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        lines.extend([f"<|im_start|>{role}", content, "<|im_end|>"])
    if add_generation_prompt:
        lines.append("<|im_start|>assistant")
    return "\n".join(lines)


def _compose_system_prompt(static_prefix: str, runtime_text: str) -> str:
    parts = [segment.strip() for segment in (static_prefix, runtime_text) if segment and segment.strip()]
    return "\n\n".join(parts)


__all__ = [
    "build_chat_prompt_with_prefix",
    "build_chat_warm_prompt",
]
