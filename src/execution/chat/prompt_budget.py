"""Exact chat prompt budgeting helpers."""

from __future__ import annotations

from dataclasses import dataclass
from src.state.session import ChatMessage
from src.messages.chat import build_chat_prompt_with_prefix
from src.tokens.tokenizer import FastTokenizer


@dataclass(frozen=True, slots=True)
class PromptFitResult:
    """Exact prompt-fit result used before chat engine calls."""

    history_messages: list[ChatMessage]
    chat_user_utt: str
    prompt: str
    prompt_tokens: int


def _copy_messages(messages: list[ChatMessage]) -> list[ChatMessage]:
    return [ChatMessage(role=msg.role, content=msg.content) for msg in messages]


def _build_prompt(
    static_prefix: str,
    runtime_text: str,
    history_messages: list[ChatMessage],
    chat_user_utt: str,
    chat_tokenizer: FastTokenizer,
) -> tuple[str, int]:
    prompt = build_chat_prompt_with_prefix(
        static_prefix,
        runtime_text,
        history_messages,
        chat_user_utt,
        chat_tokenizer,
    )
    return prompt, len(chat_tokenizer.encode_ids(prompt))


def _count_user_tokens(chat_user_utt: str, chat_tokenizer: FastTokenizer) -> int:
    return len(chat_tokenizer.encode_ids((chat_user_utt or "").strip()))


def _max_candidate_user(
    raw_chat_user_utt: str,
    chat_tokenizer: FastTokenizer,
    *,
    max_user_tokens: int | None,
) -> str:
    candidate = (raw_chat_user_utt or "").strip()
    if not candidate:
        return ""
    token_count = _count_user_tokens(candidate, chat_tokenizer)
    capped_token_count = token_count if max_user_tokens is None else min(token_count, max(1, int(max_user_tokens)))
    return _trim_raw_user(candidate, capped_token_count, chat_tokenizer)


def _trim_raw_user(
    raw_chat_user_utt: str,
    remaining_tokens: int,
    chat_tokenizer: FastTokenizer,
) -> str:
    candidate = (raw_chat_user_utt or "").strip()
    if remaining_tokens <= 0 or not candidate:
        return ""
    return chat_tokenizer.trim(candidate, max_tokens=remaining_tokens, keep="start").strip()


def _fit_user_from_raw(
    static_prefix: str,
    runtime_text: str,
    history_messages: list[ChatMessage],
    raw_chat_user_utt: str,
    chat_tokenizer: FastTokenizer,
    *,
    max_prompt_tokens: int,
    max_user_tokens: int | None,
) -> tuple[str, str, int]:
    candidate = (raw_chat_user_utt or "").strip()
    if not candidate:
        prompt, prompt_tokens = _build_prompt(
            static_prefix,
            runtime_text,
            history_messages,
            "",
            chat_tokenizer,
        )
        return "", prompt, prompt_tokens

    token_count = _count_user_tokens(candidate, chat_tokenizer)
    capped_token_count = token_count if max_user_tokens is None else min(token_count, max(1, int(max_user_tokens)))

    for remaining in range(capped_token_count, 0, -1):
        trimmed = _trim_raw_user(candidate, remaining, chat_tokenizer)
        prompt, prompt_tokens = _build_prompt(
            static_prefix,
            runtime_text,
            history_messages,
            trimmed,
            chat_tokenizer,
        )
        if prompt_tokens <= max_prompt_tokens:
            return trimmed, prompt, prompt_tokens

    raise ValueError("prompt exceeds exact context budget even after removing all history and trimming the user turn")


def fit_chat_prompt_to_budget(
    static_prefix: str,
    runtime_text: str,
    history_messages: list[ChatMessage],
    chat_user_utt: str,
    chat_tokenizer: FastTokenizer,
    *,
    max_prompt_tokens: int,
    max_user_tokens: int | None = None,
) -> PromptFitResult:
    """Fit the exact templated prompt to budget with one raw-user fit path."""
    effective_history = _copy_messages(history_messages)
    max_candidate_user = _max_candidate_user(
        chat_user_utt,
        chat_tokenizer,
        max_user_tokens=max_user_tokens,
    )
    prompt, prompt_tokens = _build_prompt(
        static_prefix,
        runtime_text,
        effective_history,
        max_candidate_user,
        chat_tokenizer,
    )

    while effective_history and prompt_tokens > max_prompt_tokens:
        effective_history = effective_history[1:]
        prompt, prompt_tokens = _build_prompt(
            static_prefix,
            runtime_text,
            effective_history,
            max_candidate_user,
            chat_tokenizer,
        )

    effective_user, prompt, prompt_tokens = _fit_user_from_raw(
        static_prefix,
        runtime_text,
        effective_history,
        chat_user_utt,
        chat_tokenizer,
        max_prompt_tokens=max_prompt_tokens,
        max_user_tokens=max_user_tokens,
    )

    if prompt_tokens > max_prompt_tokens:
        raise ValueError("prompt exceeds exact context budget before engine call")

    return PromptFitResult(
        history_messages=effective_history,
        chat_user_utt=effective_user,
        prompt=prompt,
        prompt_tokens=prompt_tokens,
    )


__all__ = ["PromptFitResult", "fit_chat_prompt_to_budget"]
