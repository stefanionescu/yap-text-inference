"""Public API for lightweight utility helpers."""

from .env import env_flag
from .sanitize import sanitize_prompt, sanitize_stream_text, StreamingSanitizer
from .rate_limit import RateLimitError, SlidingWindowRateLimiter
from .time import SessionTimestamp, get_time_classification, format_session_timestamp
from .io import read_json_file
from .language import is_mostly_english


# Lazy re-exports from helpers for backward compatibility
def __getattr__(name):
    """Lazy import input helpers to avoid circular imports."""
    if name in (
        "normalize_gender",
        "is_gender_empty_or_null",
        "normalize_personality",
        "is_personality_empty_or_null",
    ):
        from src.helpers.input import (
            normalize_gender,
            is_gender_empty_or_null,
            normalize_personality,
            is_personality_empty_or_null,
        )
        _input_funcs = {
            "normalize_gender": normalize_gender,
            "is_gender_empty_or_null": is_gender_empty_or_null,
            "normalize_personality": normalize_personality,
            "is_personality_empty_or_null": is_personality_empty_or_null,
        }
        return _input_funcs[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "env_flag",
    "sanitize_prompt",
    "sanitize_stream_text",
    "StreamingSanitizer",
    "RateLimitError",
    "SlidingWindowRateLimiter",
    "SessionTimestamp",
    "get_time_classification",
    "format_session_timestamp",
    "read_json_file",
    "is_mostly_english",
    # Re-exported from helpers for backward compatibility
    "normalize_gender",
    "is_gender_empty_or_null",
    "normalize_personality",
    "is_personality_empty_or_null",
]
