"""Tokenizer-related state dataclasses."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class TokenizerSource:
    """Metadata about where to load a tokenizer from."""

    original_path: str
    is_local: bool
    tokenizer_json_path: str | None
    awq_metadata_model: str | None


@dataclass(slots=True)
class TransformersTarget:
    """Target for loading a transformers tokenizer."""

    identifier: str
    local_only: bool


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
    "TokenizerSource",
    "TransformersTarget",
    "TokenizerValidationResult",
]
