"""Unit tests for exact chat prompt budgeting."""

from __future__ import annotations

from src.state.session import ChatMessage
from tests.support.helpers.tokenizer import use_local_tokenizers
from src.execution.chat.prompt_budget import fit_chat_prompt_to_budget


def test_fit_chat_prompt_to_budget_drops_oldest_history_until_prompt_fits() -> None:
    with use_local_tokenizers() as tokenizer:
        messages = [
            ChatMessage(role="user", content="u1"),
            ChatMessage(role="assistant", content="a1"),
            ChatMessage(role="user", content="u2"),
            ChatMessage(role="assistant", content="a2"),
            ChatMessage(role="user", content="u3"),
            ChatMessage(role="assistant", content="a3"),
        ]

        fit = fit_chat_prompt_to_budget(
            "",
            "",
            messages,
            "hello",
            tokenizer,
            max_prompt_tokens=11,
        )

        assert [(msg.role, msg.content) for msg in fit.history_messages] == [("user", "u3"), ("assistant", "a3")]
        assert fit.chat_user_utt == "hello"
        assert fit.prompt_tokens <= 11


def test_fit_chat_prompt_to_budget_trims_user_after_history_is_exhausted() -> None:
    with use_local_tokenizers() as tokenizer:
        fit = fit_chat_prompt_to_budget(
            "",
            "",
            [],
            "one two three four five six",
            tokenizer,
            max_prompt_tokens=5,
        )

        assert fit.history_messages == []
        assert fit.chat_user_utt == "one two"
        assert fit.prompt_tokens <= 5


def test_fit_chat_prompt_to_budget_raises_when_system_prompt_alone_exceeds_budget() -> None:
    with use_local_tokenizers() as tokenizer:
        try:
            fit_chat_prompt_to_budget(
                "alpha bravo charlie delta",
                "",
                [],
                "",
                tokenizer,
                max_prompt_tokens=1,
            )
        except ValueError as exc:
            assert "prompt exceeds exact context budget" in str(exc)
        else:
            raise AssertionError("expected ValueError")


def test_fit_chat_prompt_to_budget_applies_chat_user_cap_before_prompt_fit() -> None:
    with use_local_tokenizers() as tokenizer:
        fit = fit_chat_prompt_to_budget(
            "",
            "",
            [],
            "one two three four five six",
            tokenizer,
            max_prompt_tokens=20,
            max_user_tokens=4,
        )

        assert fit.chat_user_utt == "one two three four"
        assert fit.prompt_tokens <= 20


def test_fit_chat_prompt_to_budget_rejects_non_empty_user_that_cannot_fit() -> None:
    with use_local_tokenizers() as tokenizer:
        try:
            fit_chat_prompt_to_budget(
                "alpha bravo charlie delta",
                "",
                [],
                "echo",
                tokenizer,
                max_prompt_tokens=1,
            )
        except ValueError as exc:
            assert "prompt exceeds exact context budget" in str(exc)
        else:
            raise AssertionError("expected ValueError")
