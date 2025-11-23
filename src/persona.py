"""Prompt building helpers for chat and tool models using dynamic inputs."""

from __future__ import annotations

from functools import lru_cache
from collections.abc import Sequence

from .config import CHAT_MODEL
from .config.chat_prompt import ChatPromptFormat, get_prompt_format_for_model

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
    """Build the chat prompt that is fed into the chat model."""
    prompt_format = _active_prompt_format()
    history_turns = _parse_history(history_text)
    system_prompt = _compose_system_prompt(static_prefix, runtime_text)
    if prompt_format is ChatPromptFormat.CHATML:
        return _build_chatml_prompt(system_prompt, history_turns, user_utt)
    if prompt_format is ChatPromptFormat.MISTRAL_INSTRUCT:
        return _build_mistral_prompt(system_prompt, history_turns, user_utt)
    return _build_dreamgen_prompt(system_prompt, history_turns, user_utt)


def build_chat_warm_prompt(
    static_prefix: str,
    runtime_text: str,
    history_text: str,
) -> str:
    """Build a prompt that primes persona + history without a fresh user query."""
    prompt_format = _active_prompt_format()
    history_turns = _parse_history(history_text)
    system_prompt = _compose_system_prompt(static_prefix, runtime_text)
    if prompt_format is ChatPromptFormat.CHATML:
        return _build_chatml_prompt(system_prompt, history_turns, user_utt=None)
    if prompt_format is ChatPromptFormat.MISTRAL_INSTRUCT:
        return _build_mistral_prompt(system_prompt, history_turns, user_utt=None)
    return _build_dreamgen_prompt(system_prompt, history_turns, user_utt=None)


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


def _build_chatml_prompt(
    system_prompt: str,
    history_turns: Sequence[tuple[str, str]],
    user_utt: str | None,
) -> str:
    lines: list[str] = ["<|im_start|>system", system_prompt, "<|im_end|>"]

    for user_text, assistant_text in history_turns:
        if user_text:
            lines.extend(("<|im_start|>user", user_text, "<|im_end|>"))
        if assistant_text:
            lines.extend(("<|im_start|>assistant", assistant_text, "<|im_end|>"))

    if user_utt is not None:
        lines.extend(("<|im_start|>user", user_utt.strip(), "<|im_end|>"))

    lines.append("<|im_start|>assistant")
    return "\n".join(lines)


def _build_mistral_prompt(
    system_prompt: str,
    history_turns: Sequence[tuple[str, str]],
    user_utt: str | None,
) -> str:
    """Render prompts using the mistral-common instruct template (V7)."""
    system_text = system_prompt.strip()
    parts: list[str] = []
    has_turn = False

    def _format_user_block(content: str | None, include_system: bool) -> str:
        user_text = (content or "").strip()
        prefix = "<s>" if include_system else ""
        sys_segment = (
            f"[SYSTEM_PROMPT]{system_text}[/SYSTEM_PROMPT]" if include_system and system_text else ""
        )
        return f"{prefix}{sys_segment}[INST]{user_text}[/INST]"

    def _append_assistant_block(content: str | None) -> None:
        assistant_text = (content or "").strip()
        if assistant_text:
            parts.append(assistant_text)
        parts.append("</s>")

    for user_text, assistant_text in history_turns:
        if not user_text and not assistant_text:
            continue
        parts.append(_format_user_block(user_text, include_system=not has_turn))
        has_turn = True
        if assistant_text:
            _append_assistant_block(assistant_text)

    if user_utt is not None:
        parts.append(_format_user_block(user_utt, include_system=not has_turn))
    elif not has_turn:
        parts.append(_format_user_block("", include_system=True))

    return "".join(parts)


def _build_dreamgen_prompt(
    system_prompt: str,
    history_turns: Sequence[tuple[str, str]],
    user_utt: str | None,
) -> str:
    """Render prompts for DreamGen's ChatML extension with `text` role replies."""
    lines: list[str] = ["<|im_start|>system", system_prompt.strip(), "<|im_end|>"]

    def _append_block(role: str, content: str | None) -> None:
        text = (content or "").strip()
        if not text:
            return
        lines.extend((f"<|im_start|>{role}", text, "<|im_end|>"))

    for user_text, assistant_text in history_turns:
        _append_block("user", user_text)
        _append_block("text", assistant_text)

    if user_utt is not None:
        _append_block("user", user_utt)

    lines.append("<|im_start|>text")
    return "\n".join(lines)


@lru_cache(maxsize=1)
def _active_prompt_format() -> ChatPromptFormat:
    return get_prompt_format_for_model(CHAT_MODEL)


__all__ = [
    "build_chat_prompt_with_prefix",
    "build_chat_warm_prompt",
    "build_toolcall_prompt_with_history",
]


