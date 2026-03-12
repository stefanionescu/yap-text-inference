"""Exact chat prompt budgeting helpers."""

from __future__ import annotations

from dataclasses import dataclass
from src.state.session import ChatMessage
from src.tokens.tokenizer import FastTokenizer
from src.execution.chat.template_builder import build_chat_prompt_with_prefix
from src.helpers.chat_history import group_chat_turns, copy_chat_messages, flatten_chat_turns


@dataclass(frozen=True, slots=True)
class PromptFitResult:
    """Exact prompt-fit result used before chat engine calls."""

    history_messages: list[ChatMessage]
    chat_user_utt: str
    prompt: str
    prompt_tokens: int


def _build_prompt(
    static_prefix: str,
    runtime_text: str,
    history_turns: list[list[ChatMessage]],
    chat_user_utt: str,
    chat_tokenizer: FastTokenizer,
) -> tuple[str, int]:
    prompt = build_chat_prompt_with_prefix(
        static_prefix,
        runtime_text,
        flatten_chat_turns(history_turns),
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
    history_turns: list[list[ChatMessage]],
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
            history_turns,
            "",
            chat_tokenizer,
        )
        return "", prompt, prompt_tokens

    token_count = _count_user_tokens(candidate, chat_tokenizer)
    capped_token_count = token_count if max_user_tokens is None else min(token_count, max(1, int(max_user_tokens)))
    lo = 1
    hi = capped_token_count
    best_fit: tuple[str, str, int] | None = None
    while lo <= hi:
        remaining = (lo + hi) // 2
        trimmed = _trim_raw_user(candidate, remaining, chat_tokenizer)
        prompt, prompt_tokens = _build_prompt(
            static_prefix,
            runtime_text,
            history_turns,
            trimmed,
            chat_tokenizer,
        )
        if prompt_tokens <= max_prompt_tokens:
            best_fit = (trimmed, prompt, prompt_tokens)
            lo = remaining + 1
        else:
            hi = remaining - 1

    if best_fit is not None:
        return best_fit

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
    effective_history = group_chat_turns(copy_chat_messages(history_messages))
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
        history_messages=flatten_chat_turns(effective_history),
        chat_user_utt=effective_user,
        prompt=prompt,
        prompt_tokens=prompt_tokens,
    )


__all__ = ["PromptFitResult", "fit_chat_prompt_to_budget"]
