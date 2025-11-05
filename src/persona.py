"""Prompt building helpers for chat and tool models using dynamic inputs."""

from __future__ import annotations


def build_toolcall_prompt_with_history(base_prompt: str, user_utt: str, history_text: str = "") -> str:
    """Build Toolcall prompt with optional history context for KV cache sharing."""
    prompt_parts = [base_prompt.strip()]
    if history_text.strip():
        prompt_parts.append(f"Recent conversation context:\n{history_text.strip()}")
    prompt_parts.append(f"User message:\n{user_utt.strip()}")
    return "\n\n".join(prompt_parts) + "\n"


def build_chat_prompt_with_prefix(static_prefix: str, runtime_text: str, history_text: str, user_utt: str) -> str:
    return (
        f"<|persona|>\n{static_prefix.strip()}\n"
        f"<|history|>\n{history_text.strip()}\n"
        f"<|runtime|>\n{runtime_text.strip()}\n"
        f"<|user|>\n{user_utt.strip()}\n<|assistant|>\n"
    )

