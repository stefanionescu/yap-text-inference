"""Unit tests for limits configuration derivation and env behavior."""

from __future__ import annotations

from src.helpers.resolvers import resolve_limit_values


def test_context_buffer_defaults_to_25() -> None:
    resolved = resolve_limit_values(env={})
    assert resolved["CONTEXT_BUFFER"] == 25


def test_context_buffer_is_env_configurable() -> None:
    resolved = resolve_limit_values(
        env={
            "CHAT_PROMPT_MAX_TOKENS": "10",
            "CHAT_HISTORY_MAX_TOKENS": "20",
            "USER_UTT_MAX_TOKENS": "30",
            "CONTEXT_BUFFER": "40",
        }
    )
    assert resolved["CONTEXT_BUFFER"] == 40
    assert resolved["CHAT_MAX_LEN"] == 100


def test_trimmed_history_length_is_always_derived() -> None:
    resolved = resolve_limit_values(
        env={
            "CHAT_HISTORY_MAX_TOKENS": "3000",
            "HISTORY_RETENTION_PCT": "50",
            "TRIMMED_HISTORY_LENGTH": "1",
        }
    )
    assert resolved["TRIMMED_HISTORY_LENGTH"] == 1500


def test_legacy_history_env_var_is_ignored() -> None:
    resolved = resolve_limit_values(env={"HISTORY_MAX_TOKENS": "7777"})
    assert resolved["CHAT_HISTORY_MAX_TOKENS"] == 3000
