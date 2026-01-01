"""Tokenizer validation for model directories.

This module provides validation to ensure tokenizers exist locally
before the server starts. This prevents runtime failures and ensures
we never silently fall back to fetching tokenizers from HuggingFace.

Validation checks for:
1. tokenizer.json (fast tokenizers library format)
2. tokenizer_config.json (transformers AutoTokenizer format)

At least one of these must exist for the model to be usable.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(slots=True)
class TokenizerValidationResult:
    """Result of tokenizer validation.
    
    Attributes:
        valid: True if a tokenizer was found locally.
        error_message: Human-readable error if validation failed.
        model_path: The path that was validated.
        has_tokenizer_json: Whether tokenizer.json exists.
        has_tokenizer_config: Whether tokenizer_config.json exists.
    """
    valid: bool
    error_message: str | None
    model_path: str
    has_tokenizer_json: bool
    has_tokenizer_config: bool


def validate_tokenizer_exists(model_path: str) -> TokenizerValidationResult:
    """Validate that a tokenizer exists locally for the given model.
    
    Checks for tokenizer.json (tokenizers library) or tokenizer_config.json
    (transformers AutoTokenizer). At least one must exist.
    
    Args:
        model_path: Local directory path to the model.
        
    Returns:
        TokenizerValidationResult with validation status and details.
    """
    if not model_path:
        return TokenizerValidationResult(
            valid=False,
            error_message="Model path is empty",
            model_path=model_path,
            has_tokenizer_json=False,
            has_tokenizer_config=False,
        )

    if not os.path.isdir(model_path):
        return TokenizerValidationResult(
            valid=False,
            error_message=(
                f"Model directory does not exist: {model_path}\n"
                "Ensure the model has been downloaded or the path is correct."
            ),
            model_path=model_path,
            has_tokenizer_json=False,
            has_tokenizer_config=False,
        )

    tokenizer_json = os.path.join(model_path, "tokenizer.json")
    tokenizer_config = os.path.join(model_path, "tokenizer_config.json")

    has_tokenizer_json = os.path.isfile(tokenizer_json)
    has_tokenizer_config = os.path.isfile(tokenizer_config)

    if has_tokenizer_json or has_tokenizer_config:
        return TokenizerValidationResult(
            valid=True,
            error_message=None,
            model_path=model_path,
            has_tokenizer_json=has_tokenizer_json,
            has_tokenizer_config=has_tokenizer_config,
        )

    return TokenizerValidationResult(
        valid=False,
        error_message=(
            f"Tokenizer files not found in model directory: {model_path}\n"
            "Expected at least one of:\n"
            f"  - {tokenizer_json}\n"
            f"  - {tokenizer_config}\n"
            "\n"
            "If using a pre-quantized model from HuggingFace:\n"
            "  Ensure the download completed successfully and includes tokenizer files.\n"
            "\n"
            "If using a locally quantized model:\n"
            "  Re-run quantization to regenerate the tokenizer files."
        ),
        model_path=model_path,
        has_tokenizer_json=False,
        has_tokenizer_config=False,
    )


def validate_model_tokenizer(
    model_path: str | None,
    model_name: str,
    deploy_enabled: bool,
) -> str | None:
    """Validate tokenizer for a model if deployment is enabled.
    
    This is a convenience wrapper for startup validation. Returns an
    error message if validation fails, None if successful or skipped.
    
    Args:
        model_path: Path to the model directory (may be None if not configured).
        model_name: Human-readable name for error messages (e.g., "CHAT_MODEL").
        deploy_enabled: Whether this model is configured for deployment.
        
    Returns:
        Error message string if validation failed, None otherwise.
    """
    if not deploy_enabled:
        return None

    if not model_path:
        # Model path validation is handled elsewhere (validate_env checks this)
        return None

    result = validate_tokenizer_exists(model_path)
    if result.valid:
        return None

    return f"{model_name} tokenizer validation failed:\n{result.error_message}"


__all__ = [
    "TokenizerValidationResult",
    "validate_tokenizer_exists",
    "validate_model_tokenizer",
]

