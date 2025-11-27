"""Prompt building helpers for chat and tool models using dynamic inputs."""

from __future__ import annotations

import logging
from functools import lru_cache
from collections.abc import Sequence

from .config import CHAT_TEMPLATE_ENABLE_THINKING
from .tokens.tokenizer import get_chat_tokenizer, get_tool_tokenizer

logger = logging.getLogger(__name__)

# Chat templates like Qwen3 emit `<think>` sections by default. The toggle lives
# in config so deployments can reason about it centrally (default: disabled).
_CHAT_TEMPLATE_DEFAULT_KWARGS = {"enable_thinking": CHAT_TEMPLATE_ENABLE_THINKING}


def build_toolcall_prompt_with_prefix(
    base_prompt: str,
    user_utt: str,
    prefix_text: str = "",
) -> str:
    """Build the tool prompt using the tokenizer's native chat template."""
    history_turns = _parse_history(prefix_text)
    system_prompt = (base_prompt or "").strip()
    messages = _build_messages(system_prompt, history_turns, user_utt)
    if not messages:
        return ""
    return _apply_tool_chat_template(messages, add_generation_prompt=True)


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


@lru_cache(maxsize=1)
def _get_cached_chat_tokenizer():
    """Get the chat tokenizer (cached)."""
    return get_chat_tokenizer()


@lru_cache(maxsize=1)
def _get_cached_tool_tokenizer():
    """Get the tool tokenizer (cached)."""
    return get_tool_tokenizer()


def _apply_chat_template(
    messages: list[dict[str, str]],
    add_generation_prompt: bool = True,
) -> str:
    """Apply the tokenizer's chat template to format messages."""
    tokenizer = _get_cached_chat_tokenizer()
    try:
        return tokenizer.apply_chat_template(
            messages,
            add_generation_prompt,
            **_CHAT_TEMPLATE_DEFAULT_KWARGS,
        )
    except (RuntimeError, ValueError) as e:
        # Fallback to basic ChatML if no chat template available
        logger.warning("Chat template not available, falling back to ChatML: %s", e)
        return _build_chatml_prompt_from_messages(messages, add_generation_prompt)


def _apply_tool_chat_template(
    messages: list[dict[str, str]],
    add_generation_prompt: bool = True,
) -> str:
    """Apply the tool tokenizer's chat template to format messages."""
    tokenizer = _get_cached_tool_tokenizer()
    try:
        return tokenizer.apply_chat_template(
            messages,
            add_generation_prompt,
            **_CHAT_TEMPLATE_DEFAULT_KWARGS,
        )
    except (RuntimeError, ValueError) as e:
        logger.warning("Tool template not available, falling back to ChatML: %s", e)
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
    "build_toolcall_prompt_with_prefix",
]
