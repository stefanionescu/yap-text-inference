"""Unit tests for limits configuration derivation and env behavior."""

from __future__ import annotations

import importlib
from types import ModuleType
from src.config import limits


def _reload_limits() -> ModuleType:
    return importlib.reload(limits)


def test_context_buffer_defaults_to_25() -> None:
    reloaded = _reload_limits()
    assert reloaded.CONTEXT_BUFFER == 25


def test_context_buffer_is_env_configurable(monkeypatch) -> None:
    monkeypatch.setenv("CHAT_PROMPT_MAX_TOKENS", "10")
    monkeypatch.setenv("CHAT_HISTORY_MAX_TOKENS", "20")
    monkeypatch.setenv("USER_UTT_MAX_TOKENS", "30")
    monkeypatch.setenv("CONTEXT_BUFFER", "40")
    reloaded = _reload_limits()
    assert reloaded.CONTEXT_BUFFER == 40
    assert reloaded.CHAT_MAX_LEN == 100


def test_trimmed_history_length_is_always_derived(monkeypatch) -> None:
    monkeypatch.setenv("CHAT_HISTORY_MAX_TOKENS", "3000")
    monkeypatch.setenv("HISTORY_RETENTION_PCT", "50")
    monkeypatch.setenv("TRIMMED_HISTORY_LENGTH", "1")
    reloaded = _reload_limits()
    assert reloaded.TRIMMED_HISTORY_LENGTH == 1500


def test_legacy_history_env_var_is_ignored(monkeypatch) -> None:
    monkeypatch.delenv("CHAT_HISTORY_MAX_TOKENS", raising=False)
    monkeypatch.setenv("HISTORY_MAX_TOKENS", "7777")
    reloaded = _reload_limits()
    assert reloaded.CHAT_HISTORY_MAX_TOKENS == 3000
