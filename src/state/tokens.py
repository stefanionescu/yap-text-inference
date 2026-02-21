"""Tokenizer-related state dataclasses."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class TokenizerValidationResult:
    """Result of tokenizer validation."""

    valid: bool
    error_message: str | None
    model_path: str
    has_tokenizer_json: bool
    has_tokenizer_config: bool
    is_remote: bool = False


__all__ = [
    "TokenizerValidationResult",
]
