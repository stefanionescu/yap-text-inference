"""Unit tests for prompt sanitization."""

from __future__ import annotations

import pytest

from src.messages.sanitize.prompt import PromptSanitizer, sanitize_prompt


def test_sanitize_prompt_none_raises() -> None:
    with pytest.raises(ValueError, match="prompt is required"):
        sanitize_prompt(None)


def test_sanitize_prompt_non_string_raises() -> None:
    with pytest.raises(ValueError, match="prompt must be a string"):
        sanitize_prompt(123)  # type: ignore[arg-type]


def test_sanitize_prompt_empty_after_strip_raises() -> None:
    with pytest.raises(ValueError, match="prompt is empty after sanitization"):
        sanitize_prompt("")


def test_sanitize_prompt_whitespace_only_raises() -> None:
    with pytest.raises(ValueError, match="prompt is empty after sanitization"):
        sanitize_prompt("   \t\n  ")


def test_sanitize_prompt_oversized_raises() -> None:
    with pytest.raises(ValueError, match="prompt too large"):
        sanitize_prompt("x" * 100, max_chars=50)


def test_sanitize_prompt_normal_text() -> None:
    assert sanitize_prompt("hello world") == "hello world"


def test_sanitize_prompt_strips_control_chars() -> None:
    result = sanitize_prompt("hello\x00world\x1f!")
    assert "\x00" not in result
    assert "\x1f" not in result
    assert "hello" in result


def test_sanitize_prompt_strips_bidi_chars() -> None:
    result = sanitize_prompt("hello\u202aworld")
    assert "\u202a" not in result


def test_sanitize_prompt_strips_escaped_quotes() -> None:
    result = sanitize_prompt('say \\"hello\\"')
    assert '\\"' not in result


def test_prompt_sanitizer_max_chars() -> None:
    sanitizer = PromptSanitizer(max_chars=10)
    assert sanitizer.sanitize("short") == "short"


def test_prompt_sanitizer_callable_interface() -> None:
    sanitizer = PromptSanitizer()
    assert sanitizer("hello") == "hello"
