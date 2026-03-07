"""Unit tests for screen-prefix stripping and budget helpers."""

from __future__ import annotations

from src.state.session import SessionState
from src.tokens import prefix as token_prefix
from tests.support.helpers.tokenizer import use_local_tokenizers


def test_strip_screen_prefix_handles_case_insensitive_match() -> None:
    stripped = token_prefix.strip_screen_prefix("check screen: hello", "CHECK SCREEN:", None)
    untouched = token_prefix.strip_screen_prefix("hello there", "CHECK SCREEN:", None)

    assert stripped == "hello"
    assert untouched == "hello there"


def test_get_effective_user_utt_max_tokens_uses_state_and_clamps() -> None:
    state = SessionState(meta={})
    state.check_screen_prefix_tokens = 9
    state.screen_checked_prefix_tokens = 2

    assert (
        token_prefix.get_effective_user_utt_max_tokens(
            state,
            for_followup=False,
            user_utt_max_tokens=5,
        )
        == 1
    )
    assert (
        token_prefix.get_effective_user_utt_max_tokens(
            state,
            for_followup=True,
            user_utt_max_tokens=5,
        )
        == 3
    )


def test_get_effective_user_utt_max_tokens_without_state_uses_defaults() -> None:
    with use_local_tokenizers():
        start_expected = max(1, 8 - token_prefix.count_prefix_tokens("check", deploy_chat=True))
        followup_expected = max(1, 8 - token_prefix.count_prefix_tokens("screen", deploy_chat=True))

        assert (
            token_prefix.get_effective_user_utt_max_tokens(
                None,
                for_followup=False,
                user_utt_max_tokens=8,
                default_check_screen_prefix="check",
                default_screen_checked_prefix="screen",
                deploy_chat=True,
            )
            == start_expected
        )
        assert (
            token_prefix.get_effective_user_utt_max_tokens(
                None,
                for_followup=True,
                user_utt_max_tokens=8,
                default_check_screen_prefix="check",
                default_screen_checked_prefix="screen",
                deploy_chat=True,
            )
            == followup_expected
        )


def test_count_prefix_tokens_returns_zero_when_chat_is_disabled() -> None:
    assert token_prefix.count_prefix_tokens("check", deploy_chat=False) == 0
