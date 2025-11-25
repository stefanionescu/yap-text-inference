"""Prompt building helpers for chat and tool models using dynamic inputs."""

from __future__ import annotations

import logging
from functools import lru_cache
from collections.abc import Sequence

from .tokens.tokenizer import get_chat_tokenizer

logger = logging.getLogger(__name__)


def build_toolcall_prompt_with_history(
    base_prompt: str,
    user_utt: str,
    history_text: str = "",
) -> str:
    """Build Toolcall prompt with optional history context for KV cache sharing."""
    prompt_parts = [base_prompt.strip()]
    if history_text.strip():
        prompt_parts.append(f"Recent conversation context:\n{history_text.strip()}")
    prompt_parts.append(f"User message:\n{user_utt.strip()}")
    return "\n\n".join(prompt_parts) + "\n"


def build_chat_prompt_with_prefix(
    static_prefix: str,
    runtime_text: str,
    history_text: str,
    user_utt: str,
) -> str:
    """Build the chat prompt using the tokenizer's native chat template."""
    history_turns = _parse_history(history_text)
    system_prompt = _compose_system_prompt(static_prefix, runtime_text)
    messages = _build_messages(system_prompt, history_turns, user_utt)
    return _apply_chat_template(messages, add_generation_prompt=True)


def build_chat_warm_prompt(
    static_prefix: str,
    runtime_text: str,
    history_text: str,
) -> str:
    """Build a prompt that primes persona + history without a fresh user query."""
    history_turns = _parse_history(history_text)
    system_prompt = _compose_system_prompt(static_prefix, runtime_text)
    messages = _build_messages(system_prompt, history_turns, user_utt=None)
    return _apply_chat_template(messages, add_generation_prompt=True)


def _build_messages(
    system_prompt: str,
    history_turns: Sequence[tuple[str, str]],
    user_utt: str | None,
) -> list[dict[str, str]]:
    """Build a list of message dicts for the chat template."""
    messages: list[dict[str, str]] = []

    # System message (if present)
    if system_prompt.strip():
        messages.append({"role": "system", "content": system_prompt.strip()})

    # History turns
    for user_text, assistant_text in history_turns:
        if user_text:
            messages.append({"role": "user", "content": user_text.strip()})
        if assistant_text:
            messages.append({"role": "assistant", "content": assistant_text.strip()})

    # Current user message
    if user_utt is not None:
        messages.append({"role": "user", "content": user_utt.strip()})

    return messages


@lru_cache(maxsize=1)
def _get_cached_tokenizer():
    """Get the chat tokenizer (cached)."""
    return get_chat_tokenizer()


def _apply_chat_template(
    messages: list[dict[str, str]],
    add_generation_prompt: bool = True,
) -> str:
    """Apply the tokenizer's chat template to format messages."""
    tokenizer = _get_cached_tokenizer()
    try:
        return tokenizer.apply_chat_template(messages, add_generation_prompt)
    except RuntimeError as e:
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


def _parse_history(history_text: str) -> list[tuple[str, str]]:
    text = (history_text or "").strip()
    if not text:
        return []

    turns: list[tuple[str, str]] = []
    current_user: list[str] = []
    current_assistant: list[str] = []
    mode: str | None = None

    def _flush() -> None:
        nonlocal current_user, current_assistant, mode
        if not current_user and not current_assistant:
            return
        user_text = "\n".join(current_user).strip()
        assistant_text = "\n".join(current_assistant).strip()
        turns.append((user_text, assistant_text))
        current_user = []
        current_assistant = []
        mode = None

    for line in text.splitlines():
        if line.startswith("User:"):
            _flush()
            current_user = [line[len("User:"):].lstrip()]
            current_assistant = []
            mode = "user"
        elif line.startswith("Assistant:"):
            current_assistant = [line[len("Assistant:"):].lstrip()]
            mode = "assistant"
        else:
            if mode == "assistant":
                current_assistant.append(line)
            elif mode == "user":
                current_user.append(line)
            elif line.strip():
                current_user.append(line)
                mode = "user"

    _flush()
    return [turn for turn in turns if any(turn)]


__all__ = [
    "build_chat_prompt_with_prefix",
    "build_chat_warm_prompt",
    "build_toolcall_prompt_with_history",
]


