"""Unit tests for exact chat prompt budgeting."""

from __future__ import annotations

from src.execution.chat.prompt_budget import fit_chat_prompt_to_budget
from tests.support.messages.unit import CHAT_MESSAGES, ASSISTANT_FIRST_MESSAGES
from tests.support.helpers.tokenizer import use_local_tokenizers, use_punctuation_aware_tokenizers


def test_fit_chat_prompt_to_budget_drops_oldest_history_until_prompt_fits() -> None:
    with use_local_tokenizers() as tokenizer:
        messages = CHAT_MESSAGES

        fit = fit_chat_prompt_to_budget(
            "",
            "",
            messages,
            "hello",
            tokenizer,
            max_prompt_tokens=70,
        )

        assert fit.history_messages == CHAT_MESSAGES[-4:]
        assert fit.chat_user_utt == "hello"
        assert fit.prompt_tokens <= 70


def test_fit_chat_prompt_to_budget_drops_whole_turns_not_partial_messages() -> None:
    with use_local_tokenizers() as tokenizer:
        fit = fit_chat_prompt_to_budget(
            "",
            "",
            CHAT_MESSAGES[:4],
            "hello",
            tokenizer,
            max_prompt_tokens=40,
        )

        assert [(msg.role, msg.content) for msg in fit.history_messages] == [
            (
                "user",
                "i need a quiet hotel near the river and my budget is moderate",
            ),
            (
                "assistant",
                "a quiet riverside hotel in lisbon can work and i can suggest neighborhoods",
            ),
        ]


def test_fit_chat_prompt_to_budget_preserves_assistant_first_history_order_when_it_fits() -> None:
    with use_local_tokenizers() as tokenizer:
        fit = fit_chat_prompt_to_budget(
            "",
            "",
            ASSISTANT_FIRST_MESSAGES[:4],
            "also remind me to pack a rain jacket and travel adapter",
            tokenizer,
            max_prompt_tokens=200,
        )

        assert fit.history_messages == ASSISTANT_FIRST_MESSAGES[:4]
        assert fit.prompt.startswith(
            "<|im_start|>assistant\n"
            "hello can you help me plan a trip to lisbon next week\n\n"
            "sure tell me your budget and hotel area preference"
        )
        assert "<|im_start|>user\ni need a quiet hotel near the river and my budget is moderate" in fit.prompt


def test_fit_chat_prompt_to_budget_drops_leading_assistant_group_as_a_unit() -> None:
    with use_local_tokenizers() as tokenizer:
        fit = fit_chat_prompt_to_budget(
            "",
            "",
            ASSISTANT_FIRST_MESSAGES,
            "hello",
            tokenizer,
            max_prompt_tokens=60,
        )

        assert fit.history_messages == ASSISTANT_FIRST_MESSAGES[-2:]
        assert fit.prompt_tokens <= 60


def test_fit_chat_prompt_to_budget_trims_user_after_history_is_exhausted() -> None:
    with use_local_tokenizers() as tokenizer:
        fit = fit_chat_prompt_to_budget(
            "",
            "",
            [],
            "hello can you help me plan a trip to lisbon next week",
            tokenizer,
            max_prompt_tokens=5,
        )

        assert fit.history_messages == []
        assert fit.chat_user_utt == "hello can"
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
            "hello can you help me plan a trip to lisbon next week",
            tokenizer,
            max_prompt_tokens=20,
            max_user_tokens=4,
        )

        assert fit.chat_user_utt == "hello can you help"
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


def test_fit_chat_prompt_to_budget_caps_punctuation_heavy_user_with_richer_tokenizer() -> None:
    with use_punctuation_aware_tokenizers() as tokenizer:
        fit = fit_chat_prompt_to_budget(
            "",
            "",
            [],
            "remind me: passport, charger, adapters!",
            tokenizer,
            max_prompt_tokens=100,
            max_user_tokens=4,
        )

        assert fit.history_messages == []
        assert fit.chat_user_utt == "remind me: passport"
        assert fit.prompt_tokens <= 100
